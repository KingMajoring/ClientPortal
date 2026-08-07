# WGTK Client Portal — Data Model & Folder Structure (Phase 1 proposal)

This document is the thing to sanity-check against the spec before we go further.
Everything below is implemented as SQLAlchemy models in `backend/app/models/`.

## Folder structure

```
ClientPortal/
├── backend/
│   ├── app/
│   │   ├── __init__.py            # Flask app factory
│   │   ├── config.py              # Dev/Test/Prod config (SQLite/SQL Server via SQLALCHEMY_DATABASE_URI)
│   │   ├── extensions.py          # db, migrate, login_manager, bcrypt, mail
│   │   ├── models/                # SQLAlchemy models (see below)
│   │   ├── auth/                  # login/logout/me routes + RBAC & tenant-scoping decorators
│   │   ├── api/
│   │   │   ├── staff/             # WGTK staff portal endpoints (all clients)
│   │   │   ├── client/            # Client portal endpoints (own company only)
│   │   │   └── shared/            # Dashboard/MI + notifications, used by both portals
│   │   ├── services/              # business logic, kept separate from routes
│   │   │   ├── enquiry_service.py     # lifecycle transitions + tenant scoping
│   │   │   ├── sla_service.py         # SLA compliance / MI calculations
│   │   │   ├── pdf_service.py         # Letter of Authority PDF generation
│   │   │   ├── storage_service.py     # file storage abstraction (local FS now, Blob later)
│   │   │   ├── notification_service.py# in-portal notifications
│   │   │   └── email_service.py       # stub email sender (console/log, swappable to SMTP)
│   │   └── utils/
│   ├── migrations/                # Alembic
│   ├── tests/                     # pytest — auth + tenant isolation are the priority tests
│   ├── seed.py                    # dev seed data (2 sample client companies, all 4 roles)
│   ├── wsgi.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── portals/
│   │   │   ├── staff/             # WGTK staff portal pages (inbox, enquiry detail, admin)
│   │   │   └── client/            # Client portal pages (raise/track enquiry, LoA, dashboard)
│   │   ├── shared/
│   │   │   ├── dashboard/         # SLA/MI dashboard component, used by both portals
│   │   │   ├── components/
│   │   │   └── api/               # fetch client, one per API area
│   │   ├── auth/                  # shared login screen + auth context (routes to correct portal)
│   │   └── App.jsx                # top-level router: /staff/* vs /portal/*
│   └── package.json
└── docs/
    └── DATA_MODEL.md              # this file
```

Two logins, one codebase: `/staff/login` and `/portal/login` are separate routes/pages,
but both call the same `/api/auth/login` endpoint. The API returns the user's role and
(for client users) their company, and the frontend router sends them into the right
portal shell. WGTK staff hitting `/portal/*` or client users hitting `/staff/*` are
redirected — enforced client-side for UX and server-side on every API call (see RBAC below).

## Tenancy & RBAC enforcement

Multi-tenancy is enforced in the **service layer**, not in routes or the UI:

- Every model that belongs to a client (Enquiry, JobNote, JobDocument, ServiceType,
  EnquiryFormField, ClientSLATarget, ClientFeatureFlag, Notification) carries
  `client_company_id`.
- All reads/writes for these go through a service function that takes `current_user`
  and applies `.filter_by(client_company_id=...)` automatically for any `CLIENT_*` role.
  Routes never build these queries directly — this means a missing `if` in a route
  can't leak cross-tenant data.
- WGTK roles (`WGTK_ADMIN`, `WGTK_GENERAL`) are not scoped — they can see all clients,
  per spec.
- `@require_role(...)` decorator gates endpoints by role; `@require_tenant_match` on
  client-portal routes double-checks the requested resource's `client_company_id`
  matches `current_user.client_company_id` even if a client user tries to pass another
  company's enquiry ID directly in the URL.

## Roles

Single `User.role` enum: `WGTK_ADMIN`, `WGTK_GENERAL`, `CLIENT_ADMIN`, `CLIENT_GENERAL`.
`User.client_company_id` is `NULL` for WGTK staff, required for client users.

## Core tables

### ClientCompany
Onboarded trade client. `name`, `is_active`, `primary_color`, `logo_path`,
`external_ref` (nullable — future Orbit/Soter link, unused in this phase), timestamps.

