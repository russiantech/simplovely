"""OAuth 2.0 helpers (Google, GitHub). Stateless: the ``state`` is a signed, expiring token."""
import logging
import re
import secrets
from urllib.parse import urlencode, urlparse

import requests
from flask import current_app

from web.apis.utils.auth import make_signed_token, read_signed_token

log = logging.getLogger("web")

PROVIDERS = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
        "scopes": ["openid", "email", "profile"],
        "extra": {"access_type": "online", "prompt": "select_account"},
    },
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scopes": ["read:user", "user:email"],
        "extra": {},
    },
}


class OAuthError(Exception):
    """An error whose message is safe to show to the end user."""


def provider_config(name):
    if name not in PROVIDERS:
        raise OAuthError("Unknown sign-in provider.")
    cfg = current_app.config
    client_id = cfg.get(f"{name.upper()}_CLIENT_ID")
    client_secret = cfg.get(f"{name.upper()}_CLIENT_SECRET")
    if not client_id or not client_secret:
        log.error("%s OAuth is not configured: set %s_CLIENT_ID and %s_CLIENT_SECRET.", name, name.upper(), name.upper())
        raise OAuthError(f"{name.title()} sign-in is not available right now. Please use email and password.")
    return {**PROVIDERS[name], "client_id": client_id, "client_secret": client_secret}


def redirect_uri(provider):
    """The exact URI that must be registered in the provider console."""
    from flask import url_for

    base = current_app.config.get("API_PUBLIC_URL")
    path = url_for("apis.oauth2_callback", provider=provider)
    return f"{base}{path}" if base else url_for("apis.oauth2_callback", provider=provider, _external=True)


def _origin(url):
    p = urlparse(url or "")
    return f"{p.scheme}://{p.netloc}" if p.scheme and p.netloc else None


def safe_callback_url(candidate):
    """Only redirect back to our own frontend(s). Anything else falls back to the default."""
    cfg = current_app.config
    default = f"{cfg['FRONTEND_URL']}/signin"
    origin = _origin(candidate)
    if not origin:
        return default
    allowed = {o.rstrip("/") for o in cfg["CORS_ORIGINS"]} | {_origin(cfg["FRONTEND_URL"])}
    local = cfg.get("CORS_ALLOW_LOCALHOST") and re.match(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$", origin)
    if origin in allowed or local:
        return candidate.split("#")[0].split("?")[0]
    log.warning("Rejected OAuth callback URL from unknown origin %s", origin)
    return default


def frontend_url(path="", candidate=None):
    """Absolute frontend URL for ``path``; uses the caller's own origin only if it is whitelisted."""
    cfg = current_app.config
    base = _origin(safe_callback_url(candidate)) if candidate else None
    return f"{base or cfg['FRONTEND_URL']}/{path.lstrip('/')}"


def authorize_url(provider, client_callback):
    cfg = provider_config(provider)
    state = make_signed_token("oauth-state", provider, {"cb": safe_callback_url(client_callback), "n": secrets.token_urlsafe(8)})
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": redirect_uri(provider),
        "response_type": "code",
        "scope": " ".join(cfg["scopes"]),
        "state": state,
        **cfg["extra"],
    }
    return f"{cfg['authorize_url']}?{urlencode(params)}"


def read_state(state, provider):
    """Return the frontend callback URL embedded in a valid state, else raise OAuthError."""
    payload = read_signed_token("oauth-state", state or "", current_app.config["OAUTH_STATE_MAX_AGE"])
    if not isinstance(payload, dict) or payload.get("email") != provider:
        raise OAuthError("The sign-in request expired. Please try again.")
    return payload["cb"]


def fetch_profile(provider, code):
    """Exchange ``code`` for a token and return ``{"email", "name", "avatar"}`` (verified email only)."""
    cfg = provider_config(provider)
    timeout = current_app.config["HTTP_TIMEOUT"]
    try:
        token_resp = requests.post(
            cfg["token_url"],
            data={
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri(provider),
            },
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
        token_json = token_resp.json()
    except (requests.RequestException, ValueError):
        log.exception("%s token exchange failed", provider)
        raise OAuthError("Could not reach the sign-in provider. Please try again.")

    access = token_json.get("access_token")
    if not access:
        log.error("%s token exchange rejected: %s", provider, token_json.get("error") or token_resp.status_code)
        raise OAuthError("The sign-in provider rejected the request. Please try again.")

    headers = {"Authorization": f"Bearer {access}", "Accept": "application/json"}
    try:
        info = requests.get(cfg["userinfo_url"], headers=headers, timeout=timeout).json()
        if provider == "github":
            emails = requests.get("https://api.github.com/user/emails", headers=headers, timeout=timeout).json()
            verified = [e for e in emails if isinstance(e, dict) and e.get("verified")]
            primary = next((e for e in verified if e.get("primary")), verified[0] if verified else None)
            return _profile(primary["email"] if primary else None, info.get("name") or info.get("login"), info.get("avatar_url"), True)
        return _profile(info.get("email"), info.get("name"), info.get("picture"), info.get("email_verified", False))
    except (requests.RequestException, ValueError):
        log.exception("%s userinfo failed", provider)
        raise OAuthError("Could not read your profile from the sign-in provider.")


def _profile(email, name, avatar, verified):
    if not email or not verified:
        raise OAuthError("Your account has no verified email address, so we cannot sign you in with it.")
    return {"email": email.strip().lower(), "name": name, "avatar": avatar}
