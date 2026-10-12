"""Laundry/fashion services catalogue, delivery areas and customer service requests."""
from flask import request
from flask_jwt_extended import current_user, jwt_required
from sqlalchemy import func

from web.apis import api_bp as bp
from web.apis.models.services import Area, Service, ServiceCategory, ServiceRequest
from web.apis.schemas.user import ValidationFailed, clean_email, clean_phone
from web.apis.utils.decorators import admin_required
from web.apis.utils.serializers import PageSerializer, error_response, get_pagination, success_response
from web.extensions import db, limiter

REQUEST_STATUSES = ("Pending", "Confirmed", "Picked Up", "In Progress", "Completed", "Cancelled")


def _json():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _listing(items, name, message):
    return success_response(message, data=PageSerializer(items=items, resource_name=name).get_data())


def _price(value):
    try:
        price = float(value)
    except (TypeError, ValueError):
        raise ValueError("Price must be a number.")
    if price < 0:
        raise ValueError("Price cannot be negative.")
    return price


# --------------------------------------------------------- service categories
@bp.get("/service-categories")
def get_service_categories():
    return _listing(ServiceCategory.query.order_by(ServiceCategory.name).all(), "service_categories", "Service categories fetched successfully")


@bp.post("/service-categories")
@admin_required
def create_service_category():
    name = str(_json().get("name") or "").strip()
    if not name:
        return error_response("Name is required.")
    category = ServiceCategory(name=name[:100])
    db.session.add(category)
    db.session.commit()
    return success_response("Service category created successfully", data=category.get_summary(), status_code=201)


@bp.route("/service-categories/<int:category_id>", methods=["PUT", "PATCH"])
@admin_required
def update_service_category(category_id):
    category = db.session.get(ServiceCategory, category_id)
    if not category:
        return error_response("Service category not found", 404)
    name = str(_json().get("name") or "").strip()
    if not name:
        return error_response("Name is required.")
    category.name = name[:100]
    db.session.commit()
    return success_response("Service category updated successfully", data=category.get_summary())


@bp.delete("/service-categories/<int:category_id>")
@admin_required
def delete_service_category(category_id):
    category = db.session.get(ServiceCategory, category_id)
    if not category:
        return error_response("Service category not found", 404)
    if Service.query.filter_by(category_id=category.id, is_deleted=False).count():
        return error_response("This category still has services. Remove or move them first.", 409)
    db.session.delete(category)
    db.session.commit()
    return success_response("Service category deleted successfully")


# ------------------------------------------------------------------ services
_SERVICE_FIELDS = ("name", "image", "description", "link")


@bp.get("/services")
def get_services():
    query = Service.query.filter_by(is_deleted=False)
    category = request.args.get("category_id", type=int)
    if category:
        query = query.filter_by(category_id=category)
    return _listing(query.order_by(Service.id).all(), "services", "Services fetched successfully")


@bp.post("/services")
@admin_required
def create_service():
    data = _json()
    missing = [f for f in (*_SERVICE_FIELDS, "category_id") if not data.get(f)]
    if missing:
        return error_response(f"Missing required fields: {', '.join(missing)}.")
    if not db.session.get(ServiceCategory, data["category_id"]):
        return error_response("Service category not found.", 404)
    service = Service(icon=data.get("icon"), category_id=data["category_id"], **{f: str(data[f])[:255] for f in _SERVICE_FIELDS})
    db.session.add(service)
    db.session.commit()
    return success_response("Service created successfully", data=service.get_summary(), status_code=201)


@bp.route("/services/<int:service_id>", methods=["PUT", "PATCH"])
@admin_required
def update_service(service_id):
    service = Service.query.filter_by(id=service_id, is_deleted=False).first()
    if not service:
        return error_response("Service not found", 404)
    data = _json()
    for field in (*_SERVICE_FIELDS, "icon"):
        if field in data:
            setattr(service, field, data[field])
    if data.get("category_id"):
        if not db.session.get(ServiceCategory, data["category_id"]):
            return error_response("Service category not found.", 404)
        service.category_id = data["category_id"]
    db.session.commit()
    return success_response("Service updated successfully", data=service.get_summary())


@bp.delete("/services/<int:service_id>")
@admin_required
def delete_service(service_id):
    service = Service.query.filter_by(id=service_id, is_deleted=False).first()
    if not service:
        return error_response("Service not found", 404)
    service.is_deleted = True
    db.session.commit()
    return success_response("Service deleted successfully")


# --------------------------------------------------------------------- areas
@bp.get("/areas")
def get_areas():
    return _listing(Area.query.filter_by(is_deleted=False).order_by(Area.name).all(), "areas", "Areas fetched successfully")


