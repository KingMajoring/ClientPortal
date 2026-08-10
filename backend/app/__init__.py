import os

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import CONFIG_BY_NAME
from app.extensions import bcrypt, db, login_manager, migrate
from app.utils.errors import ApiError

# Built React app, copied in here at container-build time (see Dockerfile).
# In dev this directory doesn't exist — Vite serves the frontend separately
# on :5173 instead, so create_app() falls back to CORS for that case.
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "static_frontend")


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(CONFIG_BY_NAME[config_name])

    # App Service sits behind a reverse proxy that terminates TLS and sets
    # X-Forwarded-* headers; without this Flask thinks every request is
    # plain HTTP and secure cookies never get set.
    if config_name == "production":
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

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

    if os.path.isdir(FRONTEND_DIST):
        # Single-origin production deploy: Flask serves the built React app
        # directly, so there's no cross-site cookie/CORS story to get right.
        # This route is registered last, after every /api/* blueprint route,
        # but Werkzeug still matches it for an *unmatched* /api/... path (a
        # typo'd or removed endpoint) since <path:path> has no concept of
        # "already tried the api blueprints" — without the explicit guard
        # below, that 404 would silently become a 200 HTML page instead.
        @app.route("/", defaults={"path": ""})
        @app.route("/<path:path>")
        def serve_frontend(path):
            if path.startswith("api/"):
                return jsonify({"error": "Not found"}), 404
            candidate = os.path.join(FRONTEND_DIST, path) if path else None
            if candidate and os.path.isfile(candidate):
                return send_from_directory(FRONTEND_DIST, path)
            return send_from_directory(FRONTEND_DIST, "index.html")

    return app
