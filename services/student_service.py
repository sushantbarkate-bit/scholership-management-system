"""Student profile completeness and dashboard figures (all from the database)."""

from models import Application, Scholarship
from services.notification_service import unread_count
from services.scholarship_service import search_scholarships
from services.eligibility_service import check_scholarship


PROFILE_FIELDS = [
    ("mobile", "Mobile number"),
    ("gender", "Gender"),
    ("address", "Address"),
    ("city", "City"),
    ("district", "District"),
    ("state", "State"),
    ("pincode", "Pincode"),
    ("category", "Category"),
    ("annual_income", "Annual family income"),
    ("course", "Course"),
    ("college_name", "College name"),
    ("university_name", "University name"),
    ("academic_year", "Academic year"),
    ("academic_percentage", "Academic percentage"),
]


def _filled(value):
    return value is not None and str(value).strip() != ""


def profile_completion(profile):
    """Returns (percentage, list of missing field labels)."""
    if profile is None:
        return 0, [label for _, label in PROFILE_FIELDS]

    missing = [label for attr, label in PROFILE_FIELDS
               if not _filled(getattr(profile, attr, None))]
    filled = len(PROFILE_FIELDS) - len(missing)
    return int(filled / len(PROFILE_FIELDS) * 100), missing


def dashboard_summary(user, profile):
    """Figures for the student dashboard."""
    counts = {"total": 0, "pending": 0, "approved": 0, "rejected": 0,
              "documents_required": 0}

    if profile is not None:
        applications = Application.query.filter(
            Application.student_id == profile.id,
            Application.status != "draft",
        ).order_by(Application.applied_at.desc()).all()

        for application in applications:
            counts["total"] += 1
            if application.status in ("submitted", "under_review"):
                counts["pending"] += 1
            elif application.status == "approved":
                counts["approved"] += 1
            elif application.status == "rejected":
                counts["rejected"] += 1
            elif application.status == "documents_required":
                counts["documents_required"] += 1
        recent = applications[:5]
    else:
        recent = []

    active_scholarships = Scholarship.query.filter_by(is_active=True).all()
    eligible_count = 0
    if profile is not None:
        eligible_count = sum(
            1 for s in active_scholarships
            if check_scholarship(profile, s).eligible
        )

    return {
        "counts": counts,
        "recent_applications": recent,
        "active_scholarships": len(active_scholarships),
        "eligible_scholarships": eligible_count,
        "unread_notifications": unread_count(user.id),
    }


def recommended_scholarships(profile, limit=5):
    """Active scholarships the student is eligible for right now."""
    if profile is None:
        return []
    items, _ = search_scholarships({}, page=1, per_page=500)
    eligible = [s for s in items if check_scholarship(profile, s).eligible]
    return eligible[:limit]
