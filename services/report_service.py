"""Admin reports. Every number is computed from the database."""

import csv
import io
from collections import Counter, OrderedDict
from datetime import date, datetime, time

from models import Application, Scholarship, StudentProfile, User, Document
from services.constants import APPLICATION_STATUSES, DOCUMENT_STATUSES, DOCUMENT_TYPE_LABELS


def _filtered_applications(filters):
    """Applications joined with student + scholarship, filtered by date range,
    scholarship and category. Returns a SQLAlchemy query."""
    query = (
        Application.query
        .join(Application.student)
        .join(Application.scholarship)
        .filter(Application.status != "draft")
    )
    if filters.get("date_from"):
        query = query.filter(Application.applied_at >= datetime.combine(filters["date_from"], time.min))
    if filters.get("date_to"):
        query = query.filter(Application.applied_at <= datetime.combine(filters["date_to"], time.max))
    if filters.get("scholarship_id"):
        query = query.filter(Application.scholarship_id == filters["scholarship_id"])
    if filters.get("category"):
        query = query.filter(StudentProfile.category == filters["category"])
    return query


def student_registration_total(filters=None):
    query = User.query.filter_by(role="student")
    if filters and filters.get("date_from"):
        query = query.filter(User.created_at >= datetime.combine(filters["date_from"], time.min))
    if filters and filters.get("date_to"):
        query = query.filter(User.created_at <= datetime.combine(filters["date_to"], time.max))
    return query.count()


def students_by_course():
    rows = (
        StudentProfile.query.with_entities(StudentProfile.course)
        .filter(StudentProfile.course.isnot(None))
        .all()
    )
    counts = Counter((course or "").strip() or "Not specified" for (course,) in rows)
    return counts.most_common()


def application_report(filters):
    """Aggregates for the reports page."""
    applications = _filtered_applications(filters).with_entities(
        Application.id,
        Application.status,
        Application.applied_at,
        Scholarship.name,
        StudentProfile.category,
    ).all()

    by_status = Counter(status for _, status, _, _, _ in applications)
    by_scholarship = Counter(name for _, _, _, name, _ in applications)
    by_category = Counter((cat or "Not specified") for *_, cat in applications)

    monthly = OrderedDict()
    for _, _, applied_at, _, _ in sorted(applications, key=lambda r: r[2] or datetime.min):
        if applied_at:
            monthly[applied_at.strftime("%Y-%m")] = monthly.get(applied_at.strftime("%Y-%m"), 0) + 1

    approved = by_status.get("approved", 0)
    rejected = by_status.get("rejected", 0)

    return {
        "total": len(applications),
        "by_status": [(APPLICATION_STATUSES[s][0], by_status.get(s, 0))
                      for s in APPLICATION_STATUSES if s != "draft"],
        "status_codes": [s for s in APPLICATION_STATUSES if s != "draft"],
        "status_counts": [by_status.get(s, 0) for s in APPLICATION_STATUSES if s != "draft"],
        "by_scholarship": by_scholarship.most_common(),
        "by_category": by_category.most_common(),
        "monthly": list(monthly.items()),
        "approved": approved,
        "rejected": rejected,
        "decided": approved + rejected,
        "approval_rate": round(approved / (approved + rejected) * 100, 1)
        if (approved + rejected) else 0,
    }


def document_report():
    counts = Counter(status for (status,) in Document.query.with_entities(Document.status).all())
    return [(DOCUMENT_STATUSES[s][0], counts.get(s, 0)) for s in DOCUMENT_STATUSES]


def applications_csv(filters):
    """CSV text of filtered applications (one row per application)."""
    query = _filtered_applications(filters).order_by(Application.applied_at.desc())
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Reference", "Student name", "Student email", "Category", "Course",
        "Scholarship", "Status", "Applied on", "Submitted on", "Admin remarks",
    ])
    for application in query.all():
        student_user = application.student.user
        writer.writerow([
            application.reference_number,
            student_user.full_name,
            student_user.email,
            application.student.category or "",
            application.student.course or "",
            application.scholarship.name,
            APPLICATION_STATUSES[application.status][0],
            application.applied_at.strftime("%Y-%m-%d %H:%M") if application.applied_at else "",
            application.submitted_at.strftime("%Y-%m-%d %H:%M") if application.submitted_at else "",
            application.admin_remarks or "",
        ])
    return buffer.getvalue()


def scholarship_choices():
    return Scholarship.query.order_by(Scholarship.name).all()


def document_type_label(code):
    return DOCUMENT_TYPE_LABELS.get(code, code)


def parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
