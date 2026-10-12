"""One place that turns every failure into a JSON response (CORS headers are added afterwards)."""
import logging

from flask import current_app
from flask_limiter.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.exceptions import HTTPException

from web.apis.utils.serializers import error_response
from web.extensions import db

log = logging.getLogger("web")

_MESSAGES = {
    400: "Bad request.",
    401: "Authentication required.",
    403: "Access forbidden.",
    404: "Resource not found.",
    405: "Method not allowed.",
    409: "This record already exists or conflicts with another one.",
    413: "The uploaded file is too large.",
    415: "Unsupported media type.",
    422: "Unprocessable request. Check the data you sent.",
    429: "Too many requests. Please slow down and try again shortly.",
}


def register_error_handlers(app):
    @app.errorhandler(RateLimitExceeded)
    def _rate_limited(exc):
        response, status = error_response(_MESSAGES[429], 429)
        retry = getattr(exc, "retry_after", None) or getattr(getattr(exc, "limit", None), "limit", None)
        if isinstance(retry, int):
            response.headers["Retry-After"] = str(retry)
        return response, status

    @app.errorhandler(HTTPException)
    def _http(exc):
        code = exc.code or 500
        return error_response(_MESSAGES.get(code) or exc.description or "Request failed.", code)

    @app.errorhandler(IntegrityError)
    def _integrity(exc):
        db.session.rollback()
        log.warning("Integrity error: %s", exc.orig)
        return error_response(_MESSAGES[409], 409)

    @app.errorhandler(SQLAlchemyError)
    def _database(exc):
        db.session.rollback()
        log.exception("Database error")
        return error_response("The database is temporarily unavailable. Please try again shortly.", 503)

    @app.errorhandler(Exception)
    def _unexpected(exc):
        db.session.rollback()
        log.exception("Unhandled error on %s", exc.__class__.__name__)
        message = str(exc) if current_app.debug else "Something went wrong on our side. Please try again."
        return error_response(message, 500)
