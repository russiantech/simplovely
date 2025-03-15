from flask import request
from flask_jwt_extended import jwt_required, current_user
from sqlalchemy.exc import IntegrityError
from web.apis.utils.decorators import access_required
from web.apis.models.services import Area, Service, ServiceCategory, ServiceRequest
from web.extensions import db
from web.apis.utils.serializers import success_response, error_response, PageSerializer
from web.apis import api_bp as categories_bp

# Get all service categories
@categories_bp.route('/service-categories', methods=['GET'])
@jwt_required(optional=True)
def get_service_categories():
    try:
        categories = ServiceCategory.query.filter_by(is_deleted=False).all()
        categories = PageSerializer(items=categories, resource_name="service_categories").get_data()
        return success_response("Service categories fetched successfully", data=categories)
    except Exception as e:
        return error_response(str(e))

# Create a new service category
@categories_bp.route('/service-categories', methods=['POST'])
@jwt_required()
@access_required('admin', 'dev')
def create_service_category():
    try:
        data = request.json
        if not data.get('name'):
            return error_response("Name is required.")

        new_category = ServiceCategory(name=data['name'])
        db.session.add(new_category)
        db.session.commit()
        return success_response("Service category created successfully", data=new_category.get_summary(), status_code=201)

    except IntegrityError:
        db.session.rollback()
        return error_response("Service category already exists.")
    
    except Exception as e:
        db.session.rollback()
        return error_response(str(e))

# Update a service category
@categories_bp.route('/service-categories/<int:category_id>', methods=['PUT'])
@jwt_required()
@access_required('admin', 'dev')
def update_service_category(category_id):
    try:
        category = ServiceCategory.query.filter_by(id=category_id, is_deleted=False).first()
        if not category:
            return error_response("Service category not found", 404)

        data = request.json
        category.name = data.get('name', category.name)
        db.session.commit()

        return success_response("Service category updated successfully", data=category.get_summary())
    
    except Exception as e:
        return error_response(str(e))

# Delete a service category (soft delete)
@categories_bp.route('/service-categories/<int:category_id>', methods=['DELETE'])
@jwt_required()
@access_required('admin', 'dev')
def delete_service_category(category_id):
    try:
        category = ServiceCategory.query.filter_by(id=category_id, is_deleted=False).first()
        if not category:
            return error_response("Service category not found", 404)

        category.is_deleted = True
        db.session.commit()
        return success_response(None, "Service category deleted successfully")
    except Exception as e:
        return error_response(str(e))


# ++++++++++++++++++++++++++ SERVICE +++++++++++++++++++

from web.apis import api_bp as services_bp

# Get all services
@services_bp.route('/services', methods=['GET'])
@jwt_required(optional=True)
def get_services():
    try:
        services = Service.query.filter_by(is_deleted=False).all()
        services = PageSerializer(items=services, resource_name="services").get_data()
        return success_response("Services fetched successfully", data=services)
    except Exception as e:
        return error_response(str(e))

# Create a new service
@services_bp.route('/services', methods=['POST'])
@jwt_required()
@access_required('admin', 'dev')
def create_service():
    try:
        data = request.json
        if not all(key in data for key in ['name', 'image', 'description', 'link', 'category_id']):
            return error_response("Must provide all required fields: name, image, description, link, category_id.")

        new_service = Service(
            name=data['name'],
            image=data['image'],
            description=data['description'],
            link=data['link'],
            icon=data.get('icon'),
            category_id=data['category_id']
        )
        db.session.add(new_service)
        db.session.commit()
        return success_response("Service created successfully", data=new_service.get_summary(), status_code=201)

    except IntegrityError:
        db.session.rollback()
        return error_response("Service already exists.")
    
    except Exception as e:
        db.session.rollback()
        return error_response(str(e))

# Update a service
@services_bp.route('/services/<int:service_id>', methods=['PUT'])
@jwt_required()
@access_required('admin', 'dev')
def update_service(service_id):
    try:
        service = Service.query.filter_by(id=service_id, is_deleted=False).first()
        if not service:
            return error_response("Service not found", 404)

        data = request.json
        service.name = data.get('name', service.name)
        service.image = data.get('image', service.image)
        service.description = data.get('description', service.description)
        service.link = data.get('link', service.link)
        service.icon = data.get('icon', service.icon)
        service.category_id = data.get('category_id', service.category_id)
        db.session.commit()

        return success_response("Service updated successfully", data=service.get_summary())
    
    except Exception as e:
        return error_response(str(e))

# Delete a service (soft delete)
@services_bp.route('/services/<int:service_id>', methods=['DELETE'])
@jwt_required()
@access_required('admin', 'dev')
def delete_service(service_id):
    try:
        service = Service.query.filter_by(id=service_id, is_deleted=False).first()
        if not service:
            return error_response("Service not found", 404)

        service.is_deleted = True
        db.session.commit()
        return success_response(None, "Service deleted successfully")
    except Exception as e:
        return error_response(str(e))

