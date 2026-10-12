from sqlalchemy import func

from web.extensions import db

SUCCESS = "success"
PENDING = "pending"
FAILED = "failed"
ABANDONED = "abandoned"
SUCCESS_STATES = {"success", "successful"}


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = db.relationship("User", back_populates="transactions")

    amount = db.Column(db.Integer, nullable=False)  # whole naira, frozen at initialisation
    currency = db.Column(db.String(255), nullable=False, default="NGN")
    payment_method = db.Column(db.String(255), nullable=False)
    reference = db.Column(db.String(255), nullable=False, unique=True, index=True)
    status = db.Column(db.String(50), nullable=False, default=PENDING)
    description = db.Column(db.String(255), nullable=True)

    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"))
    plan = db.relationship("Plan")

    service_id = db.Column(db.Integer, db.ForeignKey("services.id"))
    service = db.relationship("Service")

    is_deleted = db.Column(db.Boolean(), nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())

    @property
    def is_success(self):
        return (self.status or "").lower() in SUCCESS_STATES

    def get_summary(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": self.amount,
            "currency": self.currency,
            "payment_method": self.payment_method,
            "reference": self.reference,
            "status": self.status,
            "description": self.description,
            "service_id": self.service_id,
            "plan_id": self.plan_id,
            "plan_name": self.plan.name if self.plan else None,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def get_by_reference(reference, lock=False):
        """Exact-reference lookup (never by id). ``lock`` takes a row lock for safe settlement."""
        if not reference:
            return None
        query = Transaction.query.filter_by(reference=str(reference).strip())
        return (query.populate_existing().with_for_update() if lock else query).first()
