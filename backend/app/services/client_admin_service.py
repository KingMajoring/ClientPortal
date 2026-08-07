"""Client-company onboarding & configuration: branding, SLA targets,
enquiry form config, service types, and feature flags. Onboarding a brand
new client (WGTK Admin only) also creates their first Client Admin user.
"""

from app.extensions import db
from app.models.client import ClientCompany, ClientFeatureFlag, ClientSLATarget, EnquiryFormField, ServiceType
from app.models.user import UserRole
from app.services import user_service
from app.services.tenant_scope import assert_tenant_match
from app.utils.errors import ValidationError

DEFAULT_FEATURES = ["dashboard", "sla_report", "document_upload"]


def onboard_client(name, primary_color, admin_email, admin_first_name, admin_last_name):
    company = ClientCompany(name=name, primary_color=primary_color)
    db.session.add(company)
    db.session.flush()

    for feature_key in DEFAULT_FEATURES:
        db.session.add(ClientFeatureFlag(client_company_id=company.id, feature_key=feature_key, is_enabled=True))
    db.session.commit()

    admin_user, temp_password = user_service.create_client_user(
        current_user=_system_actor(),
        client_company_id=company.id,
        email=admin_email,
        first_name=admin_first_name,
        last_name=admin_last_name,
        role=UserRole.CLIENT_ADMIN,
    )
    return company, admin_user, temp_password


class _SystemActor:
    """Stands in for `current_user` during onboarding, where the acting user
    is WGTK Admin but we don't want user_service's create_client_user to
    re-check tenant match against a company that didn't exist a moment ago."""

    role = UserRole.WGTK_ADMIN
    client_company_id = None


def _system_actor():
    return _SystemActor()


def set_sla_target(client_company_id, metric_key, target_hours):
    target = ClientSLATarget.query.filter_by(client_company_id=client_company_id, metric_key=metric_key).first()
    if target:
        target.target_hours = target_hours
    else:
        target = ClientSLATarget(client_company_id=client_company_id, metric_key=metric_key, target_hours=target_hours)
        db.session.add(target)
    db.session.commit()
    return target


def set_feature_flag(current_user, client_company_id, feature_key, is_enabled):
    if current_user.role == UserRole.CLIENT_ADMIN:
        assert_tenant_match(current_user, client_company_id)
    flag = ClientFeatureFlag.query.filter_by(client_company_id=client_company_id, feature_key=feature_key).first()
    if flag:
        flag.is_enabled = is_enabled
    else:
        flag = ClientFeatureFlag(client_company_id=client_company_id, feature_key=feature_key, is_enabled=is_enabled)
        db.session.add(flag)
    db.session.commit()
    return flag


def upsert_service_type(client_company_id, name, sort_order=0):
    existing = ServiceType.query.filter_by(client_company_id=client_company_id, name=name).first()
    if existing:
        return existing
    service_type = ServiceType(client_company_id=client_company_id, name=name, sort_order=sort_order)
    db.session.add(service_type)
    db.session.commit()
    return service_type


def upsert_form_field(client_company_id, field_key, label, field_type, is_required, sort_order=0, options=None):
    import json

    field = EnquiryFormField.query.filter_by(client_company_id=client_company_id, field_key=field_key).first()
    if not field:
        field = EnquiryFormField(client_company_id=client_company_id, field_key=field_key)
        db.session.add(field)
    field.label = label
    field.field_type = field_type
    field.is_required = is_required
    field.sort_order = sort_order
    field.options_json = json.dumps(options) if options else None
    db.session.commit()
    return field


def feature_flags_for(client_company_id):
    return {f.feature_key: f.is_enabled for f in ClientFeatureFlag.query.filter_by(client_company_id=client_company_id)}


def is_feature_enabled(client_company_id, feature_key, default=True):
    flag = ClientFeatureFlag.query.filter_by(client_company_id=client_company_id, feature_key=feature_key).first()
    if not flag:
        return default
    return flag.is_enabled
