from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import current_user

from extensions import db
from models import Application, Scholarship, ScholarshipRequiredDocument
from forms.application_form import DocumentUploadForm
from routes.decorators import student_required
from services import application_service as apps
from services.constants import APPLICATION_STATUSES, DOCUMENT_STATUSES, DOCUMENT_TYPE_LABELS
from services.eligibility_service import check_scholarship


application_bp = Blueprint("application", __name__, url_prefix="/applications")


def _own_application_or_404(application_id):
    application = db.session.get(Application, application_id)
    if application is None or application.student_id != current_user.student_profile.id:
        # 404 (not 403) so that other students' IDs cannot be probed.
        abort(404)
    return application


@application_bp.route("/")
@student_required
def list_applications():
    profile = current_user.student_profile
    applications = []
    if profile is not None:
        applications = (
            Application.query.filter_by(student_id=profile.id)
            .order_by(Application.applied_at.desc())
            .all()
        )
    return render_template(
        "applications/list.html",
        applications=applications,
        statuses=APPLICATION_STATUSES,
    )


@application_bp.route("/apply/<int:scholarship_id>", methods=["POST"])
@student_required
def apply(scholarship_id):
    scholarship = Scholarship.query.get_or_404(scholarship_id)
    try:
        application = apps.start_application(current_user.student_profile, scholarship)
        flash("Application started. Upload your documents and submit when ready.", "success")
        return redirect(url_for("application.detail", application_id=application.id))
    except apps.DuplicateApplicationError as error:
        flash(str(error), "warning")
        return redirect(url_for("application.detail", application_id=error.application.id))
    except apps.ApplicationError as error:
        flash(str(error), "danger")
        return redirect(url_for("scholarship.detail", scholarship_id=scholarship.id))


@application_bp.route("/<int:application_id>")
@student_required
def detail(application_id):
    application = _own_application_or_404(application_id)
    scholarship = application.scholarship

    result = check_scholarship(application.student, scholarship)
    required = ScholarshipRequiredDocument.query.filter_by(
        scholarship_id=scholarship.id
    ).all()
    uploaded = {doc.document_type: doc for doc in application.documents}
    missing = apps.mandatory_documents_missing(application)

    return render_template(
        "applications/detail.html",
        application=application,
        scholarship=scholarship,
        result=result,
        required=required,
        uploaded=uploaded,
        missing=missing,
        form=DocumentUploadForm(),
        doc_labels=DOCUMENT_TYPE_LABELS,
        doc_statuses=DOCUMENT_STATUSES,
        statuses=APPLICATION_STATUSES,
        can_edit=application.status in ("draft", "documents_required"),
        timeline=application.status_history,
    )


@application_bp.route("/<int:application_id>/documents", methods=["POST"])
@student_required
def upload_document(application_id):
    application = _own_application_or_404(application_id)
    form = DocumentUploadForm()

    if not form.validate_on_submit():
        for error in form.file.errors + form.document_type.errors:
            flash(error, "danger")
        return redirect(url_for("application.detail", application_id=application.id))

    try:
        apps.upload_student_document(application, form.document_type.data, form.file.data)
        flash("Document uploaded successfully.", "success")
    except apps.ApplicationError as error:
        flash(str(error), "danger")

    return redirect(url_for("application.detail", application_id=application.id))


@application_bp.route("/<int:application_id>/submit", methods=["POST"])
@student_required
def submit(application_id):
    application = _own_application_or_404(application_id)
    try:
        apps.submit_application(application)
        flash(
            f"Application submitted. Your reference number is {application.reference_number}.",
            "success",
        )
    except apps.ApplicationError as error:
        flash(str(error), "danger")

    return redirect(url_for("application.detail", application_id=application.id))
