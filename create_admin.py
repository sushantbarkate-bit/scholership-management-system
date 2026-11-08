from getpass import getpass

from app import app
from extensions import db
from models import User
from werkzeug.security import generate_password_hash


def create_admin():

    with app.app_context():

        print("Create Admin Account")

        full_name = input("Enter admin name: ").strip()
        email = input("Enter admin email: ").strip().lower()
        password = getpass("Enter admin password: ")
        confirm_password = getpass("Confirm admin password: ")

        if not full_name or not email:
            print("Name and email are required.")
            return

        if len(password) < 8:
            print("Password must contain at least 8 characters.")
            return

        if password != confirm_password:
            print("Passwords do not match.")
            return

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:
            print("An account with this email already exists.")
            return

        admin = User(
            full_name=full_name,
            email=email,
            password=generate_password_hash(password),
            role="admin"
        )

        try:
            db.session.add(admin)
            db.session.commit()

            print("Admin account created successfully!")

        except Exception as error:
            db.session.rollback()
            print(f"Failed to create admin: {error}")


if __name__ == "__main__":
    create_admin()