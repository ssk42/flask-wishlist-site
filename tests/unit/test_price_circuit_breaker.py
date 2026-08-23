"""Tests for the price-fetch backoff circuit breaker.

Specs: AUTO-PRC-011 .. AUTO-PRC-016 (docs/intent/boundary-autonomous/
price-processing/price-processing-specs.md). These tests are written
tests-first and FAIL until the Item columns, failure accounting, sweep
exclusion, link-change listener, and env overrides exist.
"""
import datetime
from unittest.mock import patch
import pytest
from models import db, User, Item


@pytest.fixture
def item_owner(app):
    """Create a user who owns items."""
    with app.app_context():
        user = User(name="Owner", email="cb-owner@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


def _now_naive():
    """SQLite round-trips naive datetimes; compare on naive clocks."""
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def _make_item(item_owner):
    return Item(
        description="Circuit Breaker Item",
        user_id=item_owner,
        price=10.00,
        link="https://example.com/doomed",
        price_updated_at=None,
    )


def _failed_sweep(app):
    """Run update_stale_prices with every URL fetch failing (URL absent
    from the results dict -> failure path)."""
    from services.price_service import update_stale_prices

    def fail(coro):
        coro.close()
        return {}
    with patch('asyncio.run', side_effect=fail):
        return update_stale_prices(app, db, Item)


def _fresh_item(item_id):
    """Read an item through a fresh SELECT, bypassing the identity map.
    update_stale_prices runs in its own app context / session, so cached
    instances would show stale state."""
    db.session.expire_all()  # discard state committed by other sessions
    return db.session.execute(
        db.select(Item).where(Item.id == item_id)
    ).scalar_one()


def _successful_sweep(app, price=19.99):
    """Run update_stale_prices with the fetch returning a price."""
    from services.price_service import update_stale_prices

    def succeed(coro):
        coro.close()
        return {item.link: price for item in db.session.query(Item).all()}
    with patch('asyncio.run', side_effect=succeed):
        return update_stale_prices(app, db, Item)


def _make_eligible(item):
    """Force an item back into the sweep's selection window regardless of
    prior state: stale timestamp + already-expired backoff."""
    item.price_updated_at = _now_naive() - datetime.timedelta(days=10)
    item.price_backoff_until = _now_naive() - datetime.timedelta(seconds=1)
    item.price_fail_streak = item.price_fail_streak  # keep accumulated streak
    db.session.commit()


class TestFailureProgression:
    """Consecutive automatic failures escalate the backoff schedule."""

    def test_first_two_failures_keep_daily_pacing_no_backoff(self, app, item_owner):
        # @spec AUTO-PRC-011
        """Streaks 1 and 2 stay below the default floor (3): no
        price_backoff_until is set, so ~daily retry pacing is preserved."""
        with app.app_context():
            item = _make_item(item_owner)
            db.session.add(item)
            db.session.commit()

            for expected_streak in (1, 2):
                _make_eligible(item)
                stats = _failed_sweep(app)

                fresh = _fresh_item(item.id)
                assert fresh.price_fail_streak == expected_streak
                assert fresh.price_backoff_until is None, (
                    f"streak {expected_streak} < floor: no backoff expected"
                )
            assert stats['errors'] >= 1

    def test_backoff_doubles_then_caps_at_max_days(self, app, item_owner):
        # @spec AUTO-PRC-011
        """Full progression at defaults: streak 3 -> +2d, 4 -> +4d,
        5 -> +8d, 6 -> +16d, >=7 -> +30d cap. Exact deltas asserted with a
        small tolerance for clock drift during the run."""
        schedule = [(3, 2), (4, 4), (5, 8), (6, 16), (7, 30), (8, 30)]
        tolerance = datetime.timedelta(minutes=5)

        with app.app_context():
            item = _make_item(item_owner)
            db.session.add(item)
            db.session.commit()

            # Walk the streak up to the floor first.
            for _ in range(2):
                _make_eligible(item)
                _failed_sweep(app)
            assert _fresh_item(item.id).price_fail_streak == 2

            for expected_streak, expected_days in schedule:
                _make_eligible(item)
                before = _now_naive()
                _failed_sweep(app)

                fresh = _fresh_item(item.id)
                assert fresh.price_fail_streak == expected_streak
                assert fresh.price_backoff_until is not None
                delta = fresh.price_backoff_until - before
                lower = datetime.timedelta(days=expected_days) - tolerance
                upper = datetime.timedelta(days=expected_days) + tolerance
                assert lower <= delta <= upper, (
                    f"streak {expected_streak}: expected ~+{expected_days}d "
                    f"backoff, got {delta}"
                )


class TestSuccessResets:
    """Any successful fetch clears both circuit-breaker fields."""

    def test_successful_batch_fetch_resets_streak_and_backoff(self, app, item_owner):
        # @spec AUTO-PRC-012
        """A success on the batch path resets streak to 0 and backoff to NULL."""
        with app.app_context():
            item = _make_item(item_owner)
            db.session.add(item)
            db.session.commit()

            # Build up backed-off state via two failures + manual seeding.
            for _ in range(2):
                _make_eligible(item)
                _failed_sweep(app)
            seeded = _fresh_item(item.id)
            seeded.price_fail_streak = 5
            seeded.price_backoff_until = _now_naive() + datetime.timedelta(days=8)
            db.session.commit()

            _make_eligible(seeded)
            stats = _successful_sweep(app)

            fresh = _fresh_item(item.id)
            assert stats['prices_updated'] == 1
            assert fresh.price_fail_streak == 0
            assert fresh.price_backoff_until is None

    def test_refresh_success_resets_streak_and_backoff(self, app, item_owner):
        # @spec AUTO-PRC-012
        """A successful refresh_item_price resets both fields."""
        from services.price_service import refresh_item_price

        with patch('services.price_service.fetch_price') as mock_fetch:
            mock_fetch.return_value = 39.99

            with app.app_context():
                item = _make_item(item_owner)
                db.session.add(item)
                db.session.commit()

                fresh = _fresh_item(item.id)
                fresh.price_fail_streak = 6
                fresh.price_backoff_until = _now_naive() + datetime.timedelta(days=30)
                db.session.commit()

                success, new_price, _message = refresh_item_price(fresh, db)

                assert success is True
                assert new_price == 39.99
                final = _fresh_item(item.id)
                assert final.price_fail_streak == 0
                assert final.price_backoff_until is None


class TestSweepExclusion:
    """The sweep skips future-backoff items and re-includes them on expiry."""

    def test_future_backoff_excluded_from_sweep(self, app, item_owner):
        # @spec AUTO-PRC-013
        """A stale item with price_backoff_until in the future is not selected."""
        from services.price_service import get_items_needing_update

        with app.app_context():
            item = _make_item(item_owner)
            db.session.add(item)
            db.session.commit()

            fresh = _fresh_item(item.id)
            fresh.price_updated_at = _now_naive() - datetime.timedelta(days=10)
            fresh.price_backoff_until = _now_naive() + datetime.timedelta(days=2)
            db.session.commit()

            cutoff = _now_naive() - datetime.timedelta(days=7)
            selected = get_items_needing_update(Item, db, cutoff)
            assert item.id not in [i.id for i in selected]

            stats = _failed_sweep(app)
            assert stats['items_processed'] == 0

    def test_expired_backoff_reincluded_in_sweep(self, app, item_owner):
        # @spec AUTO-PRC-013
        """Once price_backoff_until passes, the item becomes eligible again
        automatically — self-healing, no manual intervention."""
        from services.price_service import get_items_needing_update

        with app.app_context():
            item = _make_item(item_owner)
            db.session.add(item)
            db.session.commit()

            fresh = _fresh_item(item.id)
            fresh.price_updated_at = _now_naive() - datetime.timedelta(days=10)
            fresh.price_backoff_until = _now_naive() - datetime.timedelta(seconds=1)
            fresh.price_fail_streak = 3
            db.session.commit()

            cutoff = _now_naive() - datetime.timedelta(days=7)
            selected = get_items_needing_update(Item, db, cutoff)
            assert item.id in [i.id for i in selected]
            # Failure path: the attempt happened (counted as an error), which
            # proves the expired-backoff item was swept again.
            stats = _failed_sweep(app)
            assert stats['errors'] == 1
            # The retry attempt also advances failure accounting.
            reswept = _fresh_item(item.id)
            assert reswept.price_fail_streak == 4


class TestLinkChangeReset:
    """A link change through ANY write path resets both fields."""

    def test_plain_link_mutation_and_commit_resets_state(self, app, item_owner):
        # @spec AUTO-PRC-014
        """The before_flush choke point catches a bare attribute mutation +
        commit — no blueprint or service code involved — proving arbitrary
        write paths reset the circuit breaker."""
        with app.app_context():
            item = _make_item(item_owner)
            db.session.add(item)
            db.session.commit()

            fresh = _fresh_item(item.id)
            fresh.price_fail_streak = 4
            fresh.price_backoff_until = _now_naive() + datetime.timedelta(days=4)
            db.session.commit()

            # Arbitrary write path: plain mutation of link + commit.
            fresh.link = "https://example.com/fixed-page"
            db.session.commit()

            final = _fresh_item(item.id)
            assert final.price_fail_streak == 0
            assert final.price_backoff_until is None


class TestManualRefreshBypass:
    """Manual refresh ignores backoff entirely."""

    def test_manual_refresh_attempts_fetch_while_backed_off(self, app, item_owner):
        # @spec AUTO-PRC-015
        """refresh_item_price still calls the underlying fetcher while the
        item is backed off, and resets both fields on success."""
        from services.price_service import refresh_item_price

        with patch('services.price_service.fetch_price') as mock_fetch:
            mock_fetch.return_value = 12.34

            with app.app_context():
                item = _make_item(item_owner)
                db.session.add(item)
                db.session.commit()

                fresh = _fresh_item(item.id)
                fresh.price_fail_streak = 5
                # Backed off for another week.
                fresh.price_backoff_until = _now_naive() + datetime.timedelta(days=7)
                db.session.commit()

                success, new_price, _message = refresh_item_price(fresh, db)

                mock_fetch.assert_called_once_with("https://example.com/doomed")
                assert success is True
                assert new_price == 12.34
                final = _fresh_item(item.id)
                assert final.price_fail_streak == 0
                assert final.price_backoff_until is None


class TestEnvOverrides:
    """PRICE_BACKOFF_FLOOR / PRICE_BACKOFF_MAX_DAYS tune the breaker."""

    def test_floor_env_lowers_threshold(self, app, item_owner, monkeypatch):
        # @spec AUTO-PRC-016
        """With PRICE_BACKOFF_FLOOR=2, the SECOND consecutive failure
        already sets a +2d backoff (streak 2 == floor)."""
        monkeypatch.setenv("PRICE_BACKOFF_FLOOR", "2")

        with app.app_context():
            item = _make_item(item_owner)
            db.session.add(item)
            db.session.commit()

            _make_eligible(item)
            _failed_sweep(app)
            after_first = _fresh_item(item.id)
            assert after_first.price_fail_streak == 1
            assert after_first.price_backoff_until is None

            _make_eligible(after_first)
            before = _now_naive()
            _failed_sweep(app)

            after_second = _fresh_item(item.id)
            assert after_second.price_fail_streak == 2
            delta = after_second.price_backoff_until - before
            assert datetime.timedelta(days=1) <= delta <= datetime.timedelta(days=2, minutes=5)

    def test_floor_env_raises_threshold(self, app, item_owner, monkeypatch):
        # @spec AUTO-PRC-016
        """With PRICE_BACKOFF_FLOOR=5, three consecutive failures still do
        not trigger a backoff."""
        monkeypatch.setenv("PRICE_BACKOFF_FLOOR", "5")

        with app.app_context():
            item = _make_item(item_owner)
            db.session.add(item)
            db.session.commit()

            for expected in (1, 2, 3):
                _make_eligible(item)
                _failed_sweep(app)
                fresh = _fresh_item(item.id)
                assert fresh.price_fail_streak == expected
                assert fresh.price_backoff_until is None

    def test_max_days_env_caps_backoff(self, app, item_owner, monkeypatch):
        # @spec AUTO-PRC-016
        """With PRICE_BACKOFF_MAX_DAYS=4, a deep-streak backoff caps at
        +4 days instead of the default 30."""
        monkeypatch.setenv("PRICE_BACKOFF_FLOOR", "3")
        monkeypatch.setenv("PRICE_BACKOFF_MAX_DAYS", "4")

        with app.app_context():
            item = _make_item(item_owner)
            db.session.add(item)
            db.session.commit()

            # Seed deep streak so one more failure lands far past the cap.
            item.price_fail_streak = 9
            _make_eligible(item)
            before = _now_naive()
            _failed_sweep(app)

            fresh = _fresh_item(item.id)
            assert fresh.price_fail_streak == 10
            delta = fresh.price_backoff_until - before
            tolerance = datetime.timedelta(minutes=5)
            assert datetime.timedelta(days=4) - tolerance <= delta <= datetime.timedelta(days=4) + tolerance

    def test_defaults_are_floor_3_max_30(self, app, item_owner, monkeypatch):
        # @spec AUTO-PRC-016
        """Without any env vars set: floor 3 (first backoff at streak 3,
        +2d) and max 30 days (deep streaks capped at +30d)."""
        monkeypatch.delenv("PRICE_BACKOFF_FLOOR", raising=False)
        monkeypatch.delenv("PRICE_BACKOFF_MAX_DAYS", raising=False)

        with app.app_context():
            item = _make_item(item_owner)
            db.session.add(item)
            db.session.commit()

            for _ in range(2):
                _make_eligible(item)
                _failed_sweep(app)
            assert _fresh_item(item.id).price_backoff_until is None

            _make_eligible(item)
            before = _now_naive()
            _failed_sweep(app)
            at_floor = _fresh_item(item.id)
            assert at_floor.price_fail_streak == 3
            delta = at_floor.price_backoff_until - before
            assert datetime.timedelta(days=1) <= delta <= datetime.timedelta(days=2, minutes=5)

            # Deep streak caps at the default 30 days.
            at_floor.price_fail_streak = 20
            _make_eligible(at_floor)
            before_cap = _now_naive()
            _failed_sweep(app)

            capped = _fresh_item(item.id)
            delta_cap = capped.price_backoff_until - before_cap
            tolerance = datetime.timedelta(minutes=5)
            assert datetime.timedelta(days=30) - tolerance <= delta_cap <= datetime.timedelta(days=30) + tolerance
