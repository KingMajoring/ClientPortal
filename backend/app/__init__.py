import os

from flask import Flask, jsonify
from flask_cors import CORS

from app.config import CONFIG_BY_NAME
from app.extensions import bcrypt, db, login_manager, migrate
from app.utils.errors import ApiError


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(CONFIG_BY_NAME[config_name])

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_ROOT"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.session_protection = "strong"

    # Frontend is a separate origin in dev (Vite on :5173); credentials are
    # required because auth is session-cookie based.
    CORS(app, supports_credentials=True, origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","))

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({"error": "Authentication required"}), 401

    @app.errorhandler(ApiError)
    def handle_api_error(err):
        return jsonify({"error": err.message}), err.status_code

    from app.auth.routes import auth_bp
    from app.api.staff import staff_bp
    from app.api.client import client_bp
    from app.api.shared import shared_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(staff_bp, url_prefix="/api/staff")
    app.register_blueprint(client_bp, url_prefix="/api/client")
    app.register_blueprint(shared_bp, url_prefix="/api/shared")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app
