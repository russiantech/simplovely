
from datetime import timedelta
import secrets, requests, sqlalchemy as sa, traceback
# from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from requests.exceptions import ConnectionError, Timeout, RequestException
from urllib.parse import urlencode
# from flask_jwt_extended import jwt_optional, get_jwt_claims // deprecated
from flask_jwt_extended import get_jwt, jwt_required, get_jwt_identity, current_user  # Instead of get_jwt_claims
from jsonschema import validate, ValidationError
from flask import (
    abort, current_app, make_response, redirect, session, render_template, 
    url_for, request
)

from web.apis.utils.get_or_create import get_or_create
from web.apis.utils.decorators import access_required
from web.apis.utils.users import handle_reset_password, handle_verify_email
from web.extensions import db, csrf, fake, limiter
from web.apis.utils.helpers import user_ip
from web.apis.models.roles import Role
from web.apis.models.users import User
from web.apis.utils.serializers import (
    PageSerializer, error_response, success_response
)

from web.apis.schemas.user import (
    signin_schema, signup_schema, request_schema, reset_password_email_schema, 
    validTokenSchema, change_password_schema
)

from web.apis.utils import email as emailer
from web.apis.utils.oauth_providers import oauth2providers
from web.extensions import redis as redis_clients
from web.apis import api_bp as user_bp

# 

from flask import Flask, jsonify
from os import getenv
from dotenv import load_dotenv
import redis

# Load environment variables from .env file
load_dotenv()

# Requests form route
@user_bp.route('/users/message', methods=['POST'])
@csrf.exempt
def send_message():
    try:
        
        data = request.get_json()
        
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        details = data.get('details')
        concern = data.get('concern')
        budget = int(data.get('budget', 0))

        # Validate email and request content
        if not email or not phone or not details:
            return error_response('Email, Phone & Details  Are Required')

        # Validate the data against the schema
        try:
            validate(instance=data, schema=request_schema)
        except ValidationError as e:
            return error_response(e.message)
        
        # Prepare email content for support
        subject = "[Incoming Requests ] from {}".format(email)
        text_body = f"From: {email} (Phone: {phone})\n\nDetails:\n{details}"
        
        context = {
            "name":name,
            "email":email, 
            "phone":phone, 
            "budget":budget, 
            "concern":concern,
            "details":details,
        }
        
        html_body = render_template('email/requests.html', **context)

        # Send email to support team
        emailer.send_email(
            subject=subject,
            # sender=email, // can be omitted if 'DEFAULT_MAIL_SENDER' is configured
            recipients=[current_app.config['MAIL_USERNAME'], "chrisjsmez@gmail.com"],  # The contact email for receiving messages
            text_body=text_body,
            html_body=html_body
        )

        return success_response(f'Your Request has been submitted successfully. Thank you!')
    
    except ConnectionError:
            traceback.print_exc()
            return error_response("No internet connection. pls check your network and try again.")

    except Timeout:
        traceback.format_exc()
        return error_response("The request timed out. Please try again later.")

    except RequestException as e:
        traceback.print_exc()
        return error_response(f"error: {str(e)}")
    
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))

@user_bp.route("/users/signup", methods=['POST'])
@csrf.exempt
# @limiter.exempt
@jwt_required(optional=True)
def signup():
    user_identity = get_jwt_identity()
    if user_identity:
        return error_response("You're already signed in currently. Logout first to create new accounts.")

    if request.content_type != 'application/json':
        return error_response("Content-Type must be application/json")

    data = request.get_json()

    try:
        validate(instance=data, schema=signup_schema)
    except ValidationError as e:
        return error_response(e.message)

    if not all(data.get(key) for key in ('username', 'phone', 'email', 'password')):
        return error_response("Must provide ('username', 'phone', 'email', 'password')")

    # Check for existing user details
    if db.session.scalar(sa.select(User).where(User.username == data['username'])):
        return error_response("Please use a different username.")

    if db.session.scalar(sa.select(User).where(User.email == data['email'])):
        return error_response("Please use a different email address.")

    if db.session.scalar(sa.select(User).where(User.phone == data['phone'])):
        return error_response("Please use a different phone number.")

    role = get_or_create(db.session, Role, {'name': "user"}, name="user")[0]

    try:
        user = User(
            username=data['username'],
            email=data['email'],
            phone=data['phone'],
            ip=user_ip()
        )
        user.roles.append(role)
        user.set_password(data['password'])
        db.session.add(user)
        db.session.flush()  # Flush to check for integrity errors
        db.session.commit()

        emailer.verify_email(user)

        data = user.get_summary()
        data.update({"redirect": './signin'})
        # data.update({"redirect": url_for('apis.signin')})

        return success_response("Sign up successful.", data=data)

    except exc.IntegrityError as e:
        db.session.rollback()
        return error_response("This username or email is already taken.")
    except Exception as e:
        db.session.rollback()
        print(traceback.print_exc())
        return error_response(str(e))

