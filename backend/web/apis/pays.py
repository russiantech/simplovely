# from os import getenv
# from flask_jwt_extended import current_user, jwt_required
# import traceback, requests, secrets
# from flask import current_app, request, url_for
# from web.apis.models.plans import Subscription
# from web.apis.models.plans import Plan
# from web.apis.utils.serializers import error_response, success_response
# from web.apis.models.transactions import Transaction
# from requests.exceptions import ConnectionError, Timeout, RequestException
# from sqlalchemy.exc import IntegrityError
# # from jsonschema import validate, ValidationError
# # from web.apis.schemas.transactions import pay_schema
# from web.extensions import db, csrf, limiter
# from web.apis.models.users import User
# # from web.apis.models.orders import Order
# from web.apis.utils.helpers import generate_ref
# # from web.apis.transactions import save_transaction, transact_bp
# from web.apis import api_bp as transact_bp

# # PAYSTACK_SK = getenv('PAYSTACK_SK')
# # print('PAYSTACK_SK', PAYSTACK_SK)

# @transact_bp.route('/payment/<int:plan_id>/paystack', methods=['POST'])
# @csrf.exempt
# @limiter.exempt
# @jwt_required(optional=True)
# def initiate_paystack(plan_id):
#     try:
#         data = request.get_json() if request.content_type == 'application/json' else request.form.to_dict()
        
#         print("Received payment initiation request with data:", data)
        
#         if not data and not current_user:
#             return error_response(f"No data received to process transactions.")

#         # Validate input data
#         # validate(instance=data, schema=pay_schema)

#         client_callback_url = request.headers.get('Client-Callback-Url')

#         plan_id = plan_id or data['plan_id']
#         # plan = Plan.get_plan(plan_id)
#         plan = Plan.query.get(plan_id)
#         if not plan:
#             return error_response(f"Plan <{plan_id}> not found!")

#         email = data.get('email') or current_user.email if current_user else None
#         if not email:
#             return error_response(f"A valid email address is required.")

#         headers = {
#             "accept": "application/json",
#             "Authorization": f"Bearer {current_app.config['PAYSTACK_SK']}",
#             # "Authorization": f"Bearer {PAYSTACK_SK}",
#             "Content-Type": "application/json"
#         }

#         payment_url = "https://api.paystack.co/transaction/initialize"
#         reference = generate_ref(prefix="LND", num_digits=4, letters="???")

#         payload = {
#             "email": email,
#             "amount": plan.amount * 100,  # Convert to kobo
#             "currency": "NGN",
#             "callback_url": client_callback_url,
#             "reference": reference,
#             "metadata": {
#                 "plan_id": plan.id,
#                 "reference": reference,
#                 "cancel_action": str(client_callback_url + "?reference=" + reference),
#             }
#         }

#         # print(payload)

#         payment_response = requests.post(payment_url, json=payload, headers=headers)
#         payment_data = payment_response.json()
#         # print(payment_data)
#         payment_link = payment_data.get("data", {}).get("authorization_url")

#         if not payment_link:
#             error = payment_data.get('message', '')
#             return error_response(f"Failed to retrieve payment link, due to {error} .")

#         # Create a pending transaction
#         user = User.get_user(email)
#         if not user:
#             # return error_response("Not user")
#             user = User(username=email.split('@')[0], email=email, is_guest=True)
#             user.set_password(generate_ref())
#             db.session.add(user)
#             db.session.commit()

#         transaction = Transaction( 
#             plan_id=plan.id,
#             # service_id=plan.id,
#             user_id=user.id,
#             amount=plan.amount,
#             currency='NGN',
#             payment_method='paystack',
#             reference=reference,
#             status='pending'
#         )
#         db.session.add(transaction)
#         db.session.commit()
        
#         return success_response("Continue to pay securely..", data={"redirect": payment_link})

#     except ConnectionError:
#         return error_response("No internet connection. Please check your network and try again.")

#     except Timeout:
#         return error_response("The request timed out. Please try again later.")

