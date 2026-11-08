"""Shared fixtures-as-functions for the test suite."""

import io
from datetime import date, timedelta
from decimal import Decimal

from extensions import db
from models import Scholarship, EligibilityRule, ScholarshipRequiredDocument, StudentProfile, User


PDF_BYTES = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\n%%EOF\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def complete_profile(user, **overrides):
    """Fill every tracked profile field so the profile is 100% complete."""
    profile = user.student_profile
    values = {
        "mobile": "9876543210",
        "gender": "Female",
        "address": "12 Shivaji Nagar, Pune",
        "city": "Pune",
        "district": "Pune",
        "state": "Maharashtra",
        "pincode": "411005",
        "category": "OBC",
        "annual_income": Decimal("200000"),
        "course": "MCA",
        "college_name": "Sample College",
        "university_name": "Sample University",
        "academic_year": "2026-27",
        "academic_percentage": Decimal("65.00"),
    }
    values.update(overrides)
    for attr, value in values.items():
        setattr(profile, attr, value)
    db.session.commit()
    return profile


def make_scholarship(name="Test Scheme", rules=(), documents=(), mandatory=None,
                     amount=Decimal("50000"), start=None, end=None, active=True):
    """rules: iterable of (criteria_key, operator, value)
    documents: iterable of document types; mandatory: subset (default: all)."""
    today = date.today()
    scholarship = Scholarship(
        name=name,
        provider="Test Provider",
        description="Test description",
        scholarship_amount=amount,
        application_start_date=start if start is not None else today - timedelta(days=30),
        application_end_date=end if end is not None else today + timedelta(days=60),
        is_active=active,
    )
    db.session.add(scholarship)
    db.session.flush()
    for key, op, value in rules:
        db.session.add(EligibilityRule(
            scholarship_id=scholarship.id, criteria_key=key,
            operator=op, criteria_value=value,
        ))
    mandatory = set(documents) if mandatory is None else set(mandatory)
    for doc_type in documents:
        db.session.add(ScholarshipRequiredDocument(
            scholarship_id=scholarship.id, document_type=doc_type,
            is_mandatory=doc_type in mandatory,
        ))
    db.session.commit()
    return scholarship


def pdf_upload(name="document.pdf", data=PDF_BYTES):
    """A werkzeug FileStorage, as the services receive from request.files."""
    from werkzeug.datastructures import FileStorage
    return FileStorage(stream=io.BytesIO(data), filename=name,
                       content_type="application/pdf")


def get_user(email):
    return User.query.filter_by(email=email).one()


def get_profile(email):
    return StudentProfile.query.join(User).filter(User.email == email).one()