@user_bp.route("/users/signin", methods=['POST'])
@csrf.exempt
# @limiter.exempt
@jwt_required(optional=True)
def signin():
    try:
        # Check if the request content type is application/json
        if request.content_type != 'application/json' or not request.json:
            return error_response("Content-Type must be application/json & JSON payload expected.")
        
        # return error_response(f"pls check -> {request.json, request.headers}")
        # # Check if the user is already authenticated (using JWT token)
        # user_identity = get_jwt_identity()  # Attempt to get the current user's identity from the JWT token
        # if user_identity:
        #     claims = get_jwt()  # Get all claims
        #     return success_response(
        #         f"signed in already as {claims.get('username')}",
        #         data={"redirect": url_for('showcase.index')}
        #     )
        if current_user:
            return success_response(
                f"signed in already as {current_user.username}", data={"redirect": '/account'}
            )

        # Parse JSON data from the request
        data = request.get_json()

        # Ensure that no fields are empty
        if not all(data.get(key) for key in ('username', 'password')):
            return error_response("All fields are required and must not be empty.")

        # Validate the data against the schema
        try:
            validate(instance=data, schema=signin_schema)
        except ValidationError as e:
            return error_response(e.message)

        # Authentication logic
        user = User.query.filter(
            sa.or_(
                User.email == data['username'],
                User.phone == data['username'],
                User.username == data['username']
            )
        ).first()

        # If user exists and password matches
        if user and user.check_password(data['password']):
            access_token = user.make_token(token_type='access')
            refresh_token = user.make_token(token_type='refresh')

            # Create response object
            response = make_response(
                success_response(
                    "Sign in successful",
                    data={
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "redirect": '/account' # or url_for('showcase.index')
                    }
            ))

            # Set cookies for web clients
            response.set_cookie('access_token', access_token, httponly=True, secure=True, samesite='Strict')
            response.set_cookie('access_token_cookie', access_token, httponly=True, secure=True, samesite='Strict')
            response.set_cookie('refresh_token_cookie', refresh_token, httponly=True, secure=True, samesite='Strict')
            response.set_cookie('refresh_token', refresh_token, httponly=True, secure=True, samesite='Strict')

            return response

        # If authentication failed
        return error_response("Invalid username or password.", status_code=401)

    except Exception as e:
        # Log the exception for debugging
        traceback.print_exc()
        return error_response(f"Error signing in: {e}", status_code=400)

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask import make_response

@user_bp.route("/users/refresh-token", methods=['POST', 'GET'])
# @limiter.exempt
@jwt_required(refresh=True, optional=True)  # Ensure the user is sending a valid refresh token
def refresh_token():
    try:
        # Get the identity of the current user (from the refresh token)
        # current_user = get_jwt_identity()
        user = current_user

        # Ensure the current user is valid
        if user:
            # Create a new access token
            new_access_token = user.make_token(token_type='access')

            # Create response object
            response = make_response(success_response(
                "Token refreshed successfully",
                data={
                    "access_token": new_access_token,
                    "redirect": "url_for('showcase.index')"
                }
            ))

            # Set cookies for web clients
            response.set_cookie('access_token_cookie', new_access_token, httponly=True, secure=True, samesite='Strict')

            return response

        # If user not found or authentication failed
        return error_response("User not found.")

    except Exception as e:
        traceback.print_exc()
        return error_response(f"Error refreshing token: {str(e)}")

