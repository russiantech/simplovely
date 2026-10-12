from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from web.apis.models.users import User


def test_authorize_builds_google_url_and_validates_callback(client, app):
    r = client.get("/api/users/authorize/google", headers={"Client-Callback-Url": "https://simplylovely.ng/signin"})
    url = r.get_json()["redirect"]
    q = parse_qs(urlparse(url).query)
    assert url.startswith("https://accounts.google.com/") and q["client_id"] == ["test-client.apps.googleusercontent.com"]
    assert q["redirect_uri"] == ["http://localhost:5001/api/users/callback/google"]
    assert client.get("/api/users/authorize/nothing").status_code == 404


def test_unconfigured_provider_gives_clear_error(client, app):
    app.config["GOOGLE_CLIENT_ID"] = None
    r = client.get("/api/users/authorize/google")
    assert r.status_code == 503 and "not available" in r.get_json()["error"]


def _state(client, cb="https://simplylovely.ng/signin"):
    url = client.get("/api/users/authorize/google", headers={"Client-Callback-Url": cb}).get_json()["redirect"]
    return parse_qs(urlparse(url).query)["state"][0]


def test_callback_rejects_open_redirect_and_bad_state(client, app):
    state = _state(client, "https://evil.example/steal")
    r = client.get(f"/api/users/callback/google?code=x&state={state}")
    assert r.headers["Location"].startswith("http://localhost:5002/signin#")  # fell back to our frontend
    bad = client.get("/api/users/callback/google?code=x&state=forged")
    assert "success=False" in bad.headers["Location"]


def test_callback_creates_user_and_returns_tokens_in_fragment(client, app):
    state = _state(client, "http://localhost:5002/signin")
    token = MagicMock(json=lambda: {"access_token": "g-token"})
    info = MagicMock(json=lambda: {"email": "Gina@Example.com", "email_verified": True, "name": "Gina", "picture": "http://x/p.png"})
    with patch("web.apis.utils.oauth.requests.post", return_value=token), patch("web.apis.utils.oauth.requests.get", return_value=info):
        r = client.get(f"/api/users/callback/google?code=abc&state={state}")
    loc = r.headers["Location"]
    assert loc.startswith("http://localhost:5002/signin#")
    frag = parse_qs(loc.split("#", 1)[1])
    assert frag["success"] == ["True"] and frag["access_token"]
    user = User.get_user(email="gina@example.com")
    assert user and user.email_verified and user.username == "gina"
    with patch("web.apis.utils.oauth.requests.post", return_value=token), patch("web.apis.utils.oauth.requests.get", return_value=info):
        client.get(f"/api/users/callback/google?code=abc&state={_state(client, 'http://localhost:5002/signin')}")
    assert User.query.filter_by(email="gina@example.com").count() == 1


def test_provider_rejection_is_reported_not_crashed(client, app):
    state = _state(client)
    with patch("web.apis.utils.oauth.requests.post", return_value=MagicMock(json=lambda: {"error": "invalid_client"})):
        r = client.get(f"/api/users/callback/google?code=abc&state={state}")
    assert "success=False" in r.headers["Location"]
