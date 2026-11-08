from datetime import date, datetime, time

from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user

from extensions import db
from models import (
    Application,
    Document,
    EligibilityRule,
    Scholarship,
    ScholarshipRequiredDocument,
    StudentProfile,
    User,
)
from forms.scholarship_form import ScholarshipForm, EligibilityRuleForm
from forms.application_form import ApplicationReviewForm, DocumentReviewForm
from routes.decorators import admin_required
from services import application_service as apps
from services import scholarship_service as sch
from services.constants import (
    APPLICATION_STATUSES,
    CATEGORY_CHOICES,
    DOCUMENT_STATUSES,
    DOCUMENT_TYPE_LABELS,
    ELIGIBILITY_FIELDS,
    OPERATORS,
)
from services.eligibility_service import check_scholarship
from services.report_service import parse_date
from services.student_service import profile_completion


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _per_page():
    return current_app.config["ITEMS_PER_PAGE"]


# ---------------------------------------------------------------- dashboard

@admin_bp.route("/")
@admin_required
def dashboard():
    total_students = User.query.filter_by(role="student").count()
    total_scholarships = Scholarship.query.count()
    active_scholarships = Scholarship.query.filter_by(is_active=True).count()

    status_counts = {code: 0 for code in APPLICATION_STATUSES}
    for status, count in (
        db.session.query(Application.status, db.func.count(Application.id))
        .filter(Application.status != "draft")
        .group_by(Application.status)
        .all()
    ):
        status_counts[status] = count
    total_applications = sum(status_counts.values())

    recent_students = (User.query.filter_by(role="student")
                       .order_by(User.created_at.desc()).limit(5).all())
    recent_applications = (Application.query.filter(Application.status != "draft")
                           .order_by(Application.applied_at.desc()).limit(5).all())

    per_scholarship = []
    for scholarship in Scholarship.query.order_by(Scholarship.name).all():
        count = Application.query.filter(
            Application.scholarship_id == scholarship.id,
            Application.status != "draft",
        ).count()
        per_scholarship.append((scholarship, count))

    return render_template(
        "admin/dashboard.html",
        total_students=total_students,
        total_scholarships=total_scholarships,
        active_scholarships=active_scholarships,
        total_applications=total_applications,
        status_counts=status_counts,
        statuses=APPLICATION_STATUSES,
        recent_students=recent_students,
        recent_applications=recent_applications,
        per_scholarship=per_scholarship,
    )


# ----------------------------------------------------------------- students

@admin_bp.route("/students")
@admin_required
def students():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int) or 1

    query = User.query.filter_by(role="student")
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(User.full_name.ilike(like), User.email.ilike(like)))
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=_per_page(), error_out=False
    )
    return render_template("admin/students.html", pagination=pagination, q=q)


@admin_bp.route("/students/<int:user_id>")
@admin_required
def student_detail(user_id):
    user = db.session.get(User, user_id)
    if user is None or user.role != "student":
        abort(404)
    profile = user.student_profile
    percentage, missing = profile_completion(profile)
    applications = []
    if profile is not None:
        applications = (Application.query.filter_by(student_id=profile.id)
                        .order_by(Application.applied_at.desc()).all())
    return render_template(
        "admin/student_detail.html",
        student=user,
        profile=profile,
        percentage=percentage,
        missing=missing,
        applications=applications,
        statuses=APPLICATION_STATUSES,
    )


# ------------------------------------------------------------ scholarships

@admin_bp.route("/scholarships")
@admin_required
def scholarships():
    q = request.args.get("q", "").strip()
    state = request.args.get("state", "")
    page = request.args.get("page", 1, type=int) or 1

    query = Scholarship.query
    if q:
        query = query.filter(Scholarship.name.ilike(f"%{q}%"))
    if state == "active":
        query = query.filter_by(is_active=True)
    elif state == "inactive":
        query = query.filter_by(is_active=False)

    pagination = query.order_by(Scholarship.id.desc()).paginate(
        page=page, per_page=_per_page(), error_out=False
    )
    return render_template("admin/scholarships.html", pagination=pagination,
                           q=q, state=state, today=date.today())


def _fill_form_from_scholarship(form, scholarship):
    form.required_documents.data = [d.document_type for d in scholarship.required_documents]
    form.mandatory_documents.data = [d.document_type for d in scholarship.required_documents
                                     if d.is_mandatory]


