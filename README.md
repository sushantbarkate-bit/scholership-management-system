# Maharashtra Scholarship Management System

A Flask + MySQL web application for an MCA First Year mini project. Students register, complete a profile, check preliminary eligibility for configurable scholarship schemes, upload documents and track applications. Administrators manage schemes and eligibility rules, verify documents, decide applications and view reports.

> Eligibility results in this system are **preliminary** and are not official government approvals. All scholarship records shipped by the demo seeder are **illustrative sample data**, not official schemes.

## Features

| Area | What is implemented |
|---|---|
| Accounts | Student registration, login/logout, change password, password hashing, role-based access (student / admin), CSRF protection |
| Student profile | 14 tracked fields, validation, completion percentage and missing-field list |
| Scholarships (admin) | Create, edit, view, delete (or deactivate when applications exist), amount, dates, active flag, required and mandatory documents |
| Eligibility rules (admin) | Rules stored in MySQL on criteria: category, annual income, course, academic %, domicile state, academic year, gender, district, college, university. Operators: `equal`, `not_equal`, `less_than`, `less_than_equal`, `greater_than`, `greater_than_equal`, `in`, `not_in` |
| Eligibility checker (student) | Every active scheme checked against the profile; eligible and ineligible lists with exact reasons |
| Scholarship search | Name/provider search, category and course filters (evaluated against the configured rules), amount range, deadline filter, pagination |
| Documents | PDF/JPG/PNG only; magic-byte signature check; 5 MB limit; random stored names; stored outside `static/`; authorised preview and download; replacement; admin verify/reject/resubmission with remarks |
| Applications | Draft → submit (eligibility and mandatory documents re-checked), unique reference numbers (`MSS-YYYY-NNNNN`), one application per student per scheme enforced by a database constraint, full status history, admin remarks |
| Admin review | Search and filter applications, verify each document, request documents, approve (only when mandatory documents are verified), reject (remarks required), no self-approval |
| Notifications | In-app notifications on registration, submission, review, document requests, approval, rejection and password change; unread count; mark read / mark all read |
| Dashboards | Student dashboard (counts from the database, recommendations, recent applications). Admin dashboard (students, schemes, applications by status, per-scheme counts, recent activity) |
| Reports | Applications by status, scheme, category and month; approved vs rejected; students by course; document verification; date, scheme and category filters; CSV export; printable view; Chart.js charts |

## Technology

Python 3.13, Flask 3.1, Flask-SQLAlchemy 3.1, Flask-Login, Flask-WTF, Flask-Migrate (Alembic), MySQL with PyMySQL, Jinja2, Bootstrap 5.3, Bootstrap Icons, Chart.js 4, Pytest, Playwright (screenshots only).

## Project layout

```
app.py                 application factory and blueprint registration
config.py              configuration (reads .env)
extensions.py          SQLAlchemy instance
models/                database models (see documentation/database_design.md)
routes/                HTTP endpoints: auth, student, scholarship, application,
                       document, notification, admin, report, public
services/              business logic: eligibility, scholarships, applications,
                       documents, notifications, reports, student summaries
forms/                 WTForms definitions
templates/             Jinja2 templates (base layout, macros, per-feature pages)
static/                CSS and JavaScript only (no uploaded files)
uploads/               private document storage (never served directly)
migrations/            Alembic revisions
database/seed_data.py  idempotent demonstration data
tools/capture_screenshots.py   Playwright screenshot capture
tests/                 pytest suite (112 tests, isolated SQLite database)
design_screenshots/    captured screenshots of the running application
documentation/         project documentation
```

## Setup (Windows, PowerShell or Git Bash)

1. **Create and activate the virtual environment** (if you do not have one yet):

   ```
   python -m venv venv
   venv\Scripts\activate
   ```

2. **Install dependencies:**

   ```
   venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

   For screenshots and the Playwright browser (optional):

   ```
   venv\Scripts\python.exe -m pip install -r requirements-dev.txt
   venv\Scripts\python.exe -m playwright install chromium
   ```

3. **Configure `.env`** in the project root (never commit this file):

   ```
   SECRET_KEY=change-me-to-a-long-random-string
   DB_USER=your_mysql_user
   DB_PASSWORD=your_mysql_password
   DB_HOST=localhost
   DB_PORT=3306
   DB_NAME=scholarship_db
   ```

   Create the empty database in MySQL first: `CREATE DATABASE scholarship_db CHARACTER SET utf8mb4;`

4. **Apply database migrations** (safe to run on an existing database):

   ```
   venv\Scripts\python.exe -m flask --app app db upgrade
   ```

5. **Create your administrator account** (interactive; the password is not stored in code):

   ```
   venv\Scripts\python.exe create_admin.py
   ```

6. **Optional: load demonstration data** (idempotent, adds only missing records):

   ```
   venv\Scripts\python.exe -m database.seed_data
   ```

   This creates 10 demo students, 8 demo schemes, eligibility rules, sample applications in every status, and a **demo administrator** `demo.admin@example.com` / `Demo@12345`. Demo student login: `demo.student01@example.com` / `Demo@12345`. Delete these demo accounts before using the database for anything real.

7. **Run the application:**

   ```
   venv\Scripts\python.exe -m flask --app app run --port 5055
   ```

   Open http://127.0.0.1:5055

## Running the tests

The tests use an isolated in-memory SQLite database and a temporary upload folder. They never touch the MySQL database in `.env`.

```
venv\Scripts\python.exe -m pytest -q
```

Expected result: **112 passed**.

## Regenerating screenshots

With the server running on port 5055 and demo data loaded:

```
venv\Scripts\python.exe tools\capture_screenshots.py http://127.0.0.1:5055
```

Images are written to `design_screenshots/` (1440 × 900 desktop, 390 × 844 mobile).

## Database migrations

Schema changes go through Flask-Migrate only:

```
venv\Scripts\python.exe -m flask --app app db migrate -m "describe the change"
venv\Scripts\python.exe -m flask --app app db upgrade
```

Review every generated file before running `upgrade`. Current head: `a483282816d0`.

## Security notes

- Passwords are hashed with Werkzeug (scrypt). No plain-text passwords are stored.
- CSRF protection is enabled on every POST form (Flask-WTF `CSRFProtect`).
- Session cookies are HTTP-only with `SameSite=Lax`.
- Role checks run on every admin and student route; object-level checks prevent students from reading other students' applications and documents (they receive 404).
- Uploads are validated by extension, declared MIME type, size and file signature; stored under random names outside `static/`; served only through an authorised route with `Cache-Control: private, no-store`.
- Login redirects are limited to paths on this site.
- Production hardening still to do before any public deployment: set `SESSION_COOKIE_SECURE=True` behind HTTPS, add rate limiting on login, and remove the demo accounts.

## Documentation

See `FINAL_PROJECT_STATUS.md` for the module status, known limitations and test results, and `documentation/` for the design documents.
