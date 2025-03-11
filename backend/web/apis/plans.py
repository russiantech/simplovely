
import traceback
from flask import request
from flask_jwt_extended import jwt_required, current_user
from jsonschema import validate
from sqlalchemy import desc
from web.apis.models.users import User
from web.apis.utils.decorators import access_required, role_required
from web.extensions import db, limiter
from web.apis.utils.serializers import PageSerializer
from web.apis.utils.serializers import success_response, error_response
from sqlalchemy.exc import IntegrityError
from web.apis.models.plans import Plan, Subscription
from web.apis import api_bp as plans_bp

# Get all plans
@plans_bp.route('/plans', methods=['GET'])
@jwt_required(optional=True)
def get_plans():
    try:
        plans = Plan.query.filter_by(is_deleted=False).all()
        plans = PageSerializer(items=plans, resource_name="plans").get_data()
        return success_response("Plans fetched successfully", data=plans)
    except Exception as e:
        return error_response(str(e))

# Create a new plan
from flask import request
from sqlalchemy.exc import IntegrityError
import traceback
import logging

@plans_bp.route('/plans', methods=['POST'])
@role_required('admin', 'dev')
def create_plan():
    try:
        # Extracting data from the incoming request
        data = request.json
        
        # Ensure all required fields are present and have meaningful values
        if not all(key in data for key in ['name', 'amount', 'units']):
            return error_response('Must provide plan(name, amount, and units)')

        # Ensure that 'amount' and 'units' have valid values
        if not data['name'] or not data['amount'] or not data['units']:
            return error_response('Name, amount & units must not be empty or zero.')

        try:
            # Validate and convert 'amount' and 'units' to appropriate types
            amount = float(data['amount']) if data['amount'] else 0
            units = int(data['units']) if data['units'] else 0

            # Ensure amount and units are valid (greater than 0)
            if amount <= 0 or units <= 0:
                return error_response('Amount and units must be greater than zero.')
            
        except ValueError:
            return error_response('Invalid input for amount or units, must be numeric.')

        # Creating a new plan object
        new_plan = Plan(
            name=data['name'],
            amount=amount,
            units=units,
            description=data.get('description', f"Subscription for {data['name']} plan at N{amount}")
        )
        
        # Adding the new plan to the session and committing
        db.session.add(new_plan)
        db.session.commit()
        
        # Return success response
        return success_response("Plan created successfully", data=new_plan.get_summary(), status_code=201)
    
    except IntegrityError as e:
        # Rollback the session on integrity error and return a more specific error
        db.session.rollback()
        logging.error(f"Integrity error while creating plan: {str(e)}")
        return error_response("Plan already exists, duplicates are not allowed.")
    
    except Exception as e:
        # Rollback the session on any other exception
        db.session.rollback()
        logging.error(f"Unexpected error: {str(e)}")
        traceback.print_exc()
        return error_response(f"An error occurred: {str(e)}")

# Update a plan
@plans_bp.route('/plans/<int:plan_id>', methods=['PUT'])
@jwt_required()
@access_required('admin', 'dev')
def update_plan(plan_id):
    try:
        plan = Plan.query.filter_by(id=plan_id, is_deleted=False).first()
        if not plan:
            return error_response("Plan not found", 404)

        data = request.json
        plan.name = data.get('name', plan.name)
        plan.amount = data.get('price', plan.amount)
        plan.units = data.get('units', plan.units)
        plan.description = data.get('description', plan.description)
        db.session.commit()

        return success_response("Plan updated successfully", data=plan.get_summary())
    
    except Exception as e:
        return error_response(str(e))

# Delete a plan (soft delete)
@plans_bp.route('/plans/<int:plan_id>', methods=['DELETE'])
@jwt_required()
@access_required('admin', 'dev')
def delete_plan(plan_id):
    try:
        plan = Plan.query.filter_by(id=plan_id, is_deleted=False).first()
        if not plan:
            return error_response("Plan not found", 404)

        db.session.delete(plan)
        db.session.commit()
        return success_response(None, "Plan deleted successfully")
    except Exception as e:
        return error_response(str(e))

# ====================================== /// SUBSCRIPTION RESOURCE /// ===========================

from flask import request
from flask_jwt_extended import jwt_required, current_user
from sqlalchemy.exc import IntegrityError
from web.extensions import db
from web.apis.utils.decorators import access_required
from web.apis.utils.serializers import success_response, error_response, PageSerializer
from web.apis.models.plans import Subscription
from web.apis import api_bp as subscriptions_bp
import traceback