#     except RequestException as e:
#         # print(f"RequestException: {e}")
#         return error_response(f"error: {str(e)}")

#     except IntegrityError as e:
#         db.session.rollback()  # Rollback the session on error
#         traceback.print_exc()
#         return error_response(f"Payment integrity glitch {e}", status_code=500)
    
#     except Exception as e:
#         db.session.rollback()
#         traceback.print_exc()
#         return error_response(f"error: {str(e)}", status_code=500)

# @transact_bp.route('/payment/callback/paystack', methods=['GET'])
# @jwt_required(optional=True)
# @limiter.exempt
# def callback_paystack():
#     try:
#         reference = request.args.get('reference') or request.args.get('trxref')
#         transaction = Transaction.get_transaction(reference)

#         if not transaction:
#             return error_response('Transaction not found', status_code=404)

#         if transaction.status == "success" or transaction.status == "successful":
#             return success_response('Transaction verified and subscription activated already.')
        
#         headers = {
#             "accept": "application/json",
#             "Authorization": f"Bearer {current_app.config['PAYSTACK_SK']}",
#             # "Authorization": f"Bearer {PAYSTACK_SK}",
#             "Content-Type": "application/json"
#         }

#         verify_endpoint = f"https://api.paystack.co/transaction/verify/{reference}"
#         response = requests.get(verify_endpoint, headers=headers)

#         if response.status_code == 200:
#             """
#             response_data = response.json().get('data', {})
#             if (
#                 response_data.get('status') == "success"
#                 and response_data.get('amount') >= transaction.amount * 100  # Amount in kobo
#                 and response_data.get('currency') == transaction.currency
#             ):
#                 transaction.status = response_data['status']

#                 # Create subscription upon successful payment
#                 subscription = Subscription(
#                     user_id=transaction.user_id,
#                     plan_id=response_data['metadata']['plan_id'],
#                     total_units=Plan.query.get(response_data['metadata']['plan_id']).units,
#                     status='active'
#                 )
                
#                 db.session.add(subscription)
#                 db.session.commit()

#                 return success_response('Transaction verified and subscription activated.', data=response_data)
#                 """
#             response_data = response.json().get('data', {})
#             if (
#                 response_data.get('status') == "success"
#                 and response_data.get('amount') >= transaction.amount * 100  # Amount in kobo
#                 and response_data.get('currency') == transaction.currency
#             ):
#                 transaction.status = response_data['status']

#                 # Check for existing active subscription
#                 existing_subscription = Subscription.query.filter_by(user_id=transaction.user_id).first()
#                 units = Plan.query.get(response_data['metadata']['plan_id']).units
                
#                 if existing_subscription:
#                     # Update existing subscription plan and add new units
#                     existing_subscription.plan_id = response_data['metadata']['plan_id']
#                     new_units = units
                    
#                     # Increment total units
#                     existing_subscription.total_units += new_units
                    
#                     db.session.commit()

#                     return success_response('Transaction verified and existing subscription updated with new plan and units.', data=response_data)
#                 else:
#                     # Create new subscription upon successful payment
#                     subscription = Subscription(
#                         user_id=transaction.user_id,
#                         plan_id=response_data['metadata']['plan_id'],
#                         total_units=units,
#                         status='active'
#                     )
                    
#                     db.session.add(subscription)
#                     db.session.commit()

#                     return success_response('Transaction verified and subscription activated.', data=response_data)

#             else:
#                 transaction.status = response_data['status']
#                 db.session.commit()
#                 return error_response(f'Transaction verification failed.')
#         else:
#             return error_response('Failed to verify transaction')

#     except Exception as e:
#         db.session.rollback()
#         return error_response(str(e))



# v2


# v3

# Fix pays.py - return reference and access_code in the response
# Also fix the callback to use the upsert pattern (not just update existing)

