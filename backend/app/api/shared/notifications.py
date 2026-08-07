from flask import jsonify
from flask_login import current_user, login_required

from app.api.serializers import serialize_notification
from app.api.shared import shared_bp
from app.extensions import db
from app.models.notification import Notification
from app.models.user import UserRole
from app.utils.errors import NotFoundError


def _visible_query():
    if current_user.role.is_wgtk:
        # Any WGTK-staff broadcast is visible to all WGTK staff regardless of
        # exact role (Admin can do everything General can), plus anything
        # addressed to this user specifically.
        return Notification.query.filter(
            (Notification.target_role.in_([UserRole.WGTK_ADMIN, UserRole.WGTK_GENERAL]))
            | (Notification.user_id == current_user.id)
        )
    return Notification.query.filter(Notification.client_company_id == current_user.client_company_id)


@shared_bp.get("/notifications")
@login_required
def list_notifications():
    notes = _visible_query().order_by(Notification.created_at.desc()).limit(100).all()
    return jsonify([serialize_notification(n) for n in notes])


@shared_bp.post("/notifications/<int:notification_id>/read")
@login_required
def mark_read(notification_id):
    note = _visible_query().filter(Notification.id == notification_id).first()
    if not note:
        raise NotFoundError("Notification not found")
    note.is_read = True
    db.session.commit()
    return jsonify(serialize_notification(note))
