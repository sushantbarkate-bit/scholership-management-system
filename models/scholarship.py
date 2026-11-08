from extensions import db
from datetime import datetime


class Scholarship(db.Model):

    __tablename__ = "scholarships"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(db.Text)

    provider = db.Column(db.String(200))

    scholarship_amount = db.Column(
        db.Numeric(12, 2)
    )

    application_start_date = db.Column(db.Date)

    # Acts as the application deadline.
    application_end_date = db.Column(db.Date)

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    # True for sample records seeded by database/seed_data.py.
    is_demo = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    eligibility_rules = db.relationship(
        "EligibilityRule",
        back_populates="scholarship",
        cascade="all, delete-orphan",
        order_by="EligibilityRule.id"
    )

    required_documents = db.relationship(
        "ScholarshipRequiredDocument",
        back_populates="scholarship",
        cascade="all, delete-orphan",
        order_by="ScholarshipRequiredDocument.id"
    )

    applications = db.relationship(
        "Application",
        back_populates="scholarship"
    )
