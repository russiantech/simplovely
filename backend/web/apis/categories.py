"""Catalogue categories: public reads, admin-only writes."""
from flask import request
from sqlalchemy import desc

from web.apis import api_bp as category_bp
from web.apis.models.categories import Category
from web.apis.models.products import Product
from web.apis.utils.decorators import admin_required
from web.apis.utils.serializers import PageSerializer, error_response, get_pagination, success_response
from web.extensions import db


def _json():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _by_ref(ref, include_deleted=False):
    query = Category.query.filter(Category.id == int(ref)) if str(ref).isdigit() else Category.query.filter(Category.slug == str(ref))
    if not include_deleted:
        query = query.filter(Category.is_deleted.is_(False))
    return query.first()


@category_bp.get("/categories")
def list_categories():
    page, size = get_pagination(50)
    query = Category.query.filter(Category.is_deleted.is_(False))
    if request.args.get("search"):
        query = query.filter(Category.name.ilike(f"%{request.args['search'].strip()}%"))
    paginated = query.order_by(desc(Category.created_at)).paginate(page=page, per_page=size, error_out=False)
    return success_response("Categories fetched successfully.", data=PageSerializer(pagination_obj=paginated, resource_name="categories").get_data())


@category_bp.get("/categories/<category_ref>")
@category_bp.get("/categories/<category_ref>/slug")
def category_detail(category_ref):
    category = _by_ref(category_ref)
    return success_response("Category fetched successfully.", data=category.get_summary()) if category else error_response("Category not found.", 404)


@category_bp.get("/categories/<int:category_id>/products")
def category_products(category_id):
    if not _by_ref(category_id):
        return error_response("Category not found.", 404)
    page, size = get_pagination(5)
    query = Product.query.filter(Product.categories.any(id=category_id), Product.is_deleted.is_(False)).order_by(desc(Product.created_at))
    paginated = query.paginate(page=page, per_page=size, error_out=False)
    return success_response("Category products fetched successfully.", data=PageSerializer(pagination_obj=paginated, resource_name="products").get_data())


def _fields(data, creating):
    name = str(data.get("name") or "").strip()
    if creating and not name:
        raise ValueError("Category name is required.")
    out = {}
    if name:
        out["name"] = name[:140]
    if "description" in data:
        out["description"] = (str(data.get("description") or "").strip() or None) and str(data["description"]).strip()[:255]
    if "parent_id" in data:
        parent_id = data["parent_id"] or None
        if parent_id is not None and not _by_ref(parent_id):
            raise ValueError("Parent category not found.")
        out["parent_id"] = int(parent_id) if parent_id is not None else None
    return out


@category_bp.post("/categories")
@admin_required
def create_category():
    try:
        fields = _fields(_json(), creating=True)
    except ValueError as exc:
        return error_response(str(exc))
    existing = Category.query.filter(db.func.lower(Category.name) == fields["name"].lower()).first()
    if existing and not existing.is_deleted:
        return error_response("A category with this name already exists.", 409)
    category = existing or Category(name=fields["name"])  # re-activate a previously deleted one
    for key, value in fields.items():
        setattr(category, key, value)
    category.is_deleted = False
    db.session.add(category)
    db.session.commit()
    return success_response("Category created successfully.", data=category.get_summary(), status_code=201)


@category_bp.route("/categories/<int:category_id>", methods=["PUT", "PATCH"])
@admin_required
def update_category(category_id):
    category = _by_ref(category_id)
    if not category:
        return error_response("Category not found.", 404)
    try:
        fields = _fields(_json(), creating=False)
        if fields.get("parent_id") == category.id:
            raise ValueError("A category cannot be its own parent.")
        if "name" in fields:
            clash = Category.query.filter(db.func.lower(Category.name) == fields["name"].lower(), Category.id != category.id).first()
            if clash:
                raise ValueError("A category with this name already exists.")
        for key, value in fields.items():
            setattr(category, key, value)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        return error_response(str(exc))
    return success_response("Category updated successfully.", data=category.get_summary())


@category_bp.delete("/categories/<int:category_id>")
@admin_required
def delete_category(category_id):
    category = _by_ref(category_id)
    if not category:
        return error_response("Category not found.", 404)
    if category.children.filter_by(is_deleted=False).count():
        return error_response("This category has subcategories. Delete or move them first.", 409)
    category.is_deleted = True
    db.session.commit()
    return success_response("Category deleted successfully.")
