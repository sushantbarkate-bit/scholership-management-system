from extensions import db
from datetime import datetime


class StudentProfile(db.Model):

    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    # Personal information
    mobile = db.Column(db.String(15))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(20))

    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    district = db.Column(db.String(100))
    state = db.Column(
        db.String(100),
        default="Maharashtra"
    )
    pincode = db.Column(db.String(10))

    # Category information
    category = db.Column(db.String(50))

    # Financial information
    annual_income = db.Column(db.Numeric(12, 2))

    # Educational information
    course = db.Column(db.String(100))
    college_name = db.Column(db.String(200))
    university_name = db.Column(db.String(200))
    academic_year = db.Column(db.String(20))
    academic_percentage = db.Column(db.Numeric(5, 2))

    # Metadata
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    user = db.relationship(
        "User",
        back_populates="student_profile"
    )