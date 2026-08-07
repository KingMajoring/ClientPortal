"""Stub email delivery. Logs to console and records every send in
EmailOutbox so tests/dev can assert "an email would have gone out" without a
real provider. Swap the body of `send_email` for a real SMTP/SES call later —
callers don't need to change."""

import logging

from flask import current_app

from app.extensions import db
from app.models.email_outbox import EmailOutbox
from app.models.mixins import utcnow

logger = logging.getLogger("wgtk.email")


def send_email(to_email, subject, body, notification_type=None, enquiry_id=None):
    entry = EmailOutbox(
        to_email=to_email,
        subject=subject,
        body=body,
        notification_type=notification_type,
        enquiry_id=enquiry_id,
    )
    db.session.add(entry)

    backend = current_app.config.get("MAIL_BACKEND", "console")
    if backend == "console":
        logger.info("EMAIL to=%s subject=%r\n%s", to_email, subject, body)
        entry.sent_at = utcnow()
    else:
        # Real SMTP delivery would go here; not wired up in this phase.
        logger.warning("MAIL_BACKEND=%s not implemented; email not sent", backend)

    db.session.commit()
    return entry
