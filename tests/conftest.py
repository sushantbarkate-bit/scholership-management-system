import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from extensions import db
from models import User, StudentProfile


@pytest.fixture
def app(tmp_path):
    """Application wired to an isolated in-memory SQLite database.

    Tests never touch the MySQL database configured in .env, and uploaded
    files go to a temporary folder instead of the real uploads/ directory.
    """
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def make_user(email, role="student", password="password123", full_name="Test User"):
    user = User(
        full_name=full_name,
        email=email,
        password=generate_password_hash(password),
        role=role,
    )
    db.session.add(user)
    db.session.flush()
    if role == "student":
        db.session.add(StudentProfile(user_id=user.id))
    db.session.commit()
    return user


def login(client, email, password="password123"):
    # Log out any current session first, otherwise the login page redirects
    # an already-authenticated client without switching accounts.
    client.post("/auth/logout")
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
