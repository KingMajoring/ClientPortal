from flask import send_file
from flask_login import current_user, login_required

from app.api.shared import shared_bp
from app.extensions import db
from app.models.job import JobDocument, NoteVisibility
from app.services import storage_service
from app.services.tenant_scope import assert_tenant_match
from app.utils.errors import ForbiddenError, NotFoundError


@shared_bp.get("/documents/<int:document_id>/download")
@login_required
def download_document(document_id):
    document = db.session.get(JobDocument, document_id)
    if not document:
        raise NotFoundError("Document not found")
    assert_tenant_match(current_user, document.enquiry.client_company_id)
    if current_user.role.is_client and document.visibility != NoteVisibility.CLIENT_VISIBLE:
        raise ForbiddenError("This document is not visible to client users")

    return send_file(
        storage_service.absolute_path_for(document.file_path),
        download_name=document.original_filename,
        mimetype=document.content_type,
    )
