from datetime import datetime

from flask import jsonify, request
from flask_login import current_user, login_required

from app.api.client import client_bp
from app.api.serializers import serialize_document, serialize_enquiry, serialize_history, serialize_note
from app.auth.decorators import require_client
from app.models.enquiry import DeclineReasonType
from app.models.job import DocumentType, NoteVisibility
from app.services import enquiry_service
from app.utils.errors import ValidationError


def _parse_datetime(value):
    return datetime.fromisoformat(value) if value else None


@client_bp.get("/enquiries")
@login_required
@require_client
def list_enquiries():
    enquiries = enquiry_service.list_for_user(
        current_user,
        status=request.args.get("status"),
        date_from=_parse_datetime(request.args.get("date_from")),
        date_to=_parse_datetime(request.args.get("date_to")),
    )
    return jsonify([serialize_enquiry(e) for e in enquiries])


@client_bp.post("/enquiries")
@login_required
@require_client
def create_enquiry():
    payload = request.get_json(silent=True) or {}
    enquiry = enquiry_service.create_enquiry(current_user, current_user.client_company_id, payload)
    return jsonify(serialize_enquiry(enquiry)), 201


@client_bp.get("/enquiries/<int:enquiry_id>")
@login_required
@require_client
def get_enquiry(enquiry_id):
    enquiry = enquiry_service.get_for_user(current_user, enquiry_id)
    data = serialize_enquiry(enquiry)
    data["status_history"] = [serialize_history(h) for h in enquiry.status_history]
    return jsonify(data)


@client_bp.post("/enquiries/<int:enquiry_id>/accept")
@login_required
@require_client
def accept_enquiry(enquiry_id):
    enquiry = enquiry_service.get_for_user(current_user, enquiry_id)
    enquiry = enquiry_service.accept_quote(current_user, enquiry)
    return jsonify(serialize_enquiry(enquiry))


@client_bp.post("/enquiries/<int:enquiry_id>/decline")
@login_required
@require_client
def decline_enquiry(enquiry_id):
    enquiry = enquiry_service.get_for_user(current_user, enquiry_id)
    payload = request.get_json(silent=True) or {}
    if not payload.get("reason_type"):
        raise ValidationError("reason_type is required")
    reason_type = DeclineReasonType(payload["reason_type"])
    enquiry = enquiry_service.decline_by_client(current_user, enquiry, reason_type, payload.get("reason_text"))
    return jsonify(serialize_enquiry(enquiry))


@client_bp.get("/enquiries/<int:enquiry_id>/notes")
@login_required
@require_client
def list_notes(enquiry_id):
    enquiry = enquiry_service.get_for_user(current_user, enquiry_id)
    return jsonify([serialize_note(n) for n in enquiry_service.visible_notes_for(current_user, enquiry)])


@client_bp.get("/enquiries/<int:enquiry_id>/documents")
@login_required
@require_client
def list_documents(enquiry_id):
    enquiry = enquiry_service.get_for_user(current_user, enquiry_id)
    return jsonify([serialize_document(d) for d in enquiry_service.visible_documents_for(current_user, enquiry)])


@client_bp.post("/enquiries/<int:enquiry_id>/documents")
@login_required
@require_client
def upload_document(enquiry_id):
    enquiry = enquiry_service.get_for_user(current_user, enquiry_id)
    if "file" not in request.files:
        raise ValidationError("file is required")
    # Clients only ever upload their own required docs (e.g. V5); always client-visible.
    document_type = DocumentType(request.form.get("document_type", DocumentType.V5.value))
    document = enquiry_service.add_document(
        current_user, enquiry, request.files["file"], document_type, NoteVisibility.CLIENT_VISIBLE
    )
    return jsonify(serialize_document(document)), 201


@client_bp.post("/documents/<int:document_id>/accept-letter-of-authority")
@login_required
@require_client
def accept_letter_of_authority(document_id):
    from app.extensions import db
    from app.models.job import JobDocument
    from app.services.tenant_scope import assert_tenant_match
    from app.utils.errors import NotFoundError

    document = db.session.get(JobDocument, document_id)
    if not document:
        raise NotFoundError("Document not found")
    assert_tenant_match(current_user, document.enquiry.client_company_id)
    document = enquiry_service.accept_letter_of_authority(current_user, document)
    return jsonify(serialize_document(document))
