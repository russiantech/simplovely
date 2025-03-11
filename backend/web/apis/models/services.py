from sqlalchemy import func, ForeignKey
from sqlalchemy.orm import relationship
from web.extensions import db

class Area(db.Model):
    __tablename__ = 'areas'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)

    is_deleted = db.Column(db.Boolean(), nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationship to ServiceRequest
    service_requests = relationship('ServiceRequest', back_populates='area')

    def get_summary(self):
        return {
            'id': self.id,
            'area_name': self.name,
            'price': self.price,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

class ServiceCategory(db.Model):
    __tablename__ = 'service_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    
    # Relationship to Service
    services = relationship('Service', back_populates='category')

    def get_summary(self):
        return {
            'id': self.id,
            'name': self.name,
        }

class Service(db.Model):
    __tablename__ = 'services'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255), nullable=False)
    icon = db.Column(db.String(50), nullable=True)

    is_deleted = db.Column(db.Boolean(), nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Foreign key to ServiceCategory
    category_id = db.Column(db.Integer, ForeignKey('service_categories.id'), nullable=False)
    
    # Relationship to ServiceRequest
    service_requests = relationship('ServiceRequest', back_populates='service')
    
    # Relationship to ServiceCategory
    category = relationship('ServiceCategory', back_populates='services')

    def get_summary(self):
        return {
            'id': self.id,
            'name': self.name,
            'image': self.image,
            'description': self.description,
            'link': self.link,
            'icon': self.icon,
            'category_id': self.category_id,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

class ServiceRequest(db.Model):
    __tablename__ = 'service_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    
    # Foreign keys to establish relationships
    area_id = db.Column(db.Integer, ForeignKey('areas.id'), nullable=False)
    service_id = db.Column(db.Integer, ForeignKey('services.id'), nullable=False)
    
    status = db.Column(db.String(20), default='Pending')

    is_deleted = db.Column(db.Boolean(), nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    area = relationship('Area', back_populates='service_requests')
    service = relationship('Service', back_populates='service_requests')

    def get_summary(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'quantity': self.quantity,
            'address': self.address,
            'area_id': self.area_id,
            'service_id': self.service_id,
            'status': self.status,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
