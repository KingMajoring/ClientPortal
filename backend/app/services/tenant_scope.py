"""Single choke point for multi-tenant data isolation.

Every service function that reads/writes a client-scoped model (Enquiry,
JobNote, JobDocument, ServiceType, EnquiryFormField, ClientSLATarget,
ClientFeatureFlag, Notification) must build its query through
`scope_query_to_tenant` rather than filtering ad hoc in a route. That way a
missing filter in one route can't leak another company's data — there is
exactly one place tenant scoping can go wrong, and it's covered by tests.
"""

from app.utils.errors import ForbiddenError


def scope_query_to_tenant(query, model, current_user):
    """Restrict `query` (built against `model`, which must have a
    `client_company_id` column) to the current user's company. WGTK staff are
    not scoped — they see all clients, per spec."""
    if current_user.role.is_wgtk:
        return query
    if current_user.client_company_id is None:
        raise ForbiddenError("User is not associated with a client company")
    return query.filter(model.client_company_id == current_user.client_company_id)


def assert_tenant_match(current_user, client_company_id):
    """Guard for a single already-fetched record: raises if a client user is
    reaching for a record that belongs to a different company. WGTK staff are
    exempt. Use this even when the record came from an already-scoped query,
    as defence in depth for any lookup that bypassed scope_query_to_tenant
    (e.g. lookup by a token/reference passed in a URL)."""
    if current_user.role.is_wgtk:
        return
    if current_user.client_company_id != client_company_id:
        raise ForbiddenError("You do not have access to this resource")
