from datetime import date, timedelta
from decimal import Decimal

from extensions import db
from models import Scholarship, EligibilityRule, ScholarshipRequiredDocument, Application
from tests.conftest import make_user, login
from tests.helpers import make_scholarship, complete_profile, get_user


ADMIN = "admin@example.com"
STUDENT = "student@example.com"


def _admin_client(client):
    make_user(ADMIN, role="admin")
    login(client, ADMIN)
    return client


def _student_client(client, email=STUDENT):
    user = make_user(email)
    complete_profile(user)
    login(client, email)
    return client


def _scholarship_form(**overrides):
    today = date.today()
    data = {
        "name": "Post Matric Demo Scheme",
        "provider": "Demo Department",
        "description": "Demonstration record.",
        "scholarship_amount": "50000",
        "application_start_date": (today - timedelta(days=10)).isoformat(),
        "application_end_date": (today + timedelta(days=30)).isoformat(),
        "is_active": "y",
        "required_documents": ["income_certificate", "previous_marksheet"],
        "mandatory_documents": ["income_certificate"],
    }
    data.update(overrides)
    return data


# ----- authorization -----------------------------------------------------

def test_student_cannot_open_admin_scholarship_pages(app, client):
    _student_client(client)
    for url in ["/admin/scholarships", "/admin/scholarships/new", "/admin/students"]:
        response = client.get(url)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/auth/dashboard")


def test_student_cannot_create_scholarship_by_post(app, client):
    _student_client(client)
    client.post("/admin/scholarships/new", data=_scholarship_form())
    assert Scholarship.query.count() == 0


def test_anonymous_user_redirected_to_login(app, client):
    response = client.get("/scholarships/")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


# ----- admin CRUD ---------------------------------------------------------

def test_admin_creates_scholarship_with_required_documents(app, client):
    _admin_client(client)
    response = client.post("/admin/scholarships/new", data=_scholarship_form())
    assert response.status_code == 302

    scholarship = Scholarship.query.filter_by(name="Post Matric Demo Scheme").one()
    assert scholarship.scholarship_amount == Decimal("50000.00")
    docs = {d.document_type: d.is_mandatory for d in scholarship.required_documents}
    assert docs == {"income_certificate": True, "previous_marksheet": False}


def test_deadline_before_start_is_rejected(app, client):
    _admin_client(client)
    today = date.today()
    client.post("/admin/scholarships/new", data=_scholarship_form(
        application_start_date=today.isoformat(),
        application_end_date=(today - timedelta(days=1)).isoformat(),
    ))
    assert Scholarship.query.count() == 0


def test_admin_edits_scholarship(app, client):
    _admin_client(client)
    scholarship = make_scholarship("Old name")
    response = client.post(
        f"/admin/scholarships/{scholarship.id}/edit",
        data=_scholarship_form(name="New name", is_active=""),
    )
    assert response.status_code == 302
    db.session.refresh(scholarship)
    assert scholarship.name == "New name"
    assert scholarship.is_active is False


def test_admin_adds_and_removes_eligibility_rule(app, client):
    _admin_client(client)
    scholarship = make_scholarship("Rules scheme")
    client.post(f"/admin/scholarships/{scholarship.id}/rules", data={
        "criteria_key": "annual_income", "operator": "less_than_equal",
        "criteria_value": "250000",
    })
    rule = EligibilityRule.query.filter_by(scholarship_id=scholarship.id).one()
    assert rule.criteria_value == "250000"

    client.post(f"/admin/scholarships/{scholarship.id}/rules/{rule.id}/delete")
    assert EligibilityRule.query.filter_by(scholarship_id=scholarship.id).count() == 0


def test_invalid_rule_is_not_saved(app, client):
    _admin_client(client)
    scholarship = make_scholarship("Rules scheme")
    client.post(f"/admin/scholarships/{scholarship.id}/rules", data={
        "criteria_key": "annual_income", "operator": "less_than",
        "criteria_value": "not-a-number",
    })
    assert EligibilityRule.query.count() == 0


def test_delete_scholarship_without_applications_removes_it(app, client):
    _admin_client(client)
    scholarship = make_scholarship("Unused")
    client.post(f"/admin/scholarships/{scholarship.id}/delete")
    assert db.session.get(Scholarship, scholarship.id) is None


def test_delete_with_applications_deactivates_instead(app, client):
    from services.application_service import start_application
    from tests.helpers import get_profile
    student = make_user(STUDENT)
    complete_profile(student)
    scholarship = make_scholarship("Used")
    start_application(get_profile(STUDENT), scholarship)

    make_user(ADMIN, role="admin")
    login(client, ADMIN)
    client.post(f"/admin/scholarships/{scholarship.id}/delete")

    db.session.refresh(scholarship)
    assert scholarship.is_active is False
    assert Application.query.count() == 1


# ----- student listing: search, filters, pagination -----------------------

def test_student_sees_only_active_scholarships(app, client):
    make_scholarship("Visible scheme")
    make_scholarship("Hidden scheme", active=False)
    _student_client(client)
    response = client.get("/scholarships/")
    assert b"Visible scheme" in response.data
    assert b"Hidden scheme" not in response.data


def test_search_by_name(app, client):
    make_scholarship("Alpha Scholarship")
    make_scholarship("Beta Fellowship")
    _student_client(client)
    response = client.get("/scholarships/?q=alpha")
    assert b"Alpha Scholarship" in response.data
    assert b"Beta Fellowship" not in response.data


def test_filter_by_category_uses_eligibility_rules(app, client):
    make_scholarship("OBC only", rules=[("category", "equal", "OBC")])
    make_scholarship("SC only", rules=[("category", "equal", "SC")])
    make_scholarship("Open to all")
    _student_client(client)  # category OBC
    response = client.get("/scholarships/?category=OBC")
    assert b"OBC only" in response.data
    assert b"SC only" not in response.data
    assert b"Open to all" in response.data


def test_filter_by_amount(app, client):
    make_scholarship("Small", amount=Decimal("10000"))
    make_scholarship("Large", amount=Decimal("90000"))
    _student_client(client)
    response = client.get("/scholarships/?min_amount=50000")
    assert b"Large" in response.data
    assert b"Small" not in response.data


def test_pagination_splits_results(app, client):
    for i in range(12):
        make_scholarship(f"Scheme {i:02d}")
    _student_client(client)
    first = client.get("/scholarships/?page=1").data
    second = client.get("/scholarships/?page=2").data
    assert b"Scheme 00" in first and b"Scheme 11" not in first
    assert b"Scheme 11" in second


def test_scholarship_detail_shows_preliminary_disclaimer(app, client):
    scholarship = make_scholarship("Detail scheme", rules=[("category", "equal", "SC")])
    _student_client(client)
    response = client.get(f"/scholarships/{scholarship.id}")
    assert response.status_code == 200
    assert b"not an official approval" in response.data
    # Student is OBC, scheme requires SC -> apply button is disabled
    assert b"Apply (not eligible)" in response.data


def test_eligibility_page_separates_results_with_reasons(app, client):
    make_scholarship("Matches", rules=[("category", "equal", "OBC")])
    make_scholarship("Does not match", rules=[("category", "equal", "SC")])
    _student_client(client)
    response = client.get("/scholarships/eligibility")
    assert response.status_code == 200
    assert b"Eligible schemes" in response.data
    assert b"Does not match" in response.data
    assert b"requires it to be" in response.data
