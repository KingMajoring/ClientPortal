import json

from flask import jsonify
from flask_login import current_user, login_required

from app.api.client import client_bp
from app.auth.decorators import require_client
from app.models.client import EnquiryFormField, ServiceType


@client_bp.get("/enquiry-form-config")
@login_required
@require_client
def enquiry_form_config():
    """Data-driven form config for the current user's company: which fields
    to render, whether each is required, and the service-type dropdown."""
    fields = (
        EnquiryFormField.query.filter_by(client_company_id=current_user.client_company_id, is_active=True)
        .order_by(EnquiryFormField.sort_order)
        .all()
    )
    service_types = (
        ServiceType.query.filter_by(client_company_id=current_user.client_company_id, is_active=True)
        .order_by(ServiceType.sort_order)
        .all()
    )
    return jsonify(
        {
            "fields": [
                {
                    "field_key": f.field_key,
                    "label": f.label,
                    "field_type": f.field_type,
                    "is_required": f.is_required,
                    "options": json.loads(f.options_json) if f.options_json else None,
                }
                for f in fields
            ],
            "service_types": [{"id": s.id, "name": s.name} for s in service_types],
        }
    )