def _scholarship_form_data(form):
    return {
        "name": form.name.data,
        "provider": form.provider.data,
        "description": form.description.data,
        "scholarship_amount": form.scholarship_amount.data,
        "application_start_date": form.application_start_date.data,
        "application_end_date": form.application_end_date.data,
        "is_active": form.is_active.data,
    }


@admin_bp.route("/scholarships/new", methods=["GET", "POST"])
@admin_required
def scholarship_create():
    form = ScholarshipForm()
    if form.validate_on_submit():
        try:
            scholarship = Scholarship()
            sch.save_scholarship(scholarship, _scholarship_form_data(form))
            sch.set_required_documents(scholarship, form.required_documents.data,
                                       form.mandatory_documents.data)
            db.session.commit()
            flash("Scholarship created. Now add its eligibility rules.", "success")
            return redirect(url_for("admin.scholarship_detail", scholarship_id=scholarship.id))
        except sch.ScholarshipError as error:
            db.session.rollback()
            flash(str(error), "danger")
        except Exception:
            db.session.rollback()
            flash("Unable to save the scholarship. Please try again.", "danger")
    return render_template("admin/scholarship_form.html", form=form, scholarship=None)


@admin_bp.route("/scholarships/<int:scholarship_id>/edit", methods=["GET", "POST"])
@admin_required
def scholarship_edit(scholarship_id):
    scholarship = db.session.get(Scholarship, scholarship_id)
    if scholarship is None:
        abort(404)

    form = ScholarshipForm(obj=scholarship)
    if request.method == "GET":
        _fill_form_from_scholarship(form, scholarship)

    if form.validate_on_submit():
        try:
            sch.save_scholarship(scholarship, _scholarship_form_data(form))
            sch.set_required_documents(scholarship, form.required_documents.data,
                                       form.mandatory_documents.data)
            db.session.commit()
            flash("Scholarship updated.", "success")
            return redirect(url_for("admin.scholarship_detail", scholarship_id=scholarship.id))
        except sch.ScholarshipError as error:
            db.session.rollback()
            flash(str(error), "danger")
        except Exception:
            db.session.rollback()
            flash("Unable to update the scholarship. Please try again.", "danger")

    return render_template("admin/scholarship_form.html", form=form, scholarship=scholarship)


@admin_bp.route("/scholarships/<int:scholarship_id>")
@admin_required
def scholarship_detail(scholarship_id):
    scholarship = db.session.get(Scholarship, scholarship_id)
    if scholarship is None:
        abort(404)

    application_count = Application.query.filter(
        Application.scholarship_id == scholarship.id,
        Application.status != "draft",
    ).count()

    return render_template(
        "admin/scholarship_detail.html",
        scholarship=scholarship,
        rule_form=EligibilityRuleForm(),
        field_labels=ELIGIBILITY_FIELDS,
        operator_labels=OPERATORS,
        doc_labels=DOCUMENT_TYPE_LABELS,
        application_count=application_count,
    )


@admin_bp.route("/scholarships/<int:scholarship_id>/delete", methods=["POST"])
@admin_required
def scholarship_delete(scholarship_id):
    scholarship = db.session.get(Scholarship, scholarship_id)
    if scholarship is None:
        abort(404)
    try:
        outcome = sch.delete_or_deactivate(scholarship)
        db.session.commit()
        if outcome == "deleted":
            flash("Scholarship deleted.", "success")
        else:
            flash("This scholarship already has applications, so it was deactivated "
                  "instead of deleted. Application history is preserved.", "info")
    except Exception:
        db.session.rollback()
        flash("Unable to delete the scholarship.", "danger")
    return redirect(url_for("admin.scholarships"))


@admin_bp.route("/scholarships/<int:scholarship_id>/rules", methods=["POST"])
@admin_required
def rule_add(scholarship_id):
    scholarship = db.session.get(Scholarship, scholarship_id)
    if scholarship is None:
        abort(404)
    form = EligibilityRuleForm()
    if form.validate_on_submit():
        try:
            sch.add_rule(scholarship, form.criteria_key.data, form.operator.data,
                         form.criteria_value.data)
            db.session.commit()
            flash("Eligibility rule added.", "success")
        except sch.ScholarshipError as error:
            db.session.rollback()
            flash(str(error), "danger")
    else:
        flash("Please check the rule fields and try again.", "danger")
    return redirect(url_for("admin.scholarship_detail", scholarship_id=scholarship_id))