from flask_jwt_extended import current_user, jwt_required
import traceback, requests
from flask import current_app, request
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
    """Initialize a Paystack transaction and return access details for inline/popup checkout."""
    try:
        data = request.get_json() if request.content_type == 'application/json' else request.form.to_dict()
        print("Received payment initiation request with data:", data)
        
        if not data and not current_user:
            return error_response("No data received to process transactions.")

        client_callback_url = request.headers.get('Client-Callback-Url') or request.headers.get('Referer') or ''

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
        reference = generate_ref(prefix="LND", num_digits=4, letters="???")

        payload = {
            "email": email,
            "amount": int(plan.amount * 100),  # Convert to kobo
            "currency": "NGN",
            "callback_url": client_callback_url,
            "reference": reference,
            "metadata": {
                "plan_id": plan.id,
                "reference": reference,
                "cancel_action": str(client_callback_url + "?reference=" + reference),
            }
        }

        payment_response = requests.post(payment_url, json=payload, headers=headers)
        payment_data = payment_response.json()
        print("Paystack init response:", payment_data)

        if not payment_data.get("status"):
            error = payment_data.get('message', 'Unknown error from Paystack')
            return error_response(f"Paystack initialization failed: {error}")

        paystack_data = payment_data.get("data", {})
        authorization_url = paystack_data.get("authorization_url")
        access_code = paystack_data.get("access_code")

        if not authorization_url:
            return error_response("Failed to retrieve payment authorization URL from Paystack.")

        # Create a pending transaction
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
        
        # Return everything needed for both popup (access_code) and redirect (authorization_url) flows
        return success_response("Payment initialized successfully.", data={
            "redirect": authorization_url,
            "access_code": access_code,
            "reference": reference,
            "amount": plan.amount,
            "email": email
        })

    except ConnectionError:
        return error_response("No internet connection. Please check your network and try again.")
    except Timeout:
        return error_response("The request timed out. Please try again later.")
    except RequestException as e:
        return error_response(f"Network error: {str(e)}")
    except IntegrityError as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(f"Payment integrity error: {e}", status_code=500)
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(f"Error: {str(e)}", status_code=500)


# @transact_bp.route('/payment/callback/paystack', methods=['GET'])
# @jwt_required(optional=True)
# @limiter.exempt
# def callback_paystack():
#     """Verify a Paystack transaction and activate/up-sert the user's subscription."""
#     try:
#         reference = request.args.get('reference') or request.args.get('trxref')
#         if not reference:
#             return error_response('Transaction reference is required.', status_code=400)

#         transaction = Transaction.get_transaction(reference)
#         if not transaction:
#             return error_response('Transaction not found', status_code=404)

#         if transaction.status in ("success", "successful"):
#             return success_response('Transaction already verified and subscription activated.')
        
#         headers = {
#             "accept": "application/json",
#             "Authorization": f"Bearer {current_app.config['PAYSTACK_SK']}",
#             "Content-Type": "application/json"
#         }

#         verify_endpoint = f"https://api.paystack.co/transaction/verify/{reference}"
#         response = requests.get(verify_endpoint, headers=headers)

#         if response.status_code != 200:
#             return error_response('Failed to verify transaction with Paystack.')

#         response_data = response.json().get('data', {})
        
#         if (
#             response_data.get('status') == "success"
#             and response_data.get('amount') >= transaction.amount * 100
#             and response_data.get('currency') == transaction.currency
#         ):
#             transaction.status = response_data['status']
#             db.session.commit()

#             plan_id = response_data.get('metadata', {}).get('plan_id') or transaction.plan_id
#             user_id = transaction.user_id
#             plan = Plan.query.get(plan_id)
#             units = plan.units if plan else 0

#             # ─── UPSERT SUBSCRIPTION (same pattern as admin assignment) ─────
#             existing = Subscription.query.filter_by(
#                 user_id=user_id,
#                 plan_id=plan_id
#             ).first()

