from app.extensions import db
from app.models.mixins import TimestampMixin, utcnow


class ClientCompany(db.Model, TimestampMixin):
    """A trade client (fleet company / bodyshop). Root of the tenant boundary."""

    __tablename__ = "client_companies"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # White-labelling
    primary_color = db.Column(db.String(7), nullable=True)  # hex, e.g. "#1A2B3C"
    logo_path = db.Column(db.String(500), nullable=True)  # storage-relative path

    # Placeholder for future Orbit/Soter CRM linkage. Not used in this phase.
    external_ref = db.Column(db.String(100), nullable=True)

    # Apex RMS job sync (apex_service.py / apex_sync_service.py). AccountName
    # as it appears in Apex's own system, used to filter GetRecoveryJobsList
    # to just this client's jobs. Null means this client has no Apex sync.
    apex_account_name = db.Column(db.String(200), nullable=True)
    apex_last_synced_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # ANS "Contract Code" (field 1001) - identifies this client within
    # pending ANS job messages, which don't carry AccountName directly
    # (apex_ans_service.py / apex_sync_service.accept_ans_job()).
    apex_contract_code = db.Column(db.String(50), nullable=True)

    users = db.relationship("User", back_populates="client_company", lazy="dynamic")
    enquiries = db.relationship("Enquiry", back_populates="client_company", lazy="dynamic")
    feature_flags = db.relationship(
        "ClientFeatureFlag", back_populates="client_company", cascade="all, delete-orphan"
    )
    sla_targets = db.relationship(
        "ClientSLATarget", back_populates="client_company", cascade="all, delete-orphan"
    )
    service_types = db.relationship(
        "ServiceType", back_populates="client_company", cascade="all, delete-orphan"
    )
    form_fields = db.relationship(
        "EnquiryFormField", back_populates="client_company", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ClientCompany {self.id} {self.name!r}>"


class ClientFeatureFlag(db.Model):
    """Per-org feature/MI visibility toggle. Generic key/value so new features
    don't need a migration — Client Admin and WGTK Admin can both edit these."""

    __tablename__ = "client_feature_flags"
    __table_args__ = (db.UniqueConstraint("client_company_id", "feature_key", name="uq_feature_flag_per_client"),)

    id = db.Column(db.Integer, primary_key=True)
    client_company_id = db.Column(db.Integer, db.ForeignKey("client_companies.id"), nullable=False)
    feature_key = db.Column(db.String(100), nullable=False)  # e.g. "dashboard", "sla_report"
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)

    client_company = db.relationship("ClientCompany", back_populates="feature_flags")


class ClientSLATarget(db.Model):
    """Per-client SLA target. Generic key/value (metric_key -> target_hours) so new
    SLA metrics can be added later without a schema change."""

    __tablename__ = "client_sla_targets"
    __table_args__ = (db.UniqueConstraint("client_company_id", "metric_key", name="uq_sla_target_per_client"),)

    id = db.Column(db.Integer, primary_key=True)
    client_company_id = db.Column(db.Integer, db.ForeignKey("client_companies.id"), nullable=False)
    metric_key = db.Column(db.String(50), nullable=False)  # time_to_quote | time_to_attend | time_to_complete
    target_hours = db.Column(db.Float, nullable=False)

    client_company = db.relationship("ClientCompany", back_populates="sla_targets")


class ServiceType(db.Model):
    """Per-client job-type dropdown, configured by WGTK Admin at onboarding."""

    __tablename__ = "service_types"

    id = db.Column(db.Integer, primary_key=True)
    client_company_id = db.Column(db.Integer, db.ForeignKey("client_companies.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    client_company = db.relationship("ClientCompany", back_populates="service_types")
    enquiries = db.relationship("Enquiry", back_populates="service_type")


class EnquiryFormField(db.Model):
    """Data-driven enquiry form config per client: which fields exist, whether
    they're required, and (for select fields) their options. Drives both the
    client portal's rendered form and server-side validation on submit."""

    __tablename__ = "enquiry_form_fields"
    __table_args__ = (db.UniqueConstraint("client_company_id", "field_key", name="uq_form_field_per_client"),)

    id = db.Column(db.Integer, primary_key=True)
    client_company_id = db.Column(db.Integer, db.ForeignKey("client_companies.id"), nullable=False)
    field_key = db.Column(db.String(100), nullable=False)  # e.g. "vehicle_registration"
    label = db.Column(db.String(200), nullable=False)
    field_type = db.Column(db.String(20), nullable=False, default="text")  # text|select|date|checkbox|textarea|file
    is_required = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    options_json = db.Column(db.Text, nullable=True)  # JSON list of options, for field_type == "select"

    client_company = db.relationship("ClientCompany", back_populates="form_fields")
