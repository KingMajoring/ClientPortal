# WGTK Client Portal

Standalone web app for We've Got The Key (WGTK) — trade clients raise vehicle
access enquiries and track them to completion; WGTK office staff manage the
same enquiries, quote, schedule, and report on SLAs. Two logins, one
codebase: `/staff/login` (WGTK internal) and `/portal/login` (all trade
clients, routed to their own company's data after login).

This is phase 1: data model, auth, tenant isolation, the enquiry lifecycle,
and both portal shells. See `docs/DATA_MODEL.md` for the full schema and
folder-structure writeup — read that first if you're sanity-checking the
design.

## Stack

- Backend: Python / Flask, SQLAlchemy (SQLite for dev, Azure SQL-compatible
  for later via `mssql+pyodbc`), Flask-Login session auth, Flask-Migrate.
- Frontend: React (Vite), react-router-dom, plain fetch — no UI framework,
  by design, so the structure stays easy to read at this stage.
- PDF: ReportLab (Letter of Authority generation).
- Email/storage: stubbed (console log + DB record; local filesystem) —
  swappable later, see `docs/DATA_MODEL.md` → "Deliberately deferred".

## Backend setup

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=wsgi.py FLASK_ENV=development
flask db upgrade          # creates backend/instance/dev.db
python seed.py            # sample clients, users, and enquiries
python wsgi.py             # http://localhost:5000
```

Seeded logins (all `password123`):

| Role | Email |
|---|---|
| WGTK Admin | admin@wgtk.co.uk |
| WGTK General | staff@wgtk.co.uk |
| Client Admin (Fleetway Logistics) | admin@fleetway.example |
| Client General (Fleetway Logistics) | ops@fleetway.example |
| Client Admin (Bodyshop Direct) | admin@bodyshopdirect.example |

Run tests (tenant isolation + lifecycle are the priority coverage):

```bash
cd backend && source .venv/bin/activate && python -m pytest
```

## Frontend setup

```bash
cd frontend
npm install
npm run dev                # http://localhost:5173, proxies /api to :5000
```

Visit `http://localhost:5173/` for a landing page linking to both logins, or
go straight to `/staff/login` or `/portal/login`.

## Deploying to Azure

See `docs/DEPLOYMENT.md` for the full runbook — one Azure App Service
(container) serving both the API and the built frontend, Azure SQL Database,
and a GitHub Actions workflow (`.github/workflows/deploy.yml`) that deploys
on push to `main` via OIDC, so no Azure credential is ever stored as a
GitHub secret. Provisioning is `infra/main.bicep`, run once by hand.

## Layout

```
backend/app/
  models/       SQLAlchemy models — see docs/DATA_MODEL.md
  auth/         login/logout/me + RBAC decorators
  api/staff/    WGTK staff endpoints (all clients)
  api/client/   Client portal endpoints (own company only)
  api/shared/   dashboard, notifications, document download
  services/     business logic — tenant scoping, enquiry lifecycle,
                SLA/MI calculation, PDF/email/storage
frontend/src/
  portals/staff/   WGTK staff portal pages
  portals/client/  Client portal pages
  shared/          dashboard component, API client, shared UI
  auth/            shared login screen + auth context
```

## What's deliberately not here yet

Orbit/Soter CRM integration, field-engineer accounts, real email/SMS
delivery, MFA, and client self-registration are all out of scope for this
phase — see the spec's "explicitly out of scope" list and
`docs/DATA_MODEL.md` for where the seams are left for later. Azure hosting
is now scaffolded (`docs/DEPLOYMENT.md`) but still has known gaps — single
instance, SQL-auth rather than managed-identity auth to the database, and no
scheduled trigger for ETA-expiry — listed at the bottom of that doc.