# 
# INSERT SERVICES DIRECTLY
@services_bp.route('/insert-services', methods=['GET'])
# @jwt_required(optional=True)
# @access_required('admin', 'dev')
def populate_services():
    try:
        laundry_category = ServiceCategory(name='Laundry')
        fashion_category = ServiceCategory(name='Fashion')

        laundry_services = [
            {
                'name': 'Dry Cleaning',
                'image': './static/img/laundry/services/dry-cleaning.png',
                'description': 'Professional dry cleaning service.',
                'link': './laundry',
                'icon': None
            },
            {
                'name': 'Stain Removal',
                'image': './static/img/laundry/services/stain-remover.png',
                'description': 'Remove tough stains from your clothes.',
                'link': './laundry',
                'icon': None
            },
            {
                'name': 'Iron Only',
                'image': './static/img/laundry/services/ironing.png',
                'description': 'Ironing service for your clothes.',
                'link': './laundry',
                'icon': 'fi-dresser'
            },
            {
                'name': 'Wash & Iron',
                'image': './static/img/laundry/services/iron-board.png',
                'description': 'Wash and ironing services combined.',
                'link': './laundry',
                'icon': 'fi-package'
            },
            {
                'name': 'Volume Subscription (Enjoy-discount)',
                'image': './static/img/laundry/services/transaction.png',
                'description': 'Get a discount with volume subscriptions.',
                'link': './laundry',
                'icon': 'fi-gift'
            },
            {
                'name': 'Adjustment & Alterations',
                'image': './static/img/laundry/services/sewing-machine.png',
                'description': 'Alterations and adjustments for your clothes.',
                'link': './laundry',
                'icon': 'fi-scissors'
            },
            {
                'name': 'Pick-up & Delivery',
                'image': './static/img/laundry/services/pickup.png',
                'description': 'Convenient pick-up and delivery service.',
                'link': './laundry',
                'icon': 'fi-bicycle'
            }
        ]

        fashion_services = [
            {
                "name": "Men's Ankaras",
                'image': './static/img/fashion/02.jpg',
                "description": "Stylish men's Ankaras.",
                "link": "./fashion",
                "icon": None
            },
            {
                "name": "Women Ankaras",
                'image': './static/img/fashion/services/women_native.jpg',
                "description": "Elegant women's Ankaras.",
                "link": "./fashion",
                "icon": None
            },
            {
                "name": "Children Natives",
                'image': './static/img/fashion/03.jpg',
                "description": "Traditional outfits for children.",
                "link": "./fashion",
                "icon": None
            },
            {
                "name": "Men's Native Clothes",
                'image': './static/img/fashion/02.jpg',
                "description": "Classic men's native attire.",
                "link": "./fashion",
                "icon": None
            }
        ]

        # Add laundry services
        for service in laundry_services:
            new_service = Service(
                name=service['name'],
                image=service['image'],
                description=service['description'],
                link=service['link'],
                icon=service['icon'],
                category=laundry_category  # Reference the committed category
            )
            db.session.add(new_service)

        # Add fashion services
        for service in fashion_services:
            new_service = Service(
                name=service['name'],
                image=service['image'],
                description=service['description'],
                link=service['link'],
                icon=service['icon'],
                category=fashion_category  # Reference the committed category
            )
            db.session.add(new_service)

        db.session.commit()  # Commit all services at once

        return success_response(None, "Services populated successfully")

        return success_response(None, "Service category deleted successfully")
    except Exception as e:
        return error_response(str(e))


# ++++++++++++++++++++++++++ SERVICE REQUESTS +++++++++++++++++++
from web.apis import api_bp as requests_bp

# Get all service requests
@requests_bp.route('/service-requests', methods=['GET'])
@jwt_required(optional=True)
def get_service_requests():
    try:
        requests = ServiceRequest.query.filter_by(is_deleted=False).all()
        requests = PageSerializer(items=requests, resource_name="service_requests").get_data()
        return success_response("Service requests fetched successfully", data=requests)
    except Exception as e:
        return error_response(str(e))

# Create a new service request
@requests_bp.route('/service-requests', methods=['POST'])
@jwt_required()
def create_service_request():
    try:
        data = request.json
        if not all(key in data for key in ['name', 'phone', 'email', 'quantity', 'address', 'area_id', 'service_id']):
            return error_response("Must provide all required fields.")

        new_request = ServiceRequest(
            name=data['name'],
            phone=data['phone'],
            email=data['email'],
            quantity=data['quantity'],
            address=data['address'],
            area_id=data['area_id'],
            service_id=data['service_id']
        )
        db.session.add(new_request)
        db.session.commit()
        return success_response("Service request created successfully", data=new_request.get_summary(), status_code=201)

    except IntegrityError:
        db.session.rollback()
        return error_response("Service request already exists.")
    
    except Exception as e:
        db.session.rollback()
        return error_response(str(e))

