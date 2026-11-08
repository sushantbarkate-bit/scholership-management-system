"""Safe, idempotent demonstration data for the Scholarship Portal.

Run from the project folder:

    venv\\Scripts\\python.exe -m database.seed_data

What it creates (only if it does not already exist, matched by name/email):
  * 10 demo students            (email: demo.student01@example.com ... 10)
  * 8 demo scholarship schemes  (flagged is_demo = True)
  * eligibility rules and required documents for each scheme
  * demo applications in every status, with status history,
    placeholder documents and notifications

Nothing existing is modified or deleted. Your own administrator account
(create_admin.py) is never touched. The seeder also adds one DEMO admin
(demo.admin@example.com) with the demo password so the walkthrough and
screenshots can log in; delete that user before any real use.

IMPORTANT: every scheme here is an ILLUSTRATIVE sample. Its criteria are not
official government rules. Verify official notifications before using any
value from this file in a real scheme.
"""

import os
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from werkzeug.security import generate_password_hash

from app import create_app
from extensions import db
from models import (
    Application,
    ApplicationStatusHistory,
    Document,
    EligibilityRule,
    Notification,
    Scholarship,
    ScholarshipRequiredDocument,
    StudentProfile,
    User,
)


DEMO_PASSWORD = "Demo@12345"

# (full name, district, gender, category, annual income, course, percentage)
DEMO_STUDENTS = [
    ("Aarav Deshmukh", "Pune", "Male", "OPEN", "320000", "MCA", "72.40"),
    ("Sneha Kamble", "Nashik", "Female", "SC", "150000", "MCA", "68.00"),
    ("Rohit Pawar", "Ahmednagar", "Male", "OBC", "210000", "MCA", "58.75"),
    ("Priya Shinde", "Satara", "Female", "OBC", "180000", "MCA", "81.20"),
    ("Imran Shaikh", "Aurangabad", "Male", "OPEN", "450000", "MCA", "49.50"),
    ("Kavita Gaikwad", "Solapur", "Female", "ST", "120000", "MCA", "63.00"),
    ("Siddharth More", "Kolhapur", "Male", "VJNT", "95000", "MCA", "70.10"),
    ("Neha Jadhav", "Mumbai Suburban", "Female", "EWS", "240000", "MBA", "76.30"),
    ("Yash Kulkarni", "Pune", "Male", "SBC", "160000", "MCA", "55.00"),
    ("Anjali Patil", "Sangli", "Female", "OBC", "275000", "B.Sc", "88.50"),
]

# Illustrative schemes. "rules" = (criteria_key, operator, value)
DEMO_SCHOLARSHIPS = [
    {
        "name": "SC Post-Matric Scholarship (Demo)",
        "provider": "Social Justice Department (sample data)",
        "amount": "30000",
        "rules": [("category", "equal", "SC"),
                  ("annual_income", "less_than_equal", "250000"),
                  ("state", "equal", "Maharashtra")],
        "docs": ["income_certificate", "caste_certificate", "previous_marksheet",
                 "admission_receipt", "domicile_certificate"],
        "mandatory": ["income_certificate", "caste_certificate", "admission_receipt"],
    },
    {
        "name": "OBC Merit-cum-Means Scholarship (Demo)",
        "provider": "Backward Classes Welfare (sample data)",
        "amount": "25000",
        "rules": [("category", "equal", "OBC"),
                  ("annual_income", "less_than_equal", "250000"),
                  ("academic_percentage", "greater_than_equal", "50")],
        "docs": ["income_certificate", "caste_certificate", "previous_marksheet"],
        "mandatory": ["income_certificate", "caste_certificate"],
    },
    {
        "name": "Open Category Merit Grant (Demo)",
        "provider": "Higher Education Board (sample data)",
        "amount": "20000",
        "rules": [("category", "equal", "OPEN"),
                  ("annual_income", "less_than_equal", "400000"),
                  ("academic_percentage", "greater_than_equal", "65")],
        "docs": ["income_certificate", "previous_marksheet", "admission_receipt"],
        "mandatory": ["previous_marksheet", "admission_receipt"],
    },
    {
        "name": "Rajarshi Shahu Maharaj Support Scheme (Demo)",
        "provider": "Maharashtra Higher Education (sample data)",
        "amount": "40000",
        "rules": [("state", "equal", "Maharashtra"),
                  ("academic_percentage", "greater_than_equal", "55"),
                  ("annual_income", "less_than_equal", "300000")],
        "docs": ["income_certificate", "domicile_certificate", "bonafide_certificate"],
        "mandatory": ["domicile_certificate", "bonafide_certificate"],
    },
    {
        "name": "Girl Student Education Grant (Demo)",
        "provider": "Women and Child Development (sample data)",
        "amount": "18000",
        "rules": [("gender", "equal", "Female"),
                  ("annual_income", "less_than_equal", "300000")],
        "docs": ["income_certificate", "bonafide_certificate", "admission_receipt"],
        "mandatory": ["income_certificate", "admission_receipt"],
    },
    {
        "name": "VJNT and SBC Student Assistance (Demo)",
        "provider": "Tribal and Backward Welfare (sample data)",
        "amount": "22000",
        "rules": [("category", "in", "VJNT,SBC"),
                  ("annual_income", "less_than_equal", "200000")],
        "docs": ["income_certificate", "caste_certificate", "caste_validity_certificate"],
        "mandatory": ["income_certificate", "caste_certificate"],
    },
    {
        "name": "Higher Education Excellence Award (Demo)",
        "provider": "State Education Council (sample data)",
        "amount": "50000",
        "rules": [("academic_percentage", "greater_than_equal", "80"),
                  ("annual_income", "less_than_equal", "800000")],
        "docs": ["previous_marksheet", "admission_receipt"],
        "mandatory": ["previous_marksheet"],
    },
    {
        "name": "Postgraduate Computer Science Stipend (Demo)",
        "provider": "Technical Education Directorate (sample data)",
        "amount": "35000",
        "rules": [("course", "in", "MCA,M.Tech,MBA"),
                  ("academic_percentage", "greater_than_equal", "60")],
        "docs": ["income_certificate", "previous_marksheet", "admission_receipt"],
        "mandatory": ["previous_marksheet", "admission_receipt"],
    },
]

