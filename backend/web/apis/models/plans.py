from sqlalchemy import func, or_
from sqlalchemy import func, event
from web.extensions import db

class Plan(db.Model):
    __tablename__ = 'plans'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    amount = db.Column(db.Float, nullable=False, default=0.00)
    units = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.String(80), unique=True)
    is_deleted = db.Column(db.Boolean(), nullable=False, index=True, default=False)
    
    subscriptions = db.relationship('Subscription', back_populates='plan', lazy=True)

    created_at = db.Column(db.DateTime, nullable=False, index=True, default=func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())

    @staticmethod
    def get_plan(plan_id: str):
        """
        Static method to fetch a user from the database by plan_id or user ID.
        
        Args:
            plan_id (str): The plan_id or user ID to search for.
        
        Returns:
            Plan: The user object if found, otherwise None.
        
        Raises:
            ValueError: If the plan_id is empty.
        """
        if not plan_id:
            raise ValueError("Plan name/id cannot be empty")
        
        # Attempt to fetch the user by either plan_id or user ID
        plan = db.session.query(Plan).filter(or_(Plan.id == plan_id, Plan.name == plan_id)).first()
        
        return plan
    
    def get_summary(self):
        return {
            'id': self.id,
            'name': self.name,
            'amount': self.amount,
            'units': self.units,
            'description': self.description,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    # user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'), nullable=False)
    total_units = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='active')
    
    user = db.relationship('User', back_populates='subscriptions')
    plan = db.relationship('Plan', back_populates='subscriptions')
    usage = db.relationship('Usage', back_populates='subscriptions', lazy=True)
    
    is_deleted = db.Column(db.Boolean(), nullable=False, index=True, default=False)
    created_at = db.Column(db.DateTime, nullable=False, index=True, default=func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())

    @property
    def used_units(self):
        """Calculate the total units used based on Usage records."""
        return sum(usage.units_used for usage in self.usage)
    
    def update_status(self):
        """Update the status based on the remaining units. Only update status if it's running."""
        if self.total_units <= 0:
            if self.status != 'completed':  # Check to prevent unnecessary updates
                self.status = 'completed'

    def get_summary(self, include_plan=False, include_user=False):
        """Generate a summary of the subscription instance."""

        data = {
            'id': self.id,
            'user_id': self.user_id,
            'plan_id': self.plan_id,
            "total_units": self.total_units,
            "status": self.status,
            "used_units": self.used_units,  # Call the dynamic method
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

        if include_user:
            data['user'] = self.user.get_summary()
            
        if include_plan:
            data['plan'] = self.plan.get_summary()
        
        return data

class Usage(db.Model):
    __tablename__ = 'usage'
    id = db.Column(db.Integer, primary_key=True)
    # user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'))
    
    units_used = db.Column(db.Integer, nullable=False)
    total_units = db.Column(db.Integer, nullable=False)
    remaining_units = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='active')
    
    subscriptions = db.relationship('Subscription', back_populates='usage', lazy=True)
    user = db.relationship('User', back_populates='usage')
    
    is_deleted = db.Column(db.Boolean(), nullable=False, index=True, default=False)
    created_at = db.Column(db.DateTime, nullable=False, index=True, default=func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())

    def update_status(self):
        """Update the status based on the remaining units."""
        if self.remaining_units <= 0:
            self.status = 'completed'

    def calculate_usage_percentage(self):
        """Calculate the percentage of units used."""
        if self.total_units > 0:
            return (self.units_used / self.total_units) * 100
        return 0
    
    def get_summary(self, include_user=False):
        """Generate a summary of the usage instance."""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'user': self.user.get_summary(),
            'subscription_id': self.subscription_id,
            'units_used': self.units_used,
            'remaining_units': self.remaining_units,
            "total_units": self.total_units,
            "available_units": self.subscriptions.total_units,
            "status": self.status,
            'usage_percentage': self.calculate_usage_percentage(),
            'is_deleted': self.is_deleted,
            'created_at': self.created_at,
        }

        if self.user and include_user:
            data['user'] = self.user.get_summary()
        
        return data

@event.listens_for(Usage.status, 'set')
def receive_set(target, value, oldvalue, initiator):
    target.status = "finished" if target.subscriptions.total_units <= 0 else "active"
    
# @event.listens_for(Tag.name, 'set')
# def receive_set(target, value, oldvalue, initiator):
#     target.slug = slugify(str(value))
