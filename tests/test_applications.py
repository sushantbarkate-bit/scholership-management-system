from extensions import db
from models import Application, ApplicationStatusHistory, Document, Notification
from tests.conftest import make_user, login
from tests.helpers import (
    complete_profile,
    get_profile,
    get_user,
    make_scholarship,
    pdf_upload,
    PDF_BYTES,
)
from services.application_service import start_application


STUDENT = "applicant@example.com"
ADMIN = "reviewer@example.com"


def _student(client, email=STUDENT, **profile_overrides):
    user = make_user(email)
    complete_profile(user, **profile_overrides)
    login(client, email)
    return user


def _admin(client):
    make_user(ADMIN, role="admin")
    login(client, ADMIN)


def _apply(client, scholarship):
    return client.post(f"/applications/apply/{scholarship.id}", follow_redirects=False)


def _application_for(email, scholarship):
    return Application.query.filter_by(
        student_id=get_profile(email).id, scholarship_id=scholarship.id
    ).one()


def _upload(client, application, doc_type="income_certificate"):
    return client.post(
        f"/applications/{application.id}/documents",
        data={"document_type": doc_type, "file": pdf_upload()},
        content_type="multipart/form-data",
    )


# ----- eligibility gate and duplicate prevention --------------------------

def test_ineligible_student_cannot_start_application(app, client):
    scholarship = make_scholarship("SC only", rules=[("category", "equal", "SC")])
    _student(client)  # OBC
    _apply(client, scholarship)
    assert Application.query.count() == 0


def test_eligible_student_starts_draft(app, client):
    scholarship = make_scholarship("OBC scheme", rules=[("category", "equal", "OBC")])
    _student(client)
    response = _apply(client, scholarship)
    assert response.status_code == 302
    application = _application_for(STUDENT, scholarship)
    assert application.status == "draft"
    assert application.reference_number.startswith("MSS-")


def test_duplicate_application_is_prevented(app, client):
    scholarship = make_scholarship("Once only")
    _student(client)
    _apply(client, scholarship)
    _apply(client, scholarship)
    assert Application.query.filter_by(scholarship_id=scholarship.id).count() == 1


def test_database_constraint_blocks_duplicate_rows(app):
    from sqlalchemy.exc import IntegrityError
    import pytest
    scholarship = make_scholarship("Constraint test")
    user = make_user(STUDENT)
    complete_profile(user)
    profile = get_profile(STUDENT)
    db.session.add(Application(student_id=profile.id, scholarship_id=scholarship.id))
    db.session.commit()
    db.session.add(Application(student_id=profile.id, scholarship_id=scholarship.id))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


# ----- student submission rules ------------------------------------------

def test_submit_requires_mandatory_documents(app, client):
    scholarship = make_scholarship(
        "Docs scheme",
        documents=["income_certificate", "previous_marksheet"],
        mandatory=["income_certificate"],
    )
    _student(client)
    _apply(client, scholarship)
    application = _application_for(STUDENT, scholarship)

    response = client.post(f"/applications/{application.id}/submit")
    assert response.status_code == 302
    db.session.refresh(application)
    assert application.status == "draft"


def test_full_student_submission_records_history_and_notifies(app, client):
    scholarship = make_scholarship(
        "Docs scheme",
        documents=["income_certificate", "previous_marksheet"],
        mandatory=["income_certificate"],
    )
    user = _student(client)
    _apply(client, scholarship)
    application = _application_for(STUDENT, scholarship)

    _upload(client, application, "income_certificate")
    client.post(f"/applications/{application.id}/submit")

    db.session.refresh(application)
    assert application.status == "submitted"
    assert application.submitted_at is not None
    history = [h.new_status for h in application.status_history]
    assert history == ["draft", "submitted"]
    titles = [n.title for n in Notification.query.filter_by(user_id=user.id)]
    assert "Application submitted" in titles


def test_student_cannot_submit_twice(app, client):
    scholarship = make_scholarship("Simple")
    _student(client)
    _apply(client, scholarship)
    application = _application_for(STUDENT, scholarship)
    client.post(f"/applications/{application.id}/submit")
    client.post(f"/applications/{application.id}/submit")
    db.session.refresh(application)
    assert [h.new_status for h in application.status_history].count("submitted") == 1


def test_student_cannot_view_another_students_application(app, client):
    scholarship = make_scholarship("Shared scheme")
    make_user("owner@example.com")
    complete_profile(get_user("owner@example.com"))
    owner_app = start_application(get_profile("owner@example.com"), scholarship)

    _student(client, email="intruder@example.com")
    response = client.get(f"/applications/{owner_app.id}")
    assert response.status_code == 404


def test_student_cannot_change_status_through_admin_route(app, client):
    scholarship = make_scholarship("Guarded")
    _student(client)
    _apply(client, scholarship)
    application = _application_for(STUDENT, scholarship)
    application.status = "submitted"
    db.session.commit()

    client.post(f"/admin/applications/{application.id}/status",
                data={"status": "approved", "remarks": ""})
    db.session.refresh(application)
    assert application.status == "submitted"


