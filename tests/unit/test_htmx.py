"""Tests for HTMX integration."""
import pytest
from app import db, User, Item


def login_via_post(client, email):
    return client.post("/login", data={"email": email}, follow_redirects=True)


@pytest.fixture
def htmx_setup(app):
    """Create test data for htmx tests."""
    with app.app_context():
        owner = User(name="Alice", email="alice@example.com")
        claimer = User(name="Bob", email="bob@example.com")
        
        db.session.add_all([owner, claimer])
        db.session.commit()
        
        item = Item(
            description="Test Item",
            user_id=owner.id,
            status="Available"
        )
        db.session.add(item)
        db.session.commit()
        
        return owner.id, claimer.id, item.id


def test_claim_htmx_returns_partial(client, app, htmx_setup):
    """HTMX claim request returns partial HTML, not redirect."""
    owner_id, claimer_id, item_id = htmx_setup
    
    # Login as claimer (not owner)
    login_via_post(client, "bob@example.com")
    
    # Make htmx request
    response = client.post(
        f"/claim_item/{item_id}",
        headers={"HX-Request": "true"},
        follow_redirects=False
    )
    
    # Should return 200 with HTML, not 302 redirect
    assert response.status_code == 200
    assert b"Claimed" in response.data
    assert b"card" in response.data


def test_claim_regular_returns_redirect(client, app, htmx_setup):
    """Regular claim request returns redirect as before."""
    owner_id, claimer_id, item_id = htmx_setup
    
    login_via_post(client, "bob@example.com")
    
    # Regular request (no HX-Request header)
    response = client.post(
        f"/claim_item/{item_id}",
        follow_redirects=False
    )
    
    # Should redirect
    assert response.status_code == 302


def test_claim_updates_item_status(client, app, htmx_setup):
    """Claim action properly updates item status regardless of htmx."""
    owner_id, claimer_id, item_id = htmx_setup
    
    login_via_post(client, "bob@example.com")
    
    client.post(
        f"/claim_item/{item_id}",
        headers={"HX-Request": "true"}
    )
    
    with app.app_context():
        item = db.session.get(Item, item_id)
        assert item.status == "Claimed"
        assert item.last_updated_by_id == claimer_id
