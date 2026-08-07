from flask import Blueprint

staff_bp = Blueprint("staff", __name__)

from app.api.staff import enquiries, admin  # noqa: E402,F401
