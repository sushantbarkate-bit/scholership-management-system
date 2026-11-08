# Final Project Status

Maharashtra Scholarship Management System · MCA First Year mini project

Status date: 7 November 2026. Development database: MySQL, migration head `a483282816d0`.

## 1. Summary

The core application is working end to end: students register, complete a profile, check preliminary eligibility, start and submit applications with documents, and track status. Administrators manage schemes and eligibility rules, verify documents, decide applications, manage students and view reports. Notifications run in the app.

Not every item in the original brief is built. The section 4 list is the honest gap list.

## 2. Completed modules

| # | Module | Status | Notes |
|---|---|---|---|
| 1 | Authentication and users | Done | Register, login, logout, change password, role checks, CSRF, hashed passwords. Admins are created with `create_admin.py` only. |
| 2 | Student dashboard | Done | Counts, recent applications, recommendations, profile completion, notification count, all from queries. |
| 3 | Student profile | Done | 14 tracked fields, validation, completion %, missing-field list. Fixes the original `address` error (see section 6). |
| 4 | Scholarship management (admin) | Done | Create, edit, view, delete or deactivate (deactivates when applications exist), amount, dates, provider, description, required and mandatory documents, pagination and search. |
| 5 | Student scholarship discovery | Done | Search, category and course filters (evaluated against rules), amount range, deadline filter, pagination, scheme details. |
| 6 | Eligibility engine | Done | Rules stored in MySQL, eight operators, preliminary results with exact reasons, eligible and ineligible lists. No scheme-specific logic is hardcoded. |
| 7 | Document management | Done | PDF/JPG/PNG only, magic-byte check, 5 MB limit, random stored names outside `static/`, authorised preview and download, replacement with cleanup, admin verify/reject/resubmission with remarks. |
| 8 | Applications | Done | Draft → submit with re-checked eligibility and mandatory documents, reference numbers, one application per student per scheme (database constraint), status history, admin remarks, timeline view. |
| 9 | Admin review and verification | Done | Search and filter applications, per-document decisions, request documents, approve (only when mandatory documents are verified), reject (remarks required), self-action blocked. |
| 10 | Admin dashboard | Done | Totals, status counts, recent registrations and applications, per-scheme counts. |
| 11 | Notifications | Done | Generated on registration, submission, review, document requests, approval, rejection, password change, and document rejection. Unread count, mark read, mark all read. Email is not implemented. |
| 12 | Reports and analytics | Done | Status, scheme, category, monthly trend, approved vs rejected, students by course, document statistics. Date, scheme and category filters. CSV export and printable view. Chart.js charts. |
| 13 | UI design system | Done | Shared base layout with role-based sidebar, reusable macros (fields, badges, pagination, toasts, empty states, stat cards), responsive down to 390 px. |
| 14 | Automated tests | Done | 112 pytest tests, all passing (section 5). |
| 15 | Demo data | Done | Idempotent seeder: 10 students, 8 schemes, rules, required documents, 12 applications in every status, notifications, demo admin. |
| 16 | Screenshots | Done | 26 PNG files in `design_screenshots/`, captured from the running app with Playwright. |
| 17 | Documentation | Partial | README, database design (ER diagram and DFDs in Mermaid), this status file. See section 4. |

## 3. Database migration status

| Revision | Applied | Effect |
|---|---|---|
| `cb423ab850f5` sync student_profiles | Yes | Adds 8 missing profile columns. Drops `domicile_state`, which was NULL in every row. Original data preserved. |
| `a483282816d0` scholarship management, notifications, document review | Yes | New tables `notifications` and `scholarship_required_documents`; new columns `applications.submitted_at`, `documents.status/remarks/reviewed_at`, `scholarships.is_demo`; indexes. Both new NOT NULL columns have server defaults. |

After both revisions, a comparison of every model against the live tables found **0 differences**.

Original data: the single pre-existing student profile and the two original users are unchanged. A JSON backup of the profile row was taken before the first migration (in the session scratchpad, not in the project).

## 4. Pending or not done

These were in the brief and are **not** implemented:

- Forgot-password and email notifications (the brief marked both as optional).
- Admin settings and admin profile pages (the sidebar has no Settings entry).
- Admin-side notification management (students receive notifications; admins cannot manage them).
- Admin editing of student profiles (admins can list and view students, not edit them).
- Configurable scholarship categories (the category list is fixed in `services/constants.py`).
- Most of the 18 documents in the brief's `documentation/` list. Only `database_design.md` (with the ER diagram and DFDs) exists. Still missing: project synopsis, introduction, problem statement, objectives, scope, existing and proposed system, software requirements, architecture, use case diagram, testing documentation, user manual, future scope, viva questions, and the presentation outline.
- Browser-level end-to-end tests. The suite uses the Flask test client; Playwright is used only for screenshots.

