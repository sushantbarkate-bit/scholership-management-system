from extensions import db


class ScholarshipRequiredDocument(db.Model):
    """A document type a student must upload for a given scholarship."""

    __tablename__ = "scholarship_required_documents"

    id = db.Column(db.Integer, primary_key=True)

    scholarship_id = db.Column(
        db.Integer,
        db.ForeignKey("scholarships.id"),
        nullable=False
    )

    document_type = db.Column(db.String(100), nullable=False)

    is_mandatory = db.Column(db.Boolean, nullable=False, default=True)

    scholarship = db.relationship(
        "Scholarship",
        back_populates="required_documents"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "scholarship_id",
            "document_type",
            name="unique_scholarship_document"
        ),
    )
