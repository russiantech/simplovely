from sqlalchemy import func, or_
from sqlalchemy import func, event
from web.extensions import db

class Plan(db.Model):
    __tablename__ = 'plans'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    amount = db.Column(db.Float, nullable=False)
    units = db.Column(db.Integer, nullable=False)
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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
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
    
    # @property
    # def used_units(self):
    #     # Assuming self.usage is a relationship to the Usage model
    #     # Calculate the total units used based on Usage records.
    #     return sum(usage.units_used for usage in self.usages)  # Ensure this references the correct relationship
    
    def remaining_units(self):
        """Calculate remaining units based on total units and used units."""
        return self.total_units - self.used_units
    
    # amapiano -x -x -x -x
    def update_status(self):
        """Update the status based on the remaining units."""
        if self.remaining_units() <= 0:
            self.status = 'completed'

    def get_summary(self, include_plan=False, include_user=False):
        """Generate a summary of the subscription instance."""
        # Only update status if it's running
        if self.status == 'active':
            self.update_status()
        
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'plan_id': self.plan_id,
            "total_units": self.total_units,
            "status": self.status,
            "used_units": self.used_units(),  # Call the dynamic method
            "remaining_units": self.remaining_units(),
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

        if include_user:
            data['user'] = self.user.get_summary()
            
        if include_plan:
            data['plan'] = self.plan.get_summary()
        
        return data

@event.listens_for(Subscription.status, 'set')
def receive_set(target, value, oldvalue, initiator):
    """Automatically update status when the status field is set."""
    if target.status == 'active':
        target.update_status()

""" class Usage_01(db.Model):
    __tablename__ = 'usage'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
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
    
    # def remaining_units(self):
    #     # Calculate remaining units based on total units and used units.
    #     # return self.subscriptions.total_units - self.used_units()
    #     return self.subscriptions.total_units - self.units_used

    def update_status(self):
        # Update the status based on the remaining units.
        if self.remaining_units() <= 0:
            self.subscriptions.status = 'completed'

    # 
    # def used_units(self):
    #     # Calculate the total units used based on Usage records.
    #     if self.subscriptions and self.subscriptions.usage:
    #         return sum(usage.units_used for usage in self.subscriptions.usage)
    #     return 0  # Default to 0 if no subscriptions or usage records

    # def remaining_units(self):
    #     # Calculate remaining units based on total units and used units.
    #     if self.subscriptions:
    #         total_units = self.subscriptions.total_units
    #         used_units = self.used_units()
    #         return total_units - used_units
    #     return 0  # Default to 0 if no subscriptions

    def get_summary(self, include_plan=False, include_user=False):
        # Generate a summary of the usage instance.
        data = {
            'id': self.id,
            'subscription_id': self.subscription_id,
            'units_used': self.units_used,
            'remaining_units': self.remaining_units,
            "total_units": self.total_units,
            "status": self.status,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at,
        }

        if include_user:
            data['user'] = self.subscriptions.user.get_summary()
            
        if include_plan:
            data['plan'] = self.subscriptions.plan.get_summary()
        
        return data """
    

class Usage(db.Model):
    __tablename__ = 'usage'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
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

    def get_summary(self):
        """Generate a summary of the usage instance."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'subscription_id': self.subscription_id,
            'units_used': self.units_used,
            'remaining_units': self.remaining_units,
            "total_units": self.total_units,
            "status": self.status,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at,
        }