## 5. Test results

Command: `venv\Scripts\python.exe -m pytest -q`

```
112 passed
```

Coverage by area:

| File | Covers |
|---|---|
| `tests/test_auth.py` | Registration, duplicate email, role ignored at registration, login/logout, wrong password, role redirects |
| `tests/test_student_profile.py` | Profile render, valid save, invalid mobile and pincode, percentage range, completion |
| `tests/test_eligibility.py` | Brief example, exact reasons, all eight operators, missing and misconfigured values, rule validation, deadline and status checks |
| `tests/test_scholarships.py` | Admin authorization, CRUD, rules add/remove, delete vs deactivate, student search, category and amount filters, pagination, eligibility page |
| `tests/test_documents.py` | Valid PDF/PNG/JPG, renamed executable and HTML rejected, wrong extension, oversized and empty files, safe filename, replacement, owner/admin/other-student/anonymous access, path traversal |
| `tests/test_applications.py` | Eligibility gate, duplicate prevention (service and database), mandatory documents, submission, history, notifications, review transitions, approval gate, rejection remarks, student cannot change status, object-level access |
| `tests/test_reports_notifications.py` | Welcome notification, unread/mark read, cross-user protection, password change, dashboards, report filters, CSV export, student access to reports blocked |
| `tests/test_security.py` | CSRF enforced when enabled, cookie flags, uploads outside `static/`, generic 404 |

Live-database checks (read-only GET requests, seeded data): every admin and student page returned 200, with no server errors. The other student received 404 for someone else's application and document.

Not verified: the POST workflows (apply, upload, submit, review) were exercised only against SQLite in the test suite, not directly against MySQL. The seeder, which uses the same ORM, did write to MySQL successfully.

## 6. Original `AttributeError: 'StudentProfile' object has no attribute 'address'`

Root cause: the database and the model had drifted apart. `student_profiles` had no `address` column, and the model was changed without a migration. The route was writing a field the process could not see, and the database lacked the column. `create_tables.py` (`create_all`) cannot add columns to an existing table, and no migration history existed. Fixed by the first migration above, and the drift check now reports zero differences.

## 7. Known issues and limitations

- **Demo data includes a demo administrator** (`demo.admin@example.com` / `Demo@12345`) and ten demo students, all with password `Demo@12345`, in your development database. Delete them before using the database for anything real.
- **Screenshots include real data.** The live database contains a real registration, so the admin screenshots (for example "Recent registrations") show that person's name and email. Re-run `database.seed_data` against a separate database before sharing screenshots outside the project.
- **Demo scheme criteria are illustrative.** They are not official rules. Verify official notifications before using any value.
- **Category and course filters** are evaluated in Python after the database query, because they depend on the rules. This is fine at demonstration scale but would need a different design for thousands of schemes.
- **`create_tables.py` should not be used** on a database that has migrations. Use `flask db upgrade`.
- **`/test-db`** still exists as a diagnostic route. It returns a generic message on failure. Remove it before any public deployment.
- **`SECRET_KEY`** comes from `.env`. The application does not check that it is set.
- **No rate limiting** on login, and `SESSION_COOKIE_SECURE` is not set (needed behind HTTPS).
- **Mobile layout** works for the dashboards, the upload view and the sidebar (which collapses to a menu button). Wide admin tables (recent applications, scheme lists, application lists) scroll sideways on a phone, so the status column is partly off-screen until the table is scrolled. Stacking those rows as cards would fix it; not done. Other pages were not visually checked at phone width.

## 8. How to run

See `README.md` for full setup. Short version:

```
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m flask --app app db upgrade
venv\Scripts\python.exe -m database.seed_data           (optional demo data)
venv\Scripts\python.exe -m flask --app app run --port 5055
```

## 9. Demo accounts

| Role | Email | Password | Source |
|---|---|---|---|
| Administrator (demo) | demo.admin@example.com | Demo@12345 | `database.seed_data` |
| Student (demo) | demo.student01@example.com … demo.student10@example.com | Demo@12345 | `database.seed_data` |
| Administrator (yours) | your email | your password | `create_admin.py` (not changed by any script here) |

Delete the demo accounts before any real use.