# ----- admin review -------------------------------------------------------

def _submitted_application(client, documents=("income_certificate",), mandatory=None):
    scholarship = make_scholarship("Review scheme", documents=list(documents),
                                   mandatory=mandatory)
    _student(client)
    _apply(client, scholarship)
    application = _application_for(STUDENT, scholarship)
    for doc in documents:
        _upload(client, application, doc)
    client.post(f"/applications/{application.id}/submit")
    db.session.refresh(application)
    return application


def test_admin_moves_to_under_review(app, client):
    application = _submitted_application(client)
    _admin(client)
    client.post(f"/admin/applications/{application.id}/status",
                data={"status": "under_review", "remarks": ""})
    db.session.refresh(application)
    assert application.status == "under_review"


def test_request_documents_needs_remarks(app, client):
    application = _submitted_application(client)
    _admin(client)
    client.post(f"/admin/applications/{application.id}/status",
                data={"status": "documents_required", "remarks": "  "})
    db.session.refresh(application)
    assert application.status == "submitted"


def test_request_documents_then_student_reupload_returns_to_review(app, client):
    application = _submitted_application(client)
    _admin(client)
    client.post(f"/admin/applications/{application.id}/status",
                data={"status": "documents_required", "remarks": "Please re-upload a clear scan."})
    db.session.refresh(application)
    assert application.status == "documents_required"
    assert application.admin_remarks == "Please re-upload a clear scan."

    client.post("/auth/logout")
    login(client, STUDENT)
    _upload(client, application, "income_certificate")
    db.session.refresh(application)
    assert application.status == "under_review"


def test_approval_blocked_until_mandatory_documents_verified(app, client):
    application = _submitted_application(client)
    _admin(client)
    client.post(f"/admin/applications/{application.id}/status",
                data={"status": "approved", "remarks": ""})
    db.session.refresh(application)
    assert application.status == "submitted"


def test_admin_approves_after_verifying_documents(app, client):
    application = _submitted_application(client)
    _admin(client)
    document = Document.query.filter_by(application_id=application.id).one()
    client.post(f"/admin/documents/{document.id}/review",
                data={"status": "verified", "remarks": ""})
    client.post(f"/admin/applications/{application.id}/status",
                data={"status": "approved", "remarks": "All good."})
    db.session.refresh(application)
    assert application.status == "approved"

    history = [h.new_status for h in application.status_history]
    assert history[-1] == "approved"
    notifications = Notification.query.filter_by(
        user_id=get_user(STUDENT).id).all()
    assert any(n.title == "Application approved" for n in notifications)


def test_admin_rejection_requires_remarks_and_is_final(app, client):
    application = _submitted_application(client)
    _admin(client)
    client.post(f"/admin/applications/{application.id}/status",
                data={"status": "rejected", "remarks": ""})
    db.session.refresh(application)
    assert application.status == "submitted"

    client.post(f"/admin/applications/{application.id}/status",
                data={"status": "rejected", "remarks": "Income above limit."})
    db.session.refresh(application)
    assert application.status == "rejected"

    client.post(f"/admin/applications/{application.id}/status",
                data={"status": "under_review", "remarks": ""})
    db.session.refresh(application)
    assert application.status == "rejected"


def test_status_history_records_each_transition(app, client):
    application = _submitted_application(client)
    _admin(client)
    client.post(f"/admin/applications/{application.id}/status",
                data={"status": "under_review", "remarks": ""})
    client.post(f"/admin/applications/{application.id}/status",
                data={"status": "rejected", "remarks": "Not eligible."})
    db.session.refresh(application)
    entries = ApplicationStatusHistory.query.filter_by(application_id=application.id).all()
    pairs = [(e.previous_status, e.new_status) for e in entries]
    assert ("submitted", "under_review") in pairs
    assert ("under_review", "rejected") in pairs


def test_rejected_document_notifies_student(app, client):
    application = _submitted_application(client)
    _admin(client)
    document = Document.query.filter_by(application_id=application.id).one()
    client.post(f"/admin/documents/{document.id}/review",
                data={"status": "rejected", "remarks": "Scan is unreadable."})
    db.session.refresh(document)
    assert document.status == "rejected"
    assert document.remarks == "Scan is unreadable."
    notes = Notification.query.filter_by(user_id=get_user(STUDENT).id).all()
    assert any("Rejected" in n.title for n in notes)


def test_admin_dashboard_and_application_pages_render(app, client):
    _submitted_application(client)
    _admin(client)
    assert client.get("/admin/").status_code == 200
    assert client.get("/admin/applications?status=submitted").status_code == 200
    application = Application.query.one()
    response = client.get(f"/admin/applications/{application.id}")
    assert response.status_code == 200
    assert b"Decision" in response.data
