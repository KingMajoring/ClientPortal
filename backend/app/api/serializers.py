import json


def serialize_enquiry(enquiry):
    return {
        "id": enquiry.id,
        "reference": enquiry.reference,
        "client_company_id": enquiry.client_company_id,
        "client_company_name": enquiry.client_company.name if enquiry.client_company else None,
        "created_by_user_id": enquiry.created_by_user_id,
        "service_type_id": enquiry.service_type_id,
        "service_type_name": enquiry.service_type.name if enquiry.service_type else None,
        "status": enquiry.status.value,
        "vehicle_registration": enquiry.vehicle_registration,
        "vehicle_make_model": enquiry.vehicle_make_model,
        "vehicle_year": enquiry.vehicle_year,
        "location_address": enquiry.location_address,
        "urgency": enquiry.urgency,
        "on_site_contact_name": enquiry.on_site_contact_name,
        "on_site_contact_phone": enquiry.on_site_contact_phone,
        "external_ref": enquiry.external_ref,
        "extra_fields": json.loads(enquiry.extra_fields_json) if enquiry.extra_fields_json else {},
        "eta_date": enquiry.eta_date.isoformat() if enquiry.eta_date else None,
        "eta_is_same_day": enquiry.eta_is_same_day,
        "price": str(enquiry.price) if enquiry.price is not None else None,
        "scheduled_at": enquiry.scheduled_at.isoformat() if enquiry.scheduled_at else None,
        "is_eta_expired": enquiry.is_eta_expired,
        "decline_reason_type": enquiry.decline_reason_type.value if enquiry.decline_reason_type else None,
        "decline_reason_text": enquiry.decline_reason_text,
        "wgtk_decline_reason_text": enquiry.wgtk_decline_reason_text,
        "created_at": enquiry.created_at.isoformat(),
        "updated_at": enquiry.updated_at.isoformat(),
    }


def serialize_history(row):
    return {
        "id": row.id,
        "from_status": row.from_status.value if row.from_status else None,
        "to_status": row.to_status.value,
        "changed_by_user_id": row.changed_by_user_id,
        "changed_by_name": row.changed_by.full_name if row.changed_by else "System",
        "reason": row.reason,
        "created_at": row.created_at.isoformat(),
    }


def serialize_note(note):
    return {
        "id": note.id,
        "enquiry_id": note.enquiry_id,
        "author_user_id": note.author_user_id,
        "author_name": note.author.full_name if note.author else None,
        "note_text": note.note_text,
        "visibility": note.visibility.value,
        "created_at": note.created_at.isoformat(),
    }


def serialize_document(document):
    return {
        "id": document.id,
        "enquiry_id": document.enquiry_id,
        "uploaded_by_user_id": document.uploaded_by_user_id,
        "document_type": document.document_type.value,
        "visibility": document.visibility.value,
        "original_filename": document.original_filename,
        "content_type": document.content_type,
        "status": document.status.value if document.status else None,
        "accepted_by_user_id": document.accepted_by_user_id,
        "accepted_at": document.accepted_at.isoformat() if document.accepted_at else None,
        "created_at": document.created_at.isoformat(),
        "download_url": f"/api/shared/documents/{document.id}/download",
    }


def serialize_notification(note):
    return {
        "id": note.id,
        "client_company_id": note.client_company_id,
        "target_role": note.target_role.value if note.target_role else None,
        "enquiry_id": note.enquiry_id,
        "notification_type": note.notification_type.value,
        "message": note.message,
        "is_read": note.is_read,
        "created_at": note.created_at.isoformat(),
    }