# Status to give each demo application, in the order students are listed.
# Index-based so the same run always produces the same mix.
DEMO_APPLICATION_PLAN = [
    # (student index, scholarship index, final status)
    (0, 2, "approved"),
    (1, 0, "submitted"),
    (2, 1, "under_review"),
    (3, 1, "documents_required"),
    (4, 2, "rejected"),
    (5, 0, "approved"),
    (6, 5, "under_review"),
    (7, 7, "submitted"),
    (8, 1, "rejected"),
    (9, 4, "approved"),
    (0, 6, "draft"),
    (3, 3, "submitted"),
]

PLACEHOLDER_PDF = (
    b"%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    b"2 0 obj << /Type /Pages /Kids [] /Count 0 >> endobj\n"
    b"%% DEMONSTRATION PLACEHOLDER - NOT A REAL CERTIFICATE\n%%EOF\n"
)


def _demo_email(index):
    return f"demo.student{index + 1:02d}@example.com"


DEMO_ADMIN_EMAIL = "demo.admin@example.com"


def _ensure_demo_admin():
    """A DEMO administrator so the screenshots and walkthroughs can log in.

    Your own admin account (created with create_admin.py) is never changed.
    This demo account uses the well-known demo password, so do not use this
    database for real data while it exists.
    """
    admin = User.query.filter_by(email=DEMO_ADMIN_EMAIL).first()
    if admin is None:
        admin = User(
            full_name="Demo Administrator",
            email=DEMO_ADMIN_EMAIL,
            password=generate_password_hash(DEMO_PASSWORD),
            role="admin",
        )
        db.session.add(admin)
        db.session.flush()
    return admin


def _ensure_students():
    students = []
    for index, (name, district, gender, category, income, course, pct) in enumerate(DEMO_STUDENTS):
        email = _demo_email(index)
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(
                full_name=name,
                email=email,
                password=generate_password_hash(DEMO_PASSWORD),
                role="student",
                created_at=datetime.utcnow() - timedelta(days=200 - index * 17),
            )
            db.session.add(user)
            db.session.flush()
        if user.student_profile is None:
            # Assign via the relationship so user.student_profile is set at once,
            # then flush so the profile gets its primary key.
            profile = StudentProfile(user=user)
            db.session.add(profile)
            db.session.flush()
        profile = user.student_profile
        if profile.mobile is None:  # only fill blank profiles; never overwrite
            profile.mobile = f"9{index:02d}00000{index:02d}"[:10].ljust(10, "1")
            profile.gender = gender
            profile.address = f"{index + 10}, Demo Lane, {district}"
            profile.city = district
            profile.district = district
            profile.state = "Maharashtra"
            profile.pincode = f"4{index:05d}"[:6].ljust(6, "0")
            profile.category = category
            profile.annual_income = Decimal(income)
            profile.course = course
            profile.college_name = "Demo College of Computer Applications"
            profile.university_name = "Demo State University"
            profile.academic_year = "2026-27"
            profile.academic_percentage = Decimal(pct)
        students.append(user)
    return students


