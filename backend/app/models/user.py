import enum

from app.extensions import db
from app.models.mixins import TimestampMixin


class UserRole(str, enum.Enum):
    WGTK_ADMIN = "WGTK_ADMIN"
    WGTK_GENERAL = "WGTK_GENERAL"
    CLIENT_ADMIN = "CLIENT_ADMIN"
    CLIENT_GENERAL = "CLIENT_GENERAL"

    @property
    def is_wgtk(self):
        return self in (UserRole.WGTK_ADMIN, UserRole.WGTK_GENERAL)

    @property
    def is_client(self):
        return self in (UserRole.CLIENT_ADMIN, UserRole.CLIENT_GENERAL)

    @property
    def is_admin(self):
        return self in (UserRole.WGTK_ADMIN, UserRole.CLIENT_ADMIN)


class User(db.Model, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)

    # NULL for WGTK staff. Required (enforced in service layer) for client users.
    client_company_id = db.Column(db.Integer, db.ForeignKey("client_companies.id"), nullable=True)

    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Flask-Login integration
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self):
        return f"<User {self.id} {self.email!r} {self.role}>"


# Relationship declared after class body to avoid self-referential confusion above.
User.client_company = db.relationship("ClientCompany", back_populates="users")