@admin_bp.route("/scholarships/<int:scholarship_id>/rules/<int:rule_id>/delete", methods=["POST"])
@admin_required
def rule_delete(scholarship_id, rule_id):
    rule = db.session.get(EligibilityRule, rule_id)
    if rule is None or rule.scholarship_id != scholarship_id:
        abort(404)
    try:
        sch.delete_rule(rule)
        db.session.commit()
        flash("Eligibility rule removed.", "success")
    except Exception:
        db.session.rollback()
        flash("Unable to remove the rule.", "danger")
    return redirect(url_for("admin.scholarship_detail", scholarship_id=scholarship_id))


# ------------------------------------------------------------ applications

@admin_bp.route("/applications")
@admin_required
def applications():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    scholarship_id = request.args.get("scholarship_id", type=int)
    date_from = parse_date(request.args.get("date_from", ""))
    date_to = parse_date(request.args.get("date_to", ""))
    page = request.args.get("page", 1, type=int) or 1

    query = (Application.query
             .join(Application.student)
             .join(StudentProfile.user)
             .join(Application.scholarship)
             .filter(Application.status != "draft"))

    if q:
        like = f"%{q}%"
        conditions = [
            User.full_name.ilike(like),
            User.email.ilike(like),
            Scholarship.name.ilike(like),
        ]
        if q.isdigit():
            conditions.append(Application.id == int(q))
        query = query.filter(db.or_(*conditions))
    if status in APPLICATION_STATUSES:
        query = query.filter(Application.status == status)
    if scholarship_id:
        query = query.filter(Application.scholarship_id == scholarship_id)
    if date_from:
        query = query.filter(Application.applied_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(Application.applied_at <= datetime.combine(date_to, time.max))

    pagination = query.order_by(Application.applied_at.desc()).paginate(
        page=page, per_page=_per_page(), error_out=False
    )
    return render_template(
        "admin/applications.html",
        pagination=pagination,
        statuses=APPLICATION_STATUSES,
        scholarships=Scholarship.query.order_by(Scholarship.name).all(),
        filters={"q": q, "status": status, "scholarship_id": scholarship_id,
                 "date_from": request.args.get("date_from", ""),
                 "date_to": request.args.get("date_to", "")},
    )


@admin_bp.route("/applications/<int:application_id>")
@admin_required
def application_detail(application_id):
    application = db.session.get(Application, application_id)
    if application is None:
        abort(404)

    scholarship = application.scholarship
    result = check_scholarship(application.student, scholarship)
    required = ScholarshipRequiredDocument.query.filter_by(
        scholarship_id=scholarship.id).all()
    uploaded = {doc.document_type: doc for doc in application.documents}
    percentage, missing_profile = profile_completion(application.student)

    return render_template(
        "admin/application_detail.html",
        application=application,
        student=application.student.user,
        profile=application.student,
        scholarship=scholarship,
        result=result,
        required=required,
        uploaded=uploaded,
        doc_labels=DOCUMENT_TYPE_LABELS,
        doc_statuses=DOCUMENT_STATUSES,
        statuses=APPLICATION_STATUSES,
        status_form=ApplicationReviewForm(),
        doc_form=DocumentReviewForm(),
        unverified=apps.mandatory_documents_unverified(application),
        missing=apps.mandatory_documents_missing(application),
        profile_percentage=percentage,
        timeline=application.status_history,
    )


@admin_bp.route("/applications/<int:application_id>/status", methods=["POST"])
@admin_required
def application_status(application_id):
    application = db.session.get(Application, application_id)
    if application is None:
        abort(404)
    form = ApplicationReviewForm()
    if not form.validate_on_submit():
        flash("Please choose a valid status.", "danger")
        return redirect(url_for("admin.application_detail", application_id=application_id))
    try:
        apps.change_status(application, form.status.data, current_user, form.remarks.data)
        flash(f"Status changed to {APPLICATION_STATUSES[form.status.data][0]}.", "success")
    except apps.ApplicationError as error:
        flash(str(error), "danger")
    return redirect(url_for("admin.application_detail", application_id=application_id))


@admin_bp.route("/documents/<int:document_id>/review", methods=["POST"])
@admin_required
def document_review(document_id):
    document = db.session.get(Document, document_id)
    if document is None:
        abort(404)
    form = DocumentReviewForm()
    if not form.validate_on_submit():
        flash("Please choose a valid decision.", "danger")
    else:
        try:
            apps.review_document(document, form.status.data, current_user, form.remarks.data)
            flash("Document decision saved.", "success")
        except apps.ApplicationError as error:
            flash(str(error), "danger")
    return redirect(url_for("admin.application_detail",
                            application_id=document.application_id))
