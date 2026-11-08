from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models import User, StudentProfile
from forms.auth_form import ChangePasswordForm
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from routes.decorators import student_required, admin_required
from services.notification_service import notify
from services.student_service import dashboard_summary, recommended_scholarships, profile_completion


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# Registration form
class RegistrationForm(FlaskForm):

    full_name = StringField(
        "Full Name",
        validators=[DataRequired(), Length(min=3, max=150)]
    )

    email = StringField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=150)]
    )

    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8, max=128)]
    )

    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match.")
        ]
    )

    submit = SubmitField("Register")


# Login form
class LoginForm(FlaskForm):

    email = StringField(
        "Email",
        validators=[DataRequired(), Email()]
    )

    password = PasswordField(
        "Password",
        validators=[DataRequired()]
    )

    submit = SubmitField("Login")


def _safe_next_url():
    """Only allow relative redirects inside this site (prevents open redirects)."""
    target = request.args.get("next", "")
    if target.startswith("/") and not target.startswith("//"):
        return target
    return None


# Student registration
@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    form = RegistrationForm()

    if form.validate_on_submit():

        email = form.email.data.strip().lower()

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:
            flash("Email is already registered.", "danger")
            return render_template("auth/register.html", form=form)

        hashed_password = generate_password_hash(
            form.password.data
        )

        # role is always "student" here; the form never accepts a role field.
        new_user = User(
            full_name=form.full_name.data.strip(),
            email=email,
            password=hashed_password,
            role="student"
        )

        try:
            db.session.add(new_user)
            db.session.flush()

            student_profile = StudentProfile(user=new_user)
            db.session.add(student_profile)

            notify(
                new_user.id,
                "Welcome to the Scholarship Portal",
                "Your account is ready. Complete your profile to check "
                "scholarship eligibility.",
            )
            db.session.commit()

            flash("Registration successful! Please login.", "success")

            return redirect(url_for("auth.login"))

        except Exception:
            db.session.rollback()
            flash("Something went wrong. Please try again.", "danger")

    return render_template("auth/register.html", form=form)


# User login
@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    form = LoginForm()

    if form.validate_on_submit():

        email = form.email.data.strip().lower()

        user = User.query.filter_by(
            email=email
        ).first()

        if user and check_password_hash(
            user.password,
            form.password.data
        ):

            if not user.is_active:
                flash("Your account is inactive.", "danger")
                return render_template("auth/login.html", form=form)

            login_user(user)

            flash("Login successful!", "success")

            return redirect(_safe_next_url() or url_for("auth.dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html", form=form)


# Role-based dashboard redirection
@auth_bp.route("/dashboard")
@login_required
def dashboard():

    if current_user.role == "admin":
        return redirect(url_for("auth.admin_dashboard"))

    return redirect(url_for("auth.student_dashboard"))


# Student dashboard
@auth_bp.route("/student-dashboard")
@student_required
def student_dashboard():

    profile = current_user.student_profile
    summary = dashboard_summary(current_user, profile)
    summary["recommended"] = recommended_scholarships(profile)
    percentage, missing = profile_completion(profile)

    return render_template(
        "student/dashboard.html",
        user=current_user,
        profile=profile,
        summary=summary,
        profile_percentage=percentage,
        missing_fields=missing,
    )


# Admin dashboard (data comes from routes/admin.py)
@auth_bp.route("/admin-dashboard")
@admin_required
def admin_dashboard():
    return redirect(url_for("admin.dashboard"))


# Change password
@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():

    form = ChangePasswordForm()

    if form.validate_on_submit():

        if not check_password_hash(current_user.password, form.current_password.data):
            flash("Your current password is incorrect.", "danger")
        elif check_password_hash(current_user.password, form.new_password.data):
            flash("The new password must be different from the current one.", "danger")
        else:
            try:
                current_user.password = generate_password_hash(form.new_password.data)
                notify(
                    current_user.id,
                    "Password changed",
                    "Your portal password was changed. If this was not you, "
                    "contact the administrator immediately.",
                )
                db.session.commit()
                flash("Password changed successfully.", "success")
                return redirect(url_for("auth.dashboard"))
            except Exception:
                db.session.rollback()
                flash("Unable to change password. Please try again.", "danger")

    return render_template("auth/change_password.html", form=form)


# Logout
@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():

    logout_user()

    flash("You have been logged out successfully.", "success")

    return redirect(url_for("auth.login"))
