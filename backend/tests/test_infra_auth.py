import re
from unittest.mock import patch

from tests.conftest import login, make_user
from web.extensions import db


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.get_json()["database"] == "ok"


def preflight(client, origin, headers="content-type"):
    return client.open("/api/users/signin", method="OPTIONS", headers={
        "Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": headers})


def test_cors_allows_csrf_headers_and_known_origins(client):
    r = preflight(client, "https://simplylovely.ng", "content-type,x-csrftoken,x-xsrf-token,authorization")
    assert r.status_code == 200
    allowed = r.headers["Access-Control-Allow-Headers"].lower()
    assert "x-csrftoken" in allowed and "authorization" in allowed
    assert r.headers["Access-Control-Allow-Origin"] == "https://simplylovely.ng"
    assert preflight(client, "https://www.simplylovely.ng").headers["Access-Control-Allow-Origin"]
    assert preflight(client, "http://127.0.0.1:5002").headers["Access-Control-Allow-Origin"]  # dev origin
    assert "Access-Control-Allow-Origin" not in preflight(client, "https://evil.example").headers


def test_errors_are_json_with_cors(client):
    r = client.get("/api/nope", headers={"Origin": "https://simplylovely.ng"})
    assert r.status_code == 404 and r.get_json()["success"] is False
    assert r.headers["Access-Control-Allow-Origin"] == "https://simplylovely.ng"


def test_signup_signin_flow(client):
    body = {"username": "newbie", "email": "New@Example.com", "phone": "0803 444 5555", "password": "Secret123"}
    with patch("web.apis.users.emailer.send_verification_email", return_value=False):  # mail down: must not fail signup
        r = client.post("/api/users/signup", json=body)
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["email_sent"] is False
    assert client.post("/api/users/signup", json=body).status_code == 409  # duplicate
    for ident in ("new@example.com", "newbie", "08034445555"):
        s = client.post("/api/users/signin", json={"username": ident, "password": "Secret123"})
        assert s.status_code == 200, ident
    assert client.post("/api/users/signin", json={"username": "newbie", "password": "wrong"}).status_code == 401


def test_signup_validation(client):
    base = {"username": "okname", "email": "ok@example.com", "phone": "08011112222", "password": "Secret123"}
    for field, value in [("email", "nope"), ("password", "short"), ("phone", "abc"), ("username", "a b")]:
        r = client.post("/api/users/signup", json={**base, field: value})
        assert r.status_code == 400 and r.get_json()["error"], field


def test_token_has_roles_and_refresh_and_signout(client, admin):
    r = client.post("/api/users/signin", json={"username": "boss", "password": "Password123"}).get_json()
    import base64, json
    payload = json.loads(base64.urlsafe_b64decode(r["access_token"].split(".")[1] + "=="))
    assert payload["roles"] == ["admin"] and payload["name"]
    new = client.post("/api/users/refresh-token", json={"refresh_token": r["refresh_token"]},
                      headers={"Authorization": f"Bearer {r['refresh_token']}"})
    assert new.status_code == 200 and new.get_json()["access_token"]
    h = {"Authorization": f"Bearer {r['access_token']}"}
    assert client.get("/api/users/current", headers=h).status_code == 200
    assert client.post("/api/users/signout", headers=h).status_code == 200
    assert client.get("/api/users/current", headers=h).status_code == 401  # revoked


def test_email_verification_and_reset_are_single_purpose(client, app):
    user = make_user("vera", "vera@example.com", "08055556666", password="OldPass123")
    user.email_verified = False
    db.session.commit()
    from web.apis.utils.auth import make_signed_token
    token = make_signed_token("verify-email", user.email)
    assert client.get(f"/api/users/verify-email/{token}").get_json()["verified"] is True
    assert client.get("/api/users/verify-email/garbage").status_code == 400

    captured = {}
    with patch("web.apis.users.emailer.send_reset_email", side_effect=lambda u, link: captured.setdefault("link", link) or True):
        assert client.post("/api/users/reset-password", json={"email": "vera@example.com"}).status_code == 200
        assert client.post("/api/users/reset-password", json={"email": "ghost@example.com"}).status_code == 200  # no enumeration
    reset_token = re.search(r"token=([^&]+)", captured["link"]).group(1)
    from urllib.parse import unquote
    reset_token = unquote(reset_token)
    assert client.post("/api/users/reset-password/confirm", json={"token": reset_token, "password": "short"}).status_code == 400
    assert client.post("/api/users/reset-password/confirm", json={"token": reset_token, "password": "NewPass1234"}).status_code == 200
    assert client.post("/api/users/reset-password/confirm", json={"token": reset_token, "password": "Another1234"}).status_code == 400  # one use
    assert client.post("/api/users/signin", json={"username": "vera", "password": "NewPass1234"}).status_code == 200
    # a verification token must not work as a reset token
    assert client.post("/api/users/reset-password/confirm", json={"token": token, "password": "Hijack12345"}).status_code == 400


def test_permissions_on_users(client, alice, bob, admin):
    ha, hb, hadmin = login(client, alice), login(client, bob), login(client, admin)
    assert client.get("/api/users").status_code == 401
    assert client.get("/api/users", headers=ha).status_code == 403
    assert client.get("/api/users", headers=hadmin).status_code == 200
    assert client.get(f"/api/users/{bob.id}", headers=ha).status_code == 403
    assert client.get(f"/api/users/{alice.id}", headers=ha).status_code == 200
    # update by numeric id (what the settings page does)
    r = client.put(f"/api/users/{alice.id}", json={"name": "Alice A", "phone": "08099990000"}, headers=ha)
    assert r.status_code == 200 and r.get_json()["name"] == "Alice A"
    assert client.put(f"/api/users/{bob.id}", json={"name": "x"}, headers=ha).status_code == 403
    assert client.delete(f"/api/users/{bob.id}", headers=ha).status_code == 403  # was: any user could delete anyone
    assert client.delete(f"/api/users/{bob.id}", headers=hadmin).status_code == 200
    assert client.post("/api/users/signin", json={"username": "bob@example.com", "password": "Password123"}).status_code == 401


def test_change_password(client, alice):
    h = login(client, alice)
    assert client.post("/api/users/change-password", json={"current_password": "bad", "new_password": "Brandnew123"}, headers=h).status_code == 403
    assert client.post("/api/users/change-password", json={"current_password": "Password123", "new_password": "Brandnew123"}, headers=h).status_code == 200
    assert client.post("/api/users/signin", json={"username": "alice", "password": "Brandnew123"}).status_code == 200
