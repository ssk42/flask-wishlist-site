from app import db, User, Item, STATUS_CHOICES, PRIORITY_CHOICES


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


def test_submit_item_requires_description(client, login):
    response = client.post(
        "/submit_item",
        data={"description": "", "status": STATUS_CHOICES[0], "priority": PRIORITY_CHOICES[0]},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"A description is required" in response.data


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
