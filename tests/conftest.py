import sys
import threading
import time
from pathlib import Path

import pytest
from werkzeug.serving import make_server


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app as flask_app, db, User


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("data") / "test.sqlite"
    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_file}",
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_EXPIRE_ON_COMMIT=False,
    )

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture(autouse=True)
def _clean_database(app):
    with app.app_context():
        yield
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


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
def live_server(app):
    server = make_server("127.0.0.1", 5001, app)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    time.sleep(0.5)
    try:
        yield "http://127.0.0.1:5001"
    finally:
        server.shutdown()
        thread.join(timeout=5)
