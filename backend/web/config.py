"""Application configuration.

Everything is read from environment variables (loaded by ``web.extensions``).
This module must stay import-light: it must NOT import anything from ``web.apis``.
"""
from datetime import timedelta
from os import getenv

_TRUE = {"1", "true", "t", "yes", "y", "on"}


def env_bool(name, default=False):
    value = getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().strip("'\"").lower() in _TRUE


def env_int(name, default):
    try:
        return int(str(getenv(name, "")).strip().strip("'\"") or default)
    except ValueError:
        return default


def env_list(name, default=()):
    raw = getenv(name)
    if not raw:
        return list(default)
    return [item.strip().strip("'\"") for item in raw.split(",") if item.strip()]


def env_str(name, default=None):
    value = getenv(name)
    if value is None:
        return default
    value = value.strip().strip("'\"")
    return value or default


class Config:
    ENV_NAME = "base"
    DEBUG = False
    TESTING = False

    # --- Security ---------------------------------------------------------
    SECRET_KEY = env_str("SECRET_KEY") or env_str("JWT_SECRET_KEY")
    JWT_SECRET_KEY = env_str("JWT_SECRET_KEY") or SECRET_KEY
    # Tokens travel in the Authorization header only. Cookie based JWTs would
    # re-introduce CSRF requirements and are not used by the frontend.
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=env_int("JWT_ACCESS_MINUTES", 60))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=env_int("JWT_REFRESH_DAYS", 30))
    JWT_JSON_KEY = "access_token"
    JWT_REFRESH_JSON_KEY = "refresh_token"
    WTF_CSRF_ENABLED = False  # pure JSON API, authenticated by bearer tokens
    EMAIL_TOKEN_MAX_AGE = env_int("EMAIL_TOKEN_MAX_AGE", 60 * 60 * 24)  # verify link: 24h
    RESET_TOKEN_MAX_AGE = env_int("RESET_TOKEN_MAX_AGE", 60 * 60)  # reset link: 1h
    TRUST_PROXY = env_bool("TRUST_PROXY", True)

    # --- URLs / CORS ------------------------------------------------------
    FRONTEND_URL = (env_str("FRONTEND_URL", "https://simplylovely.ng") or "").rstrip("/")
    API_PUBLIC_URL = (env_str("API_PUBLIC_URL", "https://api.simplylovely.ng") or "").rstrip("/")
    CORS_ORIGINS = env_list(
        "CORS_ORIGINS",
        ["https://simplylovely.ng", "https://www.simplylovely.ng"],
    )
    # Allow any localhost / 127.0.0.1 port (dev only; see DevelopmentConfig)
    CORS_ALLOW_LOCALHOST = False
    PREFERRED_URL_SCHEME = "https"

    # --- Database ---------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = env_str("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_CREATE_TABLES = env_bool("AUTO_CREATE_TABLES", True)

    # --- Rate limiting ----------------------------------------------------
    # Generous global default (a page load fires several calls); strict limits
    # are applied per sensitive route (signin, signup, reset, ...).
    RATELIMIT_DEFAULT = env_str("RATELIMIT_DEFAULT", "600 per minute;30 per second")
    RATELIMIT_STORAGE_URI = env_str("REDIS_URL") or env_str("REDIS_URI") or "memory://"
    RATELIMIT_HEADERS_ENABLED = True

    # --- Payments ---------------------------------------------------------
    PAYSTACK_SK = env_str("PAYSTACK_SK")
    PAYSTACK_PK = env_str("PAYSTACK_PK")
    PAYSTACK_API = "https://api.paystack.co"
    PAYMENT_CURRENCY = "NGN"
    HTTP_TIMEOUT = env_int("HTTP_TIMEOUT", 20)

    # --- OAuth ------------------------------------------------------------
    GOOGLE_CLIENT_ID = env_str("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = env_str("GOOGLE_CLIENT_SECRET")
    GITHUB_CLIENT_ID = env_str("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET = env_str("GITHUB_CLIENT_SECRET")
    OAUTH_STATE_MAX_AGE = 600

    # --- Mail -------------------------------------------------------------
    MAIL_SERVER = env_str("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = env_int("MAIL_PORT", 587)
    MAIL_USE_TLS = env_bool("MAIL_USE_TLS", True)
    MAIL_USE_SSL = env_bool("MAIL_USE_SSL", False)
    MAIL_USERNAME = env_str("MAIL_USERNAME")
    MAIL_PASSWORD = env_str("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = ("SimplyLovely", env_str("DEFAULT_MAIL_SENDER") or env_str("MAIL_USERNAME") or "no-reply@simplylovely.ng")
    SUPPORT_EMAILS = env_list("SUPPORT_EMAILS") or [e for e in [env_str("MAIL_USERNAME")] if e]
    ADMINS = env_list("ADMINS")

    # --- Uploads ----------------------------------------------------------
    MEDIA_LOCATION = "static/images/"
    MAX_CONTENT_LENGTH = env_int("MAX_UPLOAD_BYTES", 16 * 1024 * 1024)
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "mp4"}
    IMAGE_MAX_DIMENSION = 1600

    JSON_SORT_KEYS = False


class DevelopmentConfig(Config):
    ENV_NAME = "development"
    DEBUG = True
    CORS_ALLOW_LOCALHOST = True
    PREFERRED_URL_SCHEME = "http"
    FRONTEND_URL = (env_str("FRONTEND_URL", "http://localhost:5002") or "").rstrip("/")
    API_PUBLIC_URL = (env_str("API_PUBLIC_URL", "http://localhost:5001") or "").rstrip("/")
    PAYSTACK_SK = env_str("PAYSTACK_TEST_SK") or Config.PAYSTACK_SK


class TestingConfig(Config):
    ENV_NAME = "testing"
    TESTING = True
    SECRET_KEY = "testing-secret-key-not-for-production-0123456789"
    JWT_SECRET_KEY = SECRET_KEY
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    CORS_ALLOW_LOCALHOST = True
    PREFERRED_URL_SCHEME = "http"
    FRONTEND_URL = "http://localhost:5002"
    API_PUBLIC_URL = "http://localhost:5001"
    RATELIMIT_ENABLED = False
    AUTO_CREATE_TABLES = True
    PAYSTACK_SK = "sk_test_unit"
    GOOGLE_CLIENT_ID = "test-client.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET = "test-secret"
    MAIL_SUPPRESS_SEND = True


class ProductionConfig(Config):
    ENV_NAME = "production"
    DEBUG = False


app_config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def engine_options(uri):
    """Connection-pool settings that are safe on shared hosting and sqlite."""
    if not uri or uri.startswith("sqlite"):
        return {}
    return {"pool_size": 5, "max_overflow": 10, "pool_timeout": 30, "pool_recycle": 280, "pool_pre_ping": True}
