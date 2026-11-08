import io
import os

from extensions import db
from models import Document
from tests.conftest import make_user, login
from tests.helpers import (
    complete_profile,
    get_profile,
    make_scholarship,
    pdf_upload,
    PNG_BYTES,
    JPG_BYTES,
    PDF_BYTES,
)
from services.application_service import start_application


OWNER = "docs.owner@example.com"
OTHER = "docs.other@example.com"


def _setup_application(client, email=OWNER):
    scholarship = make_scholarship("Docs scheme", documents=["income_certificate"])
    user = make_user(email)
    complete_profile(user)
    application = start_application(get_profile(email), scholarship)
    login(client, email)
    return application


def _upload(client, application, filename, data, doc_type="income_certificate"):
    return client.post(
        f"/applications/{application.id}/documents",
        data={"document_type": doc_type, "file": (io.BytesIO(data), filename)},
        content_type="multipart/form-data",
    )


def _uploads_dir(app):
    return app.config["UPLOAD_FOLDER"]


def test_valid_pdf_is_stored_outside_static(app, client):
    application = _setup_application(client)
    _upload(client, application, "income.pdf", PDF_BYTES)

    document = Document.query.filter_by(application_id=application.id).one()
    assert document.status == "pending"
    assert document.file_name == "income.pdf"
    stored = os.path.join(_uploads_dir(app), document.file_path)
    assert os.path.isfile(stored)
    assert "static" not in os.path.abspath(stored).lower()


def test_stored_name_is_random_not_the_user_filename(app, client):
    application = _setup_application(client)
    _upload(client, application, "../../my secret.pdf", PDF_BYTES)
    document = Document.query.filter_by(application_id=application.id).one()
    assert "secret" not in document.file_path
    assert ".." not in document.file_path
    assert document.file_name == "my_secret.pdf"


def test_png_and_jpg_are_accepted(app, client):
    application = _setup_application(client)
    _upload(client, application, "photo.png", PNG_BYTES, doc_type="income_certificate")
    assert Document.query.filter_by(application_id=application.id).count() == 1


def test_jpg_is_accepted(app, client):
    scholarship = make_scholarship("Other docs", documents=["bonafide_certificate"])
    user = make_user("jpgcase@example.com")
    complete_profile(user)
    application = start_application(get_profile("jpgcase@example.com"), scholarship)
    login(client, "jpgcase@example.com")
    _upload(client, application, "bonafide.jpg", JPG_BYTES, doc_type="bonafide_certificate")
    assert Document.query.filter_by(application_id=application.id).count() == 1


def test_executable_renamed_to_pdf_is_rejected(app, client):
    application = _setup_application(client)
    fake = b"MZ\x90\x00" + b"\x00" * 100  # Windows executable header
    _upload(client, application, "invoice.pdf", fake)
    assert Document.query.filter_by(application_id=application.id).count() == 0


def test_disallowed_extension_is_rejected(app, client):
    application = _setup_application(client)
    _upload(client, application, "script.exe", PDF_BYTES)
    assert Document.query.filter_by(application_id=application.id).count() == 0


def test_html_renamed_to_png_is_rejected(app, client):
    application = _setup_application(client)
    _upload(client, application, "page.png", b"<html><script>alert(1)</script></html>")
    assert Document.query.filter_by(application_id=application.id).count() == 0


def test_oversized_file_is_rejected(app, client):
    application = _setup_application(client)
    too_big = b"%PDF-" + b"0" * (5 * 1024 * 1024 + 10)
    _upload(client, application, "huge.pdf", too_big)
    assert Document.query.filter_by(application_id=application.id).count() == 0


def test_empty_file_is_rejected(app, client):
    application = _setup_application(client)
    _upload(client, application, "empty.pdf", b"")
    assert Document.query.filter_by(application_id=application.id).count() == 0


def test_replacing_a_document_keeps_one_record_and_removes_old_file(app, client):
    application = _setup_application(client)
    _upload(client, application, "first.pdf", PDF_BYTES)
    first = Document.query.filter_by(application_id=application.id).one()
    old_path = os.path.join(_uploads_dir(app), first.file_path)

    _upload(client, application, "second.pdf", PDF_BYTES)
    documents = Document.query.filter_by(application_id=application.id).all()
    assert len(documents) == 1
    assert documents[0].file_name == "second.pdf"
    assert not os.path.exists(old_path)


def test_owner_can_preview_and_download(app, client):
    application = _setup_application(client)
    _upload(client, application, "income.pdf", PDF_BYTES)
    document = Document.query.filter_by(application_id=application.id).one()

    preview = client.get(f"/documents/{document.id}")
    assert preview.status_code == 200
    assert preview.data == PDF_BYTES
    assert "attachment" not in preview.headers.get("Content-Disposition", "")
    assert preview.headers["Cache-Control"] == "private, no-store"

    download = client.get(f"/documents/{document.id}?download=1")
    assert "attachment" in download.headers["Content-Disposition"]


def test_other_student_cannot_download(app, client):
    application = _setup_application(client)
    _upload(client, application, "income.pdf", PDF_BYTES)
    document = Document.query.filter_by(application_id=application.id).one()

    other = make_user(OTHER)
    complete_profile(other)
    client.post("/auth/logout")
    login(client, OTHER)
    assert client.get(f"/documents/{document.id}").status_code == 404


def test_admin_can_download_any_document(app, client):
    application = _setup_application(client)
    _upload(client, application, "income.pdf", PDF_BYTES)
    document = Document.query.filter_by(application_id=application.id).one()

    client.post("/auth/logout")
    make_user("docs.admin@example.com", role="admin")
    login(client, "docs.admin@example.com")
    assert client.get(f"/documents/{document.id}").status_code == 200


def test_anonymous_download_is_redirected_to_login(app, client):
    application = _setup_application(client)
    _upload(client, application, "income.pdf", PDF_BYTES)
    document = Document.query.filter_by(application_id=application.id).one()
    client.post("/auth/logout")
    response = client.get(f"/documents/{document.id}")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_path_traversal_in_database_is_blocked(app, client):
    application = _setup_application(client)
    _upload(client, application, "income.pdf", PDF_BYTES)
    document = Document.query.filter_by(application_id=application.id).one()
    document.file_path = "../../app.py"
    db.session.commit()
    assert client.get(f"/documents/{document.id}").status_code == 404
