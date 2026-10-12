"""Accounts: sign-up / sign-in, tokens, email verification, password reset, OAuth, profile admin."""
import hashlib
import logging
import re
import secrets
from datetime import datetime, timezone
from urllib.parse import urlencode

from flask import current_app, redirect, request
from flask_jwt_extended import current_user, get_jwt, jwt_required
from sqlalchemy import desc, func
from sqlalchemy.exc import IntegrityError

from web.apis import api_bp as user_bp
from web.apis.models.roles import Role
from web.apis.models.users import User
from web.apis.schemas.user import ValidationFailed, clean_email, clean_password, clean_phone, clean_username, signup_data
from web.apis.utils import email as emailer
from web.apis.utils import oauth as oauth_utils
from web.apis.utils.auth import make_signed_token, read_signed_token, revoke_token
from web.apis.utils.decorators import admin_required
from web.apis.utils.get_or_create import get_or_create
from web.apis.utils.helpers import user_ip
from web.apis.utils.serializers import PageSerializer, error_response, get_pagination, success_response
from web.extensions import db, limiter

log = logging.getLogger("web")


# ----------------------------------------------------------------- helpers
def _json():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _session_payload(user, message):
    """Standard sign-in response body (tokens + user)."""
    user.last_seen = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.commit()
    return success_response(
        message,
        data={
            "access_token": user.make_token("access"),
            "refresh_token": user.make_token("refresh"),
            "redirect": "/account",
            "user": user.get_summary(include_roles=True),
        },
    )


def _resolve_user(ref):
    """Accept a numeric id, username or email."""
    ref = str(ref)
    return db.session.get(User, int(ref)) if ref.isdigit() else (User.get_user(username=ref) or User.get_user(email=ref))


def _can_manage(target):
    return bool(current_user) and (current_user.is_admin or current_user.id == target.id)


def _send_verification(user):
    token = make_signed_token("verify-email", user.email)
    link = oauth_utils.frontend_url(f"verify-email?{urlencode({'token': token})}", request.headers.get("Client-Callback-Url"))
    return emailer.send_verification_email(user, link)


def _password_fingerprint(user):
    """Binds a reset token to the current password so it works exactly once."""
    return hashlib.sha256((user.password or "").encode()).hexdigest()[:16]


# ----------------------------------------------------------- contact form
@user_bp.post("/users/message")
@limiter.limit("5 per hour")
def send_message():
    data = _json()
    try:
        email = clean_email(data.get("email"))
        phone = clean_phone(data.get("phone"), required=False)
    except ValidationFailed as exc:
        return error_response(str(exc))
    details = str(data.get("details") or "").strip()
    if len(details) < 5:
        return error_response("Please tell us a little more in the message.")
    try:
        budget = int(data.get("budget") or 0)
    except (TypeError, ValueError):
        return error_response("Budget must be a number.")
    recipients = current_app.config["SUPPORT_EMAILS"] + current_app.config["ADMINS"]
    context = {"name": data.get("name"), "email": email, "phone": phone, "budget": budget, "concern": data.get("concern"), "details": details}
    from flask import render_template

    sent = emailer.send_email(
        f"[Incoming Request] from {email}",
        sorted(set(recipients)),
        f"From: {email} (Phone: {phone})\n\n{details}",
        render_template("email/requests.html", **context),
    )
    if not sent:
        return error_response("We could not deliver your message right now. Please try again later or contact us on WhatsApp.", 503)
    return success_response("Your request has been submitted successfully. Thank you!")


