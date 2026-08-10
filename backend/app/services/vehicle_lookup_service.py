"""VRM (vehicle registration) lookup via the Auto Guru Services API.

Two-step OAuth 2.0 flow: exchange client_id/client_secret for a bearer
token (cached in memory until it's close to expiring), then call the VRM
lookup endpoint with that token. Credentials come from environment
variables only — never hardcoded, never accepted from a client request.
"""

import re
import time

import requests
from flask import current_app

from app.utils.errors import ApiError

TOKEN_URL = "https://auth.autoguruservices.com/token"
VEHICLE_URL_TEMPLATE = "https://api.autoguruservices.com/V2/vehicle/{vrm}"

# Refresh a bit before actual expiry so a request never straddles the boundary.
_TOKEN_REFRESH_MARGIN_SECONDS = 60

_cached_token = None
_cached_token_expires_at = 0

# Loose UK VRM shape check — good enough to reject garbage before we spend an
# API call and to stop this endpoint being used as an open HTTP proxy.
_VRM_RE = re.compile(r"^[A-Z0-9]{2,8}$")


def normalize_vrm(raw_vrm):
    cleaned = re.sub(r"\s+", "", raw_vrm or "").upper()
    if not _VRM_RE.match(cleaned):
        raise ApiError("Not a valid vehicle registration", status_code=422)
    return cleaned


def _get_credentials():
    client_id = current_app.config.get("AUTOGURU_CLIENT_ID")
    client_secret = current_app.config.get("AUTOGURU_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ApiError("Vehicle lookup is not configured", status_code=503)
    return client_id, client_secret


def _get_access_token():
    global _cached_token, _cached_token_expires_at

    if _cached_token and time.time() < _cached_token_expires_at:
        return _cached_token

    client_id, client_secret = _get_credentials()
    response = requests.post(
        TOKEN_URL,
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        data={"client_id": client_id, "client_secret": client_secret, "grant_type": "password"},
        timeout=10,
    )
    if not response.ok:
        raise ApiError("Vehicle lookup service is temporarily unavailable", status_code=502)

    payload = response.json()
    _cached_token = payload["access_token"]
    _cached_token_expires_at = time.time() + payload.get("expires_in", 0) - _TOKEN_REFRESH_MARGIN_SECONDS
    return _cached_token


def lookup_vehicle(raw_vrm):
    """Returns a normalized dict of whatever vehicle details Auto Guru has
    for this registration, or raises ApiError (404 if the reg isn't found)."""
    vrm = normalize_vrm(raw_vrm)
    token = _get_access_token()

    response = requests.get(
        VEHICLE_URL_TEMPLATE.format(vrm=vrm),
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
        timeout=10,
    )

    if response.status_code == 401:
        # Token may have been invalidated server-side; retry once with a fresh one.
        global _cached_token
        _cached_token = None
        token = _get_access_token()
        response = requests.get(
            VEHICLE_URL_TEMPLATE.format(vrm=vrm),
            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            timeout=10,
        )

    if response.status_code == 404:
        raise ApiError("No vehicle found for that registration", status_code=404)
    if not response.ok:
        raise ApiError("Vehicle lookup service is temporarily unavailable", status_code=502)

    return _normalize_response(vrm, response.json())


def _normalize_response(vrm, data):
    """Auto Guru's exact field names aren't nailed down in the integration
    guide we have, so pick up common variants defensively and always pass
    the raw payload through too."""

    def first(*keys):
        for key in keys:
            value = data.get(key)
            if value not in (None, ""):
                return value
        return None

    return {
        "registration": vrm,
        "make": first("Make", "make", "ManufacturerDescription"),
        "model": first("Model", "model", "ModelDescription", "ModelVariant"),
        "colour": first("Colour", "colour", "Color", "ColourDescription"),
        "year": first("YearOfManufacture", "year", "ManufacturedYear"),
        "fuel_type": first("FuelType", "fuel_type", "FuelTypeDescription"),
        "raw": data,
    }
