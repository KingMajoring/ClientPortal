from flask import jsonify
from flask_login import login_required

from app.api.shared import shared_bp
from app.services import vehicle_lookup_service


@shared_bp.get("/vehicle-lookup/<vrm>")
@login_required
def lookup_vehicle(vrm):
    """Looks up a vehicle by registration via Auto Guru Services, for
    autofilling the Raise Enquiry form. Available to any logged-in user
    (staff and client) since both portals can raise enquiries."""
    result = vehicle_lookup_service.lookup_vehicle(vrm)
    return jsonify(result)