# ------------------------------------------------------------------ signup
@user_bp.post("/users/signup")
@limiter.limit("10 per hour")
@jwt_required(optional=True)
def signup():
    if current_user and not current_user.is_admin:
        return error_response("You're already signed in. Sign out first to create a new account.")
    try:
        data = signup_data(_json())
    except ValidationFailed as exc:
        return error_response(str(exc))

    taken = User.query.filter(
        (func.lower(User.username) == data["username"].lower()) | (func.lower(User.email) == data["email"]) | (User.phone == data["phone"])
    ).first()
    if taken:
        if taken.email == data["email"]:
            return error_response("An account with this email address already exists.", 409)
        if taken.phone == data["phone"]:
            return error_response("An account with this phone number already exists.", 409)
        return error_response("That username is taken. Please choose another.", 409)

    try:
        user = User(username=data["username"], email=data["email"], phone=data["phone"], name=data["name"], ip=user_ip())
        user.set_password(data["password"])
        user.roles.append(get_or_create(db.session, Role, {"description": "Default role"}, name="user")[0])
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response("Those account details are already registered.", 409)

    # The account exists now; a mail problem must never turn this into an error.
    email_sent = _send_verification(user)
    body = user.get_summary()
    body.update(redirect="./signin", email_sent=email_sent)
    return success_response("Sign up successful. Please check your email to verify your account.", data=body, status_code=201)


# ------------------------------------------------------------------ signin
@user_bp.post("/users/signin")
@limiter.limit("10 per minute")
def signin():
    data = _json()
    identifier, password = str(data.get("username") or "").strip(), str(data.get("password") or "")
    if not identifier or not password:
        return error_response("Please enter your email, username or phone, and your password.")
    user = User.find_by_identifier(identifier)
    if not user or not user.check_password(password):
        return error_response("Invalid username or password.", 401)
    return _session_payload(user, "Sign in successful")


@user_bp.route("/users/refresh-token", methods=["POST"])
@limiter.limit("60 per minute")
@jwt_required(refresh=True)
def refresh_token():
    return success_response("Token refreshed successfully", data={"access_token": current_user.make_token("access")})


@user_bp.route("/users/signout", methods=["GET", "POST"])
@jwt_required()
def signout():
    revoke_token(get_jwt())
    refresh = _json().get("refresh_token")
    if refresh:
        try:
            from flask_jwt_extended import decode_token

            revoke_token(decode_token(refresh))
        except Exception:  # noqa: BLE001 - an already-invalid refresh token needs no revocation
            pass
    db.session.commit()
    return success_response("Sign out successful.", data={"redirect": "./signin"})


# ------------------------------------------------------- email verification
@user_bp.route("/users/verify-email/<token>", methods=["GET", "POST"])
@limiter.limit("30 per hour")
def verify_email(token):
    payload = read_signed_token("verify-email", token, current_app.config["EMAIL_TOKEN_MAX_AGE"])
    if payload == "expired":
        return error_response("This verification link has expired. Please request a new one.", 400)
    if not isinstance(payload, dict):
        return error_response("This verification link is invalid.", 400)
    user = User.get_user(email=payload["email"])
    if not user:
        return error_response("Account not found.", 404)
    already = user.email_verified
    if not already:
        user.email_verified = True
        db.session.commit()
    msg = "Email already verified. You can sign in." if already else "Email verified successfully! You can now sign in."
    return success_response(msg, data={"email": user.email, "verified": True, "already_verified": already, "redirect": "./signin"})


@user_bp.post("/users/resend-verification")
@limiter.limit("3 per hour")
@jwt_required(optional=True)
def resend_verification():
    user = current_user or User.get_user(email=_json().get("email") or "")
    generic = "If an unverified account exists for this email, a verification link has been sent."
    if not user:
        if not _json().get("email"):
            return error_response("Email is required.")
        return success_response(generic)  # do not reveal which emails are registered
    if user.email_verified:
        return error_response("This email is already verified.")
    return success_response(generic if not current_user else "Verification email sent. Please check your inbox.") if _send_verification(user) else error_response(
        "We could not send the email right now. Please try again later.", 503
    )


@user_bp.route("/users/check-verification-status", methods=["GET", "POST"])
@jwt_required()
def check_verification_status():
    user = current_user
    return success_response(
        "Verification status retrieved.",
        data={"email": user.email, "verified": user.email_verified, "email_verified": user.email_verified},
    )


