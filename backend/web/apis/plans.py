import traceback, logging
from flask import current_app, request
from flask_jwt_extended import jwt_required, current_user
from jsonschema import validate
from sqlalchemy import desc, func
from web.apis.models.users import User
from web.apis.utils.decorators import access_required, role_required
from web.extensions import db, limiter, cache
from web.apis.utils.serializers import PageSerializer
from web.apis.utils.serializers import success_response, error_response
from sqlalchemy.exc import IntegrityError
from web.apis.models.plans import Plan, Subscription
from web.apis import api_bp as plans_bp

# ─── Cache Helpers ──────────────────────────────────────────────────────────

def _clear_plans_cache():
    """Invalidate plans cache after any mutating operation."""
    try:
        cache.delete_memoized(get_plans)
        cache.delete_memoized(get_1_plan)
    except Exception:
        pass

# ─── PLAN CRUD ──────────────────────────────────────────────────────────────

@plans_bp.route('/plans', methods=['GET'])
@jwt_required(optional=True)
@limiter.exempt
@cache.cached(timeout=60, query_string=True)
def get_plans():
    try:
        plans = Plan.query.filter_by(is_deleted=False).all()
        plans_data = PageSerializer(items=plans, resource_name="plans").get_data()
        return success_response("Plans fetched successfully", data=plans_data)
    except Exception as e:
        return error_response(str(e))

@plans_bp.route('/plans/<int:plan_id>', methods=['GET'])
@jwt_required(optional=True)
@limiter.exempt
@cache.cached(timeout=60, query_string=True)
def get_1_plan(plan_id):
    try:
        plan = Plan.query.filter_by(id=plan_id, is_deleted=False).first()
        if not plan:
            return error_response("Plan not found", status_code=404)
        return success_response("Plan fetched successfully", data=plan.get_summary())
    except Exception as e:
        return error_response(str(e))

@plans_bp.route('/plans', methods=['POST'])
@role_required('admin', 'dev')
@limiter.exempt
def create_plan():
    try:
        data = request.get_json() or request.json
        if not data:
            return error_response('Invalid request: No JSON data provided.', status_code=400)

        required = ['name', 'amount', 'units']
        missing  = [f for f in required if f not in data or data[f] in (None, '', 0)]
        if missing:
            return error_response(f"Missing required fields: {', '.join(missing)}")

        try:
            amount = float(data['amount'])
            units  = int(data['units'])
            if amount <= 0 or units <= 0:
                return error_response('Amount and units must be greater than zero.')
        except (ValueError, TypeError):
            return error_response('Invalid input for amount or units — must be numeric.')

        new_plan = Plan(
            name=data['name'],
            amount=amount,
            units=units,
            description=data.get('description', f"Subscription for {data['name']} plan at ₦{amount:,.0f}")
        )
        db.session.add(new_plan)
        db.session.commit()
        _clear_plans_cache()
        return success_response("Plan created successfully", data=new_plan.get_summary(), status_code=201)

    except IntegrityError as e:
        db.session.rollback()
        return error_response("A plan with that name already exists.")
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(f"Error: {str(e)}")

@plans_bp.route('/plans/<int:plan_id>', methods=['PUT'])
@jwt_required()
@access_required('admin', 'dev')
@limiter.exempt
def update_plan(plan_id):
    try:
        plan = Plan.query.filter_by(id=plan_id, is_deleted=False).first()
        if not plan:
            return error_response("Plan not found", status_code=404)

        data = request.get_json() or request.json
        if not data:
            return error_response('Invalid request: No JSON data provided.', status_code=400)

        plan.name        = data.get('name',        plan.name)
        plan.amount      = data.get('amount',      data.get('price', plan.amount))
        plan.units       = data.get('units',       plan.units)
        plan.description = data.get('description', plan.description)
        db.session.commit()
        _clear_plans_cache()
        return success_response("Plan updated successfully", data=plan.get_summary())
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(str(e))

@plans_bp.route('/plans/<int:plan_id>', methods=['DELETE'])
@jwt_required()
@access_required('admin', 'dev')
@limiter.exempt
def delete_plan(plan_id):
    try:
        plan = Plan.query.filter_by(id=plan_id, is_deleted=False).first()
        if not plan:
            return error_response("Plan not found", status_code=404)
        db.session.delete(plan)
        db.session.commit()
        _clear_plans_cache()
        return success_response("Plan deleted successfully")
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(str(e))


# ─── SUBSCRIPTION RESOURCE ──────────────────────────────────────────────────

from web.apis import api_bp as subscriptions_bp

def _clear_sub_cache():
    try:
        cache.delete_memoized(get_usage_statistics)
        cache.delete_memoized(get_user_subscriptions)
        cache.delete_memoized(get_user_subscriptions_detailed)
    except Exception:
        pass

