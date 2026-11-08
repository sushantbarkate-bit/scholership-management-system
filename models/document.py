from extensions import db
from datetime import datetime


class Document(db.Model):

    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)

    application_id = db.Column(
        db.Integer,
        db.ForeignKey("applications.id"),
        nullable=False,
        index=True
    )

    document_type = db.Column(
        db.String(100),
        nullable=False
    )

    # Original (sanitised) name shown to users; never used as the storage path.
    file_name = db.Column(
        db.String(255),
        nullable=False
    )

    # Path relative to UPLOAD_FOLDER, using a generated secure name.
    file_path = db.Column(
        db.String(500),
        nullable=False
    )

    # pending, verified, rejected, resubmission_required
    status = db.Column(
        db.String(30),
        nullable=False,
        default="pending"
    )

    remarks = db.Column(db.Text)

    uploaded_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    reviewed_at = db.Column(db.DateTime)

    application = db.relationship(
        "Application",
        back_populates="documents"
    )
