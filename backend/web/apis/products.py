"""Fashion catalogue: public reads, admin-only writes."""
import logging
import re

from flask import request
from sqlalchemy import desc, func

from web.apis import api_bp as product_bp
from web.apis.models.categories import Category, products_categories
from web.apis.models.file_uploads import ProductImage
from web.apis.models.products import Product
from web.apis.models.tags import Tag
from web.apis.utils.decorators import admin_required
from web.apis.utils.get_or_create import get_or_create
from web.apis.utils.helpers import to_bool, validate_file_upload
from web.apis.utils.serializers import PageSerializer, error_response, get_pagination, success_response
from web.apis.utils.uploader import uploader
from web.extensions import db

log = logging.getLogger("web")
_INDEXED = re.compile(r"^(tags|categories)\[(\d+)\]\[(name|description)\]$")


# ------------------------------------------------------------------ helpers
def _payload():
    """JSON body or multipart form as a plain dict."""
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


def _named_items(data, key):
    """Collect ``[{name, description}]`` from JSON lists or ``key[0][name]`` form fields."""
    items = {}
    for field, value in data.items():
        m = _INDEXED.match(field)
        if m and m.group(1) == key:
            items.setdefault(int(m.group(2)), {})[m.group(3)] = str(value).strip()
    found = [items[i] for i in sorted(items) if items[i].get("name")]
    json_list = data.get(key)
    if not found and isinstance(json_list, list):
        found = [{"name": str(i.get("name") or "").strip(), "description": i.get("description")} for i in json_list if isinstance(i, dict) and i.get("name")]
    return found


def _resolve(model, entries):
    return [get_or_create(db.session, model, {"description": (e.get("description") or e["name"])[:255]}, name=e["name"][:140])[0] for e in entries]


def _number(data, key, default=None, minimum=0):
    if key not in data or data[key] in (None, ""):
        return default
    try:
        value = int(float(data[key]))
    except (TypeError, ValueError):
        raise ValueError(f"{key.title()} must be a number.")
    if value < minimum:
        raise ValueError(f"{key.title()} cannot be negative.")
    return value


def _save_images(product, files):
    for storage in files:
        if not storage or not storage.filename:
            continue
        if not validate_file_upload(storage.filename):
            raise ValueError(f"Unsupported file type: {storage.filename}")
        url, path = uploader.save(storage)
        import os

        db.session.add(ProductImage(product=product, file_path=url, file_name=os.path.basename(path), original_name=storage.filename[:140], file_size=os.path.getsize(path)))


def _remove_image(image):
    uploader.delete_local(image.file_path)
    db.session.delete(image)


def _active_products():
    return Product.query.filter(Product.is_deleted.is_(False))


def _page(query, message="Products fetched successfully.", default_size=20):
    page, size = get_pagination(default_size)
    paginated = query.order_by(desc(Product.created_at)).paginate(page=page, per_page=size, error_out=False)
    return success_response(message, data=PageSerializer(pagination_obj=paginated, resource_name="products").get_data())


def _category(ref):
    return Category.query.filter(Category.id == int(ref)).first() if str(ref).isdigit() else Category.query.filter(Category.slug == str(ref)).first()


# -------------------------------------------------------------------- reads
@product_bp.get("/products")
def products():
    query = _active_products()
    category_id, category_name, term = request.args.get("category_id", type=int), request.args.get("category"), (request.args.get("search") or "").strip()
    if category_id:
        query = query.join(products_categories).filter(products_categories.c.category_id == category_id)
    elif category_name:
        query = query.join(products_categories).join(Category).filter(Category.name.ilike(f"%{category_name}%"))
    if term:
        query = query.filter(Product.name.ilike(f"%{term}%"))
    if request.args.get("exclude", type=int):
        query = query.filter(Product.id != request.args.get("exclude", type=int))
    return _page(query)


@product_bp.get("/products/by-categories")
def get_products_by_categories():
    page, per_page = get_pagination(2, ("per_page", "page_size"))

    def tree(category):
        items = _active_products().join(products_categories).filter(products_categories.c.category_id == category.id).order_by(Product.created_at.desc()).limit(8).all()
        subs = Category.query.filter_by(parent_id=category.id, is_deleted=False).limit(per_page * 5).all()
        return {"id": category.id, "name": category.name, "slug": category.slug, "products": [p.get_summary() for p in items], "subcategories": [tree(s) for s in subs]}

    top = (
        Category.query.filter_by(parent_id=None, is_deleted=False).join(products_categories).group_by(Category.id)
        .having(func.count(products_categories.c.product_id) >= 1).paginate(page=page, per_page=per_page, error_out=False)
    )
    meta = {
        "current_page_number": top.page, "has_next_page": top.has_next, "has_prev_page": top.has_prev, "offset": (top.page - 1) * per_page,
        "requested_page_size": per_page, "total_items_count": top.total, "total_pages_count": top.pages,
    }
    return success_response("Products by categories fetched successfully.", data={"categories": [tree(c) for c in top.items], "page_meta": meta})


