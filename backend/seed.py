"""Dev seed data: two sample client companies, all four roles, and a handful
of enquiries across different lifecycle stages. Run with:

    cd backend && flask --app wsgi db upgrade && python seed.py
"""

from datetime import date, datetime, timedelta, timezone

from app import create_app
from app.extensions import bcrypt, db
from app.models.client import ClientCompany, EnquiryFormField, ServiceType
from app.models.enquiry import Enquiry, EnquiryStatus
from app.models.user import User, UserRole
from app.services import client_admin_service, enquiry_service


def hash_password(password):
    return bcrypt.generate_password_hash(password).decode("utf-8")


def run():
    app = create_app("development")
    with app.app_context():
        db.drop_all()
        db.create_all()

        # --- WGTK staff ---
        wgtk_admin = User(
            email="admin@wgtk.co.uk",
            first_name="Wendy",
            last_name="Admin",
            role=UserRole.WGTK_ADMIN,
            password_hash=hash_password("password123"),
        )
        wgtk_general = User(
            email="staff@wgtk.co.uk",
            first_name="Gary",
            last_name="General",
            role=UserRole.WGTK_GENERAL,
            password_hash=hash_password("password123"),
        )
        db.session.add_all([wgtk_admin, wgtk_general])
        db.session.commit()

        # --- Client company 1: Fleetway Logistics ---
        fleetway, fleetway_admin_user, _ = client_admin_service.onboard_client(
            name="Fleetway Logistics",
            primary_color="#0B5FFF",
            admin_email="admin@fleetway.example",
            admin_first_name="Alice",
            admin_last_name="Fleetway",
        )
        fleetway_admin_user.password_hash = hash_password("password123")
        db.session.commit()

        fleetway_general = User(
            email="ops@fleetway.example",
            first_name="Ben",
            last_name="Ops",
            role=UserRole.CLIENT_GENERAL,
            client_company_id=fleetway.id,
            password_hash=hash_password("password123"),
        )
        db.session.add(fleetway_general)

        for name in ["Lockout", "Lost Key", "Damaged Ignition", "Spare Key Programming"]:
            client_admin_service.upsert_service_type(fleetway.id, name)

        client_admin_service.upsert_form_field(fleetway.id, "vehicle_registration", "Vehicle Registration", "text", True, 0)
        client_admin_service.upsert_form_field(fleetway.id, "vehicle_make_model", "Make / Model", "text", True, 1)
        client_admin_service.upsert_form_field(fleetway.id, "location_address", "Site Address", "textarea", True, 2)
        client_admin_service.upsert_form_field(fleetway.id, "urgency", "Urgency", "select", True, 3, options=["Standard", "Urgent", "Same Day"])
        client_admin_service.upsert_form_field(fleetway.id, "on_site_contact_name", "On-site Contact", "text", False, 4)

        client_admin_service.set_sla_target(fleetway.id, "time_to_quote", 4)
        client_admin_service.set_sla_target(fleetway.id, "time_to_attend", 48)
        client_admin_service.set_sla_target(fleetway.id, "time_to_complete", 72)

        # --- Client company 2: Bodyshop Direct ---
        bodyshop, bodyshop_admin_user, _ = client_admin_service.onboard_client(
            name="Bodyshop Direct",
            primary_color="#E0223B",
            admin_email="admin@bodyshopdirect.example",
            admin_first_name="Priya",
            admin_last_name="Shah",
        )
        bodyshop_admin_user.password_hash = hash_password("password123")
        db.session.commit()

        for name in ["Key Cutting", "Immobiliser Reset", "Boot Lock Repair"]:
            client_admin_service.upsert_service_type(bodyshop.id, name)

        client_admin_service.upsert_form_field(bodyshop.id, "vehicle_registration", "Vehicle Registration", "text", True, 0)
        client_admin_service.upsert_form_field(bodyshop.id, "vehicle_make_model", "Make / Model", "text", False, 1)
        client_admin_service.upsert_form_field(bodyshop.id, "location_address", "Workshop Address", "textarea", True, 2)

        client_admin_service.set_sla_target(bodyshop.id, "time_to_quote", 6)
        client_admin_service.set_sla_target(bodyshop.id, "time_to_attend", 48)
        client_admin_service.set_sla_target(bodyshop.id, "time_to_complete", 96)

        db.session.commit()

        # --- Sample enquiries at different lifecycle stages ---
        fleetway_lockout = ServiceType.query.filter_by(client_company_id=fleetway.id, name="Lockout").first()

        e1 = enquiry_service.create_enquiry(
            fleetway_general,
            fleetway.id,
            {
                "service_type_id": fleetway_lockout.id,
                "vehicle_registration": "AB12 CDE",
                "vehicle_make_model": "Ford Transit",
                "location_address": "12 Depot Road, Leeds",
                "urgency": "Urgent",
                "on_site_contact_name": "Dave, Site Manager",
            },
        )

        e2 = enquiry_service.create_enquiry(
            fleetway_general,
            fleetway.id,
            {
                "service_type_id": fleetway_lockout.id,
                "vehicle_registration": "XY99 ZZZ",
                "vehicle_make_model": "Mercedes Sprinter",
                "location_address": "Unit 4, Trade Park, Bristol",
                "urgency": "Standard",
            },
        )
        e2 = enquiry_service.send_quote(wgtk_general, e2, date.today() + timedelta(days=1), False, 145.00)
        e2 = enquiry_service.accept_quote(fleetway_general, e2)
        e2 = enquiry_service.schedule(wgtk_general, e2, datetime.now(timezone.utc) + timedelta(days=1, hours=2))

        e3 = enquiry_service.create_enquiry(
            fleetway_general,
            fleetway.id,
            {
                "service_type_id": fleetway_lockout.id,
                "vehicle_registration": "LK03 OST",
                "vehicle_make_model": "Vauxhall Vivaro",
                "location_address": "45 High Street, Manchester",
                "urgency": "Standard",
            },
        )
        e3 = enquiry_service.send_quote(wgtk_general, e3, date.today() - timedelta(days=3), False, 120.00)
        e3 = enquiry_service.accept_quote(fleetway_general, e3)
        e3 = enquiry_service.schedule(wgtk_general, e3, datetime.now(timezone.utc) - timedelta(days=2))
        e3 = enquiry_service.complete(wgtk_general, e3, "Vehicle unlocked, spare key cut and tested on site.")

        print("Seed complete.")
        print("  WGTK Admin:      admin@wgtk.co.uk / password123")
        print("  WGTK General:    staff@wgtk.co.uk / password123")
        print("  Fleetway Admin:  admin@fleetway.example / password123")
        print("  Fleetway General:ops@fleetway.example / password123")
        print("  Bodyshop Admin:  admin@bodyshopdirect.example / password123")
        print(f"  Enquiries seeded: {e1.reference} (new), {e2.reference} (scheduled), {e3.reference} (completed)")


if __name__ == "__main__":
    run()
