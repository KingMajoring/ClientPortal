import enum

from app.extensions import db
from app.models.mixins import utcnow
from app.models.user import UserRole


class NotificationType(str, enum.Enum):
    NEW_ENQUIRY = "NEW_ENQUIRY"
    QUOTE_SENT = "QUOTE_SENT"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    ETA_EXPIRED = "ETA_EXPIRED"
    APPOINTMENT_SET = "APPOINTMENT_SET"
    RESCHEDULED = "RESCHEDULED"
    COMPLETED = "COMPLETED"


class Notification(db.Model):
    """In-portal notification. Either targeted at a specific user, or broadcast
    to a role within a client company (client side) or across WGTK (staff side)."""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)

    # NULL for a WGTK-wide notification with no company context.
    client_company_id = db.Column(db.Integer, db.ForeignKey("client_companies.id"), nullable=True, index=True)
    # NULL when broadcasting to target_role instead of one user.
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    target_role = db.Column(db.Enum(UserRole), nullable=True)

    enquiry_id = db.Column(db.Integer, db.ForeignKey("enquiries.id"), nullable=True)
    notification_type = db.Column(db.Enum(NotificationType), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    client_company = db.relationship("ClientCompany")
    user = db.relationship("User")
    enquiry = db.relationship("Enquiry")
