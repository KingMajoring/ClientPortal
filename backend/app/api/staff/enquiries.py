import csv
import io
from datetime import datetime

from flask import Response, current_app, jsonify, request
from flask_login import current_user, login_required

from app.api.serializers import serialize_document, serialize_enquiry, serialize_history, serialize_note
from app.api.staff import staff_bp
from app.auth.decorators import require_wgtk
from app.models.enquiry import EnquiryStatus
from app.models.job import DocumentType, NoteVisibility
from app.services import apex_drivers, enquiry_service
from app.utils.errors import ValidationError


def _parse_date(value):
    return datetime.fromisoformat(value).date() if value else None


def _parse_datetime(value):
    return datetime.fromisoformat(value) if value else None


@staff_bp.post("/enquiries")
@login_required
@require_wgtk
def create_enquiry_on_behalf():
    """WGTK raising an enquiry on a client's behalf, per spec."""
    payload = request.get_json(silent=True) or {}
    client_company_id = payload.get("client_company_id")
    if not client_company_id:
        raise ValidationError("client_company_id is required")
    enquiry = enquiry_service.create_enquiry(current_user, client_company_id, payload)
    return jsonify(serialize_enquiry(enquiry)), 201


@staff_bp.get("/enquiries")
@login_required
@require_wgtk
def list_enquiries():
    enquiries = enquiry_service.list_for_user(
        current_user,
        status=request.args.get("status"),
        client_company_id=request.args.get("client_company_id", type=int),
        date_from=_parse_datetime(request.args.get("date_from")),
        date_to=_parse_datetime(request.args.get("date_to")),
    )
    return jsonify([serialize_enquiry(e) for e in enquiries])


@staff_bp.get("/enquiries/export.csv")
@login_required
@require_wgtk
def export_enquiries_csv():
    enquiries = enquiry_service.list_for_user(
        current_user,
        status=request.args.get("status"),
        client_company_id=request.args.get("client_company_id", type=int),
        date_from=_parse_datetime(request.args.get("date_from")),
        date_to=_parse_datetime(request.args.get("date_to")),
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["Reference", "Client", "Status", "Vehicle Reg", "ETA Date", "Price", "Scheduled At", "Created At"]
    )
    for e in enquiries:
        writer.writerow(
            [
                e.reference,
                e.client_company.name if e.client_company else "",
                e.status.value,
                e.vehicle_registration or "",
                e.eta_date.isoformat() if e.eta_date else "",
                e.price or "",
                e.scheduled_at.isoformat() if e.scheduled_at else "",
                e.created_at.isoformat(),
            ]
        )
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=enquiries.csv"},
    )


@staff_bp.get("/enquiries/<int:enquiry_id>")
@login_required
@require_wgtk
def get_enquiry(enquiry_id):
    enquiry = enquiry_service.get_for_user(current_user, enquiry_id)
    data = serialize_enquiry(enquiry)
    data["status_history"] = [serialize_history(h) for h in enquiry.status_history]
    return jsonify(data)


@staff_bp.post("/enquiries/<int:enquiry_id>/quote")
@login_required
@require_wgtk
def send_quote(enquiry_id):
    enquiry = enquiry_service.get_for_user(current_user, enquiry_id)
    payload = request.get_json(silent=True) or {}
    if not payload.get("price"):
        raise ValidationError("Price is required")
    enquiry = enquiry_service.send_quote(
        current_user,
        enquiry,
        eta_date=_parse_date(payload.get("eta_date")),
        eta_is_same_day=bool(payload.get("eta_is_same_day")),
        price=payload["price"],
    )
    return jsonify(serialize_enquiry(enquiry))


@staff_bp.post("/enquiries/<int:enquiry_id>/accept-apex-job")
@login_required
@require_wgtk
def accept_apex_job(enquiry_id):
    enquiry = enquiry_service.get_for_user(current_user, enquiry_id)
    enquiry = enquiry_service.accept_apex_job(current_user, enquiry)
    return jsonify(serialize_enquiry(enquiry))


@staff_bp.get("/apex-drivers")
@login_required
@require_wgtk
def list_apex_drivers():
    return jsonify(apex_drivers.DRIVERS)


@staff_bp.post("/enquiries/<int:enquiry_id>/apex-set-planned-driver")
@login_required
@require_wgtk
def set_apex_planned_driver(enquiry_id):
    enquiry = enquiry_service.get_for_user(current_user, enquiry_id)
    payload = request.get_json(silent=True) or {}
    enquiry = enquiry_service.set_apex_planned_driver(current_user, enquiry, payload.get("driver_name"))
    return jsonify(serialize_enquiry(enquiry))


