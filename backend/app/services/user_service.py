"""User administration. WGTK Admin manages both sides; Client Admin manages
only their own company's users. Every write here re-checks tenant scope even
though routes also gate by role — this is the layer we don't want a single
missing check in a route to bypass.
"""

import secrets

from app.extensions import bcrypt, db
from app.models.user import User, UserRole
from app.services.tenant_scope import assert_tenant_match
from app.utils.errors import ValidationError


def _hash(password):
    return bcrypt.generate_password_hash(password).decode("utf-8")


def generate_temp_password():
    return secrets.token_urlsafe(9)


def create_wgtk_user(email, first_name, last_name, role: UserRole, password=None):
    if not role.is_wgtk:
        raise ValidationError("Not a WGTK role")
    password = password or generate_temp_password()
    user = User(
        email=email.strip().lower(),
        first_name=first_name,
        last_name=last_name,
        role=role,
        password_hash=_hash(password),
    )
    db.session.add(user)
    db.session.commit()
    return user, password


def create_client_user(current_user, client_company_id, email, first_name, last_name, role: UserRole, password=None):
    """`current_user` must be WGTK Admin (onboarding a client's first Admin,
    or any user), or that same client's Admin (adding a colleague)."""
    if not role.is_client:
        raise ValidationError("Not a client role")
    if not (current_user.role == UserRole.WGTK_ADMIN or current_user.role == UserRole.CLIENT_ADMIN):
        raise ValidationError("Only an Admin can create users")
    if current_user.role == UserRole.CLIENT_ADMIN:
        assert_tenant_match(current_user, client_company_id)

    password = password or generate_temp_password()
    user = User(
        email=email.strip().lower(),
        first_name=first_name,
        last_name=last_name,
        role=role,
        client_company_id=client_company_id,
        password_hash=_hash(password),
    )
    db.session.add(user)
    db.session.commit()
    return user, password


def reset_password(current_user, target_user: User, new_password=None):
    if current_user.role == UserRole.CLIENT_ADMIN:
        assert_tenant_match(current_user, target_user.client_company_id)
    elif current_user.role != UserRole.WGTK_ADMIN:
        raise ValidationError("Only an Admin can reset passwords")

    new_password = new_password or generate_temp_password()
    target_user.password_hash = _hash(new_password)
    db.session.commit()
    return new_password


def deactivate_user(current_user, target_user: User):
    if current_user.role == UserRole.CLIENT_ADMIN:
        assert_tenant_match(current_user, target_user.client_company_id)
    elif current_user.role != UserRole.WGTK_ADMIN:
        raise ValidationError("Only an Admin can remove users")

    target_user.is_active = False
    db.session.commit()
    return target_user


def list_client_users(current_user, client_company_id):
    assert_tenant_match(current_user, client_company_id)
    return User.query.filter_by(client_company_id=client_company_id).order_by(User.created_at).all()


def list_wgtk_users():
    return User.query.filter(User.role.in_([UserRole.WGTK_ADMIN, UserRole.WGTK_GENERAL])).order_by(
        User.created_at
    ).all()
