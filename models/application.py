from extensions import db
from datetime import datetime


class Application(db.Model):

    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student_profiles.id"),
        nullable=False,
        index=True
    )

    scholarship_id = db.Column(
        db.Integer,
        db.ForeignKey("scholarships.id"),
        nullable=False,
        index=True
    )

    # draft, submitted, under_review, documents_required, approved, rejected
    status = db.Column(
        db.String(30),
        default="draft",
        nullable=False,
        index=True
    )

    admin_remarks = db.Column(db.Text)

    applied_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # Set when the student submits (moves the application out of draft).
    submitted_at = db.Column(db.DateTime)

    student = db.relationship("StudentProfile")

    scholarship = db.relationship(
        "Scholarship",
        back_populates="applications"
    )

    documents = db.relationship(
        "Document",
        back_populates="application",
        cascade="all, delete-orphan"
    )

    status_history = db.relationship(
        "ApplicationStatusHistory",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationStatusHistory.changed_at"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "scholarship_id",
            name="unique_student_scholarship"
        ),
    )

    @property
    def reference_number(self):
        """Human-readable reference, e.g. MSS-2026-00042."""
        if self.id is None:
            return None
        year = (self.applied_at or datetime.utcnow()).year
        return f"MSS-{year}-{self.id:05d}"