@bp.post("/areas")
@admin_required
def create_area():
    data = _json()
    name = str(data.get("name") or data.get("area_name") or "").strip()
    if not name:
        return error_response("Area name is required.")
    try:
        area = Area(name=name[:50], price=_price(data.get("price")))
    except ValueError as exc:
        return error_response(str(exc))
    db.session.add(area)
    db.session.commit()
    return success_response("Area created successfully", data=area.get_summary(), status_code=201)


@bp.route("/areas/<int:area_id>", methods=["PUT", "PATCH"])
@admin_required
def update_area(area_id):
    area = Area.query.filter_by(id=area_id, is_deleted=False).first()
    if not area:
        return error_response("Area not found", 404)
    data = _json()
    try:
        if data.get("name") or data.get("area_name"):
            area.name = str(data.get("name") or data.get("area_name")).strip()[:50]
        if "price" in data:
            area.price = _price(data["price"])
    except ValueError as exc:
        return error_response(str(exc))
    db.session.commit()
    return success_response("Area updated successfully", data=area.get_summary())


@bp.delete("/areas/<int:area_id>")
@admin_required
def delete_area(area_id):
    area = Area.query.filter_by(id=area_id, is_deleted=False).first()
    if not area:
        return error_response("Area not found", 404)
    area.is_deleted = True
    db.session.commit()
    return success_response("Area deleted successfully")


# ----------------------------------------------------------- service requests
def _request_fields(data):
    """Validate a customer service request. Raises ValueError/ValidationFailed with a friendly message."""
    name = str(data.get("name") or "").strip()
    address = str(data.get("address") or "").strip()
    if not name or not address:
        raise ValueError("Name and address are required.")
    try:
        quantity = int(data.get("quantity"))
    except (TypeError, ValueError):
        raise ValueError("Quantity must be a whole number.")
    if not 1 <= quantity <= 1000:
        raise ValueError("Quantity must be between 1 and 1000.")
    area = Area.query.filter_by(id=data.get("area_id"), is_deleted=False).first() if str(data.get("area_id") or "").isdigit() else None
    service = Service.query.filter_by(id=data.get("service_id"), is_deleted=False).first() if str(data.get("service_id") or "").isdigit() else None
    if not area:
        raise ValueError("Please choose a valid delivery area.")
    if not service:
        raise ValueError("Please choose a valid service.")
    phone = clean_phone(data.get("phone"))
    return {"name": name[:100], "phone": phone[:15], "email": clean_email(data.get("email"))[:100], "quantity": quantity, "address": address[:255], "area_id": area.id, "service_id": service.id}


def _request_summary(req):
    data = req.get_summary()
    data.update(area_name=req.area.name if req.area else None, delivery_fee=req.area.price if req.area else None, service_name=req.service.name if req.service else None)
    return data


@bp.get("/service-requests")
@jwt_required()
def get_service_requests():
    page, size = get_pagination(20)
    query = ServiceRequest.query.filter_by(is_deleted=False)
    if not current_user.is_admin:  # customers see only requests made with their own email
        query = query.filter(func.lower(ServiceRequest.email) == current_user.email.lower())
    paginated = query.order_by(ServiceRequest.created_at.desc()).paginate(page=page, per_page=size, error_out=False)
    data = PageSerializer(pagination_obj=paginated, resource_name="service_requests", summary_func=lambda r: _request_summary(r)).get_data()
    return success_response("Service requests fetched successfully", data=data)


@bp.post("/service-requests")
@limiter.limit("10 per hour")
@jwt_required(optional=True)
def create_service_request():
    """Open to visitors (the pickup form is on public pages); rate limited to deter spam."""
    try:
        fields = _request_fields(_json())
    except (ValueError, ValidationFailed) as exc:
        return error_response(str(exc))
    req = ServiceRequest(**fields)
    db.session.add(req)
    db.session.commit()
    return success_response("Your service request has been received! We'll be in touch shortly.", data=_request_summary(req), status_code=201)


@bp.route("/service-requests/<int:request_id>", methods=["PUT", "PATCH"])
@admin_required
def update_service_request(request_id):
    req = ServiceRequest.query.filter_by(id=request_id, is_deleted=False).first()
    if not req:
        return error_response("Service request not found", 404)
    data = _json()
    status = data.get("status")
    if status is not None and status not in REQUEST_STATUSES:
        return error_response(f"Status must be one of: {', '.join(REQUEST_STATUSES)}.")
    try:
        fields = _request_fields({**req.get_summary(), **data})
    except (ValueError, ValidationFailed) as exc:
        return error_response(str(exc))
    for key, value in fields.items():
        setattr(req, key, value)
    req.status = status or req.status
    db.session.commit()
    return success_response("Service request updated successfully", data=_request_summary(req))


@bp.delete("/service-requests/<int:request_id>")
@admin_required
def delete_service_request(request_id):
    req = ServiceRequest.query.filter_by(id=request_id, is_deleted=False).first()
    if not req:
        return error_response("Service request not found", 404)
    req.is_deleted = True
    db.session.commit()
    return success_response("Service request deleted successfully")
