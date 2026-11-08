from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import current_user

from models import Scholarship
from routes.decorators import student_required
from services.eligibility_service import check_scholarship
from services.scholarship_service import search_scholarships
from services.constants import CATEGORY_CHOICES, DOCUMENT_TYPE_LABELS
from services.student_service import profile_completion
from services.pagination import ListPagination
from services.report_service import parse_date


scholarship_bp = Blueprint("scholarship", __name__, url_prefix="/scholarships")


def _decimal_arg(name):
    raw = request.args.get(name, "").strip()
    if not raw:
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


@scholarship_bp.route("/")
@student_required
def list_scholarships():
    page = request.args.get("page", 1, type=int) or 1

    filters = {
        "q": request.args.get("q", "").strip(),
        "category": request.args.get("category", "").strip(),
        "course": request.args.get("course", "").strip(),
        "min_amount": _decimal_arg("min_amount"),
        "max_amount": _decimal_arg("max_amount"),
        "deadline_before": parse_date(request.args.get("deadline_before", "")),
    }

    # Filter everything server-side, then paginate the matches.
    matches, total = search_scholarships(filters, page=1, per_page=10_000)
    pagination = ListPagination(matches, total, page, per_page=10)

    return render_template(
        "scholarships/list.html",
        pagination=pagination,
        total=total,
        filters=filters,
        categories=CATEGORY_CHOICES,
        today=date.today(),
    )


@scholarship_bp.route("/<int:scholarship_id>")
@student_required
def detail(scholarship_id):
    scholarship = Scholarship.query.get_or_404(scholarship_id)
    if not scholarship.is_active:
        abort(404)

    result = check_scholarship(current_user.student_profile, scholarship)
    percentage, missing = profile_completion(current_user.student_profile)

    return render_template(
        "scholarships/details.html",
        scholarship=scholarship,
        result=result,
        required_docs=scholarship.required_documents,
        doc_labels=DOCUMENT_TYPE_LABELS,
        existing=_existing_application(scholarship.id),
        profile_percentage=percentage,
    )


@scholarship_bp.route("/eligibility")
@student_required
def eligibility():
    """Eligibility checker: evaluates every active scholarship against the
    student's profile and groups the results."""
    profile = current_user.student_profile
    percentage, missing = profile_completion(profile)

    eligible, ineligible = [], []
    scholarships = Scholarship.query.filter_by(is_active=True).order_by(
        Scholarship.application_end_date.asc(), Scholarship.id.asc()
    ).all()

    for scholarship in scholarships:
        result = check_scholarship(profile, scholarship)
        bucket = eligible if result.eligible else ineligible
        bucket.append((scholarship, result))

    return render_template(
        "scholarships/eligibility.html",
        eligible=eligible,
        ineligible=ineligible,
        profile_percentage=percentage,
        missing_fields=missing,
        existing_ids={a.scholarship_id for a in _student_applications()},
    )


def _student_applications():
    from models import Application
    if current_user.student_profile is None:
        return []
    return Application.query.filter_by(student_id=current_user.student_profile.id).all()


def _existing_application(scholarship_id):
    for application in _student_applications():
        if application.scholarship_id == scholarship_id:
            return application
    return None
