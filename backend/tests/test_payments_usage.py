import hashlib
import hmac
import json
from unittest.mock import patch

from tests.conftest import login
from web.apis.models.plans import Subscription, Usage
from web.apis.models.transactions import Transaction
from web.extensions import db


def paystack_ok(reference, amount_kobo, status="success", currency="NGN"):
    return {"status": status, "reference": reference, "amount": amount_kobo, "currency": currency}


def init(client, headers, plan):
    with patch("web.apis.pays._paystack", return_value={"authorization_url": "https://paystack/x", "access_code": "AC"}):
        r = client.post(f"/api/payment/{plan.id}/paystack", headers=headers)
    assert r.status_code == 200, r.get_json()
    return r.get_json()["reference"]


def verify(client, headers, ref, data):
    with patch("web.apis.pays._paystack", return_value=data):
        return client.get(f"/api/payment/callback/paystack?reference={ref}", headers=headers)


def test_init_requires_login_and_valid_plan(client, alice, plan):
    assert client.post(f"/api/payment/{plan.id}/paystack").status_code == 401
    h = login(client, alice)
    assert client.post("/api/payment/9999/paystack", headers=h).status_code == 404


def test_full_payment_and_repeat_purchase(client, alice, plan):
    h = login(client, alice)
    ref = init(client, h, plan)
    txn = Transaction.get_by_reference(ref)
    assert txn.amount == 5000 and txn.status == "pending"
    r = verify(client, h, ref, paystack_ok(ref, 500000))
    assert r.status_code == 200 and r.get_json()["total_units"] == 10
    # double click / retry: credited once only
    r2 = verify(client, h, ref, paystack_ok(ref, 500000))
    assert r2.status_code == 200 and "already" in r2.get_json()["message"]
    assert Subscription.query.filter_by(user_id=alice.id).one().total_units == 10
    # second purchase by the same (existing) user adds to the balance - this used to crash
    ref2 = init(client, h, plan)
    verify(client, h, ref2, paystack_ok(ref2, 500000))
    assert Subscription.query.filter_by(user_id=alice.id).one().total_units == 20


def test_underpayment_and_wrong_currency_are_not_credited(client, alice, plan):
    h = login(client, alice)
    ref = init(client, h, plan)
    assert verify(client, h, ref, paystack_ok(ref, 100)).status_code == 402
    assert Subscription.query.filter_by(user_id=alice.id).first() is None
    ref2 = init(client, h, plan)
    assert verify(client, h, ref2, paystack_ok(ref2, 500000, currency="USD")).status_code == 402


def test_price_change_after_init_does_not_affect_verification(client, alice, plan):
    h = login(client, alice)
    ref = init(client, h, plan)
    plan.amount = 99999
    db.session.commit()
    assert verify(client, h, ref, paystack_ok(ref, 500000)).status_code == 200  # frozen amount


def test_failed_pending_unknown(client, alice, plan):
    h = login(client, alice)
    ref = init(client, h, plan)
    assert verify(client, h, ref, paystack_ok(ref, 0, status="pending")).status_code == 202
    assert verify(client, h, ref, paystack_ok(ref, 0, status="failed")).status_code == 402
    assert Transaction.get_by_reference(ref).status == "failed"
    assert client.get("/api/payment/callback/paystack?reference=NOPE", headers=h).status_code == 404
    assert client.get("/api/payment/callback/paystack?reference=1", headers=h).status_code == 404  # no lookup by row id
    # a failed attempt can still be paid later (webhook/verify after success)
    assert verify(client, h, ref, paystack_ok(ref, 500000)).status_code == 200


def test_other_users_cannot_verify_my_transaction(client, alice, bob, plan):
    ref = init(client, login(client, alice), plan)
    assert verify(client, login(client, bob), ref, paystack_ok(ref, 500000)).status_code == 404


