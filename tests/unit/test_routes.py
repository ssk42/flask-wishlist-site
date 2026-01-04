from pathlib import Path

import pytest

from models import db, User, Item
from config import STATUS_CHOICES, PRIORITY_CHOICES


def login_via_post(client, email):
    return client.post("/login", data={"email": email, "password": "testsecret"}, follow_redirects=True)


def test_register_creates_user(client, app):
    response = client.post(
        "/register",
        data={"name": "Alice", "email": "alice@example.com", "password": "testsecret"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    with app.app_context():
        created_user = User.query.filter_by(email="alice@example.com").one()
        assert created_user.name == "Alice"


def test_register_get_renders_form(client):
    response = client.get("/register")

    assert response.status_code == 200
    assert b"Create your account" in response.data


def test_submit_item_requires_description(client, login):
    response = client.post(
        "/submit_item",
        data={"description": "", "status": STATUS_CHOICES[0], "priority": PRIORITY_CHOICES[0]},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"A description is required" in response.data


def test_submit_item_get_returns_blank_form(client, login):
    response = client.get("/submit_item")

    assert response.status_code == 200
    assert b"Add a new wishlist item" in response.data


def test_items_filtered_by_status(client, app, login, user):
    with app.app_context():
        user_obj = db.session.get(User, user)
        available = Item(
            description="Board Game",
            status="Available",
            priority=PRIORITY_CHOICES[0],
            user_id=user_obj.id,
        )
        claimed = Item(
            description="Book",
            status="Claimed",
            priority=PRIORITY_CHOICES[1],
            user_id=user_obj.id,
        )
        db.session.add_all([available, claimed])
        db.session.commit()

    response = client.get("/items", query_string={"status_filter": "Available"})

    assert response.status_code == 200
    # only the available item should be present
    assert b"Board Game" in response.data
    assert b"Book" not in response.data


def test_items_filtered_by_user_priority_and_search(client, app, login, user, other_user):
    with app.app_context():
        db.session.add_all(
            [
                Item(
                    description="Laptop Sleeve",
                    status="Available",
                    priority="High",
                    user_id=user,
                ),
                Item(
                    description="Laptop Bag",
                    status="Available",
                    priority="Medium",
                    user_id=user,
                ),
                Item(
                    description="Laptop Stand",
                    status="Available",
                    priority="High",
                    user_id=other_user,
                ),
                Item(
                    description="Phone Charger",
                    status="Available",
                    priority="High",
                    user_id=user,
                ),
            ]
        )
        db.session.commit()

    response = client.get(
        "/items",
        query_string={
            "user_filter": user,
            "priority_filter": "High",
            "q": "Laptop",
        },
    )

    assert response.status_code == 200
    body = response.data
    assert b"Laptop Sleeve" in body
    assert b"Laptop Bag" not in body
    assert b"Laptop Stand" not in body
    assert b"Phone Charger" not in body


def test_register_duplicate_email_shows_warning(client, app):
    with app.app_context():
        db.session.add(User(name="Existing", email="duplicate@example.com"))
        db.session.commit()

    response = client.post(
        "/register",
        data={"name": "Someone", "email": "duplicate@example.com", "password": "testsecret"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"already exists" in response.data


def test_login_success_redirects_home(client, app, user):
    response = client.post(
        "/login",
        data={"email": "test@example.com", "password": "testsecret"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_login_failure_renders_error(client):
    response = client.post(
        "/login",
        data={"email": "missing@example.com", "password": "testsecret"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"could not find an account" in response.data


def test_logout_clears_session(client, app, user):
    login_via_post(client, "test@example.com")

    response = client.get("/logout", follow_redirects=True)

    assert response.status_code == 200
    assert b"You have been logged out" in response.data


def test_submit_item_success(client, app, user):
    login_via_post(client, "test@example.com")

    response = client.post(
        "/submit_item",
        data={
            "description": "New Bike",
            "status": "Available",
            "priority": "High",
            "price": "199.99",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    with app.app_context():
        item = Item.query.filter_by(description="New Bike").one()
        assert item.price == pytest.approx(199.99)


def test_submit_item_invalid_price_shows_error(client, user):
    login_via_post(client, "test@example.com")

    response = client.post(
        "/submit_item",
        data={
            "description": "Gadget",
            "status": "Available",
            "priority": "High",
            "price": "not-a-number",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Price must be a valid number" in response.data


def test_edit_item_owner_updates_fields(client, app, user):
    login_via_post(client, "test@example.com")
    with app.app_context():
        item = Item(
            description="Old Description",
            status="Available",
            priority="High",
            user_id=user,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    response = client.post(
        f"/edit_item/{item_id}",
        data={
            "description": "Updated Description",
            "status": "Claimed",
            "priority": "Medium",
            "price": "10.50",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    with app.app_context():
        updated = db.session.get(Item, item_id)
        assert updated.description == "Updated Description"
        assert updated.priority == "Medium"
        assert updated.price == pytest.approx(10.50)


def test_edit_item_missing_returns_not_found(client, app, user):
    login_via_post(client, "test@example.com")

    response = client.post("/edit_item/9999", data={"description": "Nope"})

    assert response.status_code == 404


def test_edit_item_invalid_price_keeps_form(client, app, user):
    login_via_post(client, "test@example.com")
    with app.app_context():
        item = Item(
            description="Needs Validation",
            status="Available",
            priority="High",
            user_id=user,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    response = client.post(
        f"/edit_item/{item_id}",
        data={
            "description": "Needs Validation",
            "status": "Available",
            "priority": "High",
            "price": "oops",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Price must be a valid number" in response.data


def test_edit_item_owner_blank_description_keeps_form(client, app, user):
    login_via_post(client, "test@example.com")
    with app.app_context():
        item = Item(
            description="Keep Me",
            status="Available",
            priority="High",
            user_id=user,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    response = client.post(
        f"/edit_item/{item_id}",
        data={"description": "   "},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Description cannot be empty" in response.data


def test_edit_item_other_user_invalid_status_shows_error(client, app, user, other_user):
    with app.app_context():
        item = Item(
            description="Shared Item",
            status="Available",
            priority="High",
            user_id=user,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    login_via_post(client, "other@example.com")

    response = client.post(
        f"/edit_item/{item_id}",
        data={"status": "Invalid"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Please choose a valid status" in response.data


def test_edit_item_status_update_by_other_user(client, app, user, other_user):
    with app.app_context():
        owner_item = Item(
            description="Shared Item",
            status="Available",
            priority="High",
            user_id=user,
        )
        db.session.add(owner_item)
        db.session.commit()
        item_id = owner_item.id

    login_via_post(client, "other@example.com")

    response = client.post(
        f"/edit_item/{item_id}",
        data={"status": "Claimed"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    with app.app_context():
        updated = db.session.get(Item, item_id)
        assert updated.status == "Claimed"
        assert updated.last_updated_by.email == "other@example.com"


def test_claim_item_by_other_user(client, app, user, other_user):
    with app.app_context():
        item = Item(
            description="Claimable",
            status="Available",
            priority="Medium",
            user_id=user,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    login_via_post(client, "other@example.com")

    response = client.post(f"/claim_item/{item_id}", follow_redirects=False)

    assert response.status_code == 302
    with app.app_context():
        updated = db.session.get(Item, item_id)
        assert updated.status == "Claimed"
        assert updated.last_updated_by.email == "other@example.com"


def test_claim_item_self_shows_warning(client, app, user):
    login_via_post(client, "test@example.com")
    with app.app_context():
        item = Item(
            description="Self Claim",
            status="Available",
            priority="Low",
            user_id=user,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    response = client.post(f"/claim_item/{item_id}", follow_redirects=True)

    assert response.status_code == 200
    assert b"cannot claim your own item" in response.data


def test_delete_item_owner_success(client, app, user):
    login_via_post(client, "test@example.com")
    with app.app_context():
        item = Item(
            description="Delete Me",
            status="Available",
            priority="Low",
            user_id=user,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    response = client.get(f"/delete_item/{item_id}", follow_redirects=False)

    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Item, item_id) is None


def test_delete_item_not_owner(client, app, user, other_user):
    with app.app_context():
        item = Item(
            description="Unauthorized",
            status="Available",
            priority="Low",
            user_id=user,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    login_via_post(client, "other@example.com")

    response = client.get(f"/delete_item/{item_id}", follow_redirects=True)

    assert response.status_code == 200
    assert b"do not have permission" in response.data


def test_export_items_creates_excel(client, app, user):
    login_via_post(client, "test@example.com")
    with app.app_context():
        db.session.add(
            Item(
                description="Exported",
                status="Available",
                priority="High",
                user_id=user,
            )
        )
        db.session.commit()

    target = Path("allWishlistItems.xlsx")
    if target.exists():
        target.unlink()

    response = client.get("/export_items")

    assert response.status_code == 200
    assert target.exists()
    target.unlink()


def test_export_my_status_updates(client, app, user, other_user):
    with app.app_context():
        item = Item(
            description="Status Export",
            status="Claimed",
            priority="Low",
            user_id=other_user,
            last_updated_by_id=user,
        )
        db.session.add(item)
        db.session.commit()

    login_via_post(client, "test@example.com")

    filename = Path(f"status_updates_by_Test User.xlsx")
    if filename.exists():
        filename.unlink()

    response = client.get("/export_my_status_updates")

    assert response.status_code == 200
    assert filename.exists()
    filename.unlink()


def test_register_commit_failure_rolls_back(client, monkeypatch):
    def fail_commit():
        raise RuntimeError("boom")

    rolled_back = {"called": False}

    def mark_rollback():
        rolled_back["called"] = True

    monkeypatch.setattr(db.session, "commit", fail_commit)
    monkeypatch.setattr(db.session, "rollback", mark_rollback)

    response = client.post(
        "/register",
        data={"name": "Eve", "email": "eve@example.com", "password": "testsecret"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"unexpected error" in response.data
    assert rolled_back["called"] is True


def test_submit_item_database_error_shows_message(client, user, monkeypatch):
    login_via_post(client, "test@example.com")

    def fail_commit():
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(db.session, "commit", fail_commit)

    response = client.post(
        "/submit_item",
        data={
            "description": "Tent",
            "status": "Available",
            "priority": "High",
            "price": "29.99",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Failed to create item" in response.data


def test_items_preserves_nonexistent_event_filter(client, app, login, user):
    """
    Test that filtering by an event that doesn't exist (e.g. valid ID format but no match)
    still preserves the filter value in the session.
    """
    # 999 is assumed to be a non-existent event ID
    response = client.get("/items", query_string={"event_filter": "999", "q": ""})
    assert response.status_code == 200
    # Should be preserved in session as int
    with client.session_transaction() as sess:
        assert sess.get('event_filter') == 999


def test_items_default_sorting_by_price_desc(client, app, login, user):
    with app.app_context():
        cheap = Item(
            description="Budget Watch",
            status="Available",
            priority="Low",
            price=10,
            user_id=user,
        )
        premium = Item(
            description="Luxury Watch",
            status="Available",
            priority="High",
            price=250,
            user_id=user,
        )
        db.session.add_all([cheap, premium])
        db.session.commit()

    response = client.get(
        "/items",
        query_string={"sort_by": "mystery", "sort_order": "desc"},
    )

    assert response.status_code == 200
    body = response.data
    assert body.index(b"Luxury Watch") < body.index(b"Budget Watch")


def test_items_summary_rows_include_totals(client, app, login, user, other_user):
    with app.app_context():
        db.session.add_all(
            [
                Item(
                    description="Camera",
                    status="Available",
                    priority="Medium",
                    price=300,
                    user_id=user,
                ),
                Item(
                    description="Tripod",
                    status="Claimed",
                    priority="Low",
                    price=120,
                    user_id=user,
                ),
                Item(
                    description="Backpack",
                    status="Claimed",
                    priority="Medium",
                    price=80,
                    user_id=other_user,
                ),
            ]
        )
        db.session.commit()

    response = client.get("/items")

    assert response.status_code == 200
    assert b"At a Glance" in response.data
    assert b"$120.00" in response.data
    assert b"$300.00" in response.data

def test_claim_item_missing_returns_404(client, app, other_user):
    login_via_post(client, "other@example.com")

    response = client.post("/claim_item/9999")

    assert response.status_code == 404


def test_claim_item_not_available_redirects(client, app, user, other_user):
    with app.app_context():
        item = Item(
            description="Already Claimed",
            status="Claimed",
            priority="Low",
            user_id=user,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    login_via_post(client, "other@example.com")

    response = client.post(f"/claim_item/{item_id}", follow_redirects=False)

    assert response.status_code == 302


def test_clear_filters_removes_all_session_filters(client, app, login, user):
    """Test that ?clear_filters=true clears all filters from session."""
    # First, set some filters in the session
    with client.session_transaction() as sess:
        sess['user_filter'] = user
        sess['status_filter'] = 'Available'
        sess['priority_filter'] = 'High'
        sess['event_filter'] = 1
        sess['q'] = 'search term'
        sess['sort_by'] = 'price'
        sess['sort_order'] = 'desc'

    # Request with clear_filters=true
    response = client.get("/items", query_string={"clear_filters": "true"})

    # Should redirect to /items without filters
    assert response.status_code == 302
    assert response.location.endswith('/items')

    # Verify all filters are cleared from session
    with client.session_transaction() as sess:
        assert sess.get('user_filter') is None
        assert sess.get('status_filter') is None
        assert sess.get('priority_filter') is None
        assert sess.get('event_filter') is None
        assert sess.get('q') is None
        assert sess.get('sort_by') is None
        assert sess.get('sort_order') is None


def test_unclaim_item_nonexistent_returns_404(client, app, login, user):
    """Test that unclaiming a non-existent item returns 404."""
    response = client.post("/unclaim_item/99999")

    assert response.status_code == 404


def test_unclaim_item_not_claimed_by_user_shows_error(client, app, login, user, other_user):
    """Test that a user cannot unclaim an item they did not claim."""
    with app.app_context():
        # Create an item owned by user, claimed by other_user
        item = Item(
            description="Claimed by Other",
            status="Claimed",
            priority="Medium",
            user_id=user,
            last_updated_by_id=other_user,  # other_user claimed this
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    response = client.post(f"/unclaim_item/{item_id}", follow_redirects=True)

    assert response.status_code == 200
    assert b"cannot unclaim this item" in response.data


def test_unclaim_item_available_status_shows_error(client, app, login, user):
    """Test that a user cannot unclaim an item that is Available status."""
    with app.app_context():
        item = Item(
            description="Available Item",
            status="Available",
            priority="Medium",
            user_id=user,
            last_updated_by_id=user,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    response = client.post(f"/unclaim_item/{item_id}", follow_redirects=True)

    assert response.status_code == 200
    assert b"cannot unclaim this item" in response.data


def test_item_modal_nonexistent_returns_404(client, app, login, user):
    """Test that requesting a modal for a non-existent item returns 404."""
    response = client.get("/items/99999/modal")

    assert response.status_code == 404
    assert b"Item not found" in response.data


def test_unclaim_item_htmx_from_items_list(client, app, login, user, other_user):
    """Test unclaiming an item via HTMX from items list returns partial HTML."""
    with app.app_context():
        item = Item(
            description="HTMX Unclaim Item",
            status="Claimed",
            priority="Medium",
            user_id=other_user,
            last_updated_by_id=user,  # Current user claimed it
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    # POST with HX-Request header (HTMX) but no context param (items list)
    response = client.post(
        f"/unclaim_item/{item_id}",
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    # Should return partial HTML with item card
    assert b"glass-card" in response.data or b"item-card" in response.data


def test_unclaim_item_non_htmx_success(client, app, login, user, other_user):
    """Test unclaiming an item without HTMX redirects with flash message."""
    with app.app_context():
        item = Item(
            description="Non-HTMX Unclaim Item",
            status="Claimed",
            priority="Medium",
            user_id=other_user,
            last_updated_by_id=user,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    response = client.post(f"/unclaim_item/{item_id}", follow_redirects=True)

    assert response.status_code == 200
    assert b"unclaimed" in response.data


def test_items_preserves_all_session_filters(client, app, login, user):
    """Test that items page preserves all session filter types."""
    with app.app_context():
        item = Item(
            description="Session Filter Item",
            status="Available",
            priority="High",
            user_id=user,
        )
        db.session.add(item)
        db.session.commit()

    # Apply various filters
    response = client.get(
        "/items?user_filter=1&status_filter=Available&priority_filter=High&q=test&sort_by=price&sort_order=asc"
    )
    assert response.status_code == 200

    # Visit another page and come back - filters should be preserved in session
    with client.session_transaction() as sess:
        assert sess.get('user_filter') == 1
        assert sess.get('status_filter') == 'Available'
        assert sess.get('priority_filter') == 'High'
        assert sess.get('q') == 'test'
        assert sess.get('sort_by') == 'price'
        assert sess.get('sort_order') == 'asc'


def test_items_preserves_event_filter(client, app, login, user):
    """Test that items page preserves event filter in session."""
    from models import Event
    import datetime

    with app.app_context():
        event = Event(
            name="Test Event",
            date=datetime.date.today(),
            created_by_id=user,
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

    response = client.get(f"/items?event_filter={event_id}")
    assert response.status_code == 200

    with client.session_transaction() as sess:
        assert sess.get('event_filter') == event_id


def test_get_item_modal_success(client, app, login, user):
    """Test that get_item_modal returns modal HTML for valid item."""
    with app.app_context():
        item = Item(
            description="Modal Test Item",
            status="Available",
            priority="Medium",
            user_id=user,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    response = client.get(f"/items/{item_id}/modal")

    assert response.status_code == 200
    assert b"Modal Test Item" in response.data