@product_bp.get("/products/<product_id>")
@product_bp.get("/products/<product_id>/slug")
def by_id(product_id):
    product = Product.get_product(product_id)
    return success_response("Product fetched successfully.", data=product.get_summary()) if product else error_response("Product not found.", 404)


@product_bp.get("/products/<int:user_id>/user")
def by_user(user_id):
    return _page(_active_products().filter(Product.users.any(id=user_id)), "User products fetched successfully.")


@product_bp.get("/products/<page_id>/page")
def by_page(page_id):
    if not str(page_id).isdigit():
        return error_response("Invalid page id.")
    return _page(_active_products().filter(Product.pages.any(id=int(page_id))), "Page products fetched successfully.")


@product_bp.get("/products/<category_ref>/category")
def by_category(category_ref):
    category = _category(category_ref)
    if not category or category.is_deleted:
        return error_response("Category not found.", 404)
    ids = [category.id] + [c.id for c in category.children.filter_by(is_deleted=False)]  # include direct subcategories
    query = _active_products().join(products_categories).filter(products_categories.c.category_id.in_(ids)).distinct()
    return _page(query, f"Products in {category.name} fetched successfully.")


# ------------------------------------------------------------------- writes
def _apply(product, data, creating):
    if creating or "name" in data:
        name = str(data.get("name") or "").strip()
        if not name:
            raise ValueError("Product name is required.")
        product.name = name[:255]
    if creating or "description" in data:
        product.description = (data.get("description") or "").strip() or None
    product.price = _number(data, "price", default=0 if creating else product.price)
    product.stock = _number(data, "stock", default=0 if creating else product.stock)
    if "is_deleted" in data:
        product.is_deleted = to_bool(data["is_deleted"])
    categories, tags = _named_items(data, "categories"), _named_items(data, "tags")
    if categories:
        product.categories = _resolve(Category, categories)
    if tags:
        product.tags = _resolve(Tag, tags)


@product_bp.post("/products")
@admin_required
def create():
    data = _payload()
    if not data:
        return error_response("No data received to publish your product.")
    product = Product(price=0, stock=0)
    try:
        _apply(product, data, creating=True)
        db.session.add(product)
        _save_images(product, request.files.getlist("images[]") + request.files.getlist("images"))
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        return error_response(str(exc))
    return success_response("Product created successfully", data=product.get_summary(), status_code=201)


@product_bp.route("/products/<product_ref>", methods=["PUT", "PATCH"])
@admin_required
def update(product_ref):
    product = Product.get_product(product_ref)
    if not product:
        return error_response("Product not found.", 404)
    data = _payload()
    try:
        _apply(product, data, creating=False)
        # Optional image management used by the admin editor
        action = data.get("image_action")
        keep = set(request.form.getlist("keep_images[]")) if request.form else set(map(str, data.get("keep_images", []) or []))
        if action == "replace":
            for image in product.images.all():
                if str(image.id) not in keep:
                    _remove_image(image)
        _save_images(product, request.files.getlist("images[]") + request.files.getlist("images"))
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        return error_response(str(exc))
    return success_response("Product updated successfully", data=product.get_summary())


@product_bp.delete("/products/<product_ref>")
@admin_required
def destroy(product_ref):
    """Soft delete: order/comment history keeps pointing at a real row."""
    product = Product.get_product(product_ref)
    if not product:
        return error_response("Product not found.", 404)
    product.is_deleted = True
    db.session.commit()
    return success_response("Product deleted successfully.")


@product_bp.delete("/products/<int:pro_id>/images")
@admin_required
def delete_all_media(pro_id):
    product = db.session.get(Product, pro_id)
    if not product:
        return error_response("Product not found.", 404)
    removed = 0
    for image in product.images.all():
        _remove_image(image)
        removed += 1
    db.session.commit()
    return success_response(f"{removed} image(s) deleted successfully.")


@product_bp.delete("/products/<int:pro_id>/images/<int:img_id>")
@admin_required
def delete_media(pro_id, img_id):
    image = ProductImage.query.filter_by(id=img_id, product_id=pro_id).first()  # must belong to this product
    if not image:
        return error_response("Image not found for this product.", 404)
    _remove_image(image)
    db.session.commit()
    return success_response("Image deleted successfully.")
