from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import current_user

from extensions import db
from models import StudentProfile
from forms.student_form import StudentProfileForm
from routes.decorators import student_required
from services.student_service import profile_completion


student_bp = Blueprint(
    "student",
    __name__,
    url_prefix="/student"
)


@student_bp.route("/profile", methods=["GET", "POST"])
@student_required
def profile():

    student = current_user_profile()

    form = StudentProfileForm(obj=student)

    if form.validate_on_submit():

        try:
            student.mobile = form.mobile.data
            student.date_of_birth = form.date_of_birth.data
            student.gender = form.gender.data
            student.address = form.address.data
            student.city = form.city.data
            student.district = form.district.data
            student.state = form.state.data
            student.pincode = form.pincode.data

            student.category = form.category.data
            student.annual_income = form.annual_income.data

            student.course = form.course.data
            student.college_name = form.college_name.data
            student.university_name = form.university_name.data
            student.academic_year = form.academic_year.data
            student.academic_percentage = form.academic_percentage.data

            db.session.commit()

            flash("Profile updated successfully!", "success")

            return redirect(url_for("student.profile"))

        except Exception:
            db.session.rollback()

            flash(
                "Unable to update profile. Please try again.",
                "danger"
            )

    percentage, missing = profile_completion(student)

    return render_template(
        "student/profile.html",
        form=form,
        completion_percentage=percentage,
        missing_fields=missing,
    )


def current_user_profile():
    """Return the logged-in student's profile, creating it if it is missing."""
    profile = current_user.student_profile
    if profile is None:
        profile = StudentProfile(user_id=current_user.id)
        db.session.add(profile)
        db.session.commit()
    return profile
