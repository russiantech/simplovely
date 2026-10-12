"""Authorization decorators. All of them require a valid access token."""
from functools import wraps

from flask_jwt_extended import current_user, jwt_required

from web.apis.utils.serializers import error_response

ADMIN_ROLES = ("admin", "dev")


def roles_required(*roles):
    """Allow users holding ANY of ``roles`` (admins/devs always pass)."""
    allowed = set(roles) | set(ADMIN_ROLES)

    def decorator(view):
        @wraps(view)
        @jwt_required()
        def wrapper(*args, **kwargs):
            if not current_user or not allowed.intersection(current_user.get_roles()):
                return error_response("Access forbidden: insufficient permissions.", 403)
            return view(*args, **kwargs)

        return wrapper

    return decorator


def admin_required(view):
    """Admin / dev only."""
    return roles_required()(view)


def verified_required(view):
    """Signed-in users whose email address has been verified."""

    @wraps(view)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if not current_user.email_verified:
            return error_response("Please verify your email address first.", 403)
        return view(*args, **kwargs)

    return wrapper


def is_owner_or_admin(user_id):
    """True when the current user is ``user_id`` or an admin."""
    return bool(current_user) and (current_user.is_admin or current_user.id == user_id)
