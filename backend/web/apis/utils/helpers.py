"""Small, dependency-free helpers shared by the API modules."""
import re
import secrets
import string

from flask import current_app, request

_REF_ALPHABET = string.ascii_uppercase + string.digits


def user_ip():
    """Client IP (ProxyFix already resolved X-Forwarded-For when behind a proxy)."""
    return request.remote_addr


def generate_ref(prefix="TEC", length=12):
    """Unguessable, collision-resistant payment reference, e.g. ``LND-7K2Q9XW4M1AB``."""
    return f"{prefix}-" + "".join(secrets.choice(_REF_ALPHABET) for _ in range(length))


def validate_file_upload(filename):
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", {"png", "jpg", "jpeg", "mp4"})
    return bool(filename) and "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


_PHONE_RE = re.compile(r"^\+?\d{7,15}$")


def normalize_phone(value):
    """Strip separators; return ``None`` for empty input or ``False`` when invalid."""
    if value is None or str(value).strip() == "":
        return None
    cleaned = re.sub(r"[\s().-]", "", str(value))
    return cleaned if _PHONE_RE.match(cleaned) else False


def to_bool(value, default=False):
    """Parse form/JSON booleans safely (``bool("false")`` is True in Python)."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "on"}
