"""Frontend configuration (everything comes from environment variables)."""
from os import getenv


def _bool(name, default=False):
    value = getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = getenv("SECRET_KEY") or "frontend-has-no-secrets-but-flask-wants-one"
    DEBUG = False
    # Optional explicit API URL (e.g. https://api.simplylovely.ng/api). When empty it is derived
    # from the host the page is served from (see web.api_base_for_host).
    API_BASE_URL = (getenv("API_BASE_URL") or "").rstrip("/")
    PROD_DOMAIN = getenv("PROD_DOMAIN", "simplylovely.ng")
    PROD_API_URL = getenv("PROD_API_URL", "https://api.simplylovely.ng/api").rstrip("/")
    DEV_API_PORT = int(getenv("DEV_API_PORT", "5001"))
    LOGO_URL = getenv("LOGO_URL", "./static/img/logo_11.png")
    WTF_CSRF_ENABLED = False


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


app_config = {"development": DevelopmentConfig, "production": ProductionConfig, "testing": DevelopmentConfig}