# Get all subscriptions
@subscriptions_bp.route('/subscriptions', methods=['GET'])
@jwt_required(optional=True)
def get_subscriptions():
    try:
        subscriptions = Subscription.query.filter_by(is_deleted=False).all()
        subscriptions = PageSerializer(items=subscriptions, resource_name="subscriptions").get_data()
        return success_response("Subscriptions fetched successfully", data=subscriptions)
    except Exception as e:
        return error_response(str(e))

# Get subscriptions for the current user
@subscriptions_bp.route('/user/subscriptions', methods=['GET'])
@jwt_required()
def get_user_subscriptions():
    try:
        # Fetch subscriptions for the current user
        user_subscriptions = Subscription.query.filter_by(user_id=current_user.id, is_deleted=False).all()
        
        # Serialize the response
        subscriptions = PageSerializer(items=user_subscriptions, resource_name="user_subscriptions").get_data()
        # subscriptions_data = [sub.get_summary() for sub in user_subscriptions]
        
        return success_response("User subscriptions fetched successfully", data=subscriptions)
    
    except Exception as e:
        return error_response(str(e))
    
# Create a new subscription
@subscriptions_bp.route('/subscriptions', methods=['POST'])
@jwt_required()
def create_subscription():
    try:
        data = request.json
        new_subscription = Subscription(
            user_id=current_user.id,
            plan_id=data['plan_id'],
            total_units=data['total_units']
        )
        db.session.add(new_subscription)
        db.session.commit()
        return success_response("Subscription created successfully", data=new_subscription.get_summary(), status_code=201)
    
    except IntegrityError:
        db.session.rollback()  # Rollback the session on error
        return error_response("Subscription already exists and cannot be duplicates")
    
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(str(e))

# Update a subscription
@subscriptions_bp.route('/subscriptions/<int:subscription_id>', methods=['PUT'])
@jwt_required()
@access_required('admin', 'dev')
def update_subscription(subscription_id):
    try:
        subscription = Subscription.query.filter_by(id=subscription_id, is_deleted=False).first()
        if not subscription:
            return error_response("Subscription not found", 404)

        data = request.json
        subscription.plan_id = data.get('plan_id', subscription.plan_id)
        subscription.total_units = data.get('total_units', subscription.total_units)
        db.session.commit()

        return success_response("Subscription updated successfully", data=subscription.get_summary())
    
    except Exception as e:
        return error_response(str(e))

# Delete a subscription (soft delete)
@subscriptions_bp.route('/subscriptions/<int:subscription_id>', methods=['DELETE'])
@jwt_required()
@access_required('admin', 'dev')
def delete_subscription(subscription_id):
    try:
        subscription = Subscription.query.filter_by(id=subscription_id, is_deleted=False).first()
        if not subscription:
            return error_response("Subscription not found", 404)

        db.session.delete(subscription)
        db.session.commit()
        return success_response(None, "Subscription deleted successfully")
    except Exception as e:
        return error_response(str(e))

# =====++++++++++++++++++++++++++++++++++++ USAGE RESOURCE ++++++++++++++++++===================
from flask import request
from flask_jwt_extended import jwt_required, current_user
from sqlalchemy.exc import IntegrityError
from web.extensions import db
from web.apis.utils.decorators import access_required
from web.apis.utils.serializers import success_response, error_response, PageSerializer
from web.apis.models.plans import Usage
from web.apis import api_bp as usage_bp
import traceback

# # Get all usage records
# @usage_bp.route('/usage', methods=['GET'])
# @jwt_required(optional=True)
# def get_usage():
#     try:
#         usage_records = Usage.query.filter_by(is_deleted=False).all()
#         usage_records = PageSerializer(items=usage_records, resource_name="usage").get_data()
#         return success_response("Usage records fetched successfully", data=usage_records)
#     except Exception as e:
#         return error_response(str(e))

# Get all usage records
# @usage_bp.route('/user/usage', methods=['GET'])
# @usage_bp.route('/usage', methods=['GET'])
# @jwt_required(optional=True)
# @limiter.exempt
# def get_usage():
#     try:
#         # Get pagination parameters from query string
#         page = request.args.get('page', default=1, type=int)
#         per_page = request.args.get('per_page', default=10, type=int)
        
#         # Check if a specific user ID is provided for filtering
#         user_id = request.args.get('user_id', type=int)
        
