from extensions import db


class EligibilityRule(db.Model):

    __tablename__ = "eligibility_rules"

    id = db.Column(db.Integer, primary_key=True)

    scholarship_id = db.Column(
        db.Integer,
        db.ForeignKey("scholarships.id"),
        nullable=False
    )

    criteria_key = db.Column(
        db.String(100),
        nullable=False
    )

    operator = db.Column(
        db.String(20),
        nullable=False
    )

    criteria_value = db.Column(
        db.String(255),
        nullable=False
    )

    scholarship = db.relationship(
        "Scholarship",
        back_populates="eligibility_rules"
    )