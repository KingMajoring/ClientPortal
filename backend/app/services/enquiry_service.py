"""Enquiry lifecycle: every status transition goes through this module so it
always writes an EnquiryStatusHistory row (the audit trail the SLA dashboard
reads) and fires the matching notification. Routes should never set
`enquiry.status` directly.
"""

import json
import logging
from datetime import datetime, timezone

from app.extensions import db
from app.models.client import EnquiryFormField
from app.models.enquiry import DeclineReasonType, Enquiry, EnquiryStatus, EnquiryStatusHistory
from app.models.job import DocumentStatus, DocumentType, JobDocument, JobNote, NoteVisibility
from app.services import notification_service, pdf_service
from app.services.tenant_scope import assert_tenant_match, scope_query_to_tenant
from app.utils.errors import NotFoundError, ValidationError
from app.utils.references import format_enquiry_reference

logger = logging.getLogger("wgtk.enquiry")


def _notify_safely(notify_fn, *args, **kwargs):
    """Every notify_* call here runs after the state-changing commit has
    already succeeded. A failure in here (email, a DB hiccup) must never
    turn an action that already saved into what looks like a failed
    request to the caller — log it and move on."""
    try:
        notify_fn(*args, **kwargs)
    except Exception:
        logger.exception("Notification failed: %s", notify_fn.__name__)


FIXED_FIELD_KEYS = {
    "vehicle_registration",
    "vehicle_make_model",
    "vehicle_year",
    "location_address",
    "urgency",
    "on_site_contact_name",
    "on_site_contact_phone",
}


def _record_history(enquiry, from_status, to_status, changed_by_user, reason=None):
    history = EnquiryStatusHistory(
        enquiry_id=enquiry.id,
        from_status=from_status,
        to_status=to_status,
        changed_by_user_id=changed_by_user.id if changed_by_user else None,
        reason=reason,
    )
    db.session.add(history)
    enquiry.status = to_status


def _require_status(enquiry, *allowed):
    if enquiry.status not in allowed:
        raise ValidationError(
            f"Cannot perform this action while enquiry is '{enquiry.status.value}'"
        )


def list_for_user(current_user, status=None, client_company_id=None, date_from=None, date_to=None):
    query = scope_query_to_tenant(Enquiry.query, Enquiry, current_user)
    if current_user.role.is_wgtk and client_company_id:
        query = query.filter(Enquiry.client_company_id == client_company_id)
    if status:
        query = query.filter(Enquiry.status == status)
    if date_from:
        query = query.filter(Enquiry.created_at >= date_from)
    if date_to:
        query = query.filter(Enquiry.created_at <= date_to)
    return query.order_by(Enquiry.created_at.desc()).all()


def get_for_user(current_user, enquiry_id):
    enquiry = db.session.get(Enquiry, enquiry_id)
    if not enquiry:
        raise NotFoundError("Enquiry not found")
    assert_tenant_match(current_user, enquiry.client_company_id)
    return enquiry


def create_enquiry(current_user, client_company_id, data):
    """`data` is the raw submitted form payload. Required fields come from
    that client's EnquiryFormField config; anything not backed by a fixed
    column is stashed in extra_fields_json."""
    assert_tenant_match(current_user, client_company_id)

    fields = EnquiryFormField.query.filter_by(client_company_id=client_company_id, is_active=True).all()
    extra = {}
    for field in fields:
        value = data.get(field.field_key)
        if field.is_required and not value:
            raise ValidationError(f"'{field.label}' is required")
        if field.field_key not in FIXED_FIELD_KEYS and value is not None:
            extra[field.field_key] = value

    enquiry = Enquiry(
        reference="PENDING",
        client_company_id=client_company_id,
        created_by_user_id=current_user.id,
        service_type_id=data.get("service_type_id"),
        vehicle_registration=data.get("vehicle_registration"),
        vehicle_make_model=data.get("vehicle_make_model"),
        vehicle_year=data.get("vehicle_year"),
        location_address=data.get("location_address"),
        urgency=data.get("urgency"),
        on_site_contact_name=data.get("on_site_contact_name"),
        on_site_contact_phone=data.get("on_site_contact_phone"),
        extra_fields_json=json.dumps(extra) if extra else None,
        status=EnquiryStatus.NEW,
    )
    db.session.add(enquiry)
    db.session.flush()  # assign enquiry.id

    enquiry.reference = format_enquiry_reference(enquiry.id)
    _record_history(enquiry, None, EnquiryStatus.NEW, current_user)
    db.session.commit()

    _notify_safely(notification_service.notify_new_enquiry, enquiry)
    return enquiry


