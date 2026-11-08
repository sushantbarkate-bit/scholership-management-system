"""Scholarship application workflow.

All status changes go through this module so that:
  * only allowed transitions happen,
  * every change is written to application_status_history,
  * the student receives a notification,
  * students cannot approve their own applications.
"""

from datetime import datetime

from sqlalchemy.exc import IntegrityError

from extensions import db
from models import (
    Application,
    ApplicationStatusHistory,
    Document,
    ScholarshipRequiredDocument,
)
from services import document_service
from services.constants import (
    APPLICATION_STATUSES,
    APPLICATION_TRANSITIONS,
    DOCUMENT_STATUSES,
    DOCUMENT_TYPE_LABELS,
)
from services.eligibility_service import check_scholarship
from services.notification_service import notify


class ApplicationError(ValueError):
    """A user-correctable workflow problem; the message is safe to show."""


class DuplicateApplicationError(ApplicationError):
    def __init__(self, application):
        super().__init__("You have already applied for this scholarship.")
        self.application = application


STATUS_MESSAGES = {
    "submitted": ("Application submitted",
                  "Your application {ref} for {name} has been submitted."),
    "under_review": ("Application under review",
                     "Your application {ref} for {name} is now under review."),
    "documents_required": ("Additional documents required",
                           "Application {ref} for {name} needs more documents. Remarks: {remarks}"),
    "approved": ("Application approved",
                 "Congratulations! Application {ref} for {name} has been approved. "
                 "This is the portal's status only; follow the scheme provider's instructions."),
    "rejected": ("Application rejected",
                 "Application {ref} for {name} was rejected. Remarks: {remarks}"),
}


def _notify_status(application, status, remarks=""):
    title, template = STATUS_MESSAGES[status]
    message = template.format(
        ref=application.reference_number or "(pending)",
        name=application.scholarship.name,
        remarks=remarks or "-",
    )
    notify(application.student.user_id, title, message)


def _ensure_not_self_action(actor, application):
    if actor is not None and application.student.user_id == actor.id:
        raise ApplicationError("You cannot review your own application.")


def mandatory_documents_missing(application):
    """Labels of mandatory documents that are not uploaded or are unusable."""
    required = ScholarshipRequiredDocument.query.filter_by(
        scholarship_id=application.scholarship_id, is_mandatory=True
    ).all()
    uploaded = {doc.document_type: doc for doc in application.documents}

    missing = []
    for item in required:
        doc = uploaded.get(item.document_type)
        if doc is None or doc.status in ("rejected", "resubmission_required"):
            missing.append(DOCUMENT_TYPE_LABELS.get(item.document_type, item.document_type))
    return missing


def mandatory_documents_unverified(application):
    required = ScholarshipRequiredDocument.query.filter_by(
        scholarship_id=application.scholarship_id, is_mandatory=True
    ).all()
    uploaded = {doc.document_type: doc for doc in application.documents}
    labels = []
    for item in required:
        doc = uploaded.get(item.document_type)
        if doc is None or doc.status != "verified":
            labels.append(DOCUMENT_TYPE_LABELS.get(item.document_type, item.document_type))
    return labels


def start_application(student, scholarship, today=None):
    """Create a draft application after validating eligibility."""
    if not scholarship.is_active:
        raise ApplicationError("This scholarship is closed for applications.")

    existing = Application.query.filter_by(
        student_id=student.id, scholarship_id=scholarship.id
    ).first()
    if existing:
        raise DuplicateApplicationError(existing)

    result = check_scholarship(student, scholarship, today)
    if not result.eligible:
        raise ApplicationError(
            "You are not eligible for this scholarship: " + " ".join(result.reasons)
        )

    application = Application(
        student_id=student.id,
        scholarship_id=scholarship.id,
        status="draft",
        applied_at=datetime.utcnow(),
    )
    db.session.add(application)
    try:
        db.session.flush()
        db.session.add(ApplicationStatusHistory(
            application_id=application.id,
            previous_status=None,
            new_status="draft",
            remarks="Draft created.",
        ))
        db.session.commit()
    except IntegrityError:
        # The unique (student, scholarship) constraint caught a race.
        db.session.rollback()
        existing = Application.query.filter_by(
            student_id=student.id, scholarship_id=scholarship.id
        ).first()
        raise DuplicateApplicationError(existing)
    except Exception:
        db.session.rollback()
        raise
    return application


