from tests.conftest import login


def test_client_cannot_see_other_companys_enquiry(client, two_clients, app):
    from app.services import enquiry_service
    from app.models.user import User

    with app.app_context():
        admin_b = User.query.filter_by(email=two_clients["admin_b_email"]).first()
        enquiry = enquiry_service.create_enquiry(
            admin_b, two_clients["company_b_id"], {"vehicle_registration": "B1 XYZ"}
        )
        enquiry_id = enquiry.id

    login(client, two_clients["admin_a_email"])
    resp = client.get(f"/api/client/enquiries/{enquiry_id}")
    assert resp.status_code == 403


def test_client_sees_own_companys_enquiries(client, two_clients, app):
    from app.services import enquiry_service
    from app.models.user import User

    with app.app_context():
        admin_a = User.query.filter_by(email=two_clients["admin_a_email"]).first()
        enquiry_service.create_enquiry(admin_a, two_clients["company_a_id"], {"vehicle_registration": "A1 XYZ"})

    login(client, two_clients["admin_a_email"])
    resp = client.get("/api/client/enquiries")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1


def test_client_role_cannot_hit_staff_endpoints(client, two_clients):
    login(client, two_clients["admin_a_email"])
    resp = client.get("/api/staff/enquiries")
    assert resp.status_code == 403


def test_wgtk_sees_all_clients_enquiries(client, two_clients, app):
    from app.services import enquiry_service
    from app.models.user import User

    with app.app_context():
        admin_a = User.query.filter_by(email=two_clients["admin_a_email"]).first()
        admin_b = User.query.filter_by(email=two_clients["admin_b_email"]).first()
        enquiry_service.create_enquiry(admin_a, two_clients["company_a_id"], {"vehicle_registration": "A1"})
        enquiry_service.create_enquiry(admin_b, two_clients["company_b_id"], {"vehicle_registration": "B1"})

    login(client, two_clients["wgtk_general_email"])
    resp = client.get("/api/staff/enquiries")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2


def test_client_admin_cannot_reset_password_for_other_company(client, two_clients, app):
    from app.models.user import User

    with app.app_context():
        user_b = User.query.filter_by(email=two_clients["admin_b_email"]).first()
        user_b_id = user_b.id

    login(client, two_clients["admin_a_email"])
    resp = client.post(f"/api/client/users/{user_b_id}/reset-password")
    assert resp.status_code in (403, 404, 400)