def create_enquiry_from_sync(current_user, client_company_id, fixed_fields, external_ref, internal_note_text=None):
    """Creates an Enquiry directly from an external system's data (e.g. an
    Apex RMS job) rather than a client-submitted form payload. Bypasses
    the EnquiryFormField required-field validation loop in create_enquiry
    since there's no client form submission to validate here - the caller
    is responsible for dedup (checking `external_ref` doesn't already
    exist) before calling this."""
    enquiry = Enquiry(
        reference="PENDING",
        client_company_id=client_company_id,
        created_by_user_id=current_user.id,
        external_ref=external_ref,
        status=EnquiryStatus.NEW,
        **fixed_fields,
    )
    db.session.add(enquiry)
    db.session.flush()  # assign enquiry.id

    enquiry.reference = format_enquiry_reference(enquiry.id)
    _record_history(enquiry, None, EnquiryStatus.NEW, current_user)

    if internal_note_text:
        db.session.add(
            JobNote(
                enquiry_id=enquiry.id,
                author_user_id=current_user.id,
                note_text=internal_note_text,
                visibility=NoteVisibility.INTERNAL,
            )
        )

    db.session.commit()
    _notify_safely(notification_service.notify_new_enquiry, enquiry)
    return enquiry


def send_quote(current_user, enquiry, eta_date, eta_is_same_day, price):
    _require_status(enquiry, EnquiryStatus.NEW, EnquiryStatus.ETA_EXPIRED)
    enquiry.eta_date = eta_date
    enquiry.eta_is_same_day = eta_is_same_day
    enquiry.price = price
    enquiry.is_eta_expired = False
    _record_history(enquiry, enquiry.status, EnquiryStatus.QUOTED, current_user)
    db.session.commit()
    _notify_safely(notification_service.notify_quote_sent, enquiry)
    return enquiry


def accept_quote(current_user, enquiry):
    _require_status(enquiry, EnquiryStatus.QUOTED)
    _record_history(enquiry, enquiry.status, EnquiryStatus.ACCEPTED, current_user)
    db.session.commit()

    relative_path = pdf_service.generate_letter_of_authority(enquiry)
    loa = JobDocument(
        enquiry_id=enquiry.id,
        document_type=DocumentType.LETTER_OF_AUTHORITY,
        visibility=NoteVisibility.CLIENT_VISIBLE,
        file_path=relative_path,
        original_filename=f"letter_of_authority_{enquiry.reference}.pdf",
        content_type="application/pdf",
        status=DocumentStatus.PENDING_ACCEPTANCE,
    )
    db.session.add(loa)
    db.session.commit()

    _notify_safely(notification_service.notify_accepted, enquiry)
    return enquiry


def decline_by_client(current_user, enquiry, reason_type: DeclineReasonType, reason_text=None):
    _require_status(enquiry, EnquiryStatus.QUOTED)
    enquiry.decline_reason_type = reason_type
    enquiry.decline_reason_text = reason_text

    if reason_type in (DeclineReasonType.PRICE, DeclineReasonType.ETA):
        # Re-quote request: re-open rather than close.
        _record_history(
            enquiry, enquiry.status, EnquiryStatus.NEW, current_user,
            reason=f"Declined ({reason_type.value}): {reason_text or ''}".strip(),
        )
    else:
        _record_history(
            enquiry, enquiry.status, EnquiryStatus.DECLINED_BY_CLIENT, current_user, reason=reason_text
        )
    db.session.commit()
    _notify_safely(notification_service.notify_declined, enquiry, declined_by="client")
    return enquiry


def decline_by_wgtk(current_user, enquiry, reason_text):
    _require_status(enquiry, EnquiryStatus.NEW, EnquiryStatus.QUOTED, EnquiryStatus.ETA_EXPIRED)
    if not reason_text:
        raise ValidationError("A reason is required to decline an enquiry")
    enquiry.wgtk_decline_reason_text = reason_text
    _record_history(enquiry, enquiry.status, EnquiryStatus.DECLINED_BY_WGTK, current_user, reason=reason_text)
    db.session.commit()
    _notify_safely(notification_service.notify_declined, enquiry, declined_by="wgtk")
    return enquiry


def schedule(current_user, enquiry, scheduled_at):
    _require_status(enquiry, EnquiryStatus.ACCEPTED)
    enquiry.scheduled_at = scheduled_at
    enquiry.is_eta_expired = False
    _record_history(enquiry, enquiry.status, EnquiryStatus.SCHEDULED, current_user)
    db.session.commit()
    _notify_safely(notification_service.notify_appointment_set, enquiry)
    return enquiry


