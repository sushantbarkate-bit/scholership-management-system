from models import Notification, User
from extensions import db
from tests.conftest import make_user, login
from tests.helpers import complete_profile, get_profile, get_user, make_scholarship, pdf_upload, PDF_BYTES
from services.application_service import start_application, submit_application, upload_student_document
from services.notification_service import unread_count, mark_read, mark_all_read, notify


# ----- notifications ------------------------------------------------------

def test_registration_creates_welcome_notification(app, client):
    client.post("/auth/register", data={
        "full_name": "New Student",
        "email": "newbie@example.com",
        "password": "password123",
        "confirm_password": "password123",
    })
    user = get_user("newbie@example.com")
    assert unread_count(user.id) == 1
    assert Notification.query.filter_by(user_id=user.id).one().title.startswith("Welcome")


def test_unread_count_and_mark_read(app):
    user = make_user("notify@example.com")
    notify(user.id, "One", "first")
    notify(user.id, "Two", "second")
    db.session.commit()
    assert unread_count(user.id) == 2

    first = Notification.query.filter_by(user_id=user.id, title="One").one()
    assert mark_read(first.id, user.id) is True
    assert unread_count(user.id) == 1


def test_user_cannot_mark_another_users_notification(app):
    owner = make_user("owner.n@example.com")
    other = make_user("other.n@example.com")
    notify(owner.id, "Private", "secret")
    db.session.commit()
    note = Notification.query.filter_by(user_id=owner.id).one()
    assert mark_read(note.id, other.id) is False
    assert unread_count(owner.id) == 1


def test_mark_all_read(app):
    user = make_user("many@example.com")
    for i in range(3):
        notify(user.id, f"N{i}", "msg")
    db.session.commit()
    mark_all_read(user.id)
    assert unread_count(user.id) == 0


def test_notifications_page_and_mark_read_route(app, client):
    user = make_user("page.n@example.com")
    notify(user.id, "Hello", "World")
    db.session.commit()
    login(client, "page.n@example.com")

    page = client.get("/notifications/")
    assert page.status_code == 200
    assert b"Hello" in page.data

    note = Notification.query.filter_by(user_id=user.id).one()
    client.post(f"/notifications/{note.id}/read")
    db.session.refresh(note)
    assert note.is_read is True


# ----- password change ----------------------------------------------------

def test_change_password_success_and_login_with_new_password(app, client):
    make_user("pw@example.com")
    login(client, "pw@example.com")
    response = client.post("/auth/change-password", data={
        "current_password": "password123",
        "new_password": "brand-new-pass",
        "confirm_password": "brand-new-pass",
    })
    assert response.status_code == 302
    client.post("/auth/logout")
    assert login(client, "pw@example.com", password="brand-new-pass").status_code == 302


def test_change_password_wrong_current_password(app, client):
    make_user("pw2@example.com")
    login(client, "pw2@example.com")
    client.post("/auth/change-password", data={
        "current_password": "wrong-one",
        "new_password": "brand-new-pass",
        "confirm_password": "brand-new-pass",
    })
    user = get_user("pw2@example.com")
    from werkzeug.security import check_password_hash
    assert check_password_hash(user.password, "password123")


# ----- dashboards ---------------------------------------------------------

def test_student_dashboard_shows_database_driven_counts(app, client):
    user = make_user("dash@example.com")
    complete_profile(user)
    scholarship = make_scholarship("Dash scheme")
    start_application(get_profile("dash@example.com"), scholarship)
    login(client, "dash@example.com")
    response = client.get("/auth/student-dashboard")
    assert response.status_code == 200
    assert b"Your scholarship dashboard" in response.data


def test_admin_dashboard_renders(app, client):
    make_user("boss@example.com", role="admin")
    login(client, "boss@example.com")
    response = client.get("/auth/admin-dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert b"Recent registrations" in response.data


# ----- reports ------------------------------------------------------------

def _report_setup(client):
    make_user("rep.admin@example.com", role="admin")
    user = make_user("rep.student@example.com")
    complete_profile(user, category="SC", course="MCA")
    scholarship = make_scholarship("Report scheme", documents=["income_certificate"])
    application = start_application(get_profile("rep.student@example.com"), scholarship)
    upload_student_document(application, "income_certificate", pdf_upload())
    submit_application(application)
    login(client, "rep.admin@example.com")
    return application


def test_reports_page_shows_real_counts(app, client):
    application = _report_setup(client)
    response = client.get("/admin/reports/")
    assert response.status_code == 200
    assert b"Applications by status" in response.data
    assert b"Report scheme" in response.data
    assert b"MCA" in response.data


def test_reports_date_filter_excludes_outside_range(app, client):
    _report_setup(client)
    response = client.get("/admin/reports/?date_from=2000-01-01&date_to=2000-01-02")
    assert response.status_code == 200
    assert b'<div class="msp-stat-value">0</div>' in response.data


def test_csv_export_contains_submitted_application(app, client):
    application = _report_setup(client)
    response = client.get("/admin/reports/export.csv")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    text = response.data.decode("utf-8")
    assert text.splitlines()[0].startswith("Reference,Student name")
    assert application.reference_number in text
    assert "rep.student@example.com" in text


def test_student_cannot_access_reports(app, client):
    user = make_user("nosy@example.com")
    complete_profile(user)
    login(client, "nosy@example.com")
    response = client.get("/admin/reports/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/dashboard")