@user_bp.route("/users/signout", methods=['GET', 'POST'])
@jwt_required()
# @limiter.exempt
def signout():
    try:
        # Get the JWT token from the current request
        token = get_jwt()
        # Respond to the client (success response with a redirect or message)
        data = {
            "access_token": None,
            "refresh_token": None,
            "redirect": "./signin"
            }
        
        # Create a response object
        response = make_response(
            success_response("Sign out successful.", data=data)
        )
        # Remove the cookies
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        
        # Add the token to a blacklist (using the token's jti)
        from web.extensions import redis as r
        r.sadd("blacklist", token['jti'])

        # Mark the user as offline in the database (optional)
        current_user.online = False
        db.session.commit()

        return response

    except Exception as e:
        return error_response(f'Error signing out: {str(e)}')

@user_bp.route('/users/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Allow authenticated users to change their password."""
    try:
        if not get_jwt_identity():
            return error_response("You are not authenticated. sign-in first", data={"redirect": url_for('apis.signin')})

        data = request.json
        
        try:
            validate(instance=data, schema=change_password_schema)
        except ValidationError as e:
            return error_response(f"Validation error: {e.message}")
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if not all([current_password, new_password, confirm_password]):
            return error_response("All fields are required.", status_code=400)

        if new_password != confirm_password:
            return error_response("New password and confirmation do not match.", status_code=400)

        if not current_user.check_password(current_password):
            return error_response("Current password is incorrect.", status_code=403)

        current_user.set_password(new_password)
        db.session.commit()

        return success_response("Password changed successfully.")

    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", status_code=500)

from flask_expects_json import expects_json
@user_bp.route("users/reset-password", methods=['POST'])
@jwt_required(optional=True)
@expects_json()
def reset_password():
    try:
        # Check if the user is already authenticated (using JWT token)
        user_identity = get_jwt_identity()  # Attempt to get the current user's identity from the JWT token
        if user_identity:
            return error_response("You are already authenticated. No need to try reset of password.", data={"redirect": url_for('showcase.index')})

        # Parse and validate the JSON request payload
        data = request.json
        if not data:
            return error_response('Invalid request: No JSON data provided.', status_code=400)

        try:
            validate(instance=data, schema=reset_password_email_schema)
        except ValidationError as ve:
            return error_response(f'Validation error: {ve.message}', status_code=400)

        # Extract email after validation
        email = data['email']

        # Handle the password reset logic
        user = User.query.filter_by(email=email).first()
        if user:
            """ 
            Here, 1. send reset email to users. 2. generate reset-token and link to reset passed in the request data. So that any client can utilize seamlessly.
            weather they prefer sending same link or customizing their email experience with different client(web, mobile, IOT, desktop etc)
            """
            # Generate a 5-character verification code using Faker
            verification_code = fake.lexify(text='?????').upper()  # Generates a 5-character random string
            session[email] = verification_code  # Store in session with email as key
            session['permanent'] = True  # Mark session as permanent
            # current_app.permanent_session_lifetime = current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
            current_app.permanent_session_lifetime = timedelta(hours=1)
            user.verification_code = verification_code # so it can get passed to template in email sender function
            
            emailer.reset_email(user)
            token = user.make_token(token_type="reset_password")
            data = {
                'token': token,
                "link": url_for('apis.process_token', token=token, email=user.email, _external=True)
                # 'redirect': url_for('showcase.index')
                }
            return success_response('Password reset email sent. You can also send reset token included in this response to user.', data=data)
        else:
            return error_response(f'No user found with the provided email <{email}>.', status_code=404)

    except Exception as e:
        traceback.print_exc()
        return error_response(f'An internal server error occurred. Please try again later.', status_code=500)

# # Unified route to handle all token-related actions (reset password, email verification, etc.)
@user_bp.route("/users/process-token/<token>", methods=['GET', 'POST'])
@jwt_required(optional=True)
def process_token(token: str = None):
    try:
        # Ensure the token is provided
        if not token:
            return error_response('Invalid request. Token is missing.')

        # Gather and validate incoming data against the JSON schema
        data = request.json if request.is_json else {}
        
        # Include the token from the URL in the data if not present
        if 'token' not in data:
            data['token'] = token

        # Validate the incoming data against the schema
        try:
            validate(instance=data, schema=validTokenSchema)
        except ValidationError as e:
            return error_response(f"Token validation error: {e.message}")

        # Validate the token
        valid_token = User.check_token(data['token'])
        if not valid_token:
            return error_response('Invalid or expired token.')

        # Determine the type of token
        token_type = valid_token["token_type"]

        # Handle token types
        email = valid_token.get('email')
        user = User.query.filter_by(email=email).first()
        if not user:
            return error_response(f'User not found with this email address: {email}')

        if token_type == 'reset_password':
            verification_code = data.get('verification_code')
            if not verification_code:
                return error_response('Verification code is required.', status_code=400)

            # Validate the verification code from the session using the email as the key
            stored_code = session.get(email)
            if stored_code != verification_code:
                return error_response('Invalid verification code.', status_code=403)

            # Optionally clear the verification code from the session after use
            session.pop(email, None)

            return handle_reset_password(user, data)

        elif token_type == 'verify_email':
            return handle_verify_email(user)

        # If the token type is unknown, return an error
        return error_response('Unexpected error with token type.')

    except Exception as e:
        traceback.print_exc()
        return error_response(f'An error occurred: {str(e)}')

# ==========OAUTH================
# endpoint to initialize OAuth

@user_bp.route('/users/authorize/<provider>')
@jwt_required(optional=True)
@limiter.exempt
def oauth2_authorize(provider):
    try:
        # Check if the user is already authenticated
        if get_jwt_identity() is not None:
            return success_response(f"Already signed in as {get_jwt_identity()['username']}")

        provider_data = oauth2providers.get(provider)
        if provider_data is None:
            return error_response("Provider not found", status_code=404)

        # Generate a random string for the state parameter
        oauth2_state = secrets.token_urlsafe(16)
        redis_clients.setex(f'oauth2_state:{oauth2_state}', 300, provider)  # Store state with a 5-minute expiration
        
        # Get the client callback URL from headers or set a default
        client_callback_url = request.headers.get('Client-Callback-Url') 
        redirect_uri = url_for('apis.oauth2_callback', provider=provider, _external=True)
        
        # Store the callback URL in Redis associated with the state
        redis_clients.setex(f'callback_url:{oauth2_state}', 300, client_callback_url)

        # Create a query string with all the OAuth2 parameters
        qs = urlencode({
            'client_id': provider_data['client_id'],
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(provider_data['scopes']),
            'state': oauth2_state,
            'provider': provider,
        })

        data = {"redirect": provider_data['authorize_url'] + '?' + qs}
        return success_response(f"Redirecting for {provider} sign-in", data=data)
    
    except Exception as e:
        traceback.print_exc()
        return error_response(f"An error occurred: {str(e)}")

# @user_bp.route('/users/callback/<provider>')
# @jwt_required(optional=True)
# @limiter.exempt
# def oauth2_callback(provider):
#     try:
#         # Check if the user is already authenticated
#         if get_jwt_identity() is not None:
#             return success_response("already authenticated", data={"redirect": "./account"})

#         provider_data = oauth2providers.get(provider)
#         if provider_data is None:
#             return error_response(f"provider not found.", status_code=404)
#             # return error_response(f"Invalid state or expired callback URL", status_code=404)

#         # Handle authentication errors
#         if 'error' in request.args:
#             return error_response(f"authentication errors occurred - {request.args.get('error')}")

#         # Validate the state parameter
#         oauth2_state_in_request = request.args.get('state')
#         stored_provider = redis_clients.get(f'oauth2_state:{oauth2_state_in_request}')
        
#         # Log the state values for debugging
#         print(f"Received state: {oauth2_state_in_request}")
#         print(f"Stored provider: {stored_provider}")

#         if not stored_provider:
#             return error_response("Invalid or expired state parameter", status_code=401)

#         # Validate the presence of the authorization code
#         if 'code' not in request.args:
#             return error_response("Missing authorization code", status_code=401)

#         client_callback_url = request.headers.get('Client-Callback-Url') or url_for('apis.oauth2_callback', provider=provider, _external=True)
        
#         # Exchange the authorization code for an access token
#         response = requests.post(
#             provider_data['token_url'], 
#             data={
#                 'client_id': provider_data['client_id'],
#                 'client_secret': provider_data['client_secret'],
#                 'code': request.args['code'],
#                 'grant_type': 'authorization_code',
#                 'redirect_uri': client_callback_url,
#             }, 
#             headers={'Accept': 'application/json'}
#         )
#         # 
#         # Log the response for debugging
#         print("Token exchange response status:", response.status_code)
#         print("Token exchange response body:", response.json())

#         if response.status_code != 200:
#             return error_response("Failed to obtain access token", status_code=401)

#         oauth2_token = response.json().get('access_token')
#         if not oauth2_token:
#             return error_response(f"Failed to retrieve {provider} access token", status_code=401)

#         # Use the access token to get the user's email address
#         response = requests.get(provider_data['userinfo']['url'], headers={
#             'Authorization': 'Bearer ' + oauth2_token,
#             'Accept': 'application/json',
#         })
        
#         if response.status_code != 200:
#             return error_response("Failed to retrieve user info", status_code=401)

#         email = provider_data['userinfo']['email'](response.json())

#         # Find or create the user in the database
#         user = db.session.scalar(db.select(User).where(User.email == email))
#         if user is None:
#             user = User(email=email, username=email.split('@')[0], oauth_providers=provider)
#             user.set_password(secrets.token_urlsafe(5))
#             db.session.add(user)
#             db.session.commit()

#         # Create JWT tokens for the user
#         if user:
#             access_token = user.make_token(token_type='access')
#             refresh_token = user.make_token(token_type='refresh')

#             # Create response object
#             response = urlencode(
#                 make_response(
#                 success_response(
#                     "Sign in successful",
#                     data={
#                         "access_token": access_token,
#                         "refresh_token": refresh_token,
#                         "redirect": "./account"
#                     }
#                 ) ) )
            
#             # Retrieve the callback URL from Redis using the state
#             client_callback_url = redis_clients.get(f'callback_url:{oauth2_state_in_request}')
            
#             # Remove the state from Redis after successful authentication
#             redis_clients.delete(f'oauth2_state:{oauth2_state_in_request}')
            
#             # return response
#             # Construct the full client application URL with query string
#             redirect_url = f"{client_callback_url}?{response}"

#             # Delete the state and callback URL from Redis after use
#             redis_clients.delete(f'oauth2_state:{oauth2_state_in_request}')
#             redis_clients.delete(f'callback_url:{oauth2_state_in_request}')

#             # Redirect to the client application
#             return redirect(redirect_url, external=True)
            
#         return error_response("Unable to sign in.", status_code=401)

#     except Exception as e:
#         traceback.print_exc()
#         return error_response(f"An error occurred: {str(e)}")

@user_bp.route('/users/callback/<provider>')
@jwt_required(optional=True)
@limiter.exempt
def oauth2_callback(provider):
    try:
        # Check if the user is already authenticated
        if get_jwt_identity() is not None:
            return success_response("already authenticated", data={"redirect": "./account"})

        provider_data = oauth2providers.get(provider)
        if provider_data is None:
            return error_response(f"Provider not found.", status_code=404)

        # Handle authentication errors
        if 'error' in request.args:
            return error_response(f"Authentication errors occurred - {request.args.get('error')}")

        # Validate the state parameter
        oauth2_state_in_request = request.args.get('state')
        stored_provider = redis_clients.get(f'oauth2_state:{oauth2_state_in_request}')
        
        if not stored_provider:
            return error_response("Invalid or expired state parameter", status_code=401)

        # Validate the presence of the authorization code
        if 'code' not in request.args:
            return error_response("Missing authorization code", status_code=401)

        client_callback_url = request.headers.get('Client-Callback-Url') or url_for('apis.oauth2_callback', provider=provider, _external=True)
        
        # Exchange the authorization code for an access token
        response = requests.post(
            provider_data['token_url'], 
            data={
                'client_id': provider_data['client_id'],
                'client_secret': provider_data['client_secret'],
                'code': request.args['code'],
                'grant_type': 'authorization_code',
                'redirect_uri': client_callback_url,
            }, 
            headers={'Accept': 'application/json'}
        )

        if response.status_code != 200:
            return error_response("Failed to obtain access token", status_code=401)

        oauth2_token = response.json().get('access_token')
        if not oauth2_token:
            return error_response(f"Failed to retrieve {provider} access token", status_code=401)

        # Use the access token to get the user's email address
        response = requests.get(provider_data['userinfo']['url'], headers={
            'Authorization': 'Bearer ' + oauth2_token,
            'Accept': 'application/json',
        })
        
        if response.status_code != 200:
            return error_response("Failed to retrieve user info", status_code=401)

        email = provider_data['userinfo']['email'](response.json())

        # Find or create the user in the database
        user = db.session.scalar(db.select(User).where(User.email == email))
        if user is None:
            user = User(email=email, username=email.split('@')[0], oauth_providers=provider)
            user.set_password(secrets.token_urlsafe(5))
            db.session.add(user)
            db.session.commit()

        # Create JWT tokens for the user
        if user:
            access_token = user.make_token(token_type='access')
            refresh_token = user.make_token(token_type='refresh')

            # Prepare the response data
            qs = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "redirect": "./account",
                "success":True
            }
            # data = success_response(f"{provider} auth successful", data=qs)
            # Retrieve the callback URL from Redis using the state
            # client_callback_url = redis_clients.get(f'callback_url:{oauth2_state_in_request}')
            # print(client_callback_url)
            # # Remove the state from Redis after successful authentication
            # redis_clients.delete(f'oauth2_state:{oauth2_state_in_request}')
            # redis_clients.delete(f'callback_url:{oauth2_state_in_request}')

            # # Redirect to the client application with the response data
            # # return redirect(f"{client_callback_url}?{urlencode(response_data)}", external=True)
            # return redirect(f"{client_callback_url}?{urlencode(response_data)}")
            
            # Retrieve the callback URL from Redis using the state
            client_callback_url = redis_clients.get(f'callback_url:{oauth2_state_in_request}')

            # Decode if it's a byte string
            if isinstance(client_callback_url, bytes):
                client_callback_url = client_callback_url.decode('utf-8')

            # Remove the state from Redis after successful authentication
            redis_clients.delete(f'oauth2_state:{oauth2_state_in_request}')
            redis_clients.delete(f'callback_url:{oauth2_state_in_request}')

            # Redirect to the client application with the response data
            return redirect(f"{client_callback_url}?{urlencode(qs)}")

        return error_response("Unable to sign in.", status_code=401)

    except Exception as e:
        traceback.print_exc()
        return error_response(f"An error occurred: {str(e)}")

