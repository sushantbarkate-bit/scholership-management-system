"""Capture real screenshots of the running portal with Playwright.

Prerequisites (one time):
    venv\\Scripts\\python.exe -m pip install playwright
    venv\\Scripts\\python.exe -m playwright install chromium

Usage (the server must be running and seeded with demo data):
    venv\\Scripts\\python.exe -m flask --app app run --port 5055
    venv\\Scripts\\python.exe tools\\capture_screenshots.py http://127.0.0.1:5055

Output goes to design_screenshots/ at the project root. Desktop shots are
1440 x 900, mobile shots are 390 x 844, as the brief requires.
"""

import os
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "design_screenshots")

DEMO_PASSWORD = "Demo@12345"
STUDENT = "demo.student01@example.com"
ADMIN = "demo.admin@example.com"

DESKTOP = {"width": 1440, "height": 900}
MOBILE = {"width": 390, "height": 844}


def demo_ids():
    """Look up record IDs from the seeded database (read-only)."""
    sys.path.insert(0, ROOT)
    from app import app
    from models import Application, Scholarship

    with app.app_context():
        ids = {"scholarship": {}, "application": {}}
        for s in Scholarship.query.all():
            ids["scholarship"][s.name] = s.id
        for a in Application.query.all():
            ids["application"][a.status] = a.id
        return ids


def login(context, base, email):
    page = context.new_page()
    page.goto(f"{base}/auth/login", wait_until="load")
    page.fill("input[name=email]", email)
    page.fill("input[name=password]", DEMO_PASSWORD)
    page.click("form input[type=submit], form button[type=submit]")
    page.wait_for_load_state("load")
    page.close()


def shot(context, base, path, name, viewport=DESKTOP, full=True):
    page = context.new_page()
    page.set_viewport_size(viewport)
    page.goto(f"{base}{path}", wait_until="load", timeout=30000)
    page.wait_for_timeout(500)  # let Bootstrap and Chart.js settle
    target = os.path.join(OUT, name)
    page.screenshot(path=target, full_page=full)
    page.close()
    print("saved", target)


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5055").rstrip("/")
    os.makedirs(OUT, exist_ok=True)
    ids = demo_ids()
    sch = ids["scholarship"]
    apps = ids["application"]

    detail_id = sch.get("Higher Education Excellence Award (Demo)")
    scholarship_list_name = "SC Post-Matric Scholarship (Demo)"

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- public pages (no login) ----------
        anon = browser.new_context()
        shot(anon, base, "/", "01_landing_page_desktop.png")
        shot(anon, base, "/", "01b_landing_page_mobile.png", viewport=MOBILE)
        shot(anon, base, "/auth/login", "02_student_login.png")
        shot(anon, base, "/auth/register", "03_student_registration.png")
        anon.close()

        # ---------- student pages ----------
        student = browser.new_context()
        login(student, base, STUDENT)
        shot(student, base, "/auth/student-dashboard", "04_student_dashboard.png")
        shot(student, base, "/auth/student-dashboard", "04b_student_dashboard_mobile.png", viewport=MOBILE)
        shot(student, base, "/student/profile", "05_student_profile.png")
        shot(student, base, "/scholarships/", "06_scholarship_listing.png")
        if detail_id:
            shot(student, base, f"/scholarships/{detail_id}", "07_scholarship_details.png")
        shot(student, base, "/scholarships/eligibility", "08_eligibility_checker_results.png")
        if "draft" in apps:
            shot(student, base, f"/applications/{apps['draft']}", "09_application_form_draft.png")
            shot(student, base, f"/applications/{apps['draft']}", "10_document_upload.png",
                 viewport=MOBILE)
        shot(student, base, "/applications/", "11_application_tracking_list.png")
        if "documents_required" in apps:
            shot(student, base, f"/applications/{apps['documents_required']}",
                 "12_application_tracking_detail.png")
        shot(student, base, "/notifications/", "13_student_notifications.png")
        student.close()

        # ---------- admin pages ----------
        admin = browser.new_context()
        login(admin, base, ADMIN)
        shot(admin, base, "/admin/", "14_admin_dashboard.png")
        shot(admin, base, "/admin/scholarships", "15_scholarship_management.png")
        if detail_id:
            shot(admin, base, f"/admin/scholarships/{detail_id}", "16_scholarship_rules.png")
        shot(admin, base, f"/admin/scholarships/{detail_id}/edit" if detail_id else "/admin/scholarships/new",
             "17_add_edit_scholarship.png")
        shot(admin, base, "/admin/students", "18_student_management.png")
        shot(admin, base, "/admin/applications", "19_application_list.png")
        if "submitted" in apps:
            shot(admin, base, f"/admin/applications/{apps['submitted']}", "20_application_verification.png")
        if "documents_required" in apps:
            shot(admin, base, f"/admin/applications/{apps['documents_required']}",
                 "20b_application_verification_docs_requested.png")
        shot(admin, base, "/admin/reports/", "21_reports_analytics.png")
        shot(admin, base, "/admin/reports/?print=1", "22_reports_printable.png", viewport=DESKTOP)
        shot(admin, base, "/admin/", "23_admin_dashboard_mobile.png", viewport=MOBILE)
        admin.close()

        browser.close()


if __name__ == "__main__":
    main()
