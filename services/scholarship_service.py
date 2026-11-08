"""Scholarship administration and student-facing search."""

from datetime import date
from decimal import Decimal

from flask import current_app
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Scholarship, EligibilityRule, ScholarshipRequiredDocument, Application
from services.eligibility_service import RuleError, validate_rule, scholarship_accepts
from services.constants import DOCUMENT_TYPE_LABELS


class ScholarshipError(ValueError):
    pass


def save_scholarship(scholarship, data):
    """Create or update a scholarship from validated form data (dict).

    `scholarship` may be a new Scholarship() instance. Caller commits.
    """
    if data["application_end_date"] and data["application_start_date"]:
        if data["application_end_date"] < data["application_start_date"]:
            raise ScholarshipError("The deadline cannot be before the start date.")

    scholarship.name = data["name"].strip()
    scholarship.provider = (data.get("provider") or "").strip() or None
    scholarship.description = (data.get("description") or "").strip() or None
    scholarship.scholarship_amount = data.get("scholarship_amount")
    scholarship.application_start_date = data.get("application_start_date")
    scholarship.application_end_date = data.get("application_end_date")
    scholarship.is_active = bool(data.get("is_active"))
    db.session.add(scholarship)
    db.session.flush()
    return scholarship


def set_required_documents(scholarship, document_types, mandatory_types):
    """Replace the scholarship's required-document list."""
    valid = [t for t in document_types if t in DOCUMENT_TYPE_LABELS]
    ScholarshipRequiredDocument.query.filter_by(
        scholarship_id=scholarship.id
    ).delete(synchronize_session=False)
    for doc_type in valid:
        db.session.add(ScholarshipRequiredDocument(
            scholarship_id=scholarship.id,
            document_type=doc_type,
            is_mandatory=doc_type in mandatory_types,
        ))
    db.session.flush()


def add_rule(scholarship, criteria_key, operator, criteria_value):
    try:
        validate_rule(criteria_key, operator, criteria_value)
    except RuleError as error:
        raise ScholarshipError(str(error))

    rule = EligibilityRule(
        scholarship_id=scholarship.id,
        criteria_key=criteria_key,
        operator=operator,
        criteria_value=str(criteria_value).strip(),
    )
    db.session.add(rule)
    db.session.flush()
    return rule


def delete_rule(rule):
    db.session.delete(rule)


def delete_or_deactivate(scholarship):
    """Hard-delete a scholarship only when nobody has applied to it.

    Otherwise deactivate it so application history is preserved.
    Returns "deleted" or "deactivated". Caller commits.
    """
    has_applications = db.session.query(Application.id).filter_by(
        scholarship_id=scholarship.id
    ).first() is not None

    if has_applications:
        scholarship.is_active = False
        return "deactivated"

    db.session.delete(scholarship)
    return "deleted"


def search_scholarships(filters, page, per_page=None, active_only=True, today=None):
    """Server-side search with pagination.

    filters keys (all optional):
      q           - text in name or provider
      category    - only scholarships that accept this category
      course      - only scholarships that accept this course
      min_amount / max_amount - Decimal bounds on scholarship amount
      deadline_before - date; deadline on or before this date
    Returns a list of matching scholarships and the total count.
    """
    per_page = per_page or current_app.config["ITEMS_PER_PAGE"]
    today = today or date.today()

    query = Scholarship.query
    if active_only:
        query = query.filter(Scholarship.is_active.is_(True))

    text = (filters.get("q") or "").strip()
    if text:
        like = f"%{text}%"
        query = query.filter(or_(Scholarship.name.ilike(like),
                                 Scholarship.provider.ilike(like)))

    if filters.get("min_amount") is not None:
        query = query.filter(Scholarship.scholarship_amount >= filters["min_amount"])
    if filters.get("max_amount") is not None:
        query = query.filter(Scholarship.scholarship_amount <= filters["max_amount"])
    if filters.get("deadline_before"):
        query = query.filter(Scholarship.application_end_date <= filters["deadline_before"])

    candidates = query.order_by(Scholarship.application_end_date.asc(),
                                Scholarship.id.asc()).all()

    # Category/course filters depend on the configured eligibility rules,
    # so they are evaluated with the same logic as the eligibility engine.
    category = (filters.get("category") or "").strip()
    course = (filters.get("course") or "").strip()
    matched = []
    for scholarship in candidates:
        if category and not scholarship_accepts(scholarship, "category", category):
            continue
        if course and not scholarship_accepts(scholarship, "course", course):
            continue
        matched.append(scholarship)

    total = len(matched)
    start = (page - 1) * per_page
    items = matched[start:start + per_page]
    return items, total


def scholarship_totals():
    total = Scholarship.query.count()
    active = Scholarship.query.filter_by(is_active=True).count()
    return total, active
