import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from web import api_base_for_host, create_app  # noqa: E402
from web.views import DASHBOARD_PAGES, PUBLIC_PAGES  # noqa: E402


@pytest.fixture()
def client():
    return create_app("testing").test_client()


@pytest.mark.parametrize("path", sorted({**PUBLIC_PAGES, **DASHBOARD_PAGES}))
def test_every_page_renders_with_server_decided_api(client, path):
    for host, expected in [("simplylovely.ng", "https://api.simplylovely.ng/api"), ("www.simplylovely.ng", "https://api.simplylovely.ng/api"),
                           ("localhost:5002", "http://localhost:5001/api"), ("127.0.0.1:5002", "http://127.0.0.1:5001/api")]:
        r = client.get(path, headers={"Host": host})
        assert r.status_code == 200
        assert f'"API_BASE": "{expected}"' in r.get_data(as_text=True), (path, host)


def test_no_template_guesses_the_api_url_itself(client):
    root = os.path.join(os.path.dirname(__file__), "..", "web")
    offenders = []
    for base, _, files in os.walk(root):
        if "vendor" in base or "3.6.12" in base:
            continue
        for name in files:
            if name.endswith((".html", ".js")) and not name.endswith(".min.js"):
                text = open(os.path.join(base, name), encoding="utf-8", errors="ignore").read()
                if re.search(r"hostname\s*===?\s*['\"]simplylovely\.ng|localhost:5001", text):
                    offenders.append(name)
    assert offenders == []


def test_error_pages_render(client):
    r = client.get("/definitely-missing")
    assert r.status_code == 404 and "Page not found" in r.get_data(as_text=True)


def test_api_base_override():
    cfg = {"API_BASE_URL": "https://x.example/api", "PROD_DOMAIN": "simplylovely.ng", "PROD_API_URL": "p", "DEV_API_PORT": 5001}
    assert api_base_for_host("anything", cfg) == "https://x.example/api"