# Update a service request
@requests_bp.route('/service-requests/<int:request_id>', methods=['PUT'])
@jwt_required()
def update_service_request(request_id):
    try:
        request = ServiceRequest.query.filter_by(id=request_id, is_deleted=False).first()
        if not request:
            return error_response("Service request not found", 404)

        data = request.json
        request.name = data.get('name', request.name)
        request.phone = data.get('phone', request.phone)
        request.email = data.get('email', request.email)
        request.quantity = data.get('quantity', request.quantity)
        request.address = data.get('address', request.address)
        request.area_id = data.get('area_id', request.area_id)
        request.service_id = data.get('service_id', request.service_id)
        request.status = data.get('status', request.status)
        db.session.commit()

        return success_response("Service request updated successfully", data=request.get_summary())
    
    except Exception as e:
        return error_response(str(e))

# Delete a service request (soft delete)
@requests_bp.route('/service-requests/<int:request_id>', methods=['DELETE'])
@jwt_required()
def delete_service_request(request_id):
    try:
        request = ServiceRequest.query.filter_by(id=request_id, is_deleted=False).first()
        if not request:
            return error_response("Service request not found", 404)

        request.is_deleted = True
        db.session.commit()
        return success_response(None, "Service request deleted successfully")
    except Exception as e:
        return error_response(str(e))


# ++++++++++++++++++ AREA API ++++++++++++++++++++

from web.apis import api_bp as areas_bp

# Get all areas
@areas_bp.route('/areas', methods=['GET'])
# @jwt_required(optional=True)
def get_areas():
    try:
        areas = Area.query.filter_by(is_deleted=False).all()
        areas = PageSerializer(items=areas, resource_name="areas").get_data()
        return success_response("Areas fetched successfully", data=areas)
    except Exception as e:
        return error_response(str(e))

# Create a new area
@areas_bp.route('/areas', methods=['POST'])
@jwt_required()
@access_required('admin', 'dev')
def create_area():
    try:
        data = request.json
        if not all(key in data for key in ['name', 'price']):
            return error_response("Must provide both name and price.")

        new_area = Area(
            name=data['name'],
            price=data['price']
        )
        db.session.add(new_area)
        db.session.commit()
        return success_response("Area created successfully", data=new_area.get_summary(), status_code=201)

    except IntegrityError:
        db.session.rollback()
        return error_response("Area with this name already exists.")
    
    except Exception as e:
        db.session.rollback()
        return error_response(str(e))

# Update an area
@areas_bp.route('/areas/<int:area_id>', methods=['PUT'])
@jwt_required()
@access_required('admin', 'dev')
def update_area(area_id):
    try:
        area = Area.query.filter_by(id=area_id, is_deleted=False).first()
        if not area:
            return error_response("Area not found", 404)

        data = request.json
        area.name = data.get('name', area.name)
        area.price = data.get('price', area.price)
        db.session.commit()

        return success_response("Area updated successfully", data=area.get_summary())
    
    except Exception as e:
        return error_response(str(e))

# Delete an area (soft delete)
@areas_bp.route('/areas/<int:area_id>', methods=['DELETE'])
@jwt_required()
@access_required('admin', 'dev')
def delete_area(area_id):
    try:
        area = Area.query.filter_by(id=area_id, is_deleted=False).first()
        if not area:
            return error_response("Area not found", 404)

        area.is_deleted = True
        db.session.commit()
        return success_response(None, "Area deleted successfully")
    except Exception as e:
        return error_response(str(e))

# Define the areas and their prices
AREAS_WITH_PRICES = {
    "ajah": 2000,
    "vgc": 4000,
    "chevron": 3000,
    "lekki": 4000,
    "LBS": 10000,
    "Sangotedo": 13000,
    "Awoyaya": 11000,
    "Ado Road": 0,  # Placeholder for dynamic pricing if needed
    "Badore": 0,
    "adesanya": 0,
    "graceland": 0,
    "Scheme 2": 0,
    "ogombo": 0,
}

# Endpoint to save areas with their prices
@areas_bp.route('/insert-areas', methods=['POST', 'GET'])
# @jwt_required()
def save_areas():
    try:
        # data = request.json
        
        # # Validate required fields
        # required_fields = ['name', 'phone', 'email', 'quantity', 'address']
        # if not all(field in data for field in required_fields):
        #     return error_response("Must provide name, phone, email, quantity, and address.")

        # Iterate through the predefined areas and save them
        for area_name, price in AREAS_WITH_PRICES.items():
            if price > 0:  # Only save areas with defined prices
                new_area = Area(
                    name=area_name,
                    price=price
                )
                db.session.add(new_area)

        db.session.commit()
        
        return success_response("Areas saved successfully", status_code=201)
    
    except IntegrityError:
        db.session.rollback()
        return error_response("An error occurred while saving areas.")
    
    except Exception as e:
        db.session.rollback()
        return error_response(str(e))
