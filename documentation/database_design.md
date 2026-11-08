# Database Design

Database: MySQL 8 (utf8mb4). Schema is managed by Flask-Migrate; the current Alembic head is `a483282816d0`.

## Tables

| Table | Purpose | Key constraints |
|---|---|---|
| `users` | Login accounts for students and administrators | `email` unique; `role` is `student` or `admin` |
| `student_profiles` | One profile per student: personal, category, income, education | `user_id` unique (one-to-one with `users`) |
| `scholarships` | Scheme definitions, amount, dates, active flag, `is_demo` flag | — |
| `eligibility_rules` | Configurable rules: one row per criterion per scheme | FK → `scholarships` |
| `scholarship_required_documents` | Which document types a scheme needs and whether each is mandatory | unique (`scholarship_id`, `document_type`) |
| `applications` | A student's application to a scheme, with status and reference data | unique (`student_id`, `scholarship_id`); indexes on `student_id`, `scholarship_id`, `status` |
| `documents` | Uploaded files for an application: type, stored path, review status and remarks | FK → `applications`; index on `application_id` |
| `application_status_history` | Append-only log of every status change | FK → `applications` |
| `notifications` | In-app messages for a user, with read flag | FK → `users`; index on `user_id` |
| `alembic_version` | Migration bookkeeping | — |

## Relationships

- `users` 1 — 0..1 `student_profiles`
- `scholarships` 1 — * `eligibility_rules`
- `scholarships` 1 — * `scholarship_required_documents`
- `student_profiles` 1 — * `applications` and `scholarships` 1 — * `applications`, with one application per student per scheme
- `applications` 1 — * `documents`
- `applications` 1 — * `application_status_history`
- `users` 1 — * `notifications`

## ER diagram

```mermaid
erDiagram
    USERS ||--o| STUDENT_PROFILES : "has profile"
    USERS ||--o{ NOTIFICATIONS : receives
    SCHOLARSHIPS ||--o{ ELIGIBILITY_RULES : "defined by"
    SCHOLARSHIPS ||--o{ SCHOLARSHIP_REQUIRED_DOCUMENTS : "requires"
    STUDENT_PROFILES ||--o{ APPLICATIONS : submits
    SCHOLARSHIPS ||--o{ APPLICATIONS : receives
    APPLICATIONS ||--o{ DOCUMENTS : "has uploads"
    APPLICATIONS ||--o{ APPLICATION_STATUS_HISTORY : "logs changes"

    USERS {
        int id PK
        string full_name
        string email UK
        string password
        string role
        bool is_active
        datetime created_at
    }
    STUDENT_PROFILES {
        int id PK
        int user_id FK,UK
        string mobile
        date date_of_birth
        string gender
        text address
        string city
        string district
        string state
        string pincode
        string category
        decimal annual_income
        string course
        string college_name
        string university_name
        string academic_year
        decimal academic_percentage
        datetime updated_at
    }
    SCHOLARSHIPS {
        int id PK
        string name
        text description
        string provider
        decimal scholarship_amount
        date application_start_date
        date application_end_date
        bool is_active
        bool is_demo
        datetime created_at
    }
    ELIGIBILITY_RULES {
        int id PK
        int scholarship_id FK
        string criteria_key
        string operator
        string criteria_value
    }
    SCHOLARSHIP_REQUIRED_DOCUMENTS {
        int id PK
        int scholarship_id FK
        string document_type
        bool is_mandatory
    }
    APPLICATIONS {
        int id PK
        int student_id FK
        int scholarship_id FK
        string status
        text admin_remarks
        datetime applied_at
        datetime submitted_at
    }
    DOCUMENTS {
        int id PK
        int application_id FK
        string document_type
        string file_name
        string file_path
        string status
        text remarks
        datetime uploaded_at
        datetime reviewed_at
    }
    APPLICATION_STATUS_HISTORY {
        int id PK
        int application_id FK
        string previous_status
        string new_status
        text remarks
        datetime changed_at
    }
    NOTIFICATIONS {
        int id PK
        int user_id FK
        string title
        text message
        bool is_read
        datetime created_at
    }
```

## Status values

- Application: `draft`, `submitted`, `under_review`, `documents_required`, `approved`, `rejected`.
  Allowed transitions are defined in `services/constants.py` (`APPLICATION_TRANSITIONS`).
- Document: `pending`, `verified`, `rejected`, `resubmission_required`.

## Monetary and date fields

Amounts and income use `DECIMAL` (`scholarship_amount` 12,2; `annual_income` 12,2; `academic_percentage` 5,2). Timestamps are stored as UTC `DATETIME`.

## Migration history

| Revision | Description |
|---|---|
| `cb423ab850f5` | Sync `student_profiles` with the model: add 8 columns, drop unused `domicile_state` (all NULL in existing data) |
| `a483282816d0` | Add `notifications`, `scholarship_required_documents`, `applications.submitted_at`, `documents.status/remarks/reviewed_at`, `scholarships.is_demo`, and indexes |

Both revisions were applied to the development database. Schema drift check after applying: 0 differences between models and tables.

## Data flow (level 0 → level 1)

```mermaid
flowchart LR
    S[Student] -->|register, profile, apply, upload| SYS((Scholarship Portal))
    A[Administrator] -->|schemes, rules, review, decisions| SYS
    SYS -->|eligibility result, status, notifications| S
    SYS -->|reports, CSV| A
    SYS <--> DB[(MySQL)]
    SYS <--> FS[/Private upload folder/]
```

Level 1 detail for the application process:

```mermaid
flowchart TD
    P1[1. Check eligibility] --> P2[2. Start draft]
    P2 --> P3[3. Upload documents]
    P3 --> P4[4. Submit]
    P4 --> P5[5. Admin review]
    P5 -->|documents required| P3
    P5 --> P6[6. Verify documents]
    P6 --> P7{Decision}
    P7 -->|approve, all mandatory verified| P8[Approved]
    P7 -->|reject with remarks| P9[Rejected]
    P2 --> H[(status history)]
    P4 --> H
    P5 --> H
    P7 --> H
    P4 --> N[(notifications)]
    P7 --> N
```
