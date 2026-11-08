from models import User, StudentProfile
from extensions import db
from tests.conftest import make_user, login


def test_registration_creates_student_and_profile(app, client):
    response = client.post(
        "/auth/register",
        data={
            "full_name": "Asha Patil",
            "email": "asha@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    assert response.status_code == 302
    user = User.query.filter_by(email="asha@example.com").one()
    assert user.role == "student"
    assert user.student_profile is not None


def test_duplicate_email_is_rejected(app, client):
    make_user("dup@example.com")
    response = client.post(
        "/auth/register",
        data={
            "full_name": "Other Person",
            "email": "dup@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    assert response.status_code == 200
    assert b"already registered" in response.data
    assert User.query.filter_by(email="dup@example.com").count() == 1


def test_registration_ignores_submitted_role(app, client):
    client.post(
        "/auth/register",
        data={
            "full_name": "Mallory",
            "email": "mallory@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "role": "admin",
        },
    )
    user = User.query.filter_by(email="mallory@example.com").one()
    assert user.role == "student"


def test_login_with_correct_credentials(app, client):
    make_user("ok@example.com")
    response = login(client, "ok@example.com")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/dashboard")


def test_login_with_wrong_password(app, client):
    make_user("bad@example.com")
    response = login(client, "bad@example.com", password="wrong-pass")
    assert response.status_code == 200
    assert b"Invalid email or password" in response.data


def test_anonymous_user_redirected_from_protected_page(app, client):
    response = client.get("/student/profile")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_admin_cannot_open_student_profile(app, client):
    make_user("admin@example.com", role="admin")
    login(client, "admin@example.com")
    response = client.get("/student/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/dashboard")


def test_student_cannot_open_admin_dashboard(app, client):
    make_user("stu@example.com")
    login(client, "stu@example.com")
    response = client.get("/auth/admin-dashboard")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/dashboard")