# ---------------------------------------------------------- password reset
@user_bp.post("/users/reset-password")
@limiter.limit("5 per hour")
def request_password_reset():
    """Always answers with the same message so emails cannot be enumerated."""
    try:
        email = clean_email(_json().get("email"))
    except ValidationFailed as exc:
        return error_response(str(exc))
    user = User.get_user(email=email)
    if user and not user.is_deleted:
        token = make_signed_token("reset-password", user.email, {"fp": _password_fingerprint(user)})
        link = oauth_utils.frontend_url(f"reset-password?{urlencode({'token': token})}", request.headers.get("Client-Callback-Url"))
        emailer.send_reset_email(user, link)
    return success_response("If an account exists for that email, a password reset link has been sent.")


@user_bp.post("/users/reset-password/confirm")
@limiter.limit("10 per hour")
def confirm_password_reset():
    data = _json()
    payload = read_signed_token("reset-password", str(data.get("token") or ""), current_app.config["RESET_TOKEN_MAX_AGE"])
    if payload == "expired":
        return error_response("This reset link has expired. Please request a new one.")
    if not isinstance(payload, dict):
        return error_response("This reset link is invalid.")
    try:
        password = clean_password(data.get("password"))
    except ValidationFailed as exc:
        return error_response(str(exc))
    user = User.get_user(email=payload["email"])
    if not user or payload.get("fp") != _password_fingerprint(user):
        return error_response("This reset link has already been used or is no longer valid.")
    user.set_password(password)
    user.email_verified = True  # they proved control of the mailbox
    db.session.commit()
    return success_response("Your password has been updated. You can now sign in.", data={"redirect": "./signin"})


@user_bp.post("/users/change-password")
@jwt_required()
def change_password():
    data = _json()
    if not current_user.check_password(str(data.get("current_password") or "")):
        return error_response("Current password is incorrect.", 403)
    try:
        new_password = clean_password(data.get("new_password"))
    except ValidationFailed as exc:
        return error_response(str(exc))
    if new_password == data.get("current_password"):
        return error_response("Choose a password different from the current one.")
    if data.get("confirm_password") not in (None, new_password):
        return error_response("Password confirmation does not match.")
    current_user.set_password(new_password)
    db.session.commit()
    return success_response("Password changed successfully.")


# ------------------------------------------------------------------- OAuth
@user_bp.get("/users/authorize/<provider>")
@limiter.limit("30 per minute")
def oauth2_authorize(provider):
    try:
        url = oauth_utils.authorize_url(provider, request.headers.get("Client-Callback-Url") or request.args.get("callback_url"))
    except oauth_utils.OAuthError as exc:
        return error_response(str(exc), 503 if "not available" in str(exc) else 404)
    return success_response(f"Redirecting for {provider} sign-in", data={"redirect": url})


def _unique_username(email):
    base = re.sub(r"[^A-Za-z0-9_.-]", "", email.split("@")[0])[:24] or "user"
    base = base.ljust(3, "0")
    candidate = base
    while User.query.filter(func.lower(User.username) == candidate.lower()).first():
        candidate = f"{base}{secrets.randbelow(10000):04d}"
    return candidate


@user_bp.get("/users/callback/<provider>")
@limiter.limit("30 per minute")
def oauth2_callback(provider):
    """Browser lands here from the provider; we always bounce back to the frontend with a result."""
    try:
        frontend_cb = oauth_utils.read_state(request.args.get("state"), provider)
    except oauth_utils.OAuthError:
        frontend_cb = oauth_utils.safe_callback_url(None)

    def back(**params):
        return redirect(f"{frontend_cb}#{urlencode(params)}")

    if request.args.get("error") or not request.args.get("code"):
        return back(success="False", error="Sign-in was cancelled or denied.")
    try:
        oauth_utils.read_state(request.args.get("state"), provider)  # re-validate (signature + expiry)
        profile = oauth_utils.fetch_profile(provider, request.args["code"])
    except oauth_utils.OAuthError as exc:
        return back(success="False", error=str(exc))

    user = User.get_user(email=profile["email"])
    try:
        if user is None:
            user = User(
                email=profile["email"], username=_unique_username(profile["email"]), name=profile["name"],
                avatar=profile["avatar"], oauth_providers=provider, ip=user_ip(),
            )
            user.set_password(secrets.token_urlsafe(24))
            user.roles.append(get_or_create(db.session, Role, {"description": "Default role"}, name="user")[0])
            db.session.add(user)
        elif user.is_deleted:
            return back(success="False", error="This account is no longer active.")
        user.email_verified = True  # the provider verified it
        providers = set(filter(None, (user.oauth_providers or "").split(",")))
        user.oauth_providers = ",".join(sorted(providers | {provider}))
        user.last_seen = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return back(success="False", error="We could not create your account. Please try again.")
    return back(success="True", access_token=user.make_token("access"), refresh_token=user.make_token("refresh"), redirect="/account")


