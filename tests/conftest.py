import sys
import os
import threading
import time
import gc
import atexit
from pathlib import Path

import pytest
from werkzeug.serving import make_server


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from models import db, User
from extensions import cache


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    """App fixture for unit tests - CSRF disabled for easier testing."""
    db_file = tmp_path_factory.mktemp("data") / "test.sqlite"
    
    # Set DATABASE_URL to test file and FLASK_ENV=testing
    old_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    
    old_flask_env = os.environ.get("FLASK_ENV")
    os.environ["FLASK_ENV"] = "testing"
        
    try:
        flask_app = create_app()
    finally:
        # Restore environment variables
        if old_db_url:
            os.environ["DATABASE_URL"] = old_db_url
        else:
            del os.environ["DATABASE_URL"]
            
        if old_flask_env:
            os.environ["FLASK_ENV"] = old_flask_env
        else:
            del os.environ["FLASK_ENV"]

    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_file}",
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_EXPIRE_ON_COMMIT=False,
        FAMILY_PASSWORD="testsecret",
    )

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()
        # Dispose engine to close all connections and prevent teardown errors
        db.engine.dispose()
        gc.collect()


@pytest.fixture(scope="session")
def browser_app(tmp_path_factory):
    """App fixture for browser tests - CSRF enabled for realistic testing."""
    db_file = tmp_path_factory.mktemp("browser_data") / "test.sqlite"
    
    # Set DATABASE_URL to test file and FLASK_ENV=testing
    old_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"

    old_flask_env = os.environ.get("FLASK_ENV")
    os.environ["FLASK_ENV"] = "testing"

    try:
        flask_app = create_app()
    finally:
        if old_db_url:
            os.environ["DATABASE_URL"] = old_db_url
        else:
            del os.environ["DATABASE_URL"]
            
        if old_flask_env:
            os.environ["FLASK_ENV"] = old_flask_env
        else:
            del os.environ["FLASK_ENV"]

    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_file}",
        WTF_CSRF_ENABLED=True,  # Enable CSRF for browser tests
        SQLALCHEMY_EXPIRE_ON_COMMIT=False,
        FAMILY_PASSWORD="testsecret",
    )

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()
        # Dispose engine to close all connections and prevent teardown errors
        db.engine.dispose()
        gc.collect()


@pytest.fixture(autouse=True)
def _clean_database(app):
    with app.app_context():
        cache.clear()
        yield
        try:
            for table in reversed(db.metadata.sorted_tables):
                db.session.execute(table.delete())
            db.session.commit()
        except Exception:
            db.session.rollback()
        finally:
            cache.clear()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user(app):
    with app.app_context():
        user = User(name="Test User", email="test@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture()
def other_user(app):
    with app.app_context():
        user = User(name="Other User", email="other@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture()
def login(client, user):
    with client.session_transaction() as session:
        session["_user_id"] = str(user)
        session["_fresh"] = True
    return user


@pytest.fixture(scope="session")
def live_server(browser_app):
    """Live server for browser tests - uses browser_app with CSRF enabled."""
    server = make_server("127.0.0.1", 0, browser_app)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    time.sleep(0.5)
    port = server.server_address[1]
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


@pytest.fixture(autouse=True)
def _clean_browser_database(browser_app, request):
    """Clean database after browser tests."""
    # Only run for browser tests (those that use live_server)
    if "live_server" not in request.fixturenames:
        yield
        return

    with browser_app.app_context():
        cache.clear()
        yield
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        cache.clear()