#         # Build the query
#         query = Usage.query.filter_by(is_deleted=False)
        
#         if user_id is not None:
#             query = query.filter_by(user_id=user_id)
        
#         # Paginate the results and order by latest first
#         paginated_usage = query.order_by(Usage.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
#         # Serialize the paginated data
#         usage_records = PageSerializer(items=paginated_usage.items, resource_name="usage").get_data()

#         return success_response("Usage records fetched successfully", data=usage_records)
    
#     except Exception as e:
#         return error_response(str(e))

@usage_bp.route('/user/<int:user_id>/usage', methods=['GET'])
@usage_bp.route('/usage', methods=['GET'])
@jwt_required(optional=True)
@limiter.exempt
def get_usage(user_id=None):
    try:
        # Get pagination parameters from query string
        page = request.args.get('page', default=1, type=int)
        page_size = request.args.get('per_size', default=10, type=int)

        if not user_id and current_user:
            user_id = current_user.id

        user = User.get_user(user_id)
        # Build the query
        query = Usage.query.filter_by(is_deleted=False)

        if user_id is not None and user.is_admin():
            query = query.filter_by(user_id=user_id)
        else:
            query = query.filter_by(user_id=user_id)
            
        # Paginate the results and order by latest first
        paginated_usage = query.order_by(Usage.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)

        # Serialize the paginated data
        usage_records = PageSerializer(items=paginated_usage.items, resource_name="usage").get_data()

        # if not usage_records:
        #     # Return placeholders if no usage records are found
        #     usage_records = [{
        #         'units_used': 0,
        #         'total_units': 0,
        #         'remaining_units': 0,
        #         'usage_percentage': 0,
        #         'status': 'No usage records available'
        #     }]
        
        return success_response("Usage records fetched successfully", data=usage_records)

    except Exception as e:
        return error_response(str(e), status_code=500)


# Create a new usage entry
from flask_jwt_extended import jwt_required, current_user

# @usage_bp.route('/usage', methods=['POST'])
# @jwt_required(optional=True)
# @limiter.exempt
# def create_usage():
#     try:
#         data = request.json
        
#         # Check if current_user is None
#         if current_user is None and data.get('user_id') is None:
#             return error_response("User ID must be provided if not authenticated", status_code=400)

#         # Get units used from the request data
#         units_used = data['units_used']

#         # If current_user is authenticated, check their balance
#         if current_user:
#             total_units = current_user.subscriptions.total_units
#             if units_used > total_units:
#                 return error_response("Insufficient units available", status_code=400)

#         # Create new usage entry
#         new_usage = Usage(
#             subscription_id=data.get('subscription_id'),
#             user_id=data.get('user_id', current_user.id if current_user else None),
#             units_used=units_used
#         )
        
#         db.session.add(new_usage)
#         db.session.commit()
#         return success_response("Usage recorded successfully", data=new_usage.get_summary(), status_code=201)
    
#     except IntegrityError as e:
#         db.session.rollback()  # Rollback the session on error
#         traceback.print_exc()
#         return error_response(f"{e}, {request.json}")
    
#     except Exception as e:
#         db.session.rollback()
#         traceback.print_exc()
#         return error_response(str(e))

# @usage_bp.route('/usage', methods=['POST'])
# @jwt_required(optional=True)
# @limiter.exempt
# def create_usage():
#     try:
#         data = request.json
        
#         # Check if current_user is None
#         if current_user is None and data.get('user_id') is None:
#             return error_response("User ID must be provided if not authenticated", status_code=400)

#         # Get units used from the request data
#         units_used = data['units_used']

#         user = current_user or User.get_user(data.get('user_id'))
#         # If current_user is authenticated, check their balance
#         if user:
            
#             subscription = user.subscriptions  # Assuming a single subscription for simplicity
#             total_units = subscription.total_units
            
#             if total_units < units_used:
#                 return error_response(f"Your volume [{total_units}] is not sufficient for this usage", status_code=400)

#             # Deduct units from the user's subscription
#             subscription.total_units -= units_used

#             # Update subscription status if necessary
#             if total_units <= 0:
#                 subscription.update_status()

#             # Create new usage entry
#             new_usage = Usage(
#                 user_id=data.get('user_id', current_user.id if current_user else None),
#                 subscription_id=subscription.id,
#                 units_used=units_used,
#                 total_units=total_units,
#                 remaining_units=subscription.total_units,
#             )
        