# --------------------------------------------------------- user management
@user_bp.get("/users")
@admin_required
def list_users():
    page, size = get_pagination(default_size=5)
    query = User.query.filter_by(is_deleted=False)
    term = (request.args.get("search") or "").strip()
    if term:
        like = f"%{term}%"
        query = query.filter(User.username.ilike(like) | User.email.ilike(like) | User.name.ilike(like))
    paginated = query.order_by(desc(User.created_at)).paginate(page=page, per_page=size, error_out=False)
    return success_response("Users fetched successfully", data=PageSerializer(pagination_obj=paginated, resource_name="users", include_roles=True).get_data())


@user_bp.get("/users/current")
@jwt_required()
def get_current_user():
    return success_response("Current user fetched successfully.", data=current_user.get_summary(include_products=True, include_roles=True))


@user_bp.get("/users/<user_ref>")
@jwt_required()
def get_user(user_ref):
    user = _resolve_user(user_ref)
    if not user or user.is_deleted:
        return error_response("User not found.", 404)
    if not _can_manage(user):
        return error_response("Access forbidden: insufficient permissions.", 403)
    return success_response("User fetched successfully.", data=user.get_summary(include_products=True, include_roles=True))


@user_bp.route("/users/<user_ref>", methods=["PUT", "POST", "PATCH"])
@jwt_required()
def update_user(user_ref):
    user = _resolve_user(user_ref)
    if not user or user.is_deleted:
        return error_response("User not found.", 404)
    if not _can_manage(user):
        return error_response("Unauthorized to update this user.", 403)
    data = _json()
    if not data:
        return error_response("No data provided.")
    try:
        changes = {}
        if data.get("username") and data["username"] != user.username:
            changes["username"] = clean_username(data["username"])
        if data.get("email") and data["email"].strip().lower() != user.email:
            changes["email"] = clean_email(data["email"])
        if "phone" in data and (data["phone"] or "") != (user.phone or ""):
            changes["phone"] = clean_phone(data["phone"], required=False)
        if data.get("password"):
            if not current_user.is_admin:
                return error_response("Use the change-password form to update your password.", 403)
            user.set_password(clean_password(data["password"]))
    except ValidationFailed as exc:
        return error_response(str(exc))

    for field, value in changes.items():
        clash = User.query.filter(User.id != user.id, getattr(User, field) == value).first() if value else None
        if clash:
            return error_response(f"That {field} is already in use.", 409)
    if "email" in changes:
        user.email_verified = False
    for field in ("name", "about_me", "avatar"):
        if data.get(field) is not None:
            setattr(user, field, str(data[field]).strip()[:300] or None)
    for field, value in changes.items():
        setattr(user, field, value)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response("Those details are already in use.", 409)
    if "email" in changes:
        _send_verification(user)
    return success_response("User updated successfully", data=user.get_summary(include_roles=True))


@user_bp.delete("/users/<user_ref>")
@jwt_required()
def delete_user(user_ref):
    """Soft-delete and free the unique identifiers; history (transactions, usage) is kept."""
    user = _resolve_user(user_ref)
    if not user or user.is_deleted:
        return error_response("User not found.", 404)
    if not _can_manage(user):
        return error_response("You do not have permission to delete this user.", 403)
    user.is_deleted = True
    user.email = f"deleted+{user.id}@deleted.invalid"
    user.username = f"deleted_{user.id}"
    user.phone = None
    user.name = user.avatar = user.about_me = None
    user.set_password(secrets.token_urlsafe(32))
    db.session.commit()
    return success_response("User deleted successfully.")
