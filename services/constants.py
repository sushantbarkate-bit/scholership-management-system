"""Shared constants used across services, forms and templates."""

# Document types a student can upload. Scholarships choose which of these
# are required (see ScholarshipRequiredDocument).
DOCUMENT_TYPES = [
    ("income_certificate", "Income Certificate"),
    ("caste_certificate", "Caste Certificate"),
    ("caste_validity_certificate", "Caste Validity Certificate"),
    ("domicile_certificate", "Domicile Certificate"),
    ("previous_marksheet", "Previous Academic Marksheet"),
    ("admission_receipt", "Current Admission Receipt"),
    ("bonafide_certificate", "Bonafide Certificate"),
    ("aadhaar_card", "Aadhaar Card (only where the scheme requires it)"),
]

DOCUMENT_TYPE_LABELS = dict(DOCUMENT_TYPES)

# Document review statuses.
DOCUMENT_STATUSES = {
    "pending": ("Pending", "secondary"),
    "verified": ("Verified", "success"),
    "rejected": ("Rejected", "danger"),
    "resubmission_required": ("Resubmission Required", "warning"),
}

# Application lifecycle statuses: code -> (label, bootstrap colour).
APPLICATION_STATUSES = {
    "draft": ("Draft", "secondary"),
    "submitted": ("Submitted", "primary"),
    "under_review": ("Under Review", "info"),
    "documents_required": ("Documents Required", "warning"),
    "approved": ("Approved", "success"),
    "rejected": ("Rejected", "danger"),
}

# Allowed status transitions. "draft -> submitted" happens only through
# application_service.submit_application, which runs extra validation.
APPLICATION_TRANSITIONS = {
    "draft": {"submitted"},
    "submitted": {"under_review", "documents_required", "approved", "rejected"},
    "under_review": {"documents_required", "approved", "rejected"},
    "documents_required": {"under_review", "rejected"},
    "approved": set(),
    "rejected": set(),
}

# Student profile fields that can be used in eligibility rules.
# key -> (human label, value kind, Student profile attribute)
ELIGIBILITY_FIELDS = {
    "category": ("Category", "text", "category"),
    "annual_income": ("Annual family income", "number", "annual_income"),
    "course": ("Course", "text", "course"),
    "academic_percentage": ("Academic percentage", "number", "academic_percentage"),
    "state": ("Domicile state", "text", "state"),
    "academic_year": ("Academic year", "text", "academic_year"),
    "gender": ("Gender", "text", "gender"),
    "district": ("District", "text", "district"),
    "college_name": ("College name", "text", "college_name"),
    "university_name": ("University name", "text", "university_name"),
}

# Operator code -> (label, phrase used in explanations, needs a list value)
OPERATORS = {
    "equal": ("equal to", "equal to", False),
    "not_equal": ("not equal to", "not equal to", False),
    "less_than": ("less than", "less than", False),
    "less_than_equal": ("less than or equal to", "at most", False),
    "greater_than": ("greater than", "more than", False),
    "greater_than_equal": ("greater than or equal to", "at least", False),
    "in": ("in list", "one of", True),
    "not_in": ("not in list", "none of", True),
}

CATEGORY_CHOICES = ["OPEN", "OBC", "SC", "ST", "VJNT", "SBC", "EWS"]
