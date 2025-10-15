from pathlib import Path

import pytest

from app import db, User, Item, STATUS_CHOICES, PRIORITY_CHOICES


def login_via_post(client, email):
    return client.post("/login", data={"email": email}, follow_redirects=True)


def test_register_creates_user(client, app):
    response = client.post(
        "/register",
        data={"name": "Alice", "email": "alice@example.com"},
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
        data={"name": "Someone", "email": "duplicate@example.com"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"already exists" in response.data


def test_login_success_redirects_home(client, app, user):
    response = client.post(
        "/login",
        data={"email": "test@example.com"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_login_failure_renders_error(client):
    response = client.post(
        "/login",
        data={"email": "missing@example.com"},
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
        data={"name": "Eve", "email": "eve@example.com"},
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
    assert b"problem saving your item" in response.data


def test_items_preserves_nonexistent_category_filter(client, app, login, user):
    with app.app_context():
        db.session.add(
            Item(
                description="Kayak",
                status="Available",
                priority="High",
                category="Outdoor",
                user_id=user,
            )
        )
        db.session.commit()

    response = client.get(
        "/items",
        query_string={"category_filter": "Nonexistent", "q": ""},
    )

    assert response.status_code == 200
    assert b"No items found" in response.data
    assert b'value="Nonexistent" selected' in response.data


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
    assert b"At-a-glance totals" in response.data
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
