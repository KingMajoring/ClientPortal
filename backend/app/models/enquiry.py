import enum

from app.extensions import db
from app.models.mixins import TimestampMixin, utcnow


class EnquiryStatus(str, enum.Enum):
    NEW = "NEW"
    QUOTED = "QUOTED"
    ACCEPTED = "ACCEPTED"
    DECLINED_BY_CLIENT = "DECLINED_BY_CLIENT"
    DECLINED_BY_WGTK = "DECLINED_BY_WGTK"
    SCHEDULED = "SCHEDULED"
    ETA_EXPIRED = "ETA_EXPIRED"
    COMPLETED = "COMPLETED"


class DeclineReasonType(str, enum.Enum):
    PRICE = "PRICE"
    ETA = "ETA"
    OTHER = "OTHER"


class Enquiry(db.Model, TimestampMixin):
    __tablename__ = "enquiries"

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(20), nullable=False, unique=True)  # e.g. WGTK-000123

    client_company_id = db.Column(db.Integer, db.ForeignKey("client_companies.id"), nullable=False, index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    service_type_id = db.Column(db.Integer, db.ForeignKey("service_types.id"), nullable=True)

    status = db.Column(db.Enum(EnquiryStatus), nullable=False, default=EnquiryStatus.NEW, index=True)

    # Fixed fields common across clients (also drive querying/reporting).
    vehicle_registration = db.Column(db.String(20), nullable=True)
    vehicle_make_model = db.Column(db.String(200), nullable=True)
    vehicle_year = db.Column(db.String(10), nullable=True)
    location_address = db.Column(db.String(500), nullable=True)
    urgency = db.Column(db.String(50), nullable=True)
    on_site_contact_name = db.Column(db.String(200), nullable=True)
    on_site_contact_phone = db.Column(db.String(50), nullable=True)

    # Anything beyond the fixed columns, per the client's EnquiryFormField config.
    extra_fields_json = db.Column(db.Text, nullable=True)

    # Quote
    eta_date = db.Column(db.Date, nullable=True)
    eta_is_same_day = db.Column(db.Boolean, nullable=False, default=False)
    price = db.Column(db.Numeric(10, 2), nullable=True)

    # Scheduling
    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    is_eta_expired = db.Column(db.Boolean, nullable=False, default=False)

    # Client decline
    decline_reason_type = db.Column(db.Enum(DeclineReasonType), nullable=True)
    decline_reason_text = db.Column(db.Text, nullable=True)

    # WGTK decline
    wgtk_decline_reason_text = db.Column(db.Text, nullable=True)

    # Placeholder for future Orbit/Soter CRM linkage. Not used in this phase.
    external_ref = db.Column(db.String(100), nullable=True)

    client_company = db.relationship("ClientCompany", back_populates="enquiries")
    created_by = db.relationship("User", foreign_keys=[created_by_user_id])
    service_type = db.relationship("ServiceType", back_populates="enquiries")
    status_history = db.relationship(
        "EnquiryStatusHistory",
        back_populates="enquiry",
        cascade="all, delete-orphan",
        order_by="EnquiryStatusHistory.created_at",
    )
    notes = db.relationship("JobNote", back_populates="enquiry", cascade="all, delete-orphan")
    documents = db.relationship("JobDocument", back_populates="enquiry", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Enquiry {self.reference} status={self.status}>"


class EnquiryStatusHistory(db.Model):
    """Full audit trail of status transitions — feeds SLA/MI reporting."""

    __tablename__ = "enquiry_status_history"

    id = db.Column(db.Integer, primary_key=True)
    enquiry_id = db.Column(db.Integer, db.ForeignKey("enquiries.id"), nullable=False, index=True)
    from_status = db.Column(db.Enum(EnquiryStatus), nullable=True)
    to_status = db.Column(db.Enum(EnquiryStatus), nullable=False)
    # Nullable: automatic transitions (e.g. ETA_EXPIRED) have no human actor.
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    enquiry = db.relationship("Enquiry", back_populates="status_history")
    changed_by = db.relationship("User")
