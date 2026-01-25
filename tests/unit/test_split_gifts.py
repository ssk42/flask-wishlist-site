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
    assert item.split_progress == 50  # Assuming item price is 100
    assert item.remaining_amount == 50.0
    assert item.organizer.id == user


def test_start_split_route(client, login, item):
    """Test starting a split."""
    # Create another user to start the split
    other_user = User(name='Splitter', email='splitter@example.com')
    db.session.add(other_user)
    db.session.commit()
    splitter_id = other_user.id

    with client.session_transaction() as session:
        session["_user_id"] = str(splitter_id)
        session["_fresh"] = True

    client.post(
        '/login',
        data={
            'email': 'splitter@example.com',
            'password': 'wishlist2025'})

    response = client.post(
        f'/items/{item.id}/split',
        data={
            'amount': '25.00'},
        follow_redirects=True)
    assert response.status_code == 200
    assert b'You started a split' in response.data

    updated_item = db.session.get(Item, item.id)
    assert updated_item.status == 'Splitting'
    assert len(updated_item.contributions) == 1
    assert updated_item.contributions[0].amount == 25.0
    assert updated_item.contributions[0].is_organizer


def test_join_split_route(client, login, item):
    """Test joining an existing split."""
    # Setup: Start split first
    splitter = User(name='Organizer', email='org@example.com')
    db.session.add(splitter)
    item_obj = db.session.merge(item)
    item_obj.status = 'Splitting'

    contrib = Contribution(
        item_id=item.id,
        user_id=splitter.id,
        amount=50.0,
        is_organizer=True
    )
    db.session.add(contrib)
    db.session.commit()

    # Login as current user (test user)
    # user is already logged in by 'login' fixture, but let's confirm

    response = client.post(
        f'/items/{item.id}/contribute',
        data={
            'amount': '20.00'},
        follow_redirects=True)
    assert response.status_code == 200
    assert b'You contributed $20.00' in response.data

    updated_item = db.session.get(Item, item.id)
    assert len(updated_item.contributions) == 2
    assert updated_item.total_pledged == 70.0


def test_withdraw_contribution(client, login, item):
    """Test withdrawing a contribution."""
    # Setup: User has contributed
    item_obj = db.session.merge(item)
    item_obj.status = 'Splitting'
    contrib = Contribution(
        item_id=item.id,
        user_id=login,  # The logged in user returns ID? login returns user fixture which returns ID
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
    # Should revert to available if last contrib withdrawn
    assert updated_item.status == 'Available'


def test_complete_split(client, login, item):
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

    response = client.post(
        f'/items/{item.id}/complete-split',
        follow_redirects=True)
    assert response.status_code == 200
    assert b'marked as purchased' in response.data

    updated_item = db.session.get(Item, item.id)
    assert updated_item.status == 'Purchased'
    assert updated_item.last_updated_by_id == login


def test_start_split_own_item(client, login, app):
    """Cannot split your own item."""
    # Create item owned by logged-in user
    own_item = Item(
        description="My Own Item",
        price=50.0,
        user_id=login,
        status="Available")
    db.session.add(own_item)
    db.session.commit()

    response = client.post(
        f'/items/{own_item.id}/split',
        data={
            'amount': '25.00'},
        follow_redirects=True)
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
    response = client.post(
        f'/items/{item.id}/split',
        data={
            'amount': '-5.00'},
        follow_redirects=True)
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

    response = client.post(
        f'/items/{item.id}/split',
        data={
            'amount': '0'},
        follow_redirects=True)
    assert response.status_code == 200
    assert b'must be positive' in response.data.lower()


def test_join_split_already_contributing(client, login, item):
    """Cannot join a split you're already contributing to."""
    item_obj = db.session.merge(item)
    item_obj.status = 'Splitting'

    # Already contributing
    contrib = Contribution(
        item_id=item.id,
        user_id=login,
        amount=25.0,
        is_organizer=False)
    db.session.add(contrib)
    db.session.commit()

    response = client.post(
        f'/items/{item.id}/contribute',
        data={
            'amount': '10.00'},
        follow_redirects=True)
    assert response.status_code == 200
    assert b'already contributing' in response.data.lower()


def test_join_split_not_splitting(client, login, item):
    """Cannot join a split on a non-splitting item."""
    response = client.post(
        f'/items/{item.id}/contribute',
        data={
            'amount': '10.00'},
        follow_redirects=True)
    assert response.status_code == 200
    assert b'not currently being split' in response.data.lower()


def test_join_split_invalid_amount(client, login, item):
    """Cannot join split with invalid amount."""
    item_obj = db.session.merge(item)
    item_obj.status = 'Splitting'

    other = User(name='Org', email='org2@example.com')
    db.session.add(other)
    db.session.commit()

    contrib = Contribution(
        item_id=item.id,
        user_id=other.id,
        amount=25.0,
        is_organizer=True)
    db.session.add(contrib)
    db.session.commit()

    response = client.post(
        f'/items/{item.id}/contribute',
        data={
            'amount': '-10.00'},
        follow_redirects=True)
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
    """Cannot complete split if not organizer."""
    item_obj = db.session.merge(item)
    item_obj.status = 'Splitting'

    # Another user is organizer
    organizer = User(name='OrgUser', email='orguser@example.com')
    db.session.add(organizer)
    db.session.commit()

    contrib = Contribution(
        item_id=item.id,
        user_id=organizer.id,
        amount=50.0,
        is_organizer=True)
    # Current user is just a contributor
    contrib2 = Contribution(
        item_id=item.id,
        user_id=login,
        amount=25.0,
        is_organizer=False)
    db.session.add_all([contrib, contrib2])
    db.session.commit()

    response = client.post(
        f'/items/{item.id}/complete-split',
        follow_redirects=True)
    assert response.status_code == 200
    assert b'only the split organizer' in response.data.lower()
