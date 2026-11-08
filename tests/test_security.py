import os

from app import create_app
from extensions import db
from tests.conftest import make_user


def _app_with_csrf(tmp_path):
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": True,
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    })


def test_post_without_csrf_token_is_rejected(tmp_path):
    app = _app_with_csrf(tmp_path)
    with app.app_context():
        db.create_all()
        make_user("csrf@example.com")
        client = app.test_client()
        response = client.post("/auth/login", data={
            "email": "csrf@example.com", "password": "password123",
        })
        assert response.status_code == 400  # CSRF validation failed
        db.session.remove()
        db.drop_all()


def test_session_cookie_is_http_only_and_samesite(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_uploads_are_stored_outside_static(app):
    static_dir = os.path.realpath(os.path.join(app.root_path, "static"))
    upload_dir = os.path.realpath(app.config["UPLOAD_FOLDER"])
    assert not upload_dir.startswith(static_dir)


def test_unknown_routes_return_generic_404(app, client):
    response = client.get("/this/route/does/not/exist")
    assert response.status_code == 404
    assert b"Page not found" in response.data
