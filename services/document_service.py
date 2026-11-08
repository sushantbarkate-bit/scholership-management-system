"""Secure document upload, storage and retrieval.

Security rules implemented here:
  * Only pdf / jpg / jpeg / png extensions are accepted.
  * The file's content (magic bytes) must match the extension, so a renamed
    executable or HTML file is rejected regardless of its filename.
  * The declared MIME type must not contradict the extension.
  * Size is limited by MAX_DOCUMENT_SIZE and checked while reading.
  * Stored under UPLOAD_FOLDER with a random name (never the user's filename),
    outside static/, so it is never served without an authorisation check.
  * Paths are resolved and must stay inside UPLOAD_FOLDER (no traversal).
"""

import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

from extensions import db
from models import Document
from services.constants import DOCUMENT_TYPE_LABELS


ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

# Magic-number signatures for each allowed file family.
SIGNATURES = {
    "pdf": (b"%PDF-",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
}

MIME_FOR_EXTENSION = {
    "pdf": {"application/pdf", "application/octet-stream"},
    "jpg": {"image/jpeg", "application/octet-stream"},
    "jpeg": {"image/jpeg", "application/octet-stream"},
    "png": {"image/png", "application/octet-stream"},
}


class DocumentError(ValueError):
    """Raised for user-correctable document problems."""


def upload_root():
    return os.path.join(current_app.config["UPLOAD_FOLDER"], "documents")


def validate_upload(file_storage, document_type):
    """Validate an uploaded file. Returns (extension, file_bytes)."""
    if document_type not in DOCUMENT_TYPE_LABELS:
        raise DocumentError("Unknown document type.")

    if file_storage is None or not file_storage.filename:
        raise DocumentError("Please choose a file to upload.")

    original = secure_filename(file_storage.filename)
    if "." not in original:
        raise DocumentError("The file must have an extension (PDF, JPG or PNG).")

    extension = original.rsplit(".", 1)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise DocumentError("Only PDF, JPG and PNG files are allowed.")

    declared_mime = (file_storage.mimetype or "").lower()
    if declared_mime and declared_mime not in MIME_FOR_EXTENSION[extension]:
        raise DocumentError("The file type does not match its extension.")

    max_size = current_app.config["MAX_DOCUMENT_SIZE"]
    data = file_storage.stream.read(max_size + 1)
    if len(data) == 0:
        raise DocumentError("The uploaded file is empty.")
    if len(data) > max_size:
        raise DocumentError(
            f"File is too large. The limit is {max_size // (1024 * 1024)} MB."
        )

    if not any(data.startswith(sig) for sig in SIGNATURES[extension]):
        raise DocumentError(
            "The file content does not match its extension. "
            "Please upload a genuine PDF, JPG or PNG file."
        )

    return extension, data, original


def _absolute_path(relative_path):
    root = os.path.realpath(current_app.config["UPLOAD_FOLDER"])
    full = os.path.realpath(os.path.join(root, relative_path))
    if os.path.commonpath([root, full]) != root:
        raise DocumentError("Invalid document path.")
    return full


def save_document(application, document_type, file_storage):
    """Store a document for an application, replacing any previous upload of
    the same type. Caller is responsible for committing the session.

    The new file is written before the database row changes; if the database
    step fails, the new file is removed again.
    """
    extension, data, original = validate_upload(file_storage, document_type)

    directory = os.path.join(upload_root(), str(application.id))
    os.makedirs(directory, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}.{extension}"
    relative_path = os.path.join("documents", str(application.id), stored_name)
    full_path = _absolute_path(relative_path)

    with open(full_path, "wb") as handle:
        handle.write(data)

    existing = Document.query.filter_by(
        application_id=application.id,
        document_type=document_type
    ).first()

    old_path = None
    if existing:
        old_path = existing.file_path
        existing.file_name = original
        existing.file_path = relative_path
        existing.status = "pending"
        existing.remarks = None
        existing.reviewed_at = None
        document = existing
    else:
        document = Document(
            application_id=application.id,
            document_type=document_type,
            file_name=original,
            file_path=relative_path,
            status="pending",
        )
        db.session.add(document)

    try:
        db.session.flush()
    except Exception:
        remove_file(relative_path)
        raise

    # The caller commits, then calls remove_file(old_path) if it is set.
    return document, old_path


def remove_file(relative_path):
    """Best-effort removal of a stored file (used after a replacement)."""
    if not relative_path:
        return
    try:
        os.remove(_absolute_path(relative_path))
    except (OSError, DocumentError):
        pass


def open_document_path(document):
    """Return the absolute path of a stored document, verifying it exists."""
    full = _absolute_path(document.file_path)
    if not os.path.isfile(full):
        raise DocumentError("The file is no longer available on the server.")
    return full
