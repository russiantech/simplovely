from os import getenv
from flask_jwt_extended import current_user, jwt_required
import traceback, requests, secrets
from flask import current_app, request, url_for
from web.apis.models.plans import Subscription
from web.apis.models.plans import Plan
from web.apis.utils.serializers import error_response, success_response
from web.apis.models.transactions import Transaction
from requests.exceptions import ConnectionError, Timeout, RequestException
from sqlalchemy.exc import IntegrityError
from web.extensions import db, csrf, limiter
from web.apis.models.users import User
from web.apis.utils.helpers import generate_ref
from web.apis import api_bp as transact_bp


@transact_bp.route('/payment/<int:plan_id>/paystack', methods=['POST'])
@csrf.exempt
@limiter.exempt
@jwt_required(optional=True)
def initiate_paystack(plan_id):
    try:
        data = request.get_json() if request.content_type == 'application/json' else request.form.to_dict()

        print("Received payment initiation request with data:", data)

        if not data and not current_user:
            return error_response("No data received to process transactions.")

        client_callback_url = request.headers.get('Client-Callback-Url')

        plan_id = plan_id or data.get('plan_id')
        plan = Plan.query.get(plan_id)
        if not plan:
            return error_response(f"Plan <{plan_id}> not found!")

        email = data.get('email') or (current_user.email if current_user else None)
        if not email:
            return error_response("A valid email address is required.")

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {current_app.config['PAYSTACK_SK']}",
            "Content-Type": "application/json"
        }

        payment_url = "https://api.paystack.co/transaction/initialize"
        reference   = generate_ref(prefix="LND", num_digits=4, letters="???")

        payload = {
            "email":    email,
            "amount":   plan.amount * 100,   # Convert to kobo
            "currency": "NGN",
            "callback_url": client_callback_url,
            "reference": reference,
            "metadata": {
                "plan_id":       plan.id,
                "reference":     reference,
                "cancel_action": str(client_callback_url + "?reference=" + reference) if client_callback_url else None,
            }
        }

        payment_response = requests.post(payment_url, json=payload, headers=headers)
        payment_data     = payment_response.json()
        payment_link     = payment_data.get("data", {}).get("authorization_url")

        if not payment_link:
            error = payment_data.get('message', '')
            return error_response(f"Failed to retrieve payment link: {error}.")

        # Create a pending transaction — or find the guest user
        user = User.get_user(email)
        if not user:
            user = User(username=email.split('@')[0], email=email, is_guest=True)
            user.set_password(generate_ref())
            db.session.add(user)
            db.session.commit()

        transaction = Transaction(
            plan_id=plan.id,
            user_id=user.id,
            amount=plan.amount,
            currency='NGN',
            payment_method='paystack',
            reference=reference,
            status='pending'
        )
        db.session.add(transaction)
        db.session.commit()

        # ── Return BOTH the redirect URL and the reference ──────────────────
        # The frontend uses `reference` to verify payment via the callback
        # endpoint after the Paystack popup closes, without needing a redirect.
        return success_response(
            "Continue to pay securely.",
            data={"redirect": payment_link, "reference": reference}
        )

    except ConnectionError:
        return error_response("No internet connection. Please check your network and try again.")

    except Timeout:
        return error_response("The request timed out. Please try again later.")

    except RequestException as e:
        return error_response(f"Request error: {str(e)}")

    except IntegrityError as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(f"Payment integrity error: {e}", status_code=500)

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(f"Error: {str(e)}", status_code=500)


@transact_bp.route('/payment/callback/paystack', methods=['GET'])
@jwt_required(optional=True)
@limiter.exempt
def callback_paystack():
    try:
        reference   = request.args.get('reference') or request.args.get('trxref')
        transaction = Transaction.get_transaction(reference)

        if not transaction:
            return error_response('Transaction not found.', status_code=404)

        # Idempotency guard — already processed
        if transaction.status in ("success", "successful"):
            return success_response('Transaction already verified and subscription is active.')

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {current_app.config['PAYSTACK_SK']}",
            "Content-Type": "application/json"
        }

        verify_endpoint = f"https://api.paystack.co/transaction/verify/{reference}"
        response        = requests.get(verify_endpoint, headers=headers)

        if response.status_code != 200:
            return error_response('Failed to verify transaction with Paystack.')

        response_data = response.json().get('data', {})
        ps_status     = response_data.get('status')
        ps_amount     = response_data.get('amount', 0)
        ps_currency   = response_data.get('currency', '')

        # Verify amount and currency match our record
        if (
            ps_status == "success"
            and ps_amount >= transaction.amount * 100   # Paystack returns kobo
            and ps_currency == transaction.currency
        ):
            transaction.status = ps_status

            # Check for existing subscription
            existing = Subscription.query.filter_by(user_id=transaction.user_id).first()
            plan_id  = response_data.get('metadata', {}).get('plan_id') or transaction.plan_id
            plan     = Plan.query.get(plan_id)
            units    = plan.units if plan else 0

            if existing:
                existing.plan_id      = plan_id
                existing.total_units += units
                db.session.commit()
                return success_response(
                    'Payment verified. Subscription updated with new units.',
                    data=response_data
                )
            else:
                subscription = Subscription(
                    user_id=transaction.user_id,
                    plan_id=plan_id,
                    total_units=units,
                    status='active'
                )
                db.session.add(subscription)
                db.session.commit()
                return success_response(
                    'Payment verified. Subscription activated.',
                    data=response_data
                )
        else:
            # Payment did NOT succeed — update status and commit
            transaction.status = ps_status or 'failed'
            db.session.commit()
            return error_response(
                f'Transaction verification failed. Status: {ps_status or "unknown"}.'
            )

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(str(e))

