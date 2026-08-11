"""Syncs Apex RMS recovery jobs into WGTK Enquiries, for clients that have
`apex_account_name` configured (currently just Egertons). Staff-triggered
via a "Sync now" button rather than a real schedule, matching the same
no-scheduler-infrastructure-yet pattern as `check_and_flag_eta_expired` in
enquiry_service.py.

Two things happen on every sync:
1. New Apex jobs (within the lookback window) become new Enquiries.
2. Already-synced jobs get checked for changes. Apex's GetRecoveryJobsList
   already returns each job's LastModifiedDate for free, so that's used to
   skip jobs that haven't changed without spending a details call on them -
   only jobs whose LastModifiedDate actually moved get a GetRecoveryJobDetails
   call and a diff against what we saw last time.

There's still no API method to fetch Apex's actual history/note entries
(confirmed against the WSDL) - "what changed" is inferred by diffing the
job's current field values against the last snapshot we stored, not a real
change-log feed.

Respects Apex's rate limits (2 calls/minute on GetRecoveryJobsList, 20/min
on GetRecoveryJobDetails) by refusing to sync too often and sharing a single
per-run cap across both new-job and existing-job details calls - anything
beyond that cap is picked up on the next sync.
"""

import json
from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models.enquiry import Enquiry
from app.models.job import JobNote, NoteVisibility
from app.models.user import User, UserRole
from app.services import apex_ans_service, apex_service, enquiry_service
from app.utils.errors import ValidationError

MIN_SECONDS_BETWEEN_SYNCS = 35
LOOKBACK_DAYS = 14
MAX_DETAIL_CALLS_PER_SYNC = 15

# Fields whose changes are worth flagging as a note. Anything else in
# GetRecoveryJobDetails either doesn't apply to a locksmith job or isn't
# something staff need alerted on.
WATCHED_FIELDS = [
    ("JobStatus", "Status"),
    ("JobOnHold", "On hold"),
    ("Symptom", "Symptom"),
    ("JobDestinationDesc", "Job notes"),
    ("JobRamNotes", "RAM notes"),
    ("JobPdaNotes", "Driver notes"),
]


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


def _watched_snapshot(details):
    return {key: details.get(key) for key, _ in WATCHED_FIELDS}


def _build_initial_note(job_id, job_order_no, details):
    parts = [f"Synced from Apex RMS job {job_id} ({job_order_no})."]
    for key, label in WATCHED_FIELDS:
        value = (details.get(key) or "").strip()
        if value:
            parts.append(f"{label}: {value}")
    return "\n\n".join(parts)


def _diff_note(job_id, job_order_no, old_snapshot, new_snapshot):
    changes = []
    for key, label in WATCHED_FIELDS:
        old_value = (old_snapshot.get(key) or "").strip()
        new_value = (new_snapshot.get(key) or "").strip()
        if old_value != new_value:
            changes.append(f"{label}: {old_value or '(blank)'} -> {new_value or '(blank)'}")
    if not changes:
        return None
    return f"Apex update on job {job_id} ({job_order_no}):\n\n" + "\n".join(changes)


def _create_new(admin_user, client_company_id, job, details):
    job_id = job.get("JobId")
    enquiry = enquiry_service.create_enquiry_from_sync(
        admin_user,
        client_company_id,
        {
            **_build_fixed_fields(details),
            "apex_last_modified_at": job.get("LastModifiedDate"),
            "apex_snapshot_json": json.dumps(_watched_snapshot(details)),
        },
        external_ref=f"apex:{job_id}",
        internal_note_text=_build_initial_note(job_id, job.get("JobOrderNo"), details),
    )
    return enquiry


