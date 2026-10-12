"""Transaction history (own for customers, all for admins)."""
from flask import request
from flask_jwt_extended import current_user, jwt_required
from sqlalchemy import func

from web.apis import api_bp as bp
from web.apis.models.transactions import Transaction
from web.apis.utils.serializers import get_pagination, pagination_meta, success_response
from web.extensions import db

_STATUS_ALIASES = {"successful": "success", "failure": "failed"}


def _scoped(query):
    return query if current_user.is_admin else query.filter(Transaction.user_id == current_user.id)


def _summary(txn):
    data = txn.get_summary()
    data.update(
        amount=float(txn.amount or 0),
        channel=txn.payment_method or "paystack",
        created_at=txn.created_at.isoformat() if txn.created_at else None,
        updated_at=txn.updated_at.isoformat() if txn.updated_at else None,
    )
    return data


@bp.get("/transactions")
@jwt_required()
def get_transactions():
    page, size = get_pagination(10)
    status = (request.args.get("status") or "").strip().lower()
    query = _scoped(Transaction.query.filter_by(is_deleted=False))
    if status:
        accepted = {status, *(k for k, v in _STATUS_ALIASES.items() if v == status)}
        query = query.filter(func.lower(Transaction.status).in_(accepted))
    paginated = query.order_by(Transaction.created_at.desc()).paginate(page=page, per_page=size, error_out=False)
    return success_response("Transactions fetched successfully", data={"transactions": [_summary(t) for t in paginated.items], "pagination": pagination_meta(paginated)})


@bp.get("/transactions/summary")
@jwt_required()
def get_transactions_summary():
    rows = (
        _scoped(db.session.query(Transaction).filter(Transaction.is_deleted.is_(False)))
        .with_entities(func.lower(Transaction.status), func.count(Transaction.id), func.coalesce(func.sum(Transaction.amount), 0))
        .group_by(func.lower(Transaction.status))
        .all()
    )
    result = {key: {"count": 0, "total_amount": 0.0} for key in ("success", "pending", "failed")}
    for status, count, total in rows:
        key = _STATUS_ALIASES.get(status or "unknown", status or "unknown")
        bucket = result.setdefault(key, {"count": 0, "total_amount": 0.0})
        bucket["count"] += int(count)
        bucket["total_amount"] += float(total or 0)
    return success_response("Transaction summary fetched successfully", data=result)