def reschedule(current_user, enquiry, new_scheduled_at, reason):
    _require_status(enquiry, EnquiryStatus.SCHEDULED, EnquiryStatus.ETA_EXPIRED)
    if not reason:
        raise ValidationError("A reason is required to reschedule")
    enquiry.scheduled_at = new_scheduled_at
    enquiry.is_eta_expired = False
    _record_history(enquiry, enquiry.status, EnquiryStatus.SCHEDULED, current_user, reason=reason)
    db.session.commit()
    _notify_safely(notification_service.notify_rescheduled, enquiry)
    return enquiry


def check_and_flag_eta_expired(grace_hours):
    """Scan QUOTED/SCHEDULED enquiries whose ETA/appointment window has
    passed without an update, flag them, and notify WGTK staff. Called from
    a staff-triggered endpoint in this phase (no scheduler wired up yet)."""
    now = datetime.now(timezone.utc)
    flagged = []

    quoted = Enquiry.query.filter(Enquiry.status == EnquiryStatus.QUOTED, Enquiry.eta_date.isnot(None)).all()
    for enquiry in quoted:
        deadline = datetime.combine(enquiry.eta_date, datetime.min.time(), tzinfo=timezone.utc)
        deadline = deadline.replace(hour=23, minute=59)
        if now > deadline and not enquiry.is_eta_expired:
            enquiry.is_eta_expired = True
            _record_history(enquiry, enquiry.status, EnquiryStatus.ETA_EXPIRED, None, reason="ETA passed without update")
            flagged.append(enquiry)

    scheduled = Enquiry.query.filter(
        Enquiry.status == EnquiryStatus.SCHEDULED, Enquiry.scheduled_at.isnot(None)
    ).all()
    for enquiry in scheduled:
        if (now - enquiry.scheduled_at).total_seconds() / 3600 > grace_hours and not enquiry.is_eta_expired:
            enquiry.is_eta_expired = True
            _record_history(
                enquiry, enquiry.status, EnquiryStatus.ETA_EXPIRED, None, reason="Appointment window passed without update"
            )
            flagged.append(enquiry)

    db.session.commit()
    for enquiry in flagged:
        _notify_safely(notification_service.notify_eta_expired, enquiry)
    return flagged


def complete(current_user, enquiry, completion_notes):
    _require_status(enquiry, EnquiryStatus.SCHEDULED, EnquiryStatus.ETA_EXPIRED)
    _record_history(enquiry, enquiry.status, EnquiryStatus.COMPLETED, current_user)
    if completion_notes:
        db.session.add(
            JobNote(
                enquiry_id=enquiry.id,
                author_user_id=current_user.id,
                note_text=completion_notes,
                visibility=NoteVisibility.CLIENT_VISIBLE,
            )
        )
    db.session.commit()
    _notify_safely(notification_service.notify_completed, enquiry)
    return enquiry


def add_note(current_user, enquiry, note_text, visibility: NoteVisibility):
    if not note_text:
        raise ValidationError("Note text is required")
    note = JobNote(
        enquiry_id=enquiry.id, author_user_id=current_user.id, note_text=note_text, visibility=visibility
    )
    db.session.add(note)
    db.session.commit()
    return note


def visible_notes_for(current_user, enquiry):
    if current_user.role.is_wgtk:
        return enquiry.notes
    return [n for n in enquiry.notes if n.visibility == NoteVisibility.CLIENT_VISIBLE]


def add_document(current_user, enquiry, file_storage, document_type: DocumentType, visibility: NoteVisibility):
    from app.services import storage_service

    relative_path = storage_service.save_file(enquiry.id, file_storage)
    document = JobDocument(
        enquiry_id=enquiry.id,
        uploaded_by_user_id=current_user.id,
        document_type=document_type,
        visibility=visibility,
        file_path=relative_path,
        original_filename=file_storage.filename,
        content_type=file_storage.content_type,
    )
    db.session.add(document)
    db.session.commit()
    return document


def visible_documents_for(current_user, enquiry):
    if current_user.role.is_wgtk:
        return enquiry.documents
    return [d for d in enquiry.documents if d.visibility == NoteVisibility.CLIENT_VISIBLE]


def accept_letter_of_authority(current_user, document: JobDocument):
    if document.document_type != DocumentType.LETTER_OF_AUTHORITY:
        raise ValidationError("Not a Letter of Authority document")
    document.status = DocumentStatus.ACCEPTED
    document.accepted_by_user_id = current_user.id
    document.accepted_at = datetime.now(timezone.utc)
    db.session.commit()
    return document
