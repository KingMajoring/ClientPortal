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

    # Auto Guru Services VRM lookup (vehicle_lookup_service.py). Leave unset
    # to disable the feature — the lookup endpoint then returns 503 and the
    # frontend falls back to manual entry.
    AUTOGURU_CLIENT_ID = os.environ.get("AUTOGURU_CLIENT_ID")
    AUTOGURU_CLIENT_SECRET = os.environ.get("AUTOGURU_CLIENT_SECRET")

    # Apex RMS job sync (apex_service.py). Leave unset to disable - the sync
    # endpoint then returns 503 rather than crashing.
    APEX_BASE_URL = os.environ.get("APEX_BASE_URL", "https://wevegotthekey.apex-rms.com/api/v1/RAndRWebService.asmx")
    APEX_USERNAME = os.environ.get("APEX_USERNAME")
    APEX_PASSWORD = os.environ.get("APEX_PASSWORD")


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
    # Expected form for Azure SQL: mssql+pyodbc://<user>:<pass>@<server>.database.windows.net:1433/<db>
    #   ?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no
    # Requires backend/requirements-mssql.txt + the msodbcsql18 driver on the
    # host — see the Dockerfile, which installs both for exactly this reason.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    # Served over HTTPS behind App Service's proxy (see ProxyFix in
    # create_app) — cookies should never go out in the clear.
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PREFERRED_URL_SCHEME = "https"


CONFIG_BY_NAME = {
    "development": DevConfig,
    "testing": TestConfig,
    "production": ProductionConfig,
}