### ClientFeatureFlag
Per-org feature visibility toggles, e.g. `(client_company_id, feature_key='dashboard',
is_enabled=True)`. Deliberately a generic key/value table (not fixed boolean columns)
so new features can be added later with no schema change. Client Admin edits these for
their own company; WGTK Admin can too.

### ClientSLATarget
`(client_company_id, metric_key, target_hours)`. `metric_key` is one of
`time_to_quote`, `time_to_attend`, `time_to_complete` for now — again a key/value shape
so new SLA metrics don't need a migration.

### ServiceType
Per-client job-type dropdown: `(client_company_id, name, is_active, sort_order)`.

### EnquiryFormField
Per-client dynamic enquiry form config: `(client_company_id, field_key, label,
field_type, is_required, is_active, sort_order, options_json)`. Drives both which
fields the client portal renders and server-side validation on submit. Fixed columns
(vehicle reg, make/model, address, etc.) still exist on `Enquiry` for querying/reporting;
`field_key` for those maps onto the fixed column, and anything beyond the fixed set is
stored in `Enquiry.extra_fields_json`.

### User
`email` (unique), `password_hash`, `role`, `client_company_id` (nullable),
`first_name`, `last_name`, `is_active`, `created_at`, `last_login_at`.

### Enquiry
`reference` (human-readable, e.g. `WGTK-000123`), `client_company_id`,
`created_by_user_id`, `service_type_id`, `status`, vehicle/location/contact fields,
`extra_fields_json`, `eta_date`, `eta_is_same_day`, `price`, `scheduled_at`,
`is_eta_expired`, `decline_reason_type` (`PRICE`/`ETA`/`OTHER`), `decline_reason_text`,
`wgtk_decline_reason_text`, `external_ref` (nullable, future CRM link), timestamps.

`status` enum: `NEW`, `QUOTED`, `ACCEPTED`, `DECLINED_BY_CLIENT`, `DECLINED_BY_WGTK`,
`SCHEDULED`, `ETA_EXPIRED`, `COMPLETED`. ("Rescheduled" is not a resting status — a
reschedule writes a history row with a reason and the enquiry returns to `SCHEDULED`
with a new `scheduled_at`; "declined by client for Price/ETA" re-opens the enquiry back
to `NEW` rather than closing it, per spec.)

### EnquiryStatusHistory
Full audit trail: `enquiry_id`, `from_status`, `to_status`, `changed_by_user_id`
(nullable — automatic transitions like ETA-expiry have no actor), `reason`,
`created_at`. This is what the SLA/MI dashboard is computed from.

### JobNote
`enquiry_id`, `author_user_id`, `note_text`, `visibility` (`INTERNAL` /
`CLIENT_VISIBLE`), `created_at`.

### JobDocument
`enquiry_id`, `uploaded_by_user_id` (nullable — system-generated LoA), `document_type`
(`V5`, `LETTER_OF_AUTHORITY`, `JOB_SHEET`, `COMPLETION_REPORT`, `OTHER`), `visibility`,
`file_path` (relative — see storage abstraction), `original_filename`, `content_type`,
`status` (nullable; used for LoA: `PENDING_ACCEPTANCE` / `ACCEPTED`), `accepted_by_user_id`,
`accepted_at`, `created_at`.

### Notification
In-portal notification: `client_company_id` (nullable — WGTK-wide), `user_id`
(nullable — specific user), `target_role` (nullable — broadcast, e.g. all
`WGTK_GENERAL`), `enquiry_id`, `notification_type`, `message`, `is_read`, `created_at`.

### EmailOutbox
Stub email log used by `email_service.py` in place of real SMTP delivery: `to_email`,
`subject`, `body`, `notification_type`, `enquiry_id`, `created_at`, `sent_at`. Lets us
verify "an email would have gone out" in dev/tests without a real provider.

## Deliberately deferred (per spec's out-of-scope list)

- No `Engineer`/field-user model — office staff only.
- No Orbit/Soter linkage logic — `external_ref` columns exist as placeholders on
  `ClientCompany` and `Enquiry` so a future sync job has somewhere to write an ID,
  but nothing reads/writes them yet.
- Email/PDF/storage are all behind service interfaces (`email_service`,
  `pdf_service`, `storage_service`) specifically so swapping in real SMTP, a hosted
  PDF renderer, or Azure Blob Storage later is a one-file change, not a schema change.