#         db.session.add(new_usage)
#         db.session.commit()
#         return success_response("Usage recorded successfully", data=new_usage.get_summary(), status_code=201)
    
#     except IntegrityError as e:
#         db.session.rollback()  # Rollback the session on error
#         traceback.print_exc()
#         return error_response(f"{e}, {request.json}")
    
#     except Exception as e:
#         db.session.rollback()
#         traceback.print_exc()
#         return error_response(str(e))

# @usage_bp.route('/usage', methods=['POST'])
# @jwt_required(optional=True)
# @limiter.exempt
# def create_usage():
#     try:
#         data = request.json
        
#         # Validate the presence of user ID
#         if current_user is None and data.get('user_id') is None:
#             return error_response("User ID must be provided if not authenticated", status_code=400)

#         # Extract units used from the request data
#         units_used = int(data.get('units_used'))
#         if units_used is None or units_used <= 0:
#             return error_response("Invalid units used specified", status_code=400)

#         # Determine the user context
#         user = current_user or User.get_user(data.get('user_id'))
        
#         if user:
#             # subscription = user.subscriptions  # Assuming a single subscription for simplicity
#             subscription = user.subscriptions[0] if user.subscriptions else None
            
#             total_units = subscription.total_units
            
#             # Validate sufficient units for usage
#             if total_units < units_used:
#                 return error_response(f"Your volume [{total_units}] is not sufficient for this usage", status_code=400)

#             # Deduct units from the user's subscription
#             subscription.total_units -= units_used
            
#             # Update subscription status if necessary
#             if subscription.total_units <= 0:
#                 subscription.update_status()

#             # Create new usage entry
#             new_usage = Usage(
#                 user_id=user.id,
#                 subscription_id=subscription.id,
#                 units_used=units_used,
#                 total_units=total_units,  # Record total before deduction
#                 remaining_units=subscription.total_units,
#             )
        
#             db.session.add(new_usage)
#             db.session.commit()
#             return success_response("Usage recorded successfully", data=new_usage.get_summary(), status_code=201)

#         return error_response("User not found", status_code=404)

#     except IntegrityError as e:
#         db.session.rollback()  # Rollback the session on error
#         traceback.print_exc()
#         return error_response(f"Database integrity error: {str(e)}", status_code=500)
    
#     except Exception as e:
#         db.session.rollback()
#         traceback.print_exc()
#         return error_response(f"An unexpected error occurred: {str(e)}", status_code=500)

@usage_bp.route('/usage/statistics', methods=['GET'])
@jwt_required(optional=False)
@limiter.exempt
def get_usage_statistics():
    try:
        # Ensure the current user is authenticated
        if not current_user:
            return error_response('User is not logged in.', status_code=401)

        # Query the most recent usage record for the current user
        recent_usage = Usage.query.filter_by(user_id=current_user.id).order_by(Usage.created_at.desc()).first()

        if recent_usage:
            usage_percentage = recent_usage.calculate_usage_percentage()

            data = {
                'units_used': recent_usage.units_used,
                'total_units': recent_usage.total_units,
                'remaining_units': recent_usage.subscriptions.total_units,
                # 'available_units': recent_usage.subscriptions.total_units,
                'usage_percentage': usage_percentage,
                'status': recent_usage.status
            }
            
            return success_response("Stats fetched successfully.", data=data, status_code=200)
        
        else:
            # Return placeholders if no usage records are found
            data = {
                'available_units': 0,
                'units_used': 0,
                'total_units': current_user.subscriptions[0].total_units or 0,
                'remaining_units': current_user.subscriptions[0].total_units or 0,
                'usage_percentage': 0,
                'status': 'No usage records available'
            }
            
            return success_response('No usage records found for the current user.', data=data, status_code=200)
    except Exception as e:
        return error_response(str(e), status_code=500)

