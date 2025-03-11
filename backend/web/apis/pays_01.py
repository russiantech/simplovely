from os import getenv
from flask_jwt_extended import current_user, jwt_required
import traceback, requests, secrets
from flask import current_app, request, url_for
from web.apis.models.plans import Subscription
from web.apis.models.plans import Plan
from web.apis.utils.serializers import error_response, success_response
from web.apis.models.transactions import Transaction
from requests.exceptions import ConnectionError, Timeout, RequestException
# from jsonschema import validate, ValidationError
# from web.apis.schemas.transactions import pay_schema
from web.extensions import db, csrf, limiter
from web.apis.models.users import User
# from web.apis.models.orders import Order
from web.apis.utils.helpers import generate_ref
# from web.apis.transactions import save_transaction, transact_bp
from web.apis import api_bp as transact_bp

PAYSTACK_SK = getenv('PAYSTACK_TEST_SK')

@transact_bp.route('/payment/<int:plan_id>/paystack', methods=['POST'])
@csrf.exempt
@limiter.exempt
@jwt_required(optional=True)
def initiate_paystack(plan_id):
    try:
        data = request.get_json() if request.content_type == 'application/json' else request.form.to_dict()
        if not data and not current_user:
            return error_response(f"No data received to process transactions.")

        # Validate input data
        # validate(instance=data, schema=pay_schema)
        # Capture the full URL of the client page making the request
        # referer_url = request.headers.get('Referer') or request.referrer or url_for('apis.callback_paystack', _external=True)
        # full_url = f"{request.scheme}://{request.host}{request.full_path}"
        # return error_response(f"{full_url, request.full_path, referer_url}")

        client_callback_url = request.headers.get('Client-Callback-Url')
        print(client_callback_url)
        
        # return error_response(f"{request.headers}")
        
        plan_id = plan_id or data['plan_id']
        plan = Plan.get_plan(plan_id)
        if not plan:
            return error_response(f"Plan <{plan_id}> not found!")

        email = data.get('email') or current_user.email if current_user else None
        if not email:
            return error_response(f"A valid email address is required.")

        headers = {
            "accept": "application/json",
            # "Authorization": f"Bearer {current_app.config['PAYSTACK_SK']}",
            "Authorization": f"Bearer {PAYSTACK_SK}",
            "Content-Type": "application/json"
        }

        payment_url = "https://api.paystack.co/transaction/initialize"
        reference = generate_ref(prefix="LND", num_digits=4, letters="???")
        # callback_url = request.referrer or url_for('apis.callback_paystack', _external=True)
        # # callback_url = url_for('apis.callback_paystack', _external=True)
        # print(callback_url)
        # 
        # Prepare the necessary query parameters
        from urllib.parse import urlencode
        query_params = {
            'reference': reference,
            'plan_id': plan.id,
            'user_email': email,
            'status': 'cancelled'
        }

        payload = {
            "email": email,
            "amount": plan.amount * 100,  # Convert to kobo
            "currency": "NGN",
            "callback_url": str(client_callback_url + "?status=success"),
            "reference": reference,
            "metadata": {
                "plan_id": plan.id,
                "reference": reference,
                "cancel_action": f"{client_callback_url}?{urlencode(query_params)}",
                # "cancel_action": client_callback_url,
                # "cancel_action": "https://your-cancel-url.com",
                
            }
        }

        payment_response = requests.post(payment_url, json=payload, headers=headers)
        payment_data = payment_response.json()
        payment_link = payment_data.get("data", {}).get("authorization_url")

        if not payment_link:
            return error_response("Failed to retrieve payment link.")

        # Create a pending transaction
        user = User.get_user(email) or User(username=email.split('@')[0], email=email, is_guest=True)
        db.session.add(user)
        db.session.commit()

        transaction = Transaction(
            user_id=user.id,
            amount=plan.amount,
            currency='NGN',
            payment_method='paystack',
            reference=reference,
            status='pending'
        )
        db.session.add(transaction)
        db.session.commit()
        
        return success_response("Continue to pay securely..", data={"redirect": payment_link})


    except ConnectionError:
        return error_response("No internet connection. Please check your network and try again.")

    except Timeout:
        return error_response("The request timed out. Please try again later.")

    except RequestException as e:
        return error_response(f"error: {str(e)}")

    # return error_response("Invalid request method", status_code=405)

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(f"error: {str(e)}", status_code=500)

@transact_bp.route('/payment/callback/paystack', methods=['GET'])
@jwt_required(optional=True)
def callback_paystack():
    try:
        reference = request.args.get('reference') or request.args.get('trxref')
        transaction = Transaction.get_tranasction(reference)

        if not transaction:
            return error_response('Transaction not found', status_code=404)

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {PAYSTACK_SK}",
            "Content-Type": "application/json"
        }

        verify_endpoint = f"https://api.paystack.co/transaction/verify/{reference}"
        response = requests.get(verify_endpoint, headers=headers)

        if response.status_code == 200:
            response_data = response.json().get('data', {})
            if (
                response_data.get('status') == "success"
                and response_data.get('amount') >= transaction.amount * 100  # Amount in kobo
                and response_data.get('currency') == transaction.currency
            ):
                transaction.status = response_data['status']

                # Create subscription upon successful payment
                subscription = Subscription(
                    user_id=transaction.user_id,
                    plan_id=response_data['metadata']['plan_id'],
                    total_units=Plan.query.get(response_data['metadata']['plan_id']).units,
                    status='active'
                )
                
                db.session.add(subscription)
                db.session.commit()

                return success_response('Transaction verified and subscription activated.', data=response_data)
            else:
                transaction.status = response_data['status']
                db.session.commit()
                return error_response(f'Transaction verification failed: {response_data}')
        else:
            return error_response('Failed to verify transaction')

    except Exception as e:
        db.session.rollback()
        return error_response(str(e))