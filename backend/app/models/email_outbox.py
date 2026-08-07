from app.extensions import db
from app.models.mixins import utcnow


class EmailOutbox(db.Model):
    """Stub email log — email_service.py writes here instead of calling real
    SMTP/SES/etc. Lets us verify "an email would have gone out" in dev/tests."""

    __tablename__ = "email_outbox"

    id = db.Column(db.Integer, primary_key=True)
    to_email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=True)
    enquiry_id = db.Column(db.Integer, db.ForeignKey("enquiries.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
