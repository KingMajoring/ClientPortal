"""Raw SOAP client for Apex RMS (the fleet/recovery management system WGTK
runs its own operations on, https://wevegotthekey.apex-rms.com). Confirmed
against the real WSDL and live test calls:

- Every operation takes `apiLogin` + `apiPassword` as literal body
  parameters (not a SOAP header, not HTTP Basic Auth).
- Document/literal SOAP 1.1 over plain HTTP POST.

Hand-rolled with `requests` + `xml.etree.ElementTree` rather than a WSDL
client library (zeep etc.) since there are only two operations to call and
the exact envelope shape is already verified - a generic WSDL client would
be more code and more risk for no benefit here.
"""

import re
import time
from xml.etree import ElementTree
from xml.sax.saxutils import escape

import requests
from flask import current_app

from app.utils.errors import ApiError

NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
NS_API = "http://api.apex-rms.com/V1"

_SOAP_ENVELOPE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="{ns_soap}">
  <soap:Body>
    <{operation} xmlns="{ns_api}">
{fields}
    </{operation}>
  </soap:Body>
</soap:Envelope>"""


def _get_credentials():
    base_url = current_app.config.get("APEX_BASE_URL")
    username = current_app.config.get("APEX_USERNAME")
    password = current_app.config.get("APEX_PASSWORD")
    if not base_url or not username or not password:
        raise ApiError("Apex sync is not configured", status_code=503)
    return base_url, username, password


_LOCK_RETRY_DELAY_SECONDS = 3


def _post_envelope(envelope, operation):
    """Posts a fully-built SOAP envelope and returns the parsed response
    root. Retries once on Apex's "Job is currently locked" fault (a normal,
    transient condition when a job is open for editing in Apex's own UI at
    the same moment - not a real failure worth giving up on immediately)."""
    try:
        return _post_envelope_once(envelope, operation)
    except ApiError as exc:
        if "currently locked" not in exc.message.lower():
            raise
        time.sleep(_LOCK_RETRY_DELAY_SECONDS)
        return _post_envelope_once(envelope, operation)


def _post_envelope_once(envelope, operation):
    base_url, _, _ = _get_credentials()

    try:
        response = requests.post(
            base_url,
            headers={
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": f'"{NS_API}/{operation}"',
            },
            data=envelope.encode("utf-8"),
            timeout=30,
        )
    except requests.RequestException as exc:
        raise ApiError(f"Apex RMS is unreachable: {exc}", status_code=502)

    try:
        root = ElementTree.fromstring(response.content)
    except ElementTree.ParseError:
        raise ApiError("Apex RMS returned an unreadable response", status_code=502)

    fault = root.find(f".//{{{NS_SOAP}}}Fault")
    if fault is not None:
        # SOAP 1.1 fault children (faultcode/faultstring/faultactor/detail)
        # are unqualified per spec, unlike Fault itself which is namespaced.
        faultstring = fault.findtext("faultstring") or "Unknown Apex fault"
        # Apex prefixes framework noise onto its own message with " ---> ".
        message = faultstring.split(" ---> ")[-1].strip()
        raise ApiError(f"Apex RMS error: {message}", status_code=502)

    if not response.ok:
        raise ApiError(f"Apex RMS returned HTTP {response.status_code}", status_code=502)

    return root


def _field_xml(fields):
    """Renders a flat {name: value} dict as body elements. A value of
    `Nil` renders as an explicit xsi:nil element (needed for the several
    RecoveryJobDetails fields that are required-but-nillable per the WSDL -
    the element must be present even with no value)."""
    parts = []
    for key, value in fields.items():
        if value is Nil:
            parts.append(f'      <{key} xsi:nil="true" />')
        elif value is None:
            continue
        else:
            parts.append(f"      <{key}>{escape(str(value))}</{key}>")
    return "\n".join(parts)


class _NilType:
    """Sentinel distinguishing "send this field as an explicit SOAP nil"
    from "omit this field" (plain None)."""

    def __repr__(self):
        return "Nil"


Nil = _NilType()


def _call(operation, extra_fields=None):
    """`extra_fields` is an ordered dict of {field_name: value} beyond
    apiLogin/apiPassword, in the exact order the WSDL declares them."""
    _, username, password = _get_credentials()
    fields = {"apiLogin": username, "apiPassword": password}
    fields.update(extra_fields or {})
    envelope = _SOAP_ENVELOPE.format(ns_soap=NS_SOAP, ns_api=NS_API, operation=operation, fields=_field_xml(fields))
    return _post_envelope(envelope, operation)


def _strip_ns(tag):
    return re.sub(r"^\{.*\}", "", tag)


def _leaf_children_to_dict(elem):
    """Flattens an element's direct children into {local_tag: text},
    skipping any child that itself has children (e.g. JobServices) since
    nothing we map needs those."""
    result = {}
    for child in elem:
        if len(child) == 0:
            result[_strip_ns(child.tag)] = child.text
    return result


def list_jobs(account_name=None):
    """GetRecoveryJobsList, optionally filtered client-side to one
    AccountName (Apex doesn't support filtering server-side)."""
    root = _call("GetRecoveryJobsList")
    jobs = [_leaf_children_to_dict(el) for el in root.iter(f"{{{NS_API}}}JobsListDetails")]
    if account_name:
        jobs = [j for j in jobs if j.get("AccountName") == account_name]
    return jobs


def get_job_details(job_id):
    """GetRecoveryJobDetails for one job. Returns a flat dict of the
    top-level scalar fields (JobServices is intentionally dropped - see
    _leaf_children_to_dict)."""
    root = _call("GetRecoveryJobDetails", {"jobId": job_id})
    result_elem = root.find(f".//{{{NS_API}}}GetRecoveryJobDetailsResult")
    if result_elem is None:
        raise ApiError(f"Apex RMS returned no details for job {job_id}", status_code=502)
    return _leaf_children_to_dict(result_elem)


def add_job_history_entry(job_id, audit_text, job_type="RecoveryJob"):
    """Writes a manual entry into a job's audit log in Apex (the "Job
    Changes" history table visible in Apex's own UI) - the only write-back
    method Apex's API exposes; there's no method to set ETA/on-scene/
    completion timestamps directly, so lifecycle updates get pushed as
    timestamped notes here instead."""
    root = _call("AddJobHistoryEntry", {"jobId": job_id, "jobType": job_type, "auditText": audit_text})
    result_elem = root.find(f".//{{{NS_API}}}AddJobHistoryEntryResult")
    return (result_elem.text or "").strip().lower() == "true" if result_elem is not None else False


def list_ans_messages_waiting_acceptance():
    """GetAnsJobMessagesWaitingAcceptance - confirmed via the WSDL to use
    `apiPwd` rather than `apiPassword` like every other operation, a real
    inconsistency in Apex's own API. Returns raw {FromAnsNodeId,
    ToAnsNodeId, MessageText} dicts for ALL pending messages across every
    account WGTK receives ANS jobs from - callers filter by whatever they
    can parse out of MessageText (there's no account-name field here)."""
    _, username, password = _get_credentials()
    fields = {"apiLogin": username, "apiPwd": password}
    envelope = _SOAP_ENVELOPE.format(
        ns_soap=NS_SOAP, ns_api=NS_API, operation="GetAnsJobMessagesWaitingAcceptance", fields=_field_xml(fields)
    )
    root = _post_envelope(envelope, "GetAnsJobMessagesWaitingAcceptance")
    return [_leaf_children_to_dict(el) for el in root.iter(f"{{{NS_API}}}AnsJobMessage")]


# RecoveryJobDetails fields per Apex's integration guide + WSDL. JobStatus
# is required and must be a real JobStatuses enum value (not nillable).
# JobDateTime/ETA/the four GPS fields are required-but-nillable - the
# element must be present even with no value, hence the Nil sentinel.
_RECOVERY_JOB_DETAIL_FIELDS = [
    "JobOrderNo", "JobOrderNo2", "JobSalesAccName", "JobStatus", "Symptom", "FaultCode",
    "JobDateTime", "ETA", "JobLocationCode", "JobLocationDesc",
    "JobDestinationGpsLat", "JobDestinationGpsLng", "JobDestinationCode", "JobDestinationDesc",
    "JobRamNotes", "JobPlannedDriver", "JobOnHold", "JobAuthCode", "JobPdaNotes",
    "JobLocationGpsLat", "JobLocationGpsLng", "JobContractCode", "JobEdiJobNo", "JobSiteCode",
    "JobVehicleClass", "JobPriorityFlag", "JobPriorityReason", "JobPriorityDetail", "JobInvoiceNotes",
    "JobVehicleMake", "JobVehicleModel", "JobVehicleRegistration", "JobVehicleColour",
    "JobVehicleFuelType", "JobVehicleEngineDetails", "JobVehicleWeight", "JobLength", "JobTowingTrailer",
    "JobOwnerName", "JobOwnerCompany", "JobOwnerAddress", "JobOwnerMemberNo", "JobOwnerPhone",
    "JobOwnerEmail", "JobPassengerAdult", "JobPassengerChild", "JobVehicleFleetNo", "JobVehicleVin",
]
# JobVehicleMakeModel is deliberately excluded - the doc says "leave null"
# on create, and JobServices likewise ("leave null").


def create_recovery_job(details):
    """CreateRecoveryJob - creates a permanent job record in Apex's live
    system. `details` is a dict using the RecoveryJobDetails field names
    above; any field not in _RECOVERY_JOB_DETAIL_FIELDS is ignored. Missing
    fields are omitted except the handful that are required-but-nillable
    (sent as explicit nil automatically) and JobStatus (required, defaults
    to "Unallocated" - a brand new job hasn't been allocated to anyone yet).
    Returns the new Apex JobId."""
    nillable_if_missing = {
        "JobDateTime", "ETA", "JobDestinationGpsLat", "JobDestinationGpsLng",
        "JobLocationGpsLat", "JobLocationGpsLng",
    }
    job_detail_fields = {}
    for key in _RECOVERY_JOB_DETAIL_FIELDS:
        if key in details:
            job_detail_fields[key] = details[key]
        elif key in nillable_if_missing:
            job_detail_fields[key] = Nil
        elif key == "JobStatus":
            job_detail_fields[key] = "Unallocated"

    _, username, password = _get_credentials()
    fields = {"apiLogin": username, "apiPassword": password}
    # xsi is already declared on the root soap:Envelope element (see
    # _SOAP_ENVELOPE), so nested elements can use the xsi: prefix directly.
    field_xml_parts = [_field_xml(fields)]
    field_xml_parts.append("      <recJobDetail>")
    field_xml_parts.append(_field_xml(job_detail_fields))
    field_xml_parts.append("      </recJobDetail>")
    envelope = _SOAP_ENVELOPE.format(
        ns_soap=NS_SOAP, ns_api=NS_API, operation="CreateRecoveryJob", fields="\n".join(field_xml_parts)
    )
    root = _post_envelope(envelope, "CreateRecoveryJob")
    result_elem = root.find(f".//{{{NS_API}}}CreateRecoveryJobResult")
    if result_elem is None or not result_elem.text:
        raise ApiError("Apex RMS did not return a JobId for the new job", status_code=502)
    return int(result_elem.text)
