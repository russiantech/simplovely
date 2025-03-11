from sqlalchemy import func, or_
from web.extensions import db

# class Transaction(db.Model):
#     __tablename__ = 'transactions'
    
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
#     user = db.relationship('User', back_populates='transactions')

#     amount = db.Column(db.Integer, nullable=False)
#     currency = db.Column(db.String(255), nullable=False, default='NGN')  # Set default currency
#     payment_method = db.Column(db.String(255), nullable=False)  # Added payment_method field
#     reference = db.Column(db.String(255), nullable=False)  # Added reference field
#     status = db.Column(db.String(50), nullable=False, default='pending')  # Added status field
#     description = db.Column(db.String(255))
    
#     product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
#     product = db.relationship('Product')
    
#     plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'))
#     plan = db.relationship('Plan')
    
#     service_id = db.Column(db.Integer, db.ForeignKey('services.id'))
#     service = db.relationship('Service')

#     is_deleted = db.Column(db.Boolean(), nullable=False, default=False)
#     created_at = db.Column(db.DateTime, nullable=False, default=func.now())
#     updated_at = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())

#     @staticmethod
#     def get_transaction(reference: str):
#         """
#         Static method to fetch a transaction from the database by refference or transaction ID.
        
#         Args:
#             username (str): The refference or transaction ID or to search for.
        
#         Returns:
#             Transaction: The transaction object if found, otherwise None.
        
#         Raises:
#             ValueError: If the refference is empty.
#         """
#         if not reference:
#             raise ValueError("refference cannot be empty")
        
#         # Attempt to fetch the transaction by either username or transaction ID or email
#         transaction = db.session.query(Transaction).filter(or_(Transaction.reference == reference, Transaction.id == reference)).first()
        
#         return transaction

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', back_populates='transactions')

    amount = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(255), nullable=False, default='NGN')  # Set default currency
    payment_method = db.Column(db.String(255), nullable=False)
    reference = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='pending')
    description = db.Column(db.String(255), nullable=True)

    service_id = db.Column(db.Integer, db.ForeignKey('services.id'))
    service = db.relationship('Service')

    is_deleted = db.Column(db.Boolean(), nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())

    def get_summary(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount': self.amount,
            'currency': self.currency,
            'payment_method': self.payment_method,
            'reference': self.reference,
            'status': self.status,
            'description': self.description,
            'service_id': self.service_id,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @staticmethod
    def get_transaction(reference: str):
        """
        Static method to fetch a transaction from the database by reference or transaction ID.
        
        Args:
            reference (str): The reference or transaction ID to search for.
        
        Returns:
            Transaction: The transaction object if found, otherwise None.
        
        Raises:
            ValueError: If the reference is empty.
        """
        if not reference:
            raise ValueError("Reference cannot be empty.")
        
        transaction = db.session.query(Transaction).filter(or_(Transaction.reference == reference, Transaction.id == reference)).first()
        
        if transaction is None:
            raise ValueError("Transaction not found.")
        
        return transaction
