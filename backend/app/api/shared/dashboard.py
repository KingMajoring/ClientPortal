from datetime import datetime

from flask import jsonify, request
from flask_login import current_user, login_required

from app.api.shared import shared_bp
from app.services import client_admin_service, sla_service
from app.utils.errors import ForbiddenError


def _parse_datetime(value):
    return datetime.fromisoformat(value) if value else None


@shared_bp.get("/dashboard")
@login_required
def dashboard():
    date_from = _parse_datetime(request.args.get("date_from"))
    date_to = _parse_datetime(request.args.get("date_to"))

    if current_user.role.is_wgtk:
        client_company_id = request.args.get("client_company_id", type=int)
    else:
        client_company_id = current_user.client_company_id
        # The "hide dashboard from standard users" toggle applies to Client
        # General only — their Admin always retains access to configure it.
        if current_user.role.value == "CLIENT_GENERAL" and not client_admin_service.is_feature_enabled(
            client_company_id, "dashboard"
        ):
            raise ForbiddenError("The dashboard has been hidden for your account by your company Admin")

    # client_company_id is forced to current_user's own company above for
    # client roles, so this filter is itself the tenant boundary here — WGTK
    # staff pass client_company_id=None (unscoped) unless they choose to
    # filter to one client.
    base_query = sla_service.base_query_for_range(client_company_id, date_from, date_to)

    return jsonify(
        {
            "sla_compliance": sla_service.compliance_summary(base_query, client_company_id),
            "mi": sla_service.mi_summary(base_query),
        }
    )