@staff_bp.post("/enquiries/<int:enquiry_id>/decline")
@login_required
@require_wgtk
def decline_enquiry(enquiry_id):
    enquiry = enquiry_service.get_for_user(current_user, enquiry_id)
    payload = request.get_json(silent=True) or {}
    enquiry = enquiry_service.decline_by_wgtk(current_user, enquiry, payload.get("reason_text"))
    return jsonify(serialize_enquiry(enquiry))


@staff_bp.post("/enquiries/<int:enquiry_id>/schedule")
@login_required
@require_wgtk
def schedule_enquiry(enquiry_id):
    enquiry = enquiry_service.get_for_user(current_user, enquiry_id)
    payload = request.get_json(silent=True) or {}
    scheduled_at = _parse_datetime(payload.get("scheduled_at"))
    if not scheduled_at:
        raise ValidationError("scheduled_at is required")
    enquiry = enquiry_service.schedule(current_user, enquiry, scheduled_at)
    return jsonify(serialize_enquiry(enquiry))


@staff_bp.post("/enquiries/<int:enquiry_id>/reschedule")
@login_required
@require_wgtk
def reschedule_enquiry(enquiry_id):
    enquiry = enquiry_service.get_for_user(current_user, enquiry_id)
    payload = request.get_json(silent=True) or {}
    scheduled_at = _parse_datetime(payload.get("scheduled_at"))
    if not scheduled_at:
        raise ValidationError("scheduled_at is required")
    enquiry = enquiry_service.reschedule(current_user, enquiry, scheduled_at, payload.get("reason"))
    return jsonify(serialize_enquiry(enquiry))


@staff_bp.post("/enquiries/<int:enquiry_id>/complete")
@login_required
@require_wgtk
def complete_enquiry(enquiry_id):
    enquiry = enquiry_service.get_for_user(current_user, enquiry_id)
    payload = request.get_json(silent=True) or {}
    enquiry = enquiry_service.complete(current_user, enquiry, payload.get("completion_notes"))
    return jsonify(serialize_enquiry(enquiry))


@staff_bp.post("/enquiries/check-eta-expiry")
@login_required
@require_wgtk
def check_eta_expiry():
    flagged = enquiry_service.check_and_flag_eta_expired(current_app.config["ETA_EXPIRY_GRACE_HOURS"])
    return jsonify({"flagged": [e.reference for e in flagged]})


@staff_bp.get("/enquiries/<int:enquiry_id>/notes")
@login_required
@require_wgtk
def list_notes(enquiry_id):
    enquiry = enquiry_service.get_for_user(current_user, enquiry_id)
    return jsonify([serialize_note(n) for n in enquiry_service.visible_notes_for(current_user, enquiry)])


@staff_bp.post("/enquiries/<int:enquiry_id>/notes")
@login_required
@require_wgtk
def add_note(enquiry_id):
    enquiry = enquiry_service.get_for_user(current_user, enquiry_id)
    payload = request.get_json(silent=True) or {}
    visibility = NoteVisibility(payload.get("visibility", NoteVisibility.INTERNAL.value))
    note = enquiry_service.add_note(current_user, enquiry, payload.get("note_text"), visibility)
    return jsonify(serialize_note(note)), 201


@staff_bp.get("/enquiries/<int:enquiry_id>/documents")
@login_required
@require_wgtk
def list_documents(enquiry_id):
    enquiry = enquiry_service.get_for_user(current_user, enquiry_id)
    return jsonify([serialize_document(d) for d in enquiry_service.visible_documents_for(current_user, enquiry)])


@staff_bp.post("/enquiries/<int:enquiry_id>/documents")
@login_required
@require_wgtk
def upload_document(enquiry_id):
    enquiry = enquiry_service.get_for_user(current_user, enquiry_id)
    if "file" not in request.files:
        raise ValidationError("file is required")
    document_type = DocumentType(request.form.get("document_type", DocumentType.OTHER.value))
    visibility = NoteVisibility(request.form.get("visibility", NoteVisibility.CLIENT_VISIBLE.value))
    document = enquiry_service.add_document(current_user, enquiry, request.files["file"], document_type, visibility)
    return jsonify(serialize_document(document)), 201
