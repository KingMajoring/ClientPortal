import json

from flask import jsonify, request
from flask_login import current_user, login_required

from app.api.staff import staff_bp
from app.auth.decorators import require_role, require_wgtk
from app.extensions import db
from app.models.client import ClientCompany, ClientFeatureFlag, ClientSLATarget, EnquiryFormField, ServiceType
from app.models.user import User, UserRole
from app.services import apex_sync_service, client_admin_service, user_service
from app.utils.errors import NotFoundError, ValidationError


def serialize_client(company):
    return {
        "id": company.id,
        "name": company.name,
        "is_active": company.is_active,
        "primary_color": company.primary_color,
        "logo_path": company.logo_path,
        "sla_targets": {t.metric_key: t.target_hours for t in company.sla_targets},
        "feature_flags": {f.feature_key: f.is_enabled for f in company.feature_flags},
        "service_types": [
            {"id": s.id, "name": s.name, "is_active": s.is_active} for s in company.service_types
        ],
        "form_fields": [
            {
                "id": f.id,
                "field_key": f.field_key,
                "label": f.label,
                "field_type": f.field_type,
                "is_required": f.is_required,
                "is_active": f.is_active,
                "options": json.loads(f.options_json) if f.options_json else None,
            }
            for f in company.form_fields
        ],
        "apex_account_name": company.apex_account_name,
        "apex_last_synced_at": company.apex_last_synced_at.isoformat() if company.apex_last_synced_at else None,
    }


def serialize_user_admin(user):
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role.value,
        "client_company_id": user.client_company_id,
        "is_active": user.is_active,
    }


@staff_bp.get("/clients")
@login_required
@require_wgtk
def list_clients():
    companies = ClientCompany.query.order_by(ClientCompany.name).all()
    return jsonify([serialize_client(c) for c in companies])


@staff_bp.get("/clients/<int:client_id>")
@login_required
@require_wgtk
def get_client(client_id):
    company = db.session.get(ClientCompany, client_id)
    if not company:
        raise NotFoundError("Client company not found")
    return jsonify(serialize_client(company))


@staff_bp.post("/clients")
@login_required
@require_role(UserRole.WGTK_ADMIN)
def onboard_client():
    payload = request.get_json(silent=True) or {}
    for field in ("name", "admin_email", "admin_first_name", "admin_last_name"):
        if not payload.get(field):
            raise ValidationError(f"'{field}' is required")

    company, admin_user, temp_password = client_admin_service.onboard_client(
        name=payload["name"],
        primary_color=payload.get("primary_color"),
        admin_email=payload["admin_email"],
        admin_first_name=payload["admin_first_name"],
        admin_last_name=payload["admin_last_name"],
    )
    return (
        jsonify(
            {
                "client_company": serialize_client(company),
                "admin_user": serialize_user_admin(admin_user),
                "temp_password": temp_password,
            }
        ),
        201,
    )


@staff_bp.put("/clients/<int:client_id>/sla-targets")
@login_required
@require_role(UserRole.WGTK_ADMIN)
def set_sla_targets(client_id):
    payload = request.get_json(silent=True) or {}
    targets = payload.get("targets", {})
    for metric_key, target_hours in targets.items():
        client_admin_service.set_sla_target(client_id, metric_key, target_hours)
    company = db.session.get(ClientCompany, client_id)
    return jsonify(serialize_client(company))


@staff_bp.put("/clients/<int:client_id>/feature-flags")
@login_required
@require_wgtk
def set_feature_flags(client_id):
    payload = request.get_json(silent=True) or {}
    for feature_key, is_enabled in payload.get("flags", {}).items():
        client_admin_service.set_feature_flag(current_user, client_id, feature_key, bool(is_enabled))
    company = db.session.get(ClientCompany, client_id)
    return jsonify(serialize_client(company))


@staff_bp.put("/clients/<int:client_id>/service-types")
@login_required
@require_wgtk
def set_service_types(client_id):
    payload = request.get_json(silent=True) or {}
    for i, name in enumerate(payload.get("names", [])):
        client_admin_service.upsert_service_type(client_id, name, sort_order=i)
    company = db.session.get(ClientCompany, client_id)
    return jsonify(serialize_client(company))


@staff_bp.put("/clients/<int:client_id>/form-fields")
@login_required
@require_wgtk
def set_form_fields(client_id):
    payload = request.get_json(silent=True) or {}
    for field in payload.get("fields", []):
        if not field.get("field_key") or not field.get("label"):
            raise ValidationError("Each field needs a key and a label")
    client_admin_service.replace_form_fields(client_id, payload.get("fields", []))
    company = db.session.get(ClientCompany, client_id)
    return jsonify(serialize_client(company))


@staff_bp.put("/clients/<int:client_id>/apex-account-name")
@login_required
@require_role(UserRole.WGTK_ADMIN)
def set_apex_account_name(client_id):
    company = db.session.get(ClientCompany, client_id)
    if not company:
        raise NotFoundError("Client company not found")
    payload = request.get_json(silent=True) or {}
    company.apex_account_name = (payload.get("apex_account_name") or "").strip() or None
    db.session.commit()
    return jsonify(serialize_client(company))


@staff_bp.post("/clients/<int:client_id>/apex-sync")
@login_required
@require_wgtk
def sync_apex_jobs(client_id):
    company = db.session.get(ClientCompany, client_id)
    if not company:
        raise NotFoundError("Client company not found")
    summary = apex_sync_service.sync_client(company)
    return jsonify(summary)


@staff_bp.get("/users")
@login_required
@require_wgtk
def list_users():
    client_company_id = request.args.get("client_company_id", type=int)
    if client_company_id:
        users = user_service.list_client_users(current_user, client_company_id)
    else:
        users = user_service.list_wgtk_users()
    return jsonify([serialize_user_admin(u) for u in users])


@staff_bp.post("/users")
@login_required
@require_role(UserRole.WGTK_ADMIN)
def create_wgtk_user():
    payload = request.get_json(silent=True) or {}
    for field in ("email", "first_name", "last_name", "role"):
        if not payload.get(field):
            raise ValidationError(f"'{field}' is required")
    role = UserRole(payload["role"])
    if role.is_wgtk:
        user, temp_password = user_service.create_wgtk_user(
            payload["email"], payload["first_name"], payload["last_name"], role
        )
    else:
        if not payload.get("client_company_id"):
            raise ValidationError("client_company_id is required for a client role")
        try:
            client_company_id = int(payload["client_company_id"])
        except (TypeError, ValueError):
            raise ValidationError("client_company_id must be an integer")
        user, temp_password = user_service.create_client_user(
            current_user,
            client_company_id,
            payload["email"],
            payload["first_name"],
            payload["last_name"],
            role,
        )
    return jsonify({"user": serialize_user_admin(user), "temp_password": temp_password}), 201


@staff_bp.post("/users/<int:user_id>/reset-password")
@login_required
@require_role(UserRole.WGTK_ADMIN)
def reset_password(user_id):
    target = db.session.get(User, user_id)
    if not target:
        raise NotFoundError("User not found")
    new_password = user_service.reset_password(current_user, target)
    return jsonify({"temp_password": new_password})


@staff_bp.delete("/users/<int:user_id>")
@login_required
@require_role(UserRole.WGTK_ADMIN)
def deactivate_user(user_id):
    target = db.session.get(User, user_id)
    if not target:
        raise NotFoundError("User not found")
    user_service.deactivate_user(current_user, target)
    return jsonify({"ok": True})
