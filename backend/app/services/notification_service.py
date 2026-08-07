"""In-portal notifications + the stub email trigger for each lifecycle event.

Notifications are broadcast rather than fanned out per-user for phase 1: a
client-side notification is visible to the whole company (one row, matching
the "whole company" enquiry-visibility default), and a WGTK-side one is
visible to all WGTK staff. This keeps the schema simple; if per-user
read-state is needed later, a Notification/User join table is the natural
next step and doesn't require touching this module's call sites.
"""

from app.extensions import db
from app.models.notification import Notification, NotificationType
from app.models.user import User, UserRole
from app.services import email_service


def _notify_client_company(enquiry, notification_type, message):
    note = Notification(
        client_company_id=enquiry.client_company_id,
        enquiry_id=enquiry.id,
        notification_type=notification_type,
        message=message,
    )
    db.session.add(note)

    recipients = User.query.filter_by(client_company_id=enquiry.client_company_id, is_active=True).all()
    for user in recipients:
        email_service.send_email(
            to_email=user.email,
            subject=f"[{enquiry.reference}] {message}",
            body=message,
            notification_type=notification_type.value,
            enquiry_id=enquiry.id,
        )


def _notify_wgtk_staff(enquiry, notification_type, message):
    note = Notification(
        client_company_id=enquiry.client_company_id,
        target_role=UserRole.WGTK_GENERAL,
        enquiry_id=enquiry.id,
        notification_type=notification_type,
        message=message,
    )
    db.session.add(note)

    recipients = User.query.filter(
        User.role.in_([UserRole.WGTK_ADMIN, UserRole.WGTK_GENERAL]), User.is_active.is_(True)
    ).all()
    for user in recipients:
        email_service.send_email(
            to_email=user.email,
            subject=f"[{enquiry.reference}] {message}",
            body=message,
            notification_type=notification_type.value,
            enquiry_id=enquiry.id,
        )


def notify_new_enquiry(enquiry):
    _notify_wgtk_staff(enquiry, NotificationType.NEW_ENQUIRY, f"New enquiry {enquiry.reference} received")


def notify_quote_sent(enquiry):
    _notify_client_company(enquiry, NotificationType.QUOTE_SENT, f"Quote sent for {enquiry.reference}")


def notify_accepted(enquiry):
    _notify_wgtk_staff(enquiry, NotificationType.ACCEPTED, f"{enquiry.reference} accepted by client")


def notify_declined(enquiry, declined_by):
    """`declined_by` is 'client' or 'wgtk' — notify the other side."""
    if declined_by == "client":
        _notify_wgtk_staff(enquiry, NotificationType.DECLINED, f"{enquiry.reference} declined by client")
    else:
        _notify_client_company(enquiry, NotificationType.DECLINED, f"{enquiry.reference} declined by WGTK")


def notify_eta_expired(enquiry):
    _notify_wgtk_staff(enquiry, NotificationType.ETA_EXPIRED, f"ETA expired without update on {enquiry.reference}")


def notify_appointment_set(enquiry):
    _notify_client_company(enquiry, NotificationType.APPOINTMENT_SET, f"Appointment time set for {enquiry.reference}")


def notify_rescheduled(enquiry):
    _notify_client_company(enquiry, NotificationType.RESCHEDULED, f"{enquiry.reference} has been rescheduled")
    _notify_wgtk_staff(enquiry, NotificationType.RESCHEDULED, f"{enquiry.reference} has been rescheduled")


def notify_completed(enquiry):
    _notify_client_company(enquiry, NotificationType.COMPLETED, f"{enquiry.reference} marked complete")
