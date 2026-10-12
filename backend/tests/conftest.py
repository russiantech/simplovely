import os

os.environ["APP_ENV"] = "testing"
os.environ.setdefault("ENV_FILE", "/nonexistent")

import pytest

from web import create_app
from web.apis.models.plans import Plan
from web.apis.models.roles import Role
from web.apis.models.users import User
from web.cli import seed_reference_data
from web.extensions import db


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_reference_data()
        yield app
        db.session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()


def make_user(username, email, phone, password="Password123", role=None):
    user = User(username=username, email=email, phone=phone)
    user.set_password(password)
    user.email_verified = True
    user.roles.append(Role.query.filter_by(name=role or "user").one())
    db.session.add(user)
    db.session.commit()
    return user


def login(client, user, password="Password123"):
    r = client.post("/api/users/signin", json={"username": user.email, "password": password})
    assert r.status_code == 200, r.get_json()
    return {"Authorization": f"Bearer {r.get_json()['access_token']}"}


@pytest.fixture()
def alice(app):
    return make_user("alice", "alice@example.com", "08011111111")


@pytest.fixture()
def bob(app):
    return make_user("bob", "bob@example.com", "08022222222")


@pytest.fixture()
def admin(app):
    return make_user("boss", "boss@example.com", "08033333333", role="admin")


@pytest.fixture()
def plan(app):
    p = Plan(name="Starter", amount=5000, units=10, description="Starter plan")
    db.session.add(p)
    db.session.commit()
    return p