def _refresh_existing(admin_user, enquiry, job, details):
    job_id = job.get("JobId")
    old_snapshot = json.loads(enquiry.apex_snapshot_json) if enquiry.apex_snapshot_json else {}
    new_snapshot = _watched_snapshot(details)

    for key, value in _build_fixed_fields(details).items():
        setattr(enquiry, key, value)
    enquiry.apex_last_modified_at = job.get("LastModifiedDate")
    enquiry.apex_snapshot_json = json.dumps(new_snapshot)

    note_text = _diff_note(job_id, job.get("JobOrderNo"), old_snapshot, new_snapshot)
    if note_text:
        db.session.add(
            JobNote(
                enquiry_id=enquiry.id,
                author_user_id=admin_user.id,
                note_text=note_text,
                visibility=NoteVisibility.INTERNAL,
            )
        )
    db.session.commit()
    return note_text is not None


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

    created, updated, errors = [], [], []
    skipped_unchanged = skipped_outside_lookback = skipped_rate_limit = 0
    detail_calls_made = 0

    for job in jobs:
        job_id = job.get("JobId")
        external_ref = f"apex:{job_id}"
        existing = Enquiry.query.filter_by(external_ref=external_ref).first()

        if existing:
            if existing.apex_last_modified_at == job.get("LastModifiedDate"):
                skipped_unchanged += 1
                continue
            if detail_calls_made >= MAX_DETAIL_CALLS_PER_SYNC:
                skipped_rate_limit += 1
                continue
            try:
                details = apex_service.get_job_details(job_id)
                detail_calls_made += 1
                if _refresh_existing(admin_user, existing, job, details):
                    updated.append(existing.reference)
            except Exception as exc:  # noqa: BLE001 - one bad job must not abort the whole sync
                errors.append(f"Apex job {job_id}: {exc}")
            continue

        last_modified = _parse_apex_datetime(job.get("LastModifiedDate"))
        if last_modified and last_modified < cutoff:
            skipped_outside_lookback += 1
            continue

        if detail_calls_made >= MAX_DETAIL_CALLS_PER_SYNC:
            skipped_rate_limit += 1
            continue

        try:
            details = apex_service.get_job_details(job_id)
            detail_calls_made += 1
            enquiry = _create_new(admin_user, client_company.id, job, details)
            created.append(enquiry.reference)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Apex job {job_id}: {exc}")

    client_company.apex_last_synced_at = now
    db.session.commit()

    return {
        "created": created,
        "updated": updated,
        "skipped_unchanged": skipped_unchanged,
        "skipped_outside_lookback": skipped_outside_lookback,
        "skipped_rate_limit": skipped_rate_limit,
        "errors": errors,
    }


def list_pending_ans_jobs(client_company):
    """Jobs Egertons has sent that are still sitting in Apex's ANS
    "waiting acceptance" queue - not yet real Apex jobs, so they don't
    appear in GetRecoveryJobsList/the normal sync at all. Matched to this
    client via the ANS Contract Code (field 1001) parsed out of the raw
    message, since GetAnsJobMessagesWaitingAcceptance doesn't return an
    account name directly."""
    if not client_company.apex_contract_code:
        return []
    pending = []
    for message in apex_service.list_ans_messages_waiting_acceptance():
        fields = apex_ans_service.parse_ans_message(message.get("MessageText"))
        if apex_ans_service.single_value(fields, "1001") != client_company.apex_contract_code:
            continue
        pending.append({
            "raw_message_text": message.get("MessageText"),
            **apex_ans_service.summarize(fields),
        })
    return pending


def accept_ans_job(client_company, raw_message_text):
    """Converts a pending ANS message into a real Apex job (CreateRecoveryJob)
    and immediately creates the corresponding Enquiry here - the API
    equivalent of clicking Accept in Apex's own UI, so no manual step
    there is needed. CreateRecoveryJob writes a permanent record to Apex's
    live system, so this re-validates the contract code match rather than
    trusting whatever the caller passed in."""
    admin_user = _find_admin_user(client_company.id)
    if not admin_user:
        raise ValidationError("This client has no active admin user to attribute the job to")

    fields = apex_ans_service.parse_ans_message(raw_message_text)
    if apex_ans_service.single_value(fields, "1001") != client_company.apex_contract_code:
        raise ValidationError("This message's contract code doesn't match this client")

    job_detail_fields = apex_ans_service.build_recovery_job_details(fields, client_company.apex_account_name)
    new_job_id = apex_service.create_recovery_job(job_detail_fields)

    # Re-fetch the canonical record from Apex rather than trusting our own
    # parsed values, and reuse the exact same creation path a normal sync
    # uses - so this enquiry looks identical to one picked up organically.
    details = apex_service.get_job_details(new_job_id)
    synthetic_job = {"JobId": new_job_id, "JobOrderNo": details.get("JobOrderNo"), "LastModifiedDate": None}
    return _create_new(admin_user, client_company.id, synthetic_job, details)
