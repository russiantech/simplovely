# web/apis/transactions.py
import traceback
from flask import request
from flask_jwt_extended import jwt_required, current_user
from sqlalchemy import func
from web.apis import api_bp as transactions_bp
from web.apis.models.transactions import Transaction
from web.apis.models.plans import Plan
from web.apis.models.users import User
from web.apis.utils.serializers import success_response, error_response, PageSerializer
from web.extensions import db, limiter


def _txn_summary(txn):
    """Serialize a transaction for the list/detail view."""
    return {
        'id':              txn.id,
        'reference':       txn.reference,
        'amount':          float(txn.amount) if txn.amount else 0,
        'currency':        txn.currency or 'NGN',
        'status':          txn.status or 'pending',
        'payment_method':  txn.payment_method or 'paystack',
        'channel':         txn.payment_method or 'paystack',   # alias for frontend
        'plan_id':         txn.plan_id,
        'plan_name':       txn.plan.name if getattr(txn, 'plan', None) else None,
        'user_id':         txn.user_id,
        'created_at':      txn.created_at.isoformat() if txn.created_at else None,
        'updated_at':      txn.updated_at.isoformat() if txn.updated_at else None,
    }


@transactions_bp.route('/transactions', methods=['GET'])
@jwt_required(optional=True)
@limiter.exempt
def get_transactions():
    """
    GET /api/transactions?page=1&per_page=10&status=success
    
    Returns paginated transaction history.
    Regular users see only their own; admins see all.
    """
    try:
        page      = request.args.get('page',      default=1,  type=int)
        per_page  = request.args.get('per_page',  default=10, type=int)
        status    = request.args.get('status',    default='', type=str).strip().lower()

        if not current_user:
            return error_response("Authentication required.", status_code=401)

        query = Transaction.query

        # Scope: non-admins see only their own transactions
        is_admin = getattr(current_user, 'is_admin', lambda: False)()
        if not is_admin:
            query = query.filter_by(user_id=current_user.id)

        # Optional status filter
        if status:
            query = query.filter(func.lower(Transaction.status) == status)

        # Order newest first
        query = query.order_by(Transaction.created_at.desc())

        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        records = [_txn_summary(t) for t in paginated.items]

        return success_response("Transactions fetched successfully", data={
            "transactions": records,
            "pagination": {
                "page":        paginated.page,
                "per_page":    paginated.per_page,
                "total":       paginated.total,
                "total_pages": paginated.pages,
                "has_next":    paginated.has_next,
                "has_prev":    paginated.has_prev,
                "next_num":    paginated.next_num,
                "prev_num":    paginated.prev_num,
            }
        })

    except Exception as e:
        traceback.print_exc()
        return error_response(str(e), status_code=500)


@transactions_bp.route('/transactions/summary', methods=['GET'])
@jwt_required(optional=True)
@limiter.exempt
def get_transactions_summary():
    """
    GET /api/transactions/summary
    
    Returns aggregated stats:
    {
      "success":  {"count": 5, "total_amount": 50000},
      "pending":  {"count": 2, "total_amount": 20000},
      "failed":   {"count": 1, "total_amount": 10000}
    }
    
    Regular users see only their own summary; admins see global.
    """
    try:
        if not current_user:
            return error_response("Authentication required.", status_code=401)

        is_admin = getattr(current_user, 'is_admin', lambda: False)()
        base_query = db.session.query(Transaction)

        if not is_admin:
            base_query = base_query.filter(Transaction.user_id == current_user.id)

        # Aggregate by status
        stats = (
            base_query
            .with_entities(
                func.lower(Transaction.status).label('status'),
                func.count(Transaction.id).label('count'),
                func.coalesce(func.sum(Transaction.amount), 0).label('total_amount')
            )
            .group_by(func.lower(Transaction.status))
            .all()
        )

        # Normalize keys so frontend can read success/successful/pending/failed/failure
        result = {}
        for row in stats:
            key = row.status or 'unknown'
            # Map 'successful' -> 'success' for frontend consistency
            if key == 'successful':
                key = 'success'
            elif key == 'failure':
                key = 'failed'

            result[key] = {
                'count':        int(row.count),
                'total_amount': float(row.total_amount or 0)
            }

        # Ensure all expected keys exist (frontend checks these)
        for key in ('success', 'pending', 'failed'):
            if key not in result:
                result[key] = {'count': 0, 'total_amount': 0.0}

        return success_response("Transaction summary fetched successfully", data=result)

    except Exception as e:
        traceback.print_exc()
        return error_response(str(e), status_code=500)

