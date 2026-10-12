"""SimplyLovely web frontend: serves the HTML shell; all data comes from the API in the browser."""
from os import getenv

from flask import Flask, render_template, request

from web.extensions import load_dotenv  # noqa: F401 - loads .env on import
from web.site_data import fashion_services, laundry_services


def api_base_for_host(host, cfg):
    """The API URL the browser should call, decided once on the server."""
    if cfg["API_BASE_URL"]:
        return cfg["API_BASE_URL"]
    hostname = (host or "").split(":")[0].lower()
    domain = cfg["PROD_DOMAIN"]
    if hostname == domain or hostname.endswith("." + domain):  # apex, www, staging... all use the production API
        return cfg["PROD_API_URL"]
    if hostname in ("localhost", "127.0.0.1", "::1", ""):
        return f"http://{hostname or 'localhost'}:{cfg['DEV_API_PORT']}/api"
    return cfg["PROD_API_URL"]


def create_app(config_name=None):
    from web.config import app_config

    name = (config_name or getenv("APP_ENV") or getenv("FLASK_ENV") or "production").lower()
    app = Flask(__name__)
    app.config.from_object(app_config[name])

    @app.context_processor
    def site_context():
        return {
            "app_name": "Simply Lovely",
            "hype": "Fashion & Laundry.",
            "app_location": "Graceland Estate, Lekki, Lagos, Nigeria.",
            "app_email": "info@simplylovely.ng",
            "app_logo": app.config["LOGO_URL"],
            "site_logo": app.config["LOGO_URL"],
            "site_link": "https://www.simplylovely.ng/",
            "terms_link": "https://www.simplylovely.ng/terms",
            "policy_link": "https://www.simplylovely.ng/policy",
            "cookie_link": "https://www.simplylovely.ng/cookie",
            "whatsapp_link": "https://www.simplylovely.ng/",
            "laundry_services": laundry_services,
            "fashion_services": fashion_services,
            # Single source of truth for the browser (read by incs/metas.html -> window.APP_CONFIG)
            "app_config": {"API_BASE": api_base_for_host(request.host, app.config), "TOKEN_KEY": "access_token"},
        }

    from web.views import register_pages

    register_pages(app)

    ERRORS = {
        403: ("Access denied", "You don't have permission to view this page."),
        404: ("Page not found", "The page you are looking for doesn't exist or has moved."),
        500: ("Something went wrong", "We hit a problem on our side. Please try again in a moment."),
    }

    def render_error(code):
        title, message = ERRORS[code]
        return render_template("errors/error.html", code=code, title=title, message=message), code

    for code in ERRORS:
        app.register_error_handler(code, lambda _exc, code=code: render_error(code))

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