def _ensure_scholarships():
    schemes = []
    for spec in DEMO_SCHOLARSHIPS:
        scholarship = Scholarship.query.filter_by(name=spec["name"]).first()
        if scholarship is None:
            today = date.today()
            scholarship = Scholarship(
                name=spec["name"],
                provider=spec["provider"],
                description=(
                    "Illustrative demonstration record. The criteria are sample values "
                    "for testing the eligibility engine and are NOT an official scheme. "
                    "Verify the official notification before relying on them."
                ),
                scholarship_amount=Decimal(spec["amount"]),
                application_start_date=today - timedelta(days=60),
                application_end_date=today + timedelta(days=90),
                is_active=True,
                is_demo=True,
            )
            db.session.add(scholarship)
            db.session.flush()
            for key, op, value in spec["rules"]:
                db.session.add(EligibilityRule(
                    scholarship_id=scholarship.id, criteria_key=key,
                    operator=op, criteria_value=value,
                ))
            for doc_type in spec["docs"]:
                db.session.add(ScholarshipRequiredDocument(
                    scholarship_id=scholarship.id, document_type=doc_type,
                    is_mandatory=doc_type in spec["mandatory"],
                ))
        schemes.append(scholarship)
    return schemes


def _write_placeholder(upload_root, application_id):
    directory = os.path.join(upload_root, "documents", str(application_id))
    os.makedirs(directory, exist_ok=True)
    stored = f"{uuid.uuid4().hex}.pdf"
    with open(os.path.join(directory, stored), "wb") as handle:
        handle.write(PLACEHOLDER_PDF)
    return os.path.join("documents", str(application_id), stored)


def _ensure_applications(students, schemes, upload_root):
    created = 0
    for s_index, sch_index, final_status in DEMO_APPLICATION_PLAN:
        student = students[s_index]
        scholarship = schemes[sch_index]
        profile = student.student_profile
        if Application.query.filter_by(student_id=profile.id,
                                       scholarship_id=scholarship.id).first():
            continue

        applied = datetime.utcnow() - timedelta(days=10 + s_index * 9 + sch_index * 3)
        application = Application(
            student_id=profile.id,
            scholarship_id=scholarship.id,
            status="draft",
            applied_at=applied,
        )
        db.session.add(application)
        db.session.flush()

        history = [(None, "draft", "Draft created (demo).")]
        if final_status != "draft":
            submitted = applied + timedelta(days=1)
            application.submitted_at = submitted
            history.append(("draft", "submitted", "Submitted by student (demo)."))

            # Upload every required document as a placeholder.
            for req in scholarship.required_documents:
                path = _write_placeholder(upload_root, application.id)
                db.session.add(Document(
                    application_id=application.id,
                    document_type=req.document_type,
                    file_name=f"{req.document_type}_demo.pdf",
                    file_path=path,
                    status="verified" if final_status == "approved" else "pending",
                    uploaded_at=applied + timedelta(hours=2),
                ))

        if final_status in ("under_review", "documents_required", "approved", "rejected"):
            history.append(("submitted", "under_review", "Review started (demo)."))
        if final_status == "documents_required":
            history.append(("under_review", "documents_required",
                            "Please upload a clearer scan of your certificate (demo)."))
        elif final_status == "approved":
            history.append(("under_review", "approved", "Approved (demo)."))
        elif final_status == "rejected":
            history.append(("under_review", "rejected", "Income is above the sample limit (demo)."))

        application.status = final_status
        if final_status in ("documents_required", "rejected", "approved"):
            application.admin_remarks = history[-1][2]

        for previous, new, remark in history:
            db.session.add(ApplicationStatusHistory(
                application_id=application.id,
                previous_status=previous,
                new_status=new,
                remarks=remark,
                changed_at=applied + timedelta(days=len(history)),
            ))

        db.session.add(Notification(
            user_id=student.id,
            title="Application status (demo)",
            message=f"Application for {scholarship.name} is now {final_status.replace('_', ' ')}.",
            is_read=False,
            created_at=applied + timedelta(days=2),
        ))
        created += 1
    return created


def seed():
    app = create_app()
    with app.app_context():
        upload_root = app.config["UPLOAD_FOLDER"]
        try:
            _ensure_demo_admin()
            students = _ensure_students()
            schemes = _ensure_scholarships()
            db.session.flush()
            created = _ensure_applications(students, schemes, upload_root)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        print(f"Demo students available : {len(students)}")
        print(f"Demo scholarships       : {len(schemes)}")
        print(f"New demo applications   : {created}")
        print(f"Demo student login      : {_demo_email(0)} / {DEMO_PASSWORD}")
        print(f"Demo admin login        : {DEMO_ADMIN_EMAIL} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    seed()
