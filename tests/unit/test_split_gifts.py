import pytest
from models import db, Item, User, Contribution

@pytest.fixture
def item(app, user):
    """Create a test item."""
    # user fixture returns id, so we need to fetch user or just use id
    # models.Item needs user_id
    item = Item(
        description="Test Split Item",
        price=100.0,
        user_id=user,
        status="Available"
    )
    db.session.add(item)
    db.session.commit()
    return item

def test_contribution_model(app, user, item):
    # @spec GIV-SPL-008
    """Test Contribution model creation and constraints."""
    # Create contribution
    contribution = Contribution(
        item_id=item.id,
        user_id=user,  # user fixture returns id
        amount=50.0,
        is_organizer=True
    )
    db.session.add(contribution)
    db.session.commit()

    assert contribution.id is not None
    assert contribution.created_at is not None
    
    # Test item properties
    assert item.total_pledged == 50.0
    assert item.split_progress == 50 # Assuming item price is 100
    assert item.remaining_amount == 50.0
    assert item.organizer.id == user

def test_start_split_route(client, login, item):
    # @spec GIV-SPL-001
    """Test starting a split."""
    # Create another user to start the split
    other_user = User(name='Splitter', email='splitter@example.com')
    db.session.add(other_user)
    db.session.commit()
    splitter_id = other_user.id
        
    with client.session_transaction() as session:
        session["_user_id"] = str(splitter_id)
        session["_fresh"] = True
        
    client.post('/login', data={'email': 'splitter@example.com', 'password': 'wishlist2025'})

    response = client.post(f'/items/{item.id}/split', data={'amount': '25.00'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'You started a split' in response.data
    
    updated_item = db.session.get(Item, item.id)
    assert updated_item.status == 'Splitting'
    assert len(updated_item.contributions) == 1
    assert updated_item.contributions[0].amount == 25.0
    assert updated_item.contributions[0].is_organizer == True

def test_join_split_route(client, login, item):
    # @spec GIV-SPL-002
    """Test joining an existing split."""
    # The item belongs to a distinct owner; the logged-in user is a giver joining.
    owner = User(name="Item Owner", email="owner@example.com")
    db.session.add(owner)
    db.session.commit()
    item_obj = db.session.merge(item)
    item_obj.user_id = owner.id
    item_obj.status = 'Splitting'

    splitter = User(name='Organizer', email='org@example.com')
    db.session.add(splitter)
    db.session.commit()

    contrib = Contribution(
        item_id=item.id,
        user_id=splitter.id,
        amount=50.0,
        is_organizer=True
    )
    db.session.add(contrib)
    db.session.commit()

    response = client.post(f'/items/{item.id}/contribute', data={'amount': '20.00'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'You contributed $20.00' in response.data

    updated_item = db.session.get(Item, item.id)
    assert len(updated_item.contributions) == 2
    assert updated_item.total_pledged == 70.0

def test_withdraw_contribution(client, login, item):
    # @spec GIV-SPL-003, GIV-SPL-005
    """Test withdrawing a contribution."""
    # Setup: User has contributed
    item_obj = db.session.merge(item)
    item_obj.status = 'Splitting'
    contrib = Contribution(
        item_id=item.id,
        user_id=login, # The logged in user returns ID? login returns user fixture which returns ID
        amount=30.0,
        is_organizer=True
    )
    db.session.add(contrib)
    db.session.commit()

    response = client.post(f'/items/{item.id}/withdraw', follow_redirects=True)
    assert response.status_code == 200
    assert b'Contribution withdrawn' in response.data

    updated_item = db.session.get(Item, item.id)
    assert len(updated_item.contributions) == 0
    assert updated_item.status == 'Available' # Should revert to available if last contrib withdrawn

def test_complete_split(client, login, item):
    # @spec GIV-SPL-006
    """Test completing a split."""
    # Setup: User is organizer
    item_obj = db.session.merge(item)
    item_obj.status = 'Splitting'
    contrib = Contribution(
        item_id=item.id,
        user_id=login,
        amount=100.0,
        is_organizer=True
    )
    db.session.add(contrib)
    db.session.commit()

    response = client.post(f'/items/{item.id}/complete-split', follow_redirects=True)
    assert response.status_code == 200
    assert b'marked as purchased' in response.data

    updated_item = db.session.get(Item, item.id)
    assert updated_item.status == 'Purchased'
    assert updated_item.last_updated_by_id == login


def test_start_split_own_item(client, login, app):
    """Cannot split your own item."""
    # Create item owned by logged-in user
    own_item = Item(description="My Own Item", price=50.0, user_id=login, status="Available")
    db.session.add(own_item)
    db.session.commit()
    
    response = client.post(f'/items/{own_item.id}/split', data={'amount': '25.00'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'cannot split your own item' in response.data.lower()


def test_start_split_invalid_amount(client, login, item, app):
    """Cannot split with invalid amount."""
    # Create another user to do the split
    splitter = User(name='Splitter2', email='splitter2@example.com')
    db.session.add(splitter)
    db.session.commit()
    
    with client.session_transaction() as session:
        session["_user_id"] = str(splitter.id)
        session["_fresh"] = True
    
    # Test with negative amount
    response = client.post(f'/items/{item.id}/split', data={'amount': '-5.00'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'must be positive' in response.data.lower()


def test_start_split_zero_amount(client, login, item, app):
    """Cannot split with zero amount."""
    splitter = User(name='Splitter3', email='splitter3@example.com')
    db.session.add(splitter)
    db.session.commit()
    
    with client.session_transaction() as session:
        session["_user_id"] = str(splitter.id)
        session["_fresh"] = True
    
    response = client.post(f'/items/{item.id}/split', data={'amount': '0'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'must be positive' in response.data.lower()


def test_join_split_already_contributing(client, login, item):
    """Cannot join a split you're already contributing to."""
    item_obj = db.session.merge(item)
    item_obj.status = 'Splitting'
    owner = User(name="Item Owner 2", email="owner2@example.com")
    db.session.add(owner)
    db.session.commit()
    item_obj.user_id = owner.id
    db.session.commit()

    # Already contributing (as a giver)
    contrib = Contribution(item_id=item.id, user_id=login, amount=25.0, is_organizer=False)
    db.session.add(contrib)
    db.session.commit()
    
    response = client.post(f'/items/{item.id}/contribute', data={'amount': '10.00'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'already contributing' in response.data.lower()


def test_join_split_not_splitting(client, login, item):
    """Cannot join a split on a non-splitting item."""
    item_obj = db.session.merge(item)
    owner = User(name="Item Owner 3", email="owner3@example.com")
    db.session.add(owner)
    db.session.commit()
    item_obj.user_id = owner.id
    db.session.commit()

    response = client.post(f'/items/{item.id}/contribute', data={'amount': '10.00'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'not currently being split' in response.data.lower()


def test_join_split_invalid_amount(client, login, item):
    """Cannot join split with invalid amount."""
    item_obj = db.session.merge(item)
    item_obj.status = 'Splitting'
    owner = User(name="Item Owner 4", email="owner4@example.com")
    db.session.add(owner)
    db.session.commit()
    item_obj.user_id = owner.id
    db.session.commit()

    other = User(name='Org', email='org2@example.com')
    db.session.add(other)
    db.session.commit()
    
    contrib = Contribution(item_id=item.id, user_id=other.id, amount=25.0, is_organizer=True)
    db.session.add(contrib)
    db.session.commit()
    
    response = client.post(f'/items/{item.id}/contribute', data={'amount': '-10.00'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'must be positive' in response.data.lower()


def test_withdraw_not_contributing(client, login, item):
    """Cannot withdraw if not contributing."""
    item_obj = db.session.merge(item)
    item_obj.status = 'Splitting'
    db.session.commit()
    
    response = client.post(f'/items/{item.id}/withdraw', follow_redirects=True)
    assert response.status_code == 200
    assert b'not contributing' in response.data.lower()


def test_complete_split_not_organizer(client, login, item):
    # @spec GIV-SPL-007
    """Cannot complete split if not organizer."""
    item_obj = db.session.merge(item)
    item_obj.status = 'Splitting'
    
    # Another user is organizer
    organizer = User(name='OrgUser', email='orguser@example.com')
    db.session.add(organizer)
    db.session.commit()
    
    contrib = Contribution(item_id=item.id, user_id=organizer.id, amount=50.0, is_organizer=True)
    # Current user is just a contributor
    contrib2 = Contribution(item_id=item.id, user_id=login, amount=25.0, is_organizer=False)
    db.session.add_all([contrib, contrib2])
    db.session.commit()
    
    response = client.post(f'/items/{item.id}/complete-split', follow_redirects=True)
    assert response.status_code == 200
    assert b'only the split organizer' in response.data.lower()

def test_withdraw_reassigns_organizer_to_next_contributor(client, login, item, app):
    # @spec GIV-SPL-004
    """GIV-SPL-004: when the organizer withdraws and contributors remain,
    the oldest remaining contributor becomes the new organizer."""
    with app.app_context():
        item_obj = db.session.merge(item)
        item_obj.status = 'Splitting'

        # Organizer (current user `login`) + two contributors; organizer is oldest
        organizer = db.session.get(User, login)
        second = User(name='Second Person', email='second@example.com')
        third = User(name='Third Person', email='third@example.com')
        db.session.add_all([second, third])
        db.session.commit()

        db.session.add_all([
            Contribution(item_id=item.id, user_id=organizer.id, amount=40.0, is_organizer=True),
            Contribution(item_id=item.id, user_id=second.id, amount=30.0, is_organizer=False),
            Contribution(item_id=item.id, user_id=third.id, amount=30.0, is_organizer=False),
        ])
        db.session.commit()

    response = client.post(f'/items/{item.id}/withdraw', follow_redirects=True)
    assert response.status_code == 200
    assert b'Contribution withdrawn' in response.data

    with app.app_context():
        updated = db.session.get(Item, item.id)
        assert updated.status == 'Splitting'  # contributors remain
        contribs = sorted(updated.contributions, key=lambda c: c.created_at)
        assert len(contribs) == 2
        assert contribs[0].is_organizer is True, "oldest remaining contributor becomes organizer"
        assert contribs[1].is_organizer is False

def test_complete_split_notifies_other_contributors(client, login, item, app):
    # @spec GIV-SEC-007
    """GIV-SEC-007: completing a split notifies all other contributors (not the
    organizer, not the item owner)."""
    import datetime
    from models import Notification
    with app.app_context():
        item_obj = db.session.merge(item)
        item_obj.status = 'Splitting'

        organizer = db.session.get(User, login)
        contributor_b = User(name="Contributor Beth", email="beth@example.com")
        contributor_c = User(name="Contributor Craig", email="craig@example.com")
        db.session.add_all([contributor_b, contributor_c])
        db.session.commit()
        b_id, c_id, organizer_id, owner_id = contributor_b.id, contributor_c.id, organizer.id, item_obj.user_id

        db.session.add_all([
            Contribution(item_id=item.id, user_id=organizer_id, amount=40.0, is_organizer=True),
            Contribution(item_id=item.id, user_id=b_id, amount=30.0, is_organizer=False),
            Contribution(item_id=item.id, user_id=c_id, amount=30.0, is_organizer=False),
        ])
        db.session.commit()

    response = client.post(f'/items/{item.id}/complete-split', follow_redirects=True)
    assert response.status_code == 200
    assert b'marked as purchased' in response.data

    with app.app_context():
        notifs = Notification.query.all()
        recipients = {n.user_id for n in notifs}
        assert recipients == {b_id, c_id}, f"Expected Beth+Craig notified, got {recipients}"
        assert organizer_id not in recipients, "Organizer must not notify themselves"
        assert owner_id not in recipients, "Item owner must not be notified"
        assert all("purchased" in n.message.lower() for n in notifs)

def test_join_split_own_item_rejected(client, app, login, item):
    """The item owner must not be able to contribute to their own split
    (surprise protection: they must not see gift-coordination state)."""
    with app.app_context():
        item_obj = db.session.merge(item)
        item_obj.status = 'Splitting'
        db.session.commit()

    response = client.post(f'/items/{item.id}/contribute', data={'amount': '10.00'},
                           follow_redirects=True)
    assert response.status_code == 200
    assert b'cannot contribute to your own item' in response.data

    with app.app_context():
        assert Contribution.query.filter_by(item_id=item.id).count() == 0
