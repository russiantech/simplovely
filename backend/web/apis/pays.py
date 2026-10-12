"""Paystack payments: initialise, verify (redirect/popup return) and webhook.

All three settlement paths end in ``settle()``, which is idempotent: a transaction credits the
customer's units exactly once no matter how many times (or how concurrently) it is verified.
"""
import hashlib
import hmac
import logging

import requests
from flask import current_app, request
from flask_jwt_extended import current_user, jwt_required

from web.apis import api_bp as pay_bp
from web.apis.models.plans import Plan, Subscription
from web.apis.models.transactions import ABANDONED, FAILED, PENDING, SUCCESS, Transaction
from web.apis.utils import oauth as oauth_utils
from web.apis.utils.helpers import generate_ref
from web.apis.utils.serializers import error_response, success_response
from web.extensions import db, limiter

log = logging.getLogger("web")


class PaymentError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def _paystack(method, path, **kwargs):
    secret = current_app.config.get("PAYSTACK_SK")
    if not secret:
        log.error("PAYSTACK_SK is not configured")
        raise PaymentError("Payments are temporarily unavailable. Please try again later.", 503)
    try:
        resp = requests.request(
            method,
            f"{current_app.config['PAYSTACK_API']}{path}",
            headers={"Authorization": f"Bearer {secret}", "Accept": "application/json"},
            timeout=current_app.config["HTTP_TIMEOUT"],
            **kwargs,
        )
        body = resp.json()
    except requests.Timeout:
        raise PaymentError("The payment provider timed out. Please try again.", 504)
    except (requests.RequestException, ValueError):
        log.exception("Paystack request %s %s failed", method, path)
        raise PaymentError("Could not reach the payment provider. Please try again.", 502)
    if not resp.ok or not body.get("status"):
        log.warning("Paystack %s %s -> %s %s", method, path, resp.status_code, body.get("message"))
        raise PaymentError(body.get("message") or "The payment provider rejected the request.", 502)
    return body.get("data") or {}


# --------------------------------------------------------------- initialise
@pay_bp.post("/payment/<int:plan_id>/paystack")
@limiter.limit("50 per minute")
@jwt_required()
def initiate_paystack(plan_id):
    plan = Plan.query.filter_by(id=plan_id, is_deleted=False).first()
    if not plan or plan.amount_naira <= 0 or plan.units <= 0:
        return error_response("This plan is not available.", 404)

    # Record intent first so every Paystack attempt is traceable; the amount is frozen here.
    txn = Transaction(
        user_id=current_user.id, plan_id=plan.id, amount=plan.amount_naira, currency=current_app.config["PAYMENT_CURRENCY"],
        payment_method="paystack", reference=generate_ref("LND"), status=PENDING, description=f"{plan.name} plan",
    )
    db.session.add(txn)
    db.session.commit()

    callback = oauth_utils.frontend_url("plans", request.headers.get("Client-Callback-Url"))
    try:
        data = _paystack(
            "POST", "/transaction/initialize",
            json={
                "email": current_user.email,
                "amount": txn.amount * 100,  # kobo
                "currency": txn.currency,
                "reference": txn.reference,
                "callback_url": callback,
                "metadata": {"plan_id": plan.id, "user_id": current_user.id, "cancel_action": f"{callback}?reference={txn.reference}"},
            },
        )
    except PaymentError as exc:
        txn.status, txn.description = FAILED, f"Initialisation failed: {exc}"[:255]
        db.session.commit()
        return error_response(str(exc), exc.status)

    return success_response(
        "Payment initialized successfully.",
        data={
            "redirect": data.get("authorization_url"),
            "access_code": data.get("access_code"),
            "reference": txn.reference,
            "amount": txn.amount,
            "email": current_user.email,
            "public_key": current_app.config.get("PAYSTACK_PK"),
        },
    )


