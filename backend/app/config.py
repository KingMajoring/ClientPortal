import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Local filesystem storage for dev; storage_service.py is the only place
    # that needs to change to swap this for Azure Blob Storage later.
    UPLOAD_ROOT = os.environ.get("UPLOAD_ROOT", os.path.join(BASE_DIR, "instance", "uploads"))

    # Stub email "delivery" — logs to console and records in EmailOutbox.
    # Swap MAIL_BACKEND to "smtp" and fill in the SMTP_* vars for real delivery later.
    MAIL_BACKEND = os.environ.get("MAIL_BACKEND", "console")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "no-reply@wgtk.co.uk")
    SMTP_HOST = os.environ.get("SMTP_HOST")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")

    # How long an unactioned ETA is allowed to stand before it's flagged expired.
    ETA_EXPIRY_GRACE_HOURS = int(os.environ.get("ETA_EXPIRY_GRACE_HOURS", "2"))


class DevConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'dev.db')}"
    )


class TestConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    UPLOAD_ROOT = "/tmp/wgtk-test-uploads"


class ProductionConfig(BaseConfig):
    DEBUG = False
    # Expected form for Azure SQL: mssql+pyodbc://<user>:<pass>@<server>/<db>?driver=ODBC+Driver+18+for+SQL+Server
    # Requires backend/requirements-mssql.txt installed on the target host.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")


CONFIG_BY_NAME = {
    "development": DevConfig,
    "testing": TestConfig,
    "production": ProductionConfig,
}
