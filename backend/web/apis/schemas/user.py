"""Input validation for the auth endpoints (returns a clean dict or raises ``ValidationFailed``)."""
import re

from email_validator import EmailNotValidError, validate_email

from web.apis.utils.helpers import normalize_phone

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
MIN_PASSWORD = 8


class ValidationFailed(ValueError):
    pass


def clean_email(value):
    try:
        return validate_email(str(value or "").strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        raise ValidationFailed("Please enter a valid email address.")


def clean_username(value):
    value = str(value or "").strip()
    if not USERNAME_RE.match(value):
        raise ValidationFailed("Username must be 3-32 characters: letters, numbers, dot, dash or underscore.")
    return value


def clean_phone(value, required=True):
    phone = normalize_phone(value)
    if phone is False:
        raise ValidationFailed("Please enter a valid phone number (7-15 digits).")
    if phone is None and required:
        raise ValidationFailed("Phone number is required.")
    return phone


def clean_password(value):
    value = str(value or "")
    if len(value) < MIN_PASSWORD:
        raise ValidationFailed(f"Password must be at least {MIN_PASSWORD} characters.")
    if len(value) > 128:
        raise ValidationFailed("Password is too long.")
    return value


def signup_data(data):
    return {
        "username": clean_username(data.get("username")),
        "email": clean_email(data.get("email")),
        "phone": clean_phone(data.get("phone")),
        "password": clean_password(data.get("password")),
        "name": (str(data.get("name")).strip()[:300] or None) if data.get("name") else None,
    }
