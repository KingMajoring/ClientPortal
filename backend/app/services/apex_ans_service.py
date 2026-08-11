"""Parses raw ANS Data Transmission Standard messages - the free-text
format Apex's GetAnsJobMessagesWaitingAcceptance returns for jobs still
sitting in the "waiting acceptance" queue, not yet a real Apex job.

Field meanings are taken from the official ANS Data Transmission Standard
spec (numbered fields like 1004, 1101, 1201 etc. have fixed, industry-wide
definitions - this isn't an Apex-specific format) and cross-checked
against a real Egertons message: the field count in that message's `9999`
terminator matched exactly, and two fields (1004 Job Number, 1210 Remarks)
matched values/text we'd already seen independently in Apex's own
GetRecoveryJobDetails output for other jobs.

Message format: one `"CODE,value[,value...]"` line per field. A field
can appear more than once (e.g. multi-line addresses) - either as
repeated lines with the same code, or joined with `^` within one line.
Both forms get flattened to newline-joined text here.
"""

import re

_LINE_RE = re.compile(r'^"(\d{4}),(.*)"$')


def parse_ans_message(message_text):
    """Returns {field_code: [raw_value, ...]}.

    Apex wraps the actual ANS field lines in SOURCE=/DEST=/MESSAGE=
    envelope lines; MESSAGE= prefixes the first field on the same line
    (e.g. `MESSAGE="9100,APX-JOB"`) rather than being on its own line."""
    fields = {}
    for line in (message_text or "").splitlines():
        line = line.strip()
        if line.startswith("MESSAGE="):
            line = line[len("MESSAGE="):]
        match = _LINE_RE.match(line)
        if not match:
            continue
        code, rest = match.groups()
        fields.setdefault(code, []).append(rest)
    return fields


def single_value(fields, code):
    values = fields.get(code)
    return values[0] if values else None


def _joined(fields, code):
    """Fields that can span multiple lines (1102, 1200, 1208, 1210) -
    flatten repeated-line and caret-joined forms alike to newline text."""
    values = fields.get(code)
    if not values:
        return None
    lines = [segment for value in values for segment in value.split("^")]
    text = "\n".join(line for line in lines if line).strip()
    return text or None


def _split_symptom(fields):
    """1116 Symptom Code is "code,description" - description is what we
    actually want to show/store; the code is Apex's own symptom taxonomy,
    which we don't have a mapping for, so it's dropped rather than guessed."""
    raw = single_value(fields, "1116")
    if not raw:
        return None
    parts = raw.split(",", 1)
    return parts[1].strip() if len(parts) > 1 and parts[1].strip() else parts[0].strip()


def _split_passengers(fields):
    raw = single_value(fields, "1203")
    if not raw:
        return None, None
    parts = [p.strip() for p in raw.split(",")]
    adults = parts[0] if len(parts) > 0 and parts[0] else None
    children = parts[1] if len(parts) > 1 and parts[1] else None
    return adults, children


def summarize(fields):
    """Human-readable preview of a pending ANS message, for staff to
    review before accepting it - not the full RecoveryJobDetails shape."""
    return {
        "job_number": single_value(fields, "1004"),
        "contract_code": single_value(fields, "1001"),
        "owner_name": single_value(fields, "1101"),
        "owner_phone": single_value(fields, "1201"),
        "vehicle_registration": single_value(fields, "1105"),
        "vehicle_make": single_value(fields, "1118"),
        "vehicle_model": single_value(fields, "1119"),
        "location": _joined(fields, "1200"),
        "destination": _joined(fields, "1208"),
        "symptom": _split_symptom(fields),
        "remarks": _joined(fields, "1210"),
        "priority": single_value(fields, "1240") == "Y",
    }


def build_recovery_job_details(fields, account_name):
    """Maps parsed ANS fields onto Apex's own RecoveryJobDetails shape,
    ready for apex_service.create_recovery_job(). `account_name` is set
    explicitly from our own client-company config (apex_account_name)
    rather than parsed from the message - JobSalesAccName is what Apex
    actually uses for account attribution, and we already know which
    client this message belongs to (that's how it got matched here)."""
    location = _joined(fields, "1200")
    postcode = single_value(fields, "1216")
    if location and postcode:
        location = f"{location}\n{postcode}"

    destination = _joined(fields, "1208")
    dest_postcode = single_value(fields, "1250")
    if destination and dest_postcode:
        destination = f"{destination}\n{dest_postcode}"

    adults, children = _split_passengers(fields)

    return {
        "JobOrderNo": single_value(fields, "1004"),
        "JobSalesAccName": account_name,
        "JobContractCode": single_value(fields, "1001"),
        "JobOwnerName": single_value(fields, "1101"),
        "JobOwnerAddress": _joined(fields, "1102"),
        "JobOwnerPhone": single_value(fields, "1201"),
        "JobVehicleRegistration": single_value(fields, "1105"),
        "JobVehicleMake": single_value(fields, "1118"),
        "JobVehicleModel": single_value(fields, "1119"),
        "JobVehicleFuelType": single_value(fields, "1120"),
        "JobLocationDesc": location,
        "JobDestinationDesc": destination,
        "Symptom": _split_symptom(fields),
        "JobRamNotes": _joined(fields, "1210"),
        "JobTowingTrailer": "true" if single_value(fields, "1112") == "Y" else "false",
        "JobPriorityFlag": "true" if single_value(fields, "1240") == "Y" else "false",
        "JobPassengerAdult": adults,
        "JobPassengerChild": children,
    }
