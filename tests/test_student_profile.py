from decimal import Decimal

from extensions import db
from models import StudentProfile
from tests.conftest import make_user, login


VALID_PROFILE = {
    "mobile": "9876543210",
    "date_of_birth": "2004-05-15",
    "gender": "Female",
    "address": "12 Shivaji Nagar, Pune",
    "city": "Pune",
    "district": "Pune",
    "state": "Maharashtra",
    "pincode": "411005",
    "category": "OBC",
    "annual_income": "200000",
    "course": "MCA",
    "college_name": "Sample College of Computer Applications",
    "university_name": "Savitribai Phule Pune University",
    "academic_year": "2026-27",
    "academic_percentage": "65.50",
}


def _logged_in_student(client, email="profile@example.com"):
    user = make_user(email)
    login(client, email)
    return user


def test_profile_page_renders_for_student(app, client):
    _logged_in_student(client)
    response = client.get("/student/profile")
    assert response.status_code == 200
    assert b"Profile completion" in response.data


def test_valid_profile_update_is_saved(app, client):
    user = _logged_in_student(client)
    response = client.post("/student/profile", data=VALID_PROFILE)
    assert response.status_code == 302

    profile = StudentProfile.query.filter_by(user_id=user.id).one()
    assert profile.address == VALID_PROFILE["address"]
    assert profile.city == "Pune"
    assert profile.pincode == "411005"
    assert profile.academic_percentage == Decimal("65.50")
    assert profile.annual_income == Decimal("200000.00")


def test_invalid_mobile_is_rejected_and_not_saved(app, client):
    user = _logged_in_student(client)
    data = dict(VALID_PROFILE, mobile="12345")
    response = client.post("/student/profile", data=data)
    assert response.status_code == 200
    assert b"valid 10-digit mobile" in response.data
    assert StudentProfile.query.filter_by(user_id=user.id).one().mobile is None


def test_invalid_pincode_is_rejected(app, client):
    _logged_in_student(client)
    response = client.post("/student/profile", data=dict(VALID_PROFILE, pincode="41"))
    assert response.status_code == 200
    assert b"valid 6-digit pincode" in response.data


def test_percentage_out_of_range_is_rejected(app, client):
    _logged_in_student(client)
    response = client.post(
        "/student/profile", data=dict(VALID_PROFILE, academic_percentage="150")
    )
    assert response.status_code == 200


def test_completion_percentage_reflects_saved_fields(app, client):
    _logged_in_student(client)
    client.post("/student/profile", data=VALID_PROFILE)
    response = client.get("/student/profile")
    # All 14 tracked fields are filled after a valid save.
    assert b"100%" in response.data
