"""Tests for automatic archiving of gifts requested more than 10 months ago."""
import datetime
from unittest.mock import MagicMock, patch

from dateutil.relativedelta import relativedelta

from models import db, Event, Item, Notification
from services.item_service import archive_stale_items

NOW = datetime.datetime(2026, 10, 29, 12, 0, tzinfo=datetime.timezone.utc)


def _make_item(app, description, owner_id, age_months, event_id=None):
    with app.app_context():
        item = Item(description=description, user_id=owner_id, event_id=event_id)
        db.session.add(item)
        db.session.commit()
        item.created_at = NOW - relativedelta(months=age_months)
        db.session.commit()
        return item.id


def _make_event(app, name, date, created_by_id):
    with app.app_context():
        event = Event(name=name, date=date, created_by_id=created_by_id)
        db.session.add(event)
        db.session.commit()
        return event.id


def _archived_at(app, item_id):
    with app.app_context():
        return db.session.get(Item, item_id).archived_at


class TestArchiveStaleItems:
    def test_archives_item_older_than_ten_months(self, app, user):
        # @spec OWN-ITEM-019
        item_id = _make_item(app, "Last year's idea", user, age_months=11)

        with app.app_context():
            result = archive_stale_items(now=NOW)

        assert result["archived_count"] == 1
        assert _archived_at(app, item_id) is not None

    def test_keeps_item_younger_than_ten_months(self, app, user):
        # @spec OWN-ITEM-019
        item_id = _make_item(app, "Recent idea", user, age_months=9)

        with app.app_context():
            result = archive_stale_items(now=NOW)

        assert result["archived_count"] == 0
        assert _archived_at(app, item_id) is None

    def test_already_archived_item_untouched(self, app, user):
        # @spec OWN-ITEM-019
        item_id = _make_item(app, "Archived long ago", user, age_months=14)
        original = datetime.datetime(2026, 1, 15, tzinfo=datetime.timezone.utc)
        with app.app_context():
            item = db.session.get(Item, item_id)
            item.archived_at = original
            db.session.commit()

        with app.app_context():
            result = archive_stale_items(now=NOW)

        assert result["archived_count"] == 0
        # SQLite round-trips datetimes as naive; the stored instant is unchanged.
        assert _archived_at(app, item_id) == original.replace(tzinfo=None)

    def test_item_for_future_event_is_exempt(self, app, user):
        # @spec OWN-ITEM-019
        event_id = _make_event(app, "Next Christmas", datetime.date(2026, 12, 25), user)
        item_id = _make_item(app, "Early request", user, age_months=11, event_id=event_id)

        with app.app_context():
            result = archive_stale_items(now=NOW)

        assert result["archived_count"] == 0
        assert _archived_at(app, item_id) is None

    def test_item_for_past_event_is_archived(self, app, user):
        # @spec OWN-ITEM-019
        event_id = _make_event(app, "Last Christmas", datetime.date(2025, 12, 25), user)
        item_id = _make_item(app, "Stale request", user, age_months=11, event_id=event_id)

        with app.app_context():
            result = archive_stale_items(now=NOW)

        assert result["archived_count"] == 1
        assert _archived_at(app, item_id) is not None

    def test_owner_gets_one_summary_notification(self, app, user, other_user):
        # @spec OWN-ITEM-020
        _make_item(app, "Old one", user, age_months=12)
        _make_item(app, "Old two", user, age_months=13)
        _make_item(app, "Fresh one", other_user, age_months=2)

        with app.app_context():
            archive_stale_items(now=NOW)
            notes = Notification.query.filter_by(user_id=user).all()
            assert len(notes) == 1
            assert "2" in notes[0].message
            assert "Archived" in notes[0].link
            assert Notification.query.filter_by(user_id=other_user).count() == 0

    def test_second_run_is_a_no_op(self, app, user):
        # @spec OWN-ITEM-019
        _make_item(app, "Old one", user, age_months=12)

        with app.app_context():
            first = archive_stale_items(now=NOW)
            second = archive_stale_items(now=NOW)

        assert first["archived_count"] == 1
        assert second["archived_count"] == 0


class TestArchiveBeatSchedule:
    def test_beat_dispatches_daily_archive_task(self):
        # @spec AUTO-TSK-012
        from celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "archive-stale-items" in schedule
        entry = schedule["archive-stale-items"]
        assert entry["task"] == "services.celery_tasks.archive_stale_items_async"
        assert entry["schedule"].hour == {3}


class TestArchiveTaskWrapper:
    def test_task_calls_sweep_and_returns_result(self):
        # @spec AUTO-TSK-007, AUTO-TSK-009, AUTO-TSK-012
        from services.celery_tasks import archive_stale_items_async

        with patch("app.create_app") as mock_create, \
             patch("services.item_service.archive_stale_items",
                   return_value={"archived_count": 3, "owner_count": 2}) as mock_sweep:
            mock_create.return_value = MagicMock()
            result = archive_stale_items_async.run()

        mock_sweep.assert_called_once()
        assert result["archived_count"] == 3

    def test_task_retries_with_countdown_60_on_failure(self):
        # @spec AUTO-TSK-007
        from services.celery_tasks import archive_stale_items_async

        with patch("app.create_app"), \
             patch("services.item_service.archive_stale_items",
                   side_effect=RuntimeError("db down")), \
             patch.object(archive_stale_items_async, "retry") as mock_retry:
            mock_retry.side_effect = RuntimeError("retried")
            try:
                archive_stale_items_async.run()
            except RuntimeError:
                pass

        mock_retry.assert_called_once()
        assert mock_retry.call_args[1]["countdown"] == 60