@usage_bp.route('/usage', methods=['POST'])
@jwt_required(optional=True)
@limiter.exempt
@role_required('admin', 'dev')
def create_usage():
    try:
        data = request.json
        
        # Validate the presence of user ID
        # if current_user is None and data.get('user_id') is None:
        if data.get('user_id') is None:
            return error_response("Choose a user to record usage for.", status_code=400)

        # Extract units used from the request data
        units_used = int(data.get('units_used', 0))
        if units_used is None or units_used <= 0:
            return error_response("Invalid units used specified", status_code=400)

        # Determine the user context
        # user = current_user or User.get_user(data.get('user_id'))
        user = User.get_user(data.get('user_id'))
        
        if user:
            # Assuming the user has multiple subscriptions, select the first one or implement your logic to choose
            subscription = user.subscriptions[0] if user.subscriptions else None
            # subscription = user.subscriptions if user.subscriptions else None
            
            if subscription is None:
                return error_response(f"Hey, return those fabrics right now. No active subscriptions found for this {user.username}", status_code=404)

            total_units = subscription.total_units
            
            # Validate sufficient units for usage
            if total_units < units_used:
                return error_response(f"Your volume [{total_units}] is not sufficient for this usage", status_code=400)

            # Deduct units from the user's subscription
            subscription.total_units -= units_used
            
            # Update subscription status if necessary
            if subscription.total_units <= 0:
                subscription.update_status()

            # Create new usage entry
            new_usage = Usage(
                user_id=user.id,
                subscription_id=subscription.id,
                units_used=units_used,
                total_units=total_units,  # Record total before deduction
                remaining_units=subscription.total_units,
            )

            db.session.add(new_usage)
            db.session.commit()
            return success_response("Usage recorded successfully", data=new_usage.get_summary(), status_code=201)

        return error_response("User not found", status_code=404)

    except IntegrityError as e:
        db.session.rollback()  # Rollback the session on error
        traceback.print_exc()
        return error_response(f"Database integrity error: {str(e)}", status_code=500)
    
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(f"An unexpected error occurred: {str(e)}", status_code=500)

# Update a usage entry
@usage_bp.route('/usage/<int:usage_id>', methods=['PUT'])
@jwt_required()
@access_required('admin', 'dev')
def update_usage(usage_id):
    try:
        usage = Usage.query.filter_by(id=usage_id, is_deleted=False).first()
        if not usage:
            return error_response("Usage entry not found", 404)

        data = request.json
        usage.subscription_id = data.get('subscription_id', usage.subscription_id)
        usage.units_used = data.get('units_used', usage.units_used)
        db.session.commit()

        return success_response("Usage entry updated successfully", data=usage.get_summary())
    
    except Exception as e:
        return error_response(str(e))

# Delete a usage entry (soft delete)
@usage_bp.route('/usage/<int:usage_id>', methods=['DELETE'])
@jwt_required()
@access_required('admin', 'dev')
def delete_usage(usage_id):
    try:
        usage = Usage.query.filter_by(id=usage_id, is_deleted=False).first()
        if not usage:
            return error_response("Usage entry not found", 404)

        usage.is_deleted = True  # Soft delete
        db.session.commit()
        return success_response(None, "Usage entry deleted successfully")
    except Exception as e:
        return error_response(str(e))



# USAGE RESOURCE

from flask import jsonify, request
from flask_restful import Resource, Api
from web.apis.models.plans import  Usage
# from web.extensions import app
# from flask import current_app as app
# from flask_restful import Resource, Api
# # api = Api(app)

class UsageResource(Resource):
    
    def get(self, usage_id=None):
        if usage_id:
            usage = Usage.query.get(usage_id)
            if usage:
                return jsonify(usage.get_summary())
            return jsonify({'message': 'Usage not found'}), 404
        
        # Return all usages
        usages = Usage.query.filter_by(is_deleted=False).all()
        return jsonify([usage.get_summary() for usage in usages])

    def post(self):
        data = request.get_json()
        new_usage = Usage(
            subscription_id=data['subscription_id'],
            units_used=data['units_used']
        )
        db.session.add(new_usage)
        db.session.commit()
        return jsonify(new_usage.get_summary()), 201

    def put(self, usage_id):
        usage = Usage.query.get(usage_id)
        if not usage:
            return jsonify({'message': 'Usage not found'}), 404
        
        data = request.get_json()
        usage.units_used = data.get('units_used', usage.units_used)
        usage.is_deleted = data.get('is_deleted', usage.is_deleted)

        db.session.commit()
        return jsonify(usage.get_summary())

    def delete(self, usage_id):
        usage = Usage.query.get(usage_id)
        if not usage:
            return jsonify({'message': 'Usage not found'}), 404
        
        usage.is_deleted = True
        db.session.commit()
        return jsonify({'message': 'Usage record deleted'})

# Add the resource to the API
""" But I commented it out for now since I have another resource for usage - not using the flask_restful library. """
# from web.extensions import api
# api.add_resource(UsageResource, '/api/usage', '/api/usage/<int:usage_id>') 

