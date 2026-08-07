import pytest

from app import create_app
from app.extensions import bcrypt, db
from app.models.user import User, UserRole
from app.services import client_admin_service


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def _make_user(email, role, client_company_id=None, password="password123"):
    user = User(
        email=email,
        first_name="Test",
        last_name="User",
        role=role,
        client_company_id=client_company_id,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def two_clients(app):
    with app.app_context():
        company_a, admin_a, _ = client_admin_service.onboard_client(
            "Company A", "#111111", "admin@a.example", "Admin", "A"
        )
        company_b, admin_b, _ = client_admin_service.onboard_client(
            "Company B", "#222222", "admin@b.example", "Admin", "B"
        )
        admin_a.password_hash = bcrypt.generate_password_hash("password123").decode("utf-8")
        admin_b.password_hash = bcrypt.generate_password_hash("password123").decode("utf-8")
        db.session.commit()
        wgtk_admin = _make_user("wgtk-admin@wgtk.co.uk", UserRole.WGTK_ADMIN)
        wgtk_general = _make_user("wgtk-general@wgtk.co.uk", UserRole.WGTK_GENERAL)
        return {
            "company_a_id": company_a.id,
            "company_b_id": company_b.id,
            "admin_a_email": admin_a.email,
            "admin_b_email": admin_b.email,
            "wgtk_admin_email": wgtk_admin.email,
            "wgtk_general_email": wgtk_general.email,
        }


def login(client, email, password="password123"):
    return client.post("/api/auth/login", json={"email": email, "password": password})