# ------------------------------------------------------------------ settle
def settle(reference):
    """Verify ``reference`` with Paystack and apply the result once.

    Returns ``(transaction, outcome)`` where outcome is one of
    ``success | already | pending | failed | not_found``.
    """
    if not Transaction.get_by_reference(reference):
        return None, "not_found"
    data = _paystack("GET", f"/transaction/verify/{reference}")  # network call outside the DB lock
    status = (data.get("status") or "").lower()

    txn = Transaction.get_by_reference(reference, lock=True)  # row lock: serialises concurrent settlements
    if txn.is_success:
        db.session.rollback()
        return txn, "already"

    if status == "success":
        valid = (
            data.get("reference") == txn.reference
            and data.get("currency") == txn.currency
            and int(data.get("amount") or 0) >= txn.amount * 100
        )
        if not valid:
            log.error("Paystack amount/reference mismatch for %s: %s", reference, {k: data.get(k) for k in ("reference", "currency", "amount")})
            txn.status, txn.description = FAILED, "Verification mismatch - flagged for manual review."
            db.session.commit()
            return txn, "failed"
        plan = db.session.get(Plan, txn.plan_id) if txn.plan_id else None
        if plan is None:
            log.error("Transaction %s paid but its plan %s no longer exists", reference, txn.plan_id)
            txn.status, txn.description = SUCCESS, "Paid, but plan missing - credit manually."
        else:
            Subscription.credit(txn.user_id, plan)
            txn.status = SUCCESS
        db.session.commit()
        return txn, "success"

    if status in ("failed", "reversed"):
        txn.status = FAILED
    elif status == "abandoned":
        txn.status = ABANDONED
    else:  # pending / ongoing / queued: keep waiting
        db.session.rollback()
        return txn, "pending"
    db.session.commit()
    return txn, "failed"


@pay_bp.get("/payment/callback/paystack")
@limiter.limit("60 per minute")
@jwt_required(optional=True)
def callback_paystack():
    reference = request.args.get("reference") or request.args.get("trxref")
    if not reference:
        return error_response("Transaction reference is required.")
    existing = Transaction.get_by_reference(reference)
    if existing and current_user and existing.user_id != current_user.id and not current_user.is_admin:
        return error_response("Transaction not found.", 404)
    try:
        txn, outcome = settle(reference)
    except PaymentError as exc:
        return error_response(str(exc), exc.status)

    if outcome == "not_found":
        return error_response("Transaction not found.", 404)
    plan = txn.plan
    info = {"reference": reference, "status": txn.status, "plan_name": plan.name if plan else None, "units_added": plan.units if plan else 0}
    if outcome in ("success", "already"):
        sub = Subscription.query.filter_by(user_id=txn.user_id).first()
        info["total_units"] = sub.total_units if sub else 0
        msg = "Payment successful! Your subscription has been updated." if outcome == "success" else "This payment was already confirmed and credited."
        return success_response(msg, data=info)
    if outcome == "pending":
        return error_response("Your payment is still being processed. We'll credit it automatically once confirmed.", 202, data=info)
    return error_response("Payment was not completed. You have not been charged for this attempt.", 402, data=info)


# ------------------------------------------------------------------ webhook
@pay_bp.post("/payment/webhook/paystack")
def paystack_webhook():
    """Server-to-server confirmation: credits the customer even if they closed the browser."""
    secret = current_app.config.get("PAYSTACK_SK") or ""
    expected = hmac.new(secret.encode(), request.get_data(), hashlib.sha512).hexdigest()
    if not secret or not hmac.compare_digest(expected, request.headers.get("x-paystack-signature", "")):
        return error_response("Invalid signature.", 401)
    event = request.get_json(force=True, silent=True) or {}
    reference = (event.get("data") or {}).get("reference")
    if event.get("event") == "charge.success" and reference:
        try:
            settle(reference)
        except PaymentError:
            return error_response("Temporary verification failure.", 503)  # Paystack will retry
        except Exception:  # noqa: BLE001
            log.exception("Webhook settlement failed for %s", reference)
            db.session.rollback()
            return error_response("Settlement failed.", 500)  # retried by Paystack
    return success_response("ok")