#             if existing:
#                 # Reactivate soft-deleted, add volume
#                 if getattr(existing, 'is_deleted', False):
#                     existing.is_deleted = False
#                 existing.total_units += units
#                 existing.status = 'active'
#                 db.session.commit()
#                 return success_response(
#                     'Payment successful! Your subscription has been topped up.',
#                     data={
#                         'reference': reference,
#                         'plan_name': plan.name if plan else None,
#                         'units_added': units,
#                         'total_units': existing.total_units
#                     }
#                 )
#             else:
#                 # Create new subscription
#                 subscription = Subscription(
#                     user_id=user_id,
#                     plan_id=plan_id,
#                     total_units=units,
#                     status='active'
#                 )
#                 db.session.add(subscription)
#                 db.session.commit()
#                 return success_response(
#                     'Payment successful! Your subscription is now active.',
#                     data={
#                         'reference': reference,
#                         'plan_name': plan.name if plan else None,
#                         'units': units
#                     }
#                 )
#         else:
#             transaction.status = response_data.get('status', 'failed')
#             db.session.commit()
#             return error_response(
#                 f"Transaction verification failed. Status: {response_data.get('status', 'unknown')}",
#                 data={'reference': reference, 'status': transaction.status}
#             )

#     except Exception as e:
#         db.session.rollback()
#         traceback.print_exc()
#         return error_response(str(e))


# v2
@transact_bp.route('/payment/callback/paystack', methods=['GET'])
@jwt_required(optional=True)
@limiter.exempt
def callback_paystack():
    """Verify a Paystack transaction and upsert the user's subscription."""
    try:
        reference = request.args.get('reference') or request.args.get('trxref')
        if not reference:
            return error_response('Transaction reference is required.', status_code=400)

        transaction = Transaction.get_transaction(reference)
        if not transaction:
            return error_response('Transaction not found', status_code=404)

        if transaction.status in ("success", "successful"):
            return success_response('Transaction already verified and subscription activated.')
        
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {current_app.config['PAYSTACK_SK']}",
            "Content-Type": "application/json"
        }

        verify_endpoint = f"https://api.paystack.co/transaction/verify/{reference}"
        response = requests.get(verify_endpoint, headers=headers)

        if response.status_code != 200:
            return error_response('Failed to verify transaction with Paystack.')

        response_data = response.json().get('data', {})
        
        if (
            response_data.get('status') == "success"
            and response_data.get('amount') >= transaction.amount * 100
            and response_data.get('currency') == transaction.currency
        ):
            transaction.status = response_data['status']
            db.session.commit()

            plan_id = response_data.get('metadata', {}).get('plan_id') or transaction.plan_id
            user_id = transaction.user_id
            plan = Plan.query.get(plan_id)
            units = plan.units if plan else 0

            # ─── FIX: look up by user_id ONLY because of UNIQUE(user_id) ─────
            existing = Subscription.query.filter_by(user_id=user_id).first()

            if existing:
                # Update existing subscription (user can only have one row)
                existing.plan_id = plan_id
                existing.total_units += units
                existing.status = 'active'
                if hasattr(existing, 'is_deleted'):
                    existing.is_deleted = False
                db.session.commit()
                return success_response(
                    'Payment successful! Your subscription has been updated.',
                    data={
                        'reference': reference,
                        'plan_name': plan.name if plan else None,
                        'units_added': units,
                        'total_units': existing.total_units
                    }
                )
            else:
                # Create first subscription for this user
                subscription = Subscription(
                    user_id=user_id,
                    plan_id=plan_id,
                    total_units=units,
                    status='active'
                )
                db.session.add(subscription)
                db.session.commit()
                return success_response(
                    'Payment successful! Your subscription is now active.',
                    data={
                        'reference': reference,
                        'plan_name': plan.name if plan else None,
                        'units': units
                    }
                )
        else:
            transaction.status = response_data.get('status', 'failed')
            db.session.commit()
            # return error_response(
            return success_response(
                f"Transaction verification failed. Status: {response_data.get('status', 'unknown')}",
                data={'reference': reference, 'status': transaction.status}
            )

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(str(e))