from sqlalchemy import desc, func, exc

@user_bp.route('/users', methods=['GET'])
@user_bp.route('/users/<user_id>', methods=['GET'])
@jwt_required(optional=True)
# @access_required('admin', 'editor', strict=False)  # Specify required roles
@limiter.exempt
def get_users(user_id=None):
    try:
        # Fetch specific user record by ID/USERNAME
        if user_id is not None:
            
            if not (
                str(current_user.id) == user_id or
                current_user.email == user_id or
                current_user.username == user_id
                # ) and not any(role in [role_y.name for role_y in current_user.roles] for role in required_roles):
                ) and not any(role in [role_y.name for role_y in current_user.roles] for role in ["admin", "dev"]):
                # ) and not any(role in current_user.get_roles() for role in ["admin", "dev"]):
                # If none of the conditions are met, deny access
                return error_response("Access forbidden: insufficient permissions.", status_code=403)  # Forbidden
                
            # Check if the user_id is an integer (assumed to be the user id)
            if user_id.isdigit():
                user = User.query.get(int(user_id))
            else:
                # Otherwise, treat it as a slug and query by slug
                user = User.query.filter_by(username=user_id).first()
                
            if not user:
                return error_response("User not found.", status_code=404)
            
            # return success_response("User fetched successfully.", data=PageSerializer(items=[user], resource_name="user"))
            # data=PageSerializer(items=[user], resource_name="user").get_data()
            data=user.get_summary(include_products=True, include_roles=True)
            return success_response("User fetched successfully.", data=data)

        # Pagination parameters
        page = request.args.get('page', 1, type=int)  # Ensure page is an integer
        page_size = request.args.get('page_size', 5, type=int)  # Fixed to 'page_size'

        # Fetch users with pagination
        paginated_users = User.query.order_by(desc(User.created_at)).paginate(page=page, per_page=page_size)
        # paginated_users = User.query.order_by(desc(User.created_at)).offset((page - 1) * page_size).limit(page_size).all()

        response_data = PageSerializer(pagination_obj=paginated_users, resource_name="users")
        # response_data = PageSerializer(items=paginated_users, resource_name="users") // user items param in PageSerializer() when returning a list of item(s)
        data = response_data.get_data()
        
        return success_response("Users fetched successfully", data=data)

    except Exception as e:
        traceback.print_exc()
        access_token = request.cookies.get('access_token')
        return error_response(f"An error occurred: {access_token, str(e)}")