def upload_student_document(application, document_type, file_storage):
    if application.status not in ("draft", "documents_required"):
        raise ApplicationError("Documents can no longer be changed for this application.")

    try:
        document, old_path = document_service.save_document(
            application, document_type, file_storage
        )
        previous = application.status
        if previous == "documents_required":
            application.status = "under_review"
            db.session.add(ApplicationStatusHistory(
                application_id=application.id,
                previous_status=previous,
                new_status="under_review",
                remarks=f"Student re-uploaded {DOCUMENT_TYPE_LABELS[document_type]}.",
            ))
        db.session.commit()
    except document_service.DocumentError as error:
        db.session.rollback()
        raise ApplicationError(str(error))
    except Exception:
        db.session.rollback()
        raise

    document_service.remove_file(old_path)
    return document


def submit_application(application, today=None):
    if application.status != "draft":
        raise ApplicationError("Only draft applications can be submitted.")

    result = check_scholarship(application.student, application.scholarship, today)
    if not result.eligible:
        raise ApplicationError(
            "Eligibility is no longer satisfied: " + " ".join(result.reasons)
        )

    missing = mandatory_documents_missing(application)
    if missing:
        raise ApplicationError(
            "Please upload these mandatory documents first: " + ", ".join(missing)
        )

    try:
        application.status = "submitted"
        application.submitted_at = datetime.utcnow()
        db.session.add(ApplicationStatusHistory(
            application_id=application.id,
            previous_status="draft",
            new_status="submitted",
            remarks="Application submitted by student.",
        ))
        _notify_status(application, "submitted")
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return application


def change_status(application, new_status, actor, remarks=None):
    """Admin-driven status change with validation and history."""
    if new_status not in APPLICATION_STATUSES:
        raise ApplicationError("Unknown status.")

    _ensure_not_self_action(actor, application)

    current = application.status
    if new_status not in APPLICATION_TRANSITIONS.get(current, set()):
        raise ApplicationError(
            f"Cannot change status from {APPLICATION_STATUSES[current][0]} "
            f"to {APPLICATION_STATUSES[new_status][0]}."
        )

    remarks = (remarks or "").strip()
    if new_status in ("documents_required", "rejected") and not remarks:
        raise ApplicationError("Please add remarks explaining the decision.")

    if new_status == "approved":
        unverified = mandatory_documents_unverified(application)
        if unverified:
            raise ApplicationError(
                "Verify all mandatory documents before approval. Pending: "
                + ", ".join(unverified)
            )

    try:
        application.status = new_status
        if remarks:
            application.admin_remarks = remarks
        db.session.add(ApplicationStatusHistory(
            application_id=application.id,
            previous_status=current,
            new_status=new_status,
            remarks=remarks or None,
        ))
        if new_status in STATUS_MESSAGES:
            _notify_status(application, new_status, remarks)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return application


def review_document(document, new_status, actor, remarks=None):
    if new_status not in ("verified", "rejected", "resubmission_required"):
        raise ApplicationError("Unknown document status.")

    _ensure_not_self_action(actor, document.application)

    remarks = (remarks or "").strip()
    if new_status != "verified" and not remarks:
        raise ApplicationError("Please add remarks for the student.")

    try:
        document.status = new_status
        document.remarks = remarks or None
        document.reviewed_at = datetime.utcnow()
        if new_status != "verified":
            application = document.application
            label = DOCUMENT_TYPE_LABELS.get(document.document_type, document.document_type)
            notify(
                application.student.user_id,
                f"{DOCUMENT_STATUSES[new_status][0]}: {label}",
                f"Your {label} for application {application.reference_number} "
                f"was marked '{DOCUMENT_STATUSES[new_status][0]}'. Remarks: {remarks}",
            )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return document


def document_for_student(document_id, student_profile_id):
    """Fetch a document only if it belongs to the given student."""
    document = db.session.get(Document, document_id)
    if document is None:
        return None
    if document.application.student_id != student_profile_id:
        return None
    return document