def _sub_summary(sub):
    if hasattr(sub, 'get_summary'):
        return sub.get_summary()
    return {
        'id':          sub.id,
        'user_id':     sub.user_id,
        'plan_id':     sub.plan_id,
        'total_units': sub.total_units,
        'status':      getattr(sub, 'status', 'active'),
    }


@subscriptions_bp.route('/subscriptions', methods=['GET'])
@jwt_required(optional=True)
@limiter.exempt
@cache.cached(timeout=60, query_string=True)
def get_subscriptions():
    try:
        subscriptions = Subscription.query.filter_by(is_deleted=False).all()
        subs_data = PageSerializer(items=subscriptions, resource_name="subscriptions").get_data()
        return success_response("Subscriptions fetched successfully", data=subs_data)
    except Exception as e:
        return error_response(str(e))


@subscriptions_bp.route('/user/subscriptions', methods=['GET'])
@jwt_required()
@limiter.exempt
@cache.cached(timeout=5, query_string=True)
def get_user_subscriptions():
    try:
        subs = Subscription.query.filter_by(
            user_id=current_user.id,
            is_deleted=False
        ).order_by(Subscription.created_at.desc()).all()

        enriched = []
        for sub in subs:
            sub_data = _sub_summary(sub)
            plan = Plan.query.get(sub.plan_id)
            if plan:
                sub_data['plan'] = {
                    'id': plan.id, 'name': plan.name,
                    'amount': plan.amount, 'units': plan.units,
                    'description': plan.description
                }
            enriched.append(sub_data)

        return success_response("User subscriptions fetched successfully", data={
            "subscriptions": enriched, "count": len(enriched)
        })
    except Exception as e:
        return error_response(str(e))


