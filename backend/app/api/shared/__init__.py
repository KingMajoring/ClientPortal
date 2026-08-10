from flask import Blueprint

shared_bp = Blueprint("shared", __name__)

from app.api.shared import dashboard, notifications, documents, vehicle_lookup  # noqa: E402,F401
