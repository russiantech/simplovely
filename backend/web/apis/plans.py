"""Plans, subscriptions (volume balance) and usage logs."""
from flask import request
from flask_jwt_extended import current_user, jwt_required
from sqlalchemy import func

from web.apis import api_bp as bp
from web.apis.models.plans import Plan, Subscription, Usage
from web.apis.models.users import User
from web.apis.utils.decorators import admin_required, is_owner_or_admin
from web.apis.utils.serializers import PageSerializer, error_response, get_pagination, pagination_meta, success_response
from web.extensions import db


def _json():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _positive_int(value, label):
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number.")
    if number <= 0:
        raise ValueError(f"{label} must be greater than zero.")
    return number


def _plan_fields(data, partial=False):
    """Validated plan columns from request data. Raises ValueError with a user-facing message."""
    out = {}
    if not partial or "name" in data:
        name = str(data.get("name") or "").strip()
        if not name or len(name) > 50:
            raise ValueError("Plan name is required (max 50 characters).")
        out["name"] = name
    if not partial or "amount" in data or "price" in data:
        out["amount"] = float(_positive_int(data.get("amount", data.get("price")), "Amount"))
    if not partial or "units" in data:
        out["units"] = _positive_int(data.get("units"), "Units")
    if "description" in data or not partial:
        desc = str(data.get("description") or "").strip()
        if not desc:
            if not partial:
                desc = f"{out['name']} plan - {out['units']} units"
        out["description"] = desc[:80] or None if desc else None
    return out


def _active_plan(plan_id):
    return Plan.query.filter_by(id=plan_id, is_deleted=False).first()


# ------------------------------------------------------------------- plans
@bp.get("/plans")
def get_plans():
    plans = Plan.query.filter_by(is_deleted=False).order_by(Plan.amount).all()
    return success_response("Plans fetched successfully", data=PageSerializer(items=plans, resource_name="plans").get_data())


@bp.get("/plans/<int:plan_id>")
def get_plan(plan_id):
    plan = _active_plan(plan_id)
    return success_response("Plan fetched successfully", data=plan.get_summary()) if plan else error_response("Plan not found", 404)


@bp.post("/plans")
@admin_required
def create_plan():
    try:
        fields = _plan_fields(_json())
    except ValueError as exc:
        return error_response(str(exc))
    plan = Plan(**fields)
    db.session.add(plan)
    db.session.commit()
    return success_response("Plan created successfully", data=plan.get_summary(), status_code=201)


@bp.route("/plans/<int:plan_id>", methods=["PUT", "PATCH"])
@admin_required
def update_plan(plan_id):
    plan = _active_plan(plan_id)
    if not plan:
        return error_response("Plan not found", 404)
    try:
        fields = _plan_fields(_json(), partial=True)
    except ValueError as exc:
        return error_response(str(exc))
    for key, value in fields.items():
        setattr(plan, key, value)
    db.session.commit()
    return success_response("Plan updated successfully", data=plan.get_summary())


@bp.delete("/plans/<int:plan_id>")
@admin_required
def delete_plan(plan_id):
    plan = _active_plan(plan_id)
    if not plan:
        return error_response("Plan not found", 404)
    plan.is_deleted = True  # soft delete: existing subscriptions/transactions keep their reference
    db.session.commit()
    return success_response("Plan deleted successfully")


# ----------------------------------------------------------- subscriptions
def _with_plan(sub):
    data = sub.get_summary()
    if sub.plan:
        data["plan"] = {k: getattr(sub.plan, k) for k in ("id", "name", "amount", "units", "description")}
    return data


@bp.get("/subscriptions")
@admin_required
def get_subscriptions():
    subs = Subscription.query.filter_by(is_deleted=False).all()
    return success_response("Subscriptions fetched successfully", data=PageSerializer(items=subs, resource_name="subscriptions").get_data())


@bp.get("/user/subscriptions")
@jwt_required()
def get_user_subscriptions():
    subs = Subscription.query.filter_by(user_id=current_user.id, is_deleted=False).all()
    return success_response("User subscriptions fetched successfully", data={"subscriptions": [_with_plan(s) for s in subs], "count": len(subs)})


@bp.get("/user/subscriptions/detailed")
@bp.get("/user/<int:user_id>/subscriptions/detailed")
@jwt_required()
def get_user_subscriptions_detailed(user_id=None):
    target = user_id or current_user.id
    if not is_owner_or_admin(target):
        return error_response("Unauthorized to view another user's subscriptions", 403)
    page, size = get_pagination(10)
    paginated = Subscription.query.filter_by(user_id=target, is_deleted=False).order_by(Subscription.created_at.desc()).paginate(page=page, per_page=size, error_out=False)
    return success_response("Subscriptions fetched successfully", data={"subscriptions": [_with_plan(s) for s in paginated.items], "pagination": pagination_meta(paginated)})


@bp.post("/subscriptions")
@bp.post("/subscription/<int:user_id>")
@admin_required
def assign_subscription(user_id=None):
    """Admin credit: switches the user's plan and tops up units (one row per user)."""
    data = _json()
    uid = user_id or data.get("user_id") or current_user.id
    user = db.session.get(User, int(uid)) if str(uid).isdigit() else None
    if not user or user.is_deleted:
        return error_response("User not found.", 404)
    plan = _active_plan(data.get("plan_id")) if str(data.get("plan_id") or "").isdigit() else None
    if not plan:
        return error_response("A valid plan_id is required.", 400)
    try:
        units = _positive_int(data.get("total_units", plan.units), "Units")
    except ValueError as exc:
        return error_response(str(exc))
    existed = Subscription.query.filter_by(user_id=user.id).first() is not None
    sub = Subscription.credit(user.id, plan, units)
    db.session.commit()
    msg = f"{units} units credited on '{plan.name}'." if existed else f"Subscription created - {units} units on '{plan.name}'."
    return success_response(msg, data=sub.get_summary(), status_code=200 if existed else 201)