@user_bp.route('/users/current', methods=['GET'])
@jwt_required()
@limiter.exempt
def get_current_user():
    try:
        user = User.get_user(current_user.id)
        if not user:
            return error_response("User not found.", status_code=404)

        data = user.get_summary(include_products=True, include_roles=True)
        return success_response("Current user fetched successfully.", data=data)

    except Exception as e:
        return error_response(f"An error occurred: {str(e)}", status_code=500)

@user_bp.route('/users/<user_id>', methods=['PUT', 'POST'])
@jwt_required()
# @expects_json(signup_schema)
@limiter.exempt
def update_user(user_id):
    try:
        user = None
        
        if user_id is not None:

            user = User.get_user(username=user_id)
            if not user:
                return error_response("User not found.", status_code=404)

        data = request.json

        # Validation -> this is because incoming data may not contain same data/schemas as signup_schema
        # try:
        #     validate(instance=data, schema=signup_schema)
        # except ValidationError as e:
        #     return error_response(f"Validation error: {e.message}")
        
        # Perform checks on the data
        if 'username' in data and data['username'] != user.username and \
            db.session.scalar(sa.select(User).where(
                User.username == data['username'])):
            return error_response('please use a different username')

        if 'email' in data and data['email'] != user.email and \
            db.session.scalar(sa.select(User).where(
                User.email == data['email'])):
            return error_response('please use a different email address')
        
        if 'phone' in data and data['phone'] != user.phone and \
            db.session.scalar(sa.select(User).where(
                User.phone == data['phone'])):
            return error_response('please use a different phone number')
    
        # Update user attributes
        user.name = data.get('name', user.name)
        user.username = data.get('username', user.username)
        user.phone = data.get('phone', user.phone)
        user.email = data.get('email', user.email)
        user.about_me = data.get('about_me', user.about_me)

        # Update password only if provided
        if 'password' in data and data['password'] != None:
            user.set_password(data['password'])

        user.avatar = data.get('avatar', user.avatar)
        user.updated_at = func.now()
        
        db.session.commit()
        
        # data=PageSerializer(items=[user], resource_name="user").get_data()
        data=user.get_summary()
        return success_response("User updated successfully.", data=data)
    
    except Exception as e:
        return error_response(f"{str(e)}")

@user_bp.route('/users/<user_id>', methods=['DELETE'])
@jwt_required()
@access_required('admin', 'editor', strict=False)  # Specify required roles
def delete_user(user_id=None):
    try:
        # return current_user.get_roles()
        if user_id is not None:
            # Check if the user_id is an integer
            if user_id.isdigit():
                # Query by user ID
                user = User.query.get(int(user_id))
            else:
                # Otherwise, treat it as a username and query by username
                user = User.query.filter_by(username=user_id).first()
                
            if not user:
                return error_response("User not found.", status_code=404)
            
            # Check if the current user is an admin or the user to be deleted
            if current_user.is_admin or current_user.id == user.id:
                # Delete the user
                db.session.delete(user)
                db.session.commit()
                return success_response("User deleted successfully.")
            else:
                return error_response("You do not have permission to delete this user.", status_code=403)
        
        return error_response(f"user cannot be none")
    
    except Exception as e:
        traceback.print_exc()
        return error_response(f"{str(e)}")