"""JWT callbacks and signed one-purpose tokens (email verification, password reset)."""
from datetime import datetime, timezone

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from web.apis.models.tokens import RevokedToken
from web.apis.models.users import User
from web.apis.utils.serializers import error_response
from web.extensions import db, jwt

# ---------------------------------------------------------------- JWT callbacks


@jwt.user_identity_loader
def _identity(user_id):
    return str(user_id)


@jwt.user_lookup_loader
def _load_user(_header, data):
    sub = str(data["sub"])
    query = User.query.filter_by(is_deleted=False)
    user = query.filter_by(id=int(sub)).one_or_none() if sub.isdigit() else query.filter_by(email=sub).one_or_none()
    return user  # tokens issued before the id-based identity used the email as subject


@jwt.token_in_blocklist_loader
def _is_revoked(_header, data):
    return RevokedToken.is_revoked(data.get("jti"))


@jwt.unauthorized_loader
def _missing(reason):
    return error_response("Please sign in to continue.", 401)


@jwt.invalid_token_loader
def _invalid(reason):
    return error_response("Your session is invalid. Please sign in again.", 401)


@jwt.expired_token_loader
def _expired(_header, _data):
    return error_response("Your session has expired.", 401)


@jwt.revoked_token_loader
def _revoked(_header, _data):
    return error_response("Your session has ended. Please sign in again.", 401)


@jwt.user_lookup_error_loader
def _no_user(_header, _data):
    return error_response("Account not found. Please sign in again.", 401)


def revoke_token(claims):
    """Blacklist a decoded JWT (``get_jwt()``) until it would have expired anyway."""
    expires = datetime.fromtimestamp(claims["exp"], tz=timezone.utc).replace(tzinfo=None)
    db.session.add(RevokedToken(jti=claims["jti"], token_type=claims.get("type", "access"), expires_at=expires))


# --------------------------------------------------------- signed email tokens

def _serializer(purpose):
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=f"simplylovely.{purpose}")


def make_signed_token(purpose, email, extra=None):
    return _serializer(purpose).dumps({"email": email, **(extra or {})})


def read_signed_token(purpose, token, max_age):
    """Return the payload dict, or a string error code: ``"expired"`` / ``"invalid"``."""
    try:
        return _serializer(purpose).loads(token, max_age=max_age)
    except SignatureExpired:
        return "expired"
    except BadSignature:
        return "invalid"
