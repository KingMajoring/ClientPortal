"""Syncs Apex RMS recovery jobs into WGTK Enquiries, for clients that have
`apex_account_name` configured (currently just Egertons). Staff-triggered
via a "Sync now" button rather than a real schedule, matching the same
no-scheduler-infrastructure-yet pattern as `check_and_flag_eta_expired` in
enquiry_service.py.

Respects Apex's rate limits (2 calls/minute on GetRecoveryJobsList, 20/min
on GetRecoveryJobDetails) by refusing to sync too often and capping how
many new jobs get their full details pulled per run - any jobs beyond
that cap are picked up on the next sync.
"""

from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models.enquiry import Enquiry
from app.models.user import User, UserRole
from app.services import apex_service, enquiry_service
from app.utils.errors import ValidationError

MIN_SECONDS_BETWEEN_SYNCS = 35
LOOKBACK_DAYS = 14
MAX_DETAILS_PER_SYNC = 15


def _find_admin_user(client_company_id):
    return User.query.filter_by(
        client_company_id=client_company_id, role=UserRole.CLIENT_ADMIN, is_active=True
    ).first()


def _parse_apex_datetime(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _build_fixed_fields(details):
    priority_flag = (details.get("JobPriorityFlag") or "").strip().lower() == "true"
    return {
        "vehicle_registration": details.get("JobVehicleRegistration"),
        "vehicle_make_model": details.get("JobVehicleMakeModel"),
        "location_address": details.get("JobLocationDesc"),
        "urgency": "Urgent" if priority_flag else "Standard",
        "on_site_contact_name": details.get("JobOwnerName"),
        "on_site_contact_phone": details.get("JobOwnerPhone"),
    }


def _build_internal_note(job_id, job_order_no, details):
    parts = [f"Synced from Apex RMS job {job_id} ({job_order_no})."]
    for label, key in (
        ("Symptom", "Symptom"),
        ("Job notes", "JobDestinationDesc"),
        ("RAM notes", "JobRamNotes"),
        ("Driver notes", "JobPdaNotes"),
    ):
        value = (details.get(key) or "").strip()
        if value:
            parts.append(f"{label}: {value}")
    return "\n\n".join(parts)


def sync_client(client_company):
    if not client_company.apex_account_name:
        raise ValidationError("This client has no Apex account name configured")

    now = datetime.now(timezone.utc)
    last_synced_at = client_company.apex_last_synced_at
    if last_synced_at:
        # SQLite (dev) doesn't round-trip tzinfo even on a timezone=True
        # column, so this can come back naive - normalize before comparing.
        if last_synced_at.tzinfo is None:
            last_synced_at = last_synced_at.replace(tzinfo=timezone.utc)
        elapsed = (now - last_synced_at).total_seconds()
        if elapsed < MIN_SECONDS_BETWEEN_SYNCS:
            raise ValidationError(
                f"Please wait {int(MIN_SECONDS_BETWEEN_SYNCS - elapsed)}s before syncing again (Apex rate limit)"
            )

    admin_user = _find_admin_user(client_company.id)
    if not admin_user:
        raise ValidationError("This client has no active admin user to attribute synced jobs to")

    jobs = apex_service.list_jobs(account_name=client_company.apex_account_name)
    cutoff = now - timedelta(days=LOOKBACK_DAYS)

    created, errors = [], []
    skipped_existing = skipped_outside_lookback = skipped_rate_limit = 0

    for job in jobs:
        job_id = job.get("JobId")
        external_ref = f"apex:{job_id}"

        if Enquiry.query.filter_by(external_ref=external_ref).first():
            skipped_existing += 1
            continue

        last_modified = _parse_apex_datetime(job.get("LastModifiedDate"))
        if last_modified and last_modified < cutoff:
            skipped_outside_lookback += 1
            continue

        if len(created) >= MAX_DETAILS_PER_SYNC:
            skipped_rate_limit += 1
            continue

        try:
            details = apex_service.get_job_details(job_id)
            enquiry = enquiry_service.create_enquiry_from_sync(
                admin_user,
                client_company.id,
                _build_fixed_fields(details),
                external_ref=external_ref,
                internal_note_text=_build_internal_note(job_id, job.get("JobOrderNo"), details),
            )
            created.append(enquiry.reference)
        except Exception as exc:  # noqa: BLE001 - one bad job must not abort the whole sync
            errors.append(f"Apex job {job_id}: {exc}")

    client_company.apex_last_synced_at = now
    db.session.commit()

    return {
        "created": created,
        "skipped_existing": skipped_existing,
        "skipped_outside_lookback": skipped_outside_lookback,
        "skipped_rate_limit": skipped_rate_limit,
        "errors": errors,
    }
