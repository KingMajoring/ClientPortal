from flask import jsonify, request
from flask_login import current_user, login_required

from app.api.client import client_bp
from app.auth.decorators import require_client, require_role
from app.extensions import db
from app.models.client import ClientCompany
from app.models.user import User, UserRole
from app.services import client_admin_service, user_service
from app.utils.errors import NotFoundError, ValidationError


def serialize_user(user):
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role.value,
        "is_active": user.is_active,
    }


@client_bp.get("/users")
@login_required
@require_client
def list_users():
    users = user_service.list_client_users(current_user, current_user.client_company_id)
    return jsonify([serialize_user(u) for u in users])


@client_bp.post("/users")
@login_required
@require_role(UserRole.CLIENT_ADMIN)
def create_user():
    payload = request.get_json(silent=True) or {}
    for field in ("email", "first_name", "last_name"):
        if not payload.get(field):
            raise ValidationError(f"'{field}' is required")
    role = UserRole(payload.get("role", UserRole.CLIENT_GENERAL.value))
    user, temp_password = user_service.create_client_user(
        current_user,
        current_user.client_company_id,
        payload["email"],
        payload["first_name"],
        payload["last_name"],
        role,
    )
    return jsonify({"user": serialize_user(user), "temp_password": temp_password}), 201


@client_bp.post("/users/<int:user_id>/reset-password")
@login_required
@require_role(UserRole.CLIENT_ADMIN)
def reset_password(user_id):
    target = db.session.get(User, user_id)
    if not target:
        raise NotFoundError("User not found")
    new_password = user_service.reset_password(current_user, target)
    return jsonify({"temp_password": new_password})


@client_bp.delete("/users/<int:user_id>")
@login_required
@require_role(UserRole.CLIENT_ADMIN)
def deactivate_user(user_id):
    target = db.session.get(User, user_id)
    if not target:
        raise NotFoundError("User not found")
    user_service.deactivate_user(current_user, target)
    return jsonify({"ok": True})


@client_bp.get("/feature-flags")
@login_required
@require_client
def get_feature_flags():
    return jsonify(client_admin_service.feature_flags_for(current_user.client_company_id))


@client_bp.put("/feature-flags")
@login_required
@require_role(UserRole.CLIENT_ADMIN)
def set_feature_flags():
    payload = request.get_json(silent=True) or {}
    for feature_key, is_enabled in payload.get("flags", {}).items():
        client_admin_service.set_feature_flag(current_user, current_user.client_company_id, feature_key, bool(is_enabled))
    return jsonify(client_admin_service.feature_flags_for(current_user.client_company_id))


@client_bp.get("/branding")
@login_required
@require_client
def get_branding():
    company = db.session.get(ClientCompany, current_user.client_company_id)
    return jsonify(
        {
            "name": company.name,
            "primary_color": company.primary_color,
            "logo_path": company.logo_path,
        }
    )
