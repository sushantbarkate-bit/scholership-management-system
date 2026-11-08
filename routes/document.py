from flask import Blueprint, abort, request, send_file
from flask_login import login_required, current_user

from extensions import db
from models import Document
from services.document_service import DocumentError, open_document_path


document_bp = Blueprint("document", __name__, url_prefix="/documents")


def _can_access(document):
    """Admins can view any document; students only their own."""
    if current_user.role == "admin":
        return True
    profile = current_user.student_profile
    return profile is not None and document.application.student_id == profile.id


@document_bp.route("/<int:document_id>")
@login_required
def view(document_id):
    """Preview (inline) by default; add ?download=1 to force a download."""
    document = db.session.get(Document, document_id)
    if document is None or not _can_access(document):
        # Same response for "missing" and "not yours": no information leak.
        abort(404)

    try:
        path = open_document_path(document)
    except DocumentError:
        abort(404)

    response = send_file(
        path,
        as_attachment=request.args.get("download") == "1",
        download_name=document.file_name,
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
