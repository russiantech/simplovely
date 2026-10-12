"""SimplyLovely API application factory."""
import logging
import sys
from os import getenv

from flask import Flask
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

from web.extensions import LOADED_ENV_FILES, config_app, db, init_ext

log = logging.getLogger("web")


def _configure_logging(app):
    if not logging.getLogger().handlers:
        logging.basicConfig(
            stream=sys.stderr,
            level=logging.DEBUG if app.debug else logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )


def _check_config(app):
    """Fail fast on the one thing that cannot be defaulted; warn about the rest."""
    cfg = app.config
    if not cfg.get("SECRET_KEY"):
        if cfg["ENV_NAME"] == "production":
            raise RuntimeError(
                "SECRET_KEY is not set. Define it in the environment or in a .env file "
                f"(searched: {LOADED_ENV_FILES or 'no .env file found'})."
            )
        import secrets

        cfg["SECRET_KEY"] = cfg["JWT_SECRET_KEY"] = secrets.token_urlsafe(48)
        log.warning("SECRET_KEY missing: using an ephemeral key (tokens reset on restart).")
    if not cfg.get("SQLALCHEMY_DATABASE_URI"):
        if cfg["ENV_NAME"] == "production":
            raise RuntimeError("SQLALCHEMY_DATABASE_URI is not set.")
        cfg["SQLALCHEMY_DATABASE_URI"] = "sqlite:///dev.db"
        log.warning("SQLALCHEMY_DATABASE_URI missing: using sqlite:///dev.db")
    for label, keys in {
        "Paystack": ("PAYSTACK_SK",),
        "Google OAuth": ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"),
        "Mail": ("MAIL_USERNAME", "MAIL_PASSWORD"),
    }.items():
        missing = [k for k in keys if not cfg.get(k)]
        if missing:
            log.warning("%s is not configured (missing %s): related features are disabled.", label, ", ".join(missing))


def create_app(config_name=None):
    config_name = (config_name or getenv("APP_ENV") or getenv("FLASK_ENV") or "production").lower()
    app = Flask(__name__, instance_relative_config=False)
    config_app(app, config_name)
    _configure_logging(app)
    _check_config(app)
    log.info("Starting SimplyLovely API (%s). Env files: %s", config_name, LOADED_ENV_FILES or "none")

    if app.config["TRUST_PROXY"]:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    init_ext(app)

    # Blueprints (importing the package registers every route and model)
    from web.apis import api_bp
    from web.apis.errors.handlers import register_error_handlers
    from web.apis.utils import auth as _auth  # noqa: F401 - registers JWT callbacks

    app.register_blueprint(api_bp, url_prefix="/api")
    register_error_handlers(app)
    from web.cli import register_cli

    register_cli(app)

    if app.config["AUTO_CREATE_TABLES"]:
        with app.app_context():
            try:
                db.create_all()
            except Exception:  # noqa: BLE001
                # Keep serving: /api/health reports the failure, other routes answer 500 JSON.
                log.exception("Database initialisation failed; check SQLALCHEMY_DATABASE_URI and the DB driver.")

    @app.get("/api/health")
    def health():
        """Liveness + DB check. Safe to expose: no secrets, no config values."""
        try:
            db.session.execute(text("SELECT 1"))
            database = "ok"
        except Exception:  # noqa: BLE001
            db.session.rollback()
            database = "error"
        status = 200 if database == "ok" else 503
        return {"status": "ok" if status == 200 else "degraded", "database": database}, status

    return app
