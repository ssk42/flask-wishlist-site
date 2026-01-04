
import pytest
from app import create_app
from models import db, User

@pytest.fixture
def auth_app(app):
    """Reuse the session-scoped app but configure for auth testing."""
    old_pw = app.config.get('FAMILY_PASSWORD')
    app.config['FAMILY_PASSWORD'] = 'testsecret'
    
    yield app
    
    # Cleanup config
    if old_pw:
        app.config['FAMILY_PASSWORD'] = old_pw
    else:
        app.config.pop('FAMILY_PASSWORD', None)

def test_register_success(auth_app):
    """Test registration with correct family code."""
    client = auth_app.test_client()
    response = client.post('/register', data={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'testsecret'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Registration successful" in response.data
    
    with auth_app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        assert user is not None
        assert user.name == 'Test User'

def test_register_failure_wrong_code(auth_app):
    """Test registration with incorrect family code."""
    client = auth_app.test_client()
    response = client.post('/register', data={
        'name': 'Hacker',
        'email': 'hacker@example.com',
        'password': 'wrongcode'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Incorrect Family Code" in response.data
    
    with auth_app.app_context():
        user = User.query.filter_by(email='hacker@example.com').first()
        assert user is None

def test_login_success(auth_app):
    """Test login with correct family code."""
    # First create a user (manually to skip reg check)
    with auth_app.app_context():
        user = User(name='Existing User', email='existing@example.com')
        db.session.add(user)
        db.session.commit()

    client = auth_app.test_client()
    response = client.post('/login', data={
        'email': 'existing@example.com',
        'password': 'testsecret'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Welcome back, Existing User!" in response.data

def test_login_failure_wrong_code(auth_app):
    """Test login with incorrect family code."""
    # First create a user
    with auth_app.app_context():
        user = User(name='Target User', email='target@example.com')
        db.session.add(user)
        db.session.commit()

    client = auth_app.test_client()
    response = client.post('/login', data={
        'email': 'target@example.com',
        'password': 'wrongcode'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Incorrect Family Code" in response.data
    # "Welcome back" is in the login page header, so we can't assert it's missing.
    # Instead verify we didn't get the user-specific welcome flash
    assert b"Welcome back, Target User" not in response.data
