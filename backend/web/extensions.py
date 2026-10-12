"""Centralised Flask extensions and infrastructure helpers."""
from __future__ import annotations

import logging
import re
from os import getenv
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger("web")

# --------------------------------------------------------------------------
# Environment loading
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent


def load_environment() -> list[str]:
    """Load .env files without ever overriding real environment variables.

    Search order (first match for each variable wins):
      $ENV_FILE, <root>/.env.production (production only), <root>/.env,
      <root>/web/.env.production (production only), <root>/web/.env
    Returns the list of files that were loaded (for the startup log).
    """
    production = (getenv("APP_ENV") or getenv("FLASK_ENV") or "production").lower() == "production"
    candidates = []
    if getenv("ENV_FILE"):
        candidates.append(Path(getenv("ENV_FILE")))
    for folder in (BASE_DIR, BASE_DIR / "web"):
        if production:
            candidates.append(folder / ".env.production")
        candidates.append(folder / ".env")
    loaded = []
    for file in candidates:
        if file.is_file():
            load_dotenv(file, override=False)
            loaded.append(str(file))
    return loaded


LOADED_ENV_FILES = load_environment()

# --------------------------------------------------------------------------
# Extensions
# --------------------------------------------------------------------------
from authlib.integrations.flask_client import OAuth  # noqa: E402
from faker import Faker  # noqa: E402
from flask import request  # noqa: E402
from flask_bcrypt import Bcrypt  # noqa: E402
from flask_cors import CORS  # noqa: E402
from flask_jwt_extended import JWTManager  # noqa: E402
from flask_limiter import Limiter  # noqa: E402
from flask_limiter.util import get_remote_address  # noqa: E402
from flask_mail import Mail  # noqa: E402
from flask_migrate import Migrate  # noqa: E402
from flask_sqlalchemy import SQLAlchemy  # noqa: E402

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
bcrypt = Bcrypt()
jwt = JWTManager()
oauth = OAuth()
fake = Faker()


def _client_ip():
    """Real client IP behind a proxy (ProxyFix has already normalised it)."""
    return get_remote_address()


limiter = Limiter(
    key_func=_client_ip,
    default_limits_exempt_when=lambda: request.method == "OPTIONS",
    strategy="fixed-window",
    # Never let a limiter storage outage take the API down.
    swallow_errors=True,
    in_memory_fallback_enabled=True,
)


def resolve_limiter_storage(uri: str | None) -> str:
    """Use Redis only if it answers a PING; otherwise fall back to memory."""
    if not uri or uri.startswith("memory"):
        return "memory://"
    try:
        from redis import Redis

        Redis.from_url(uri, socket_connect_timeout=2, socket_timeout=2).ping()
        return uri
    except Exception as exc:  # noqa: BLE001 - any failure means "no redis"
        logger.warning("Redis unavailable (%s); rate limits use in-process memory.", exc)
        return "memory://"


def init_cors(app) -> None:
    origins = list(app.config["CORS_ORIGINS"])
    if app.config.get("CORS_ALLOW_LOCALHOST"):
        origins.append(re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"))
    CORS(
        app,
        resources={r"/api/*": {"origins": origins}},
        supports_credentials=True,
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=r".*",  # echo whatever the browser asks for (incl. X-CSRFToken)
        expose_headers=["Content-Type", "Retry-After", "X-Request-ID"],
        max_age=3600,
    )


def config_app(app, config_name: str) -> None:
    from web.config import app_config, engine_options

    app.config.from_object(app_config[config_name])
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options(app.config.get("SQLALCHEMY_DATABASE_URI"))
    app.config["RATELIMIT_STORAGE_URI"] = resolve_limiter_storage(app.config.get("RATELIMIT_STORAGE_URI"))


def init_ext(app) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    oauth.init_app(app)
    limiter.init_app(app)
    init_cors(app)