def test_webhook_signature_and_credit(client, alice, plan, app):
    ref = init(client, login(client, alice), plan)
    body = json.dumps({"event": "charge.success", "data": {"reference": ref}}).encode()
    assert client.post("/api/payment/webhook/paystack", data=body, headers={"x-paystack-signature": "bad"}).status_code == 401
    sig = hmac.new(app.config["PAYSTACK_SK"].encode(), body, hashlib.sha512).hexdigest()
    with patch("web.apis.pays._paystack", return_value=paystack_ok(ref, 500000)):
        assert client.post("/api/payment/webhook/paystack", data=body, headers={"x-paystack-signature": sig}).status_code == 200
        client.post("/api/payment/webhook/paystack", data=body, headers={"x-paystack-signature": sig})  # retry
    assert Subscription.query.filter_by(user_id=alice.id).one().total_units == 10


def test_provider_outage_marks_init_failed(client, alice, plan):
    from web.apis.pays import PaymentError
    h = login(client, alice)
    with patch("web.apis.pays._paystack", side_effect=PaymentError("down", 502)):
        r = client.post(f"/api/payment/{plan.id}/paystack", headers=h)
    assert r.status_code == 502 and Transaction.query.one().status == "failed"


def test_plans_admin_only_and_validation(client, alice, admin, plan):
    assert client.get("/api/plans").status_code == 200
    ha, hadmin = login(client, alice), login(client, admin)
    assert client.post("/api/plans", json={"name": "X", "amount": 1, "units": 1}, headers=ha).status_code == 403
    assert client.post("/api/plans", json={"name": "Bad", "amount": -5, "units": 3}, headers=hadmin).status_code == 400
    ok = client.post("/api/plans", json={"name": "Pro", "amount": 9000, "units": 30}, headers=hadmin)
    assert ok.status_code == 201
    pid = ok.get_json()["id"]
    assert client.delete(f"/api/plans/{pid}", headers=hadmin).status_code == 200
    names = [p["name"] for p in client.get("/api/plans").get_json()["plans"]]
    assert "Pro" not in names and "Starter" in names  # no stale cache


def test_usage_debit_limits_and_refund(client, alice, admin, plan):
    h, hadmin = login(client, alice), login(client, admin)
    assert client.post(f"/api/subscription/{alice.id}", json={"plan_id": plan.id}, headers=h).status_code == 403
    assert client.post(f"/api/subscription/{alice.id}", json={"plan_id": plan.id}, headers=hadmin).status_code == 201
    assert client.post("/api/usage", json={"user_id": alice.id, "units_used": 4}, headers=hadmin).status_code == 201
    assert client.post("/api/usage", json={"user_id": alice.id, "units_used": 7}, headers=hadmin).status_code == 400  # only 6 left
    assert client.post("/api/usage", json={"user_id": alice.id, "units_used": 0}, headers=hadmin).status_code == 400
    stats = client.get("/api/usage/statistics", headers=h).get_json()
    assert (stats["units_used"], stats["remaining_units"], stats["total_units"]) == (4, 6, 10)
    usage_id = Usage.query.one().id
    assert client.put(f"/api/usage/{usage_id}", json={"units_used": 6}, headers=hadmin).status_code == 200
    assert Subscription.query.one().total_units == 4
    assert client.delete(f"/api/usage/{usage_id}", headers=hadmin).status_code == 200
    assert Subscription.query.one().total_units == 10  # units restored
    # customers only see their own usage; anonymous sees nothing
    assert client.get("/api/usage").status_code == 401
    assert client.get(f"/api/user/{admin.id}/usage", headers=h).status_code == 403


def test_subscriptions_are_not_shared_between_users(client, alice, bob, admin, plan):
    hadmin = login(client, admin)
    client.post(f"/api/subscription/{alice.id}", json={"plan_id": plan.id}, headers=hadmin)
    ha, hb = login(client, alice), login(client, bob)
    assert client.get("/api/user/subscriptions", headers=ha).get_json()["count"] == 1
    assert client.get("/api/user/subscriptions", headers=hb).get_json()["count"] == 0  # was: cached copy of alice's
    assert client.get("/api/subscriptions", headers=hb).status_code == 403
    assert client.get("/api/transactions", headers=hb).get_json()["transactions"] == []
