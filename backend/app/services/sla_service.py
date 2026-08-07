"""SLA compliance + MI calculations, kept separate from the raw data models so
the reporting layer can be extended (new metrics, new breakdowns) without
touching the enquiry lifecycle logic. Both the WGTK and client dashboards
call this module — the client-facing one just calls it with a fixed
client_company_id and gets the same shape back.
"""

from collections import defaultdict

from app.extensions import db
from app.models.client import ClientSLATarget
from app.models.enquiry import Enquiry, EnquiryStatus, EnquiryStatusHistory

# Each metric is defined by the (from_status, to_status) transition whose
# timestamp gap we measure. Adding a new SLA metric is: add a row here, and a
# matching ClientSLATarget with the same metric_key — no other code changes.
METRIC_TRANSITIONS = {
    "time_to_quote": (EnquiryStatus.NEW, EnquiryStatus.QUOTED),
    "time_to_attend": (EnquiryStatus.NEW, EnquiryStatus.SCHEDULED),
    "time_to_complete": (EnquiryStatus.SCHEDULED, EnquiryStatus.COMPLETED),
}


def _first_time_reached(history_rows, status):
    for row in history_rows:
        if row.to_status == status:
            return row.created_at
    return None


def compute_enquiry_metric_hours(enquiry):
    """Return {metric_key: hours_taken} for a single enquiry. For each metric
    we take the first time the enquiry reached `from_status` (or its creation
    time, for NEW) and the first time it reached `to_status`; metrics whose
    end transition hasn't happened yet are omitted."""
    history_rows = list(enquiry.status_history)
    first_reached = {EnquiryStatus.NEW: enquiry.created_at}
    for status in EnquiryStatus:
        if status not in first_reached:
            first_reached[status] = _first_time_reached(history_rows, status)

    results = {}
    for metric_key, (from_status, to_status) in METRIC_TRANSITIONS.items():
        start = first_reached.get(from_status)
        end = first_reached.get(to_status)
        if start and end and end >= start:
            results[metric_key] = round((end - start).total_seconds() / 3600, 2)
    return results


def compliance_summary(query, client_company_id=None):
    """query: an already tenant/date-scoped Enquiry query. Returns per-metric
    compliance against the relevant client's SLA targets."""
    enquiries = query.all()

    targets_by_client = defaultdict(dict)
    target_rows = ClientSLATarget.query
    if client_company_id:
        target_rows = target_rows.filter_by(client_company_id=client_company_id)
    for t in target_rows.all():
        targets_by_client[t.client_company_id][t.metric_key] = t.target_hours

    metric_actuals = defaultdict(list)
    metric_breaches = defaultdict(int)

    for enquiry in enquiries:
        actuals = compute_enquiry_metric_hours(enquiry)
        targets = targets_by_client.get(enquiry.client_company_id, {})
        for metric_key, hours in actuals.items():
            metric_actuals[metric_key].append(hours)
            target = targets.get(metric_key)
            if target is not None and hours > target:
                metric_breaches[metric_key] += 1

    summary = {}
    for metric_key in METRIC_TRANSITIONS:
        actuals = metric_actuals.get(metric_key, [])
        summary[metric_key] = {
            "target_hours": targets_by_client.get(client_company_id, {}).get(metric_key) if client_company_id else None,
            "sample_size": len(actuals),
            "average_hours": round(sum(actuals) / len(actuals), 2) if actuals else None,
            "breaches": metric_breaches.get(metric_key, 0),
            "compliance_rate": round(1 - (metric_breaches.get(metric_key, 0) / len(actuals)), 3) if actuals else None,
        }
    return summary


def mi_summary(query):
    """Job counts by status + ETA-expired flag count + volume-over-time, for
    an already tenant/date-scoped Enquiry query."""
    enquiries = query.all()

    counts_by_status = defaultdict(int)
    volume_by_day = defaultdict(int)
    eta_expired_count = 0

    for enquiry in enquiries:
        counts_by_status[enquiry.status.value] += 1
        volume_by_day[enquiry.created_at.date().isoformat()] += 1
        if enquiry.is_eta_expired:
            eta_expired_count += 1

    return {
        "total": len(enquiries),
        "counts_by_status": dict(counts_by_status),
        "eta_expired_count": eta_expired_count,
        "volume_by_day": dict(sorted(volume_by_day.items())),
    }


def base_query_for_range(client_company_id=None, date_from=None, date_to=None):
    query = db.session.query(Enquiry)
    if client_company_id:
        query = query.filter(Enquiry.client_company_id == client_company_id)
    if date_from:
        query = query.filter(Enquiry.created_at >= date_from)
    if date_to:
        query = query.filter(Enquiry.created_at <= date_to)
    return query
