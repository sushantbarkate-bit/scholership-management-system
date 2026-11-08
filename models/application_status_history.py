from extensions import db
from datetime import datetime


class ApplicationStatusHistory(db.Model):

    __tablename__ = "application_status_history"

    id = db.Column(db.Integer, primary_key=True)

    application_id = db.Column(
        db.Integer,
        db.ForeignKey("applications.id"),
        nullable=False
    )

    previous_status = db.Column(db.String(30))

    new_status = db.Column(
        db.String(30),
        nullable=False
    )

    remarks = db.Column(db.Text)

    changed_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    application = db.relationship(
        "Application",
        back_populates="status_history"
    )