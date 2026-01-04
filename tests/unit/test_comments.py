
import pytest
from models import db, User, Item, Comment, Notification

def login_via_post(client, email):
    return client.post("/login", data={"email": email, "password": "testsecret"}, follow_redirects=True)

@pytest.fixture
def test_data(app):
    with app.app_context():
        # User A (Owner)
        user_a = User(name="Alice", email="alice@example.com")
        # User B (Commenter 1)
        user_b = User(name="Bob", email="bob@example.com")
        # User C (Commenter 2)
        user_c = User(name="Charlie", email="charlie@example.com")
        
        db.session.add_all([user_a, user_b, user_c])
        db.session.commit()
        
        item = Item(description="Bike", user_id=user_a.id)
        db.session.add(item)
        db.session.commit()
        
        return user_a.id, user_b.id, user_c.id, item.id

def test_add_comment_success(client, app, test_data):
    user_a_id, user_b_id, user_c_id, item_id = test_data
    
    # Login as Bob
    login_via_post(client, "bob@example.com")
    
    response = client.post(
        f"/item/{item_id}/comment",
        data={"text": "Splitting this?"},
        follow_redirects=True
    )
    
    assert response.status_code == 200
    assert b"Comment added!" in response.data
    
    with app.app_context():
        comment = Comment.query.first()
        assert comment.text == "Splitting this?"
        assert comment.user_id == user_b_id
        assert comment.item_id == item_id

def test_add_comment_owner_forbidden(client, app, test_data):
    user_a_id, user_b_id, user_c_id, item_id = test_data
    
    # Login as Alice (Owner)
    login_via_post(client, "alice@example.com")
    
    response = client.post(
        f"/item/{item_id}/comment",
        data={"text": "I want this"},
        follow_redirects=True
    )
    
    # Should redirect with flash message
    assert response.status_code == 200
    assert b"You cannot comment on your own wishlist item" in response.data
    
    with app.app_context():
        assert Comment.query.count() == 0

def test_notification_generated_for_participants(client, app, test_data):
    user_a_id, user_b_id, user_c_id, item_id = test_data
    
    # 1. Bob comments first
    login_via_post(client, "bob@example.com")
    client.post(f"/item/{item_id}/comment", data={"text": "First"})
    
    # 2. Charlie comments
    login_via_post(client, "charlie@example.com")
    client.post(f"/item/{item_id}/comment", data={"text": "Second"})
    
    with app.app_context():
        # Bob should get a notification
        notif = Notification.query.filter_by(user_id=user_b_id).first()
        assert notif is not None
        assert "Charlie commented" in notif.message
        
        # Alice (Owner) should NOT get a notification
        notif_owner = Notification.query.filter_by(user_id=user_a_id).first()
        assert notif_owner is None
        
        # Charlie (Sender) should NOT get a notification
        notif_sender = Notification.query.filter_by(user_id=user_c_id).first()
        assert notif_sender is None

def test_mark_notification_read(client, app, test_data):
    user_a_id, user_b_id, user_c_id, item_id = test_data
    
    with app.app_context():
        notif = Notification(message="Test", link="/", user_id=user_b_id)
        db.session.add(notif)
        db.session.commit()
        notif_id = notif.id
        
    login_via_post(client, "bob@example.com")
    
    response = client.post(f"/notifications/read/{notif_id}", follow_redirects=True)
    assert response.status_code == 200
    
    with app.app_context():
        notif = db.session.get(Notification, notif_id)
        assert notif.is_read is True

def test_items_page_shows_comments_to_non_owner(client, app, test_data):
    user_a_id, user_b_id, _, item_id = test_data

    # Add a comment
    with app.app_context():
        db.session.add(Comment(text="Secret", user_id=user_b_id, item_id=item_id))
        db.session.commit()

    # View as Charlie (Non-owner)
    login_via_post(client, "charlie@example.com")
    response = client.get("/items")
    assert b"Secret" in response.data
    assert b"Comments (1)" in response.data

    # View as Alice (Owner)
    login_via_post(client, "alice@example.com")
    response_owner = client.get("/items")
    assert b"Secret" not in response_owner.data


def test_add_comment_empty_text_shows_warning(client, app, test_data):
    """Test that empty comment text shows a warning flash message."""
    user_a_id, user_b_id, user_c_id, item_id = test_data

    # Login as Bob
    login_via_post(client, "bob@example.com")

    response = client.post(
        f"/item/{item_id}/comment",
        data={"text": ""},
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Comment cannot be empty" in response.data

    with app.app_context():
        assert Comment.query.count() == 0


def test_add_comment_whitespace_only_shows_warning(client, app, test_data):
    """Test that whitespace-only comment shows a warning flash message."""
    user_a_id, user_b_id, user_c_id, item_id = test_data

    # Login as Bob
    login_via_post(client, "bob@example.com")

    response = client.post(
        f"/item/{item_id}/comment",
        data={"text": "   "},
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Comment cannot be empty" in response.data

    with app.app_context():
        assert Comment.query.count() == 0


def test_mark_notification_read_ajax_returns_json(client, app, test_data):
    """Test that AJAX request to mark notification as read returns JSON."""
    user_a_id, user_b_id, user_c_id, item_id = test_data

    with app.app_context():
        notif = Notification(message="Test notification", link="/", user_id=user_b_id)
        db.session.add(notif)
        db.session.commit()
        notif_id = notif.id

    login_via_post(client, "bob@example.com")

    response = client.post(
        f"/notifications/read/{notif_id}",
        headers={"X-Requested-With": "XMLHttpRequest"}
    )

    assert response.status_code == 200
    assert response.content_type == "application/json"
    json_data = response.get_json()
    assert json_data["success"] is True

    with app.app_context():
        notif = db.session.get(Notification, notif_id)
        assert notif.is_read is True
