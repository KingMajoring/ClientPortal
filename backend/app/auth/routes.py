from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import bcrypt, db
from app.models.user import User
from app.utils.errors import ApiError

auth_bp = Blueprint("auth", __name__)


def serialize_user(user):
    data = {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role.value,
        "client_company_id": user.client_company_id,
    }
    if user.client_company:
        data["client_company"] = {
            "id": user.client_company.id,
            "name": user.client_company.name,
            "primary_color": user.client_company.primary_color,
            "logo_path": user.client_company.logo_path,
        }
    return data


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.is_active or not bcrypt.check_password_hash(user.password_hash, password):
        raise ApiError("Invalid email or password", status_code=401)

    login_user(user)
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(serialize_user(user))


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"ok": True})


@auth_bp.get("/me")
@login_required
def me():
    return jsonify(serialize_user(current_user))
