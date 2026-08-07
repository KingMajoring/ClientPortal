from flask import Blueprint

client_bp = Blueprint("client", __name__)

from app.api.client import enquiries, admin, config  # noqa: E402,F401