@subscriptions_bp.route('/user/subscriptions/detailed', methods=['GET'])
@subscriptions_bp.route('/user/<int:user_id>/subscriptions/detailed', methods=['GET'])
@jwt_required()
@limiter.exempt
@cache.cached(timeout=5, query_string=True)
def get_user_subscriptions_detailed(user_id=None):
    try:
        page     = request.args.get('page',     default=1,  type=int)
        per_page = request.args.get('per_page', default=10, type=int)
        target   = user_id or current_user.id

        if user_id and user_id != current_user.id:
            if not getattr(current_user, 'is_admin', lambda: False)():
                return error_response("Unauthorized to view another user's subscriptions", status_code=403)

        paginated = Subscription.query.filter_by(user_id=target).order_by(
            Subscription.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        enriched = []
        for sub in paginated.items:
            sub_data = _sub_summary(sub)
            plan = Plan.query.get(sub.plan_id)
            if plan:
                sub_data['plan'] = {
                    'id': plan.id, 'name': plan.name,
                    'amount': plan.amount, 'units': plan.units,
                    'description': plan.description
                }
            enriched.append(sub_data)

        return success_response("Subscriptions fetched successfully", data={
            "subscriptions": enriched,
            "pagination": {
                "page": paginated.page, "per_page": paginated.per_page,
                "total": paginated.total, "total_pages": paginated.pages,
                "has_next": paginated.has_next, "has_prev": paginated.has_prev,
                "next_num": paginated.next_num, "prev_num": paginated.prev_num,
            }
        })
    except Exception as e:
        return error_response(str(e))


# ─── CREATE / ASSIGN SUBSCRIPTION ──────────────────────────────────────────
#
# Design: one subscription row per user (unique user_id constraint).
# Admin assigning a DIFFERENT plan should update the existing row, not insert.
# Admin assigning the SAME plan should top up the units on the existing row.
# Either way, the operation is a safe upsert keyed on user_id alone.
#
@subscriptions_bp.route('/subscriptions', methods=['POST'])
@subscriptions_bp.route('/subscription/<int:user_id>', methods=['POST'])
@jwt_required()
@role_required('admin', 'dev')
@limiter.exempt
def create_subscription(user_id=None):
    try:
        data = request.get_json() or request.json
        print("Received data for create_subscription:", data)

        if not data:
            return error_response('Invalid request: No JSON data provided.', status_code=400)

        uid     = user_id or current_user.id
        plan_id = data.get('plan_id')
        if not plan_id:
            return error_response("plan_id is required.", status_code=400)

        plan = Plan.query.get(plan_id)
        if not plan:
            return error_response(f"Plan {plan_id} not found.", status_code=404)

        units_to_add = int(data.get('total_units', plan.units))

        # ── KEY FIX ───────────────────────────────────────────────────────────
        # The table has UNIQUE(user_id), so we must look up by user_id only.
        # Filtering by plan_id as well misses subscriptions to a *different* plan,
        # causing a spurious IntegrityError on INSERT.
        # ─────────────────────────────────────────────────────────────────────
        existing = Subscription.query.filter_by(user_id=uid).first()   # any plan, any state

        if existing:
            changing_plan = existing.plan_id != plan.id
            if getattr(existing, 'is_deleted', False):
                existing.is_deleted = False   # reactivate soft-deleted row

            existing.plan_id     = plan.id         # switch plan if different
            existing.total_units += units_to_add   # always top-up units
            existing.status      = 'active'
            db.session.commit()
            _clear_sub_cache()

            msg = (
                f"Plan changed to '{plan.name}' and {units_to_add} units credited."
                if changing_plan else
                f"{units_to_add} units added to existing '{plan.name}' plan."
            )
            return success_response(msg, data=_sub_summary(existing))

        # ── No subscription yet — create fresh ────────────────────────────────
        new_sub = Subscription(
            user_id=uid,
            plan_id=plan.id,
            total_units=units_to_add,
            status='active'
        )
        db.session.add(new_sub)
        db.session.commit()
        _clear_sub_cache()
        return success_response(
            f"Subscription created — {units_to_add} units on '{plan.name}'.",
            data=_sub_summary(new_sub),
            status_code=201
        )

    except IntegrityError:
        # Last-resort race-condition guard — requery by user_id only
        db.session.rollback()
        try:
            existing = Subscription.query.filter_by(user_id=uid).first()
            if existing:
                plan = Plan.query.get(plan_id)          # re-fetch in new transaction
                units_to_add = int(data.get('total_units', plan.units if plan else 0))
                if getattr(existing, 'is_deleted', False):
                    existing.is_deleted = False
                existing.plan_id     = plan_id
                existing.total_units += units_to_add
                existing.status      = 'active'
                db.session.commit()
                _clear_sub_cache()
                return success_response(
                    "Units credited (race-condition retry).",
                    data=_sub_summary(existing)
                )
        except Exception:
            db.session.rollback()
        return error_response("Could not assign subscription — please try again.", status_code=500)

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(str(e))


@subscriptions_bp.route('/subscriptions/<int:subscription_id>', methods=['PUT'])
@jwt_required()
@access_required('admin', 'dev')
@limiter.exempt
def update_subscription(subscription_id):
    try:
        sub = Subscription.query.filter_by(id=subscription_id, is_deleted=False).first()
        if not sub:
            return error_response("Subscription not found", status_code=404)
        data = request.get_json() or request.json
        if not data:
            return error_response('No JSON data provided.', status_code=400)
        sub.plan_id     = data.get('plan_id',     sub.plan_id)
        sub.total_units = data.get('total_units', sub.total_units)
        db.session.commit()
        _clear_sub_cache()
        return success_response("Subscription updated successfully", data=_sub_summary(sub))
    except Exception as e:
        return error_response(str(e))


@subscriptions_bp.route('/subscriptions/<int:subscription_id>', methods=['DELETE'])
@jwt_required()
@access_required('admin', 'dev')
@limiter.exempt
def delete_subscription(subscription_id):
    try:
        sub = Subscription.query.filter_by(id=subscription_id, is_deleted=False).first()
        if not sub:
            return error_response("Subscription not found", status_code=404)
        db.session.delete(sub)
        db.session.commit()
        _clear_sub_cache()
        return success_response("Subscription deleted successfully")
    except Exception as e:
        return error_response(str(e))


# ─── USAGE RESOURCE ─────────────────────────────────────────────────────────

from web.apis.models.plans import Usage
from web.apis import api_bp as usage_bp


@usage_bp.route('/usage/statistics', methods=['GET'])
@jwt_required()
@limiter.exempt
@cache.cached(timeout=5, query_string=True)
def get_usage_statistics():
    try:
        subscription = (
            current_user.subscriptions[0]
            if getattr(current_user, 'subscriptions', None) else None
        )

        total_used     = 0
        total_capacity = 0
        status         = 'no_subscription'

        if subscription:
            total_used = db.session.query(
                func.coalesce(func.sum(Usage.units_used), 0)
            ).filter(
                Usage.user_id        == current_user.id,
                Usage.subscription_id == subscription.id,
                Usage.is_deleted     == False
            ).scalar() or 0

            total_capacity = subscription.total_units + total_used
            status         = getattr(subscription, 'status', 'active')

        usage_pct = (total_used / total_capacity * 100) if total_capacity > 0 else 0

        return success_response("Usage statistics retrieved successfully", data={
            'units_used':       total_used,
            'total_units':      total_capacity or getattr(subscription, 'total_units', 0),
            'remaining_units':  getattr(subscription, 'total_units', 0),
            'usage_percentage': round(usage_pct, 2),
            'status':           status,
        })
    except Exception as e:
        traceback.print_exc()
        return error_response("Error fetching usage statistics", status_code=500)


@usage_bp.route('/usage', methods=['GET'])
@usage_bp.route('/user/<int:user_id>/usage', methods=['GET'])
@jwt_required(optional=True)
@limiter.exempt
@cache.cached(timeout=5, query_string=True)
def get_usage(user_id=None):
    try:
        page      = request.args.get('page',     default=1,  type=int)
        page_size = request.args.get('per_size', default=10, type=int)
        include_user = request.args.get('include_user', 0, type=int)

        if not user_id and current_user:
            user_id = current_user.id

        user  = User.get_user(user_id)
        query = Usage.query.filter_by(is_deleted=False)

        # Admins fetching /usage see ALL users; regular users see only their own
        if user and not user.is_admin():
            query = query.filter_by(user_id=user_id)

        paginated = query.order_by(Usage.created_at.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        usage_records = PageSerializer(
            items=paginated.items,
            resource_name="usage",
            include_user=bool(include_user)
        ).get_data()

        return success_response("Usage records fetched successfully", data={
            "usage": usage_records,
            "pagination": {
                "page":       paginated.page,
                "per_page":   paginated.per_page,
                "total":      paginated.total,
                "total_pages": paginated.pages,
                "has_next":   paginated.has_next,
                "has_prev":   paginated.has_prev,
                "next_num":   paginated.next_num,
                "prev_num":   paginated.prev_num,
            }
        })
    except Exception as e:
        traceback.print_exc()
        return error_response(str(e), status_code=500)


@usage_bp.route('/usage', methods=['POST'])
@jwt_required(optional=True)
@limiter.exempt
@role_required('admin', 'dev')
def create_usage():
    try:
        data = request.get_json() or request.json
        if not data:
            return error_response('No JSON data provided.', status_code=400)

        if not data.get('user_id'):
            return error_response("user_id is required.", status_code=400)

        units_used = int(data.get('units_used', 0))
        if units_used <= 0:
            return error_response("units_used must be a positive integer.", status_code=400)

        user = User.get_user(data['user_id'])
        if not user:
            return error_response("User not found.", status_code=404)

        subscription = user.subscriptions[0] if user.subscriptions else None
        if not subscription:
            return error_response(
                f"No active subscription found for {user.username}.", status_code=404
            )

        if subscription.total_units < units_used:
            return error_response(
                f"Insufficient balance — {subscription.total_units} units available, "
                f"{units_used} requested.",
                status_code=400
            )

        prev_total = subscription.total_units
        subscription.total_units -= units_used
        if subscription.total_units <= 0:
            subscription.update_status()

        new_usage = Usage(
            user_id=user.id,
            subscription_id=subscription.id,
            units_used=units_used,
            total_units=prev_total,
            remaining_units=subscription.total_units,
        )
        db.session.add(new_usage)
        db.session.commit()

        try:
            cache.delete_memoized(get_usage_statistics)
            cache.delete_memoized(get_usage)
        except Exception:
            pass

        return success_response("Usage recorded successfully", data=new_usage.get_summary(), status_code=201)

    except IntegrityError as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(f"Database integrity error: {str(e)}", status_code=500)
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(f"Unexpected error: {str(e)}", status_code=500)


@usage_bp.route('/usage/<int:usage_id>', methods=['PUT'])
@jwt_required()
@access_required('admin', 'dev')
@limiter.exempt
def update_usage(usage_id):
    try:
        usage = Usage.query.filter_by(id=usage_id, is_deleted=False).first()
        if not usage:
            return error_response("Usage entry not found", status_code=404)
        data = request.get_json() or request.json
        if not data:
            return error_response('No JSON data provided.', status_code=400)
        usage.subscription_id = data.get('subscription_id', usage.subscription_id)
        usage.units_used      = data.get('units_used',      usage.units_used)
        db.session.commit()
        return success_response("Usage updated successfully", data=usage.get_summary())
    except Exception as e:
        return error_response(str(e))


@usage_bp.route('/usage/<int:usage_id>', methods=['DELETE'])
@jwt_required()
@access_required('admin', 'dev')
@limiter.exempt
def delete_usage(usage_id):
    try:
        usage = Usage.query.filter_by(id=usage_id, is_deleted=False).first()
        if not usage:
            return error_response("Usage entry not found", status_code=404)
        usage.is_deleted = True
        db.session.commit()
        return success_response("Usage entry deleted successfully")
    except Exception as e:
        return error_response(str(e))