@bp.route("/subscriptions/<int:subscription_id>", methods=["PUT", "PATCH"])
@admin_required
def update_subscription(subscription_id):
    sub = Subscription.query.filter_by(id=subscription_id, is_deleted=False).first()
    if not sub:
        return error_response("Subscription not found", 404)
    data = _json()
    if "plan_id" in data:
        if not _active_plan(data["plan_id"]):
            return error_response("Plan not found.", 404)
        sub.plan_id = int(data["plan_id"])
    if "total_units" in data:
        try:
            units = int(data["total_units"])
        except (TypeError, ValueError):
            return error_response("Units must be a number.")
        if units < 0:
            return error_response("Units cannot be negative.")
        sub.total_units = units
    sub.refresh_status()
    db.session.commit()
    return success_response("Subscription updated successfully", data=sub.get_summary())


@bp.delete("/subscriptions/<int:subscription_id>")
@admin_required
def delete_subscription(subscription_id):
    sub = Subscription.query.filter_by(id=subscription_id, is_deleted=False).first()
    if not sub:
        return error_response("Subscription not found", 404)
    sub.is_deleted, sub.status = True, "cancelled"
    db.session.commit()
    return success_response("Subscription deleted successfully")


# ------------------------------------------------------------------- usage
def _locked_subscription(user_id):
    return Subscription.query.filter_by(user_id=user_id, is_deleted=False).with_for_update().first()


@bp.get("/usage/statistics")
@jwt_required()
def get_usage_statistics():
    sub = Subscription.query.filter_by(user_id=current_user.id, is_deleted=False).first()
    used = remaining = 0
    status = "no_subscription"
    if sub:
        used = db.session.query(func.coalesce(func.sum(Usage.units_used), 0)).filter(
            Usage.user_id == current_user.id, Usage.subscription_id == sub.id, Usage.is_deleted.is_(False)
        ).scalar() or 0
        remaining, status = sub.total_units, sub.status
    capacity = used + remaining
    return success_response("Usage statistics retrieved successfully", data={
        "units_used": int(used), "total_units": int(capacity), "remaining_units": int(remaining),
        "usage_percentage": round(used / capacity * 100, 2) if capacity else 0, "status": status,
    })


@bp.get("/usage")
@bp.get("/user/<int:user_id>/usage")
@jwt_required()
def get_usage(user_id=None):
    page, size = get_pagination(10)
    query = Usage.query.filter_by(is_deleted=False)
    if current_user.is_admin:
        target = user_id or request.args.get("user_id", type=int)
        if target:
            query = query.filter_by(user_id=target)
    else:
        if user_id and user_id != current_user.id:
            return error_response("Unauthorized to view another user's usage.", 403)
        query = query.filter_by(user_id=current_user.id)
    paginated = query.order_by(Usage.created_at.desc()).paginate(page=page, per_page=size, error_out=False)
    records = PageSerializer(items=paginated.items, resource_name="usage", include_user=bool(request.args.get("include_user", 0, type=int))).get_data()
    return success_response("Usage records fetched successfully", data={"usage": records, "pagination": pagination_meta(paginated)})


@bp.post("/usage")
@admin_required
def create_usage():
    data = _json()
    user = db.session.get(User, int(data["user_id"])) if str(data.get("user_id") or "").isdigit() else None
    if not user or user.is_deleted:
        return error_response("User not found.", 404)
    try:
        units = _positive_int(data.get("units_used"), "units_used")
    except ValueError as exc:
        return error_response(str(exc))
    sub = _locked_subscription(user.id)  # row lock: two admins cannot spend the same units
    if not sub:
        return error_response(f"No active subscription found for {user.username}.", 404)
    if sub.total_units < units:
        return error_response(f"Insufficient balance - {sub.total_units} units available, {units} requested.")
    before = sub.total_units
    sub.total_units -= units
    sub.refresh_status()
    entry = Usage(user_id=user.id, subscription_id=sub.id, units_used=units, total_units=before, remaining_units=sub.total_units, status=sub.status)
    db.session.add(entry)
    db.session.commit()
    return success_response("Usage recorded successfully", data=entry.get_summary(), status_code=201)


@bp.route("/usage/<int:usage_id>", methods=["PUT", "PATCH"])
@admin_required
def update_usage(usage_id):
    entry = Usage.query.filter_by(id=usage_id, is_deleted=False).first()
    if not entry:
        return error_response("Usage entry not found", 404)
    try:
        units = _positive_int(_json().get("units_used"), "units_used")
    except ValueError as exc:
        return error_response(str(exc))
    sub = _locked_subscription(entry.user_id)
    if not sub:
        return error_response("Subscription not found.", 404)
    delta = units - entry.units_used
    if delta > sub.total_units:
        return error_response(f"Insufficient balance - only {sub.total_units} more units available.")
    sub.total_units -= delta
    sub.refresh_status()
    entry.units_used = units
    entry.remaining_units = max(entry.remaining_units - delta, 0)
    db.session.commit()
    return success_response("Usage updated successfully", data=entry.get_summary())


@bp.delete("/usage/<int:usage_id>")
@admin_required
def delete_usage(usage_id):
    entry = Usage.query.filter_by(id=usage_id, is_deleted=False).first()
    if not entry:
        return error_response("Usage entry not found", 404)
    sub = _locked_subscription(entry.user_id)
    if sub:  # give the units back so balances stay consistent with the log
        sub.total_units += entry.units_used
        sub.refresh_status()
    entry.is_deleted = True
    db.session.commit()
    return success_response("Usage entry deleted and units restored.")
