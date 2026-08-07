"""Letter of Authority PDF generation.

Phase 1 uses a simple ReportLab template pre-filled with the enquiry's
vehicle details. This is a compliance document (SERMI — Security-related
Repair and Maintenance Information — access authorisation) giving WGTK
authority to work on the vehicle; the content here covers the fields the
spec calls out. Swapping this for a designed template/hosted PDF service
later only touches this file.
"""

from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.services import storage_service


def generate_letter_of_authority(enquiry):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 30 * mm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, y, "Letter of Authority")
    y -= 8 * mm
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, "SERMI-compliant authorisation for vehicle security-related repair and maintenance work")

    y -= 14 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, f"Enquiry reference: {enquiry.reference}")

    y -= 10 * mm
    c.setFont("Helvetica", 10)
    rows = [
        ("Client company", enquiry.client_company.name if enquiry.client_company else "-"),
        ("Vehicle registration", enquiry.vehicle_registration or "-"),
        ("Vehicle make/model", enquiry.vehicle_make_model or "-"),
        ("Location", enquiry.location_address or "-"),
        ("On-site contact", enquiry.on_site_contact_name or "-"),
    ]
    for label, value in rows:
        c.drawString(20 * mm, y, f"{label}: {value}")
        y -= 7 * mm

    y -= 6 * mm
    c.setFont("Helvetica", 9)
    text = (
        "By accepting this Letter of Authority, the client company named above authorises "
        "We've Got The Key (WGTK) to carry out security-related repair and maintenance work "
        "on the vehicle identified above, including obtaining any keys, key codes, or "
        "immobiliser data required to complete the work, in accordance with SERMI access "
        "requirements."
    )
    for line in _wrap(text, 95):
        c.drawString(20 * mm, y, line)
        y -= 5.5 * mm

    y -= 10 * mm
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, "Client acceptance: pending digital acceptance in the WGTK Client Portal")

    c.showPage()
    c.save()
    buffer.seek(0)

    relative_path = storage_service.save_bytes(
        enquiry.id, f"letter_of_authority_{enquiry.reference}.pdf", buffer.read()
    )
    return relative_path


def _wrap(text, width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines
