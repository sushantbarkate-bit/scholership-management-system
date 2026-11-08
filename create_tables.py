from app import app
from extensions import db

# Import all models
from models import (
    User,
    StudentProfile,
    Scholarship,
    EligibilityRule,
    Application,
    Document,
    ApplicationStatusHistory
)


def create_tables():

    with app.app_context():

        db.create_all()

        print("Database tables created successfully!")


if __name__ == "__main__":
    create_tables()