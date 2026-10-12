from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func

from web.extensions import db


class Plan(db.Model):
    __tablename__ = "plans"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    amount = db.Column(db.Float, nullable=False, default=0.00)
    units = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.String(80), unique=True)
    is_deleted = db.Column(db.Boolean(), nullable=False, index=True, default=False)

    subscriptions = db.relationship("Subscription", back_populates="plan", lazy=True)

    created_at = db.Column(db.DateTime, nullable=False, index=True, default=func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())

    @property
    def amount_naira(self):
        """Price as whole naira (what we store on a Transaction and charge)."""
        return int(Decimal(str(self.amount or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    @property
    def amount_kobo(self):
        return self.amount_naira * 100

    def get_summary(self):
        return {
            "id": self.id,
            "name": self.name,
            "amount": self.amount,
            "units": self.units,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class Subscription(db.Model):
    """One row per user (unique ``user_id``): ``total_units`` is the *remaining* balance."""

    __tablename__ = "subscriptions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=False)
    total_units = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="active")

    user = db.relationship("User", back_populates="subscriptions")
    plan = db.relationship("Plan", back_populates="subscriptions")
    usage = db.relationship("Usage", back_populates="subscriptions", lazy=True)

    is_deleted = db.Column(db.Boolean(), nullable=False, index=True, default=False)
    created_at = db.Column(db.DateTime, nullable=False, index=True, default=func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())

    @property
    def used_units(self):
        return sum(u.units_used for u in self.usage if not u.is_deleted)

    def refresh_status(self):
        self.status = "completed" if (self.total_units or 0) <= 0 else "active"

    @staticmethod
    def credit(user_id, plan, units=None):
        """Add units to the user's subscription (create it if needed). Caller commits.

        Row-locked so concurrent credits cannot lose an update.
        """
        units = plan.units if units is None else int(units)
        sub = Subscription.query.filter_by(user_id=user_id).with_for_update().first()
        if sub is None:
            sub = Subscription(user_id=user_id, plan_id=plan.id, total_units=units, status="active")
            db.session.add(sub)
        else:
            sub.plan_id = plan.id
            sub.total_units = (sub.total_units or 0) + units
            sub.is_deleted = False
        sub.refresh_status()
        db.session.flush()
        return sub

    def get_summary(self, include_plan=False, include_user=False):
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "plan_id": self.plan_id,
            "total_units": self.total_units,
            "status": self.status,
            "used_units": self.used_units,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_user and self.user:
            data["user"] = self.user.get_summary()
        if include_plan and self.plan:
            data["plan"] = self.plan.get_summary()
        return data


class Usage(db.Model):
    __tablename__ = "usage"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscriptions.id"))

    units_used = db.Column(db.Integer, nullable=False)
    total_units = db.Column(db.Integer, nullable=False)
    remaining_units = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="active")

    subscriptions = db.relationship("Subscription", back_populates="usage", lazy=True)
    user = db.relationship("User", back_populates="usage")

    is_deleted = db.Column(db.Boolean(), nullable=False, index=True, default=False)
    created_at = db.Column(db.DateTime, nullable=False, index=True, default=func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())

    def usage_percentage(self):
        return (self.units_used / self.total_units) * 100 if self.total_units else 0

    def get_summary(self, include_user=False):
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "subscription_id": self.subscription_id,
            "units_used": self.units_used,
            "remaining_units": self.remaining_units,
            "total_units": self.total_units,
            "available_units": self.subscriptions.total_units if self.subscriptions else 0,
            "status": self.status,
            "usage_percentage": self.usage_percentage(),
            "is_deleted": self.is_deleted,
            "created_at": self.created_at,
        }
        if include_user and self.user:
            data["user"] = self.user.get_summary()
        return data
