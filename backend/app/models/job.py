import enum

from app.extensions import db
from app.models.mixins import utcnow


class NoteVisibility(str, enum.Enum):
    INTERNAL = "INTERNAL"  # WGTK staff only
    CLIENT_VISIBLE = "CLIENT_VISIBLE"  # visible to WGTK + the owning client company


class DocumentType(str, enum.Enum):
    V5 = "V5"
    LETTER_OF_AUTHORITY = "LETTER_OF_AUTHORITY"
    JOB_SHEET = "JOB_SHEET"
    COMPLETION_REPORT = "COMPLETION_REPORT"
    OTHER = "OTHER"


class DocumentStatus(str, enum.Enum):
    PENDING_ACCEPTANCE = "PENDING_ACCEPTANCE"  # LoA generated, awaiting client digital acceptance
    ACCEPTED = "ACCEPTED"


class JobNote(db.Model):
    __tablename__ = "job_notes"

    id = db.Column(db.Integer, primary_key=True)
    enquiry_id = db.Column(db.Integer, db.ForeignKey("enquiries.id"), nullable=False, index=True)
    author_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    note_text = db.Column(db.Text, nullable=False)
    visibility = db.Column(db.Enum(NoteVisibility), nullable=False, default=NoteVisibility.INTERNAL)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    enquiry = db.relationship("Enquiry", back_populates="notes")
    author = db.relationship("User")


class JobDocument(db.Model):
    __tablename__ = "job_documents"

    id = db.Column(db.Integer, primary_key=True)
    enquiry_id = db.Column(db.Integer, db.ForeignKey("enquiries.id"), nullable=False, index=True)
    # Nullable: system-generated documents (e.g. the Letter of Authority) have no uploader.
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    document_type = db.Column(db.Enum(DocumentType), nullable=False)
    visibility = db.Column(db.Enum(NoteVisibility), nullable=False, default=NoteVisibility.CLIENT_VISIBLE)

    file_path = db.Column(db.String(500), nullable=False)  # relative to storage root — see storage_service.py
    original_filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(100), nullable=True)

    # Only meaningful for LETTER_OF_AUTHORITY (digital acceptance flow).
    status = db.Column(db.Enum(DocumentStatus), nullable=True)
    accepted_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    accepted_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    enquiry = db.relationship("Enquiry", back_populates="documents")
    uploaded_by = db.relationship("User", foreign_keys=[uploaded_by_user_id])
    accepted_by = db.relationship("User", foreign_keys=[accepted_by_user_id])
