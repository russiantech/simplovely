import os
from pathlib import Path
import re
import traceback
from flask import current_app as app, request
from flask_jwt_extended import jwt_required, current_user
from jsonschema import ValidationError, validate
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc, exc, func
from werkzeug.utils import secure_filename
from web.apis.utils.uploader import uploader
from web.extensions import db, limiter
from web.apis.models.categories import Category, products_categories
from web.apis.models.pages import Page
from web.apis.models.tags import Tag
from web.apis.models.file_uploads import ProductImage
from web.apis.models.products import Product
from web.apis.schemas.product import product_schema
from web.apis.utils.get_or_create import get_or_create
from web.apis.utils.helpers import validate_file_upload
from web.apis.utils.serializers import PageSerializer, error_response, success_response
from web.apis import api_bp as product_bp

@product_bp.route('/products', methods=['GET'])
@jwt_required(optional=True)
@limiter.exempt
def products():
    """
    Retrieve a paginated list of products.

    Returns a list of products, paginated by the specified page and page size.
    If no products are found, an empty list is returned.

    :return: JSON response with paginated product data.
    """
    try:
        # Pagination parameters: Default page = 1, page_size = 5
        page = request.args.get('page', 1, type=int)  # Ensure 'page' is an integer
        page_size = request.args.get('page_size', 5, type=int)  # Ensure 'page_size' is an integer

        # 
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        category_id = request.args.get('category_id', type=int)
        category_name = request.args.get('category')

        query = Product.query

        if category_id:
            query = query.join(products_categories).filter(products_categories.c.category_id == category_id)
        elif category_name:
            query = query.join(products_categories).join(Category).filter(Category.name.ilike(f"%{category_name}%"))

        products = query.order_by(desc(Product.created_at)).paginate(page=page, per_page=page_size)
        #
        
        # Fetch products with pagination
        # products = Product.query.order_by(desc(Product.created_at)).paginate(page=page, per_page=page_size)

        # Serialize the paginated result using PageSerializer
        data = PageSerializer(pagination_obj=products, resource_name="products").get_data()
        
        return success_response("Products fetched successfully.", data=data)

    except Exception as e:
        
        # Handle any unexpected errors
        return error_response(f"An error occurred: {str(e)}", status_code=500)


# @product_bp.route('/products', methods=['GET'])
# @limiter.exempt
# def get_products():
#     page = request.args.get('page', 1, type=int)
#     page_size = request.args.get('page_size', 20, type=int)
#     category_id = request.args.get('category_id', type=int)
#     category_name = request.args.get('category')

#     query = Product.query

#     if category_id:
#         query = query.join(products_categories).filter(products_categories.c.category_id == category_id)
#     elif category_name:
#         query = query.join(products_categories).join(Category).filter(Category.name.ilike(f"%{category_name}%"))

#     products = query.order_by(desc(Product.created_at)).paginate(page=page, per_page=page_size)

#     return PageSerializer(
#         pagination_obj=products,
#         resource_name="products"
#     ).to_dict()

@product_bp.route('/products/<product_id>', methods=['GET'])
@jwt_required(optional=True)
@limiter.exempt
def by_id(product_id):
    """
    Retrieve a product by its ID.

    :param product_id: The ID of the product to retrieve.
    :return: JSON response with product data or error message.
    """
    try:
        product = Product.get_product(product_id)
        if not product:
            return error_response("Product not found", status_code=404)
        
        return success_response("Product fetched successfully", data=product.get_summary())
    except Exception as e:
        traceback.print_exc()
        return error_response(f"An error occurred: {str(e)}", status_code=500)


@product_bp.route('/products/by-categories', methods=['GET'])
@limiter.exempt
def get_products_by_categories():
    """
    Fetch products organized by categories and subcategories.
    Uses PageSerializer for pagination and response handlers for consistent responses.
    """
    try:
        # Pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 2, type=int)

        def build_category_tree(category):
            # Fetch products for the current category
            products = Product.query.join(products_categories).filter(
                products_categories.c.category_id == category.id
            ).order_by(Product.created_at.desc()).limit(8).all()
            # ).order_by(func.random()).limit(4).all()
            
            # Fetch subcategories
            subcategories = Category.query.filter_by(parent_id=category.id).paginate(page=page, per_page=per_page, error_out=False)
            
            # Recursively build the tree for subcategories
            subcategory_tree = [build_category_tree(subcategory) for subcategory in subcategories.items]
            
            return {
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'products': [product.get_summary() for product in products],
                'subcategories': subcategory_tree
            }
        
        # Fetch top-level categories with at least 1 product
        top_level_categories = (
            Category.query
            .filter_by(parent_id=None)  # Ensure it's a top-level category
            .join(products_categories)  # Join with products_categories
            .group_by(Category.id)  # Group by category
            .having(func.count(products_categories.c.product_id) >= 1)  # Ensure at least 1 product
            .paginate(page=page, per_page=per_page, error_out=False)
        )

        # Build the full category tree
        category_tree = [build_category_tree(category) for category in top_level_categories.items]
        
        # Serialize pagination metadata for top-level categories
        page_meta = {
            'current_page_number': top_level_categories.page,
            'has_next_page': top_level_categories.has_next,
            'has_prev_page': top_level_categories.has_prev,
            'next_page_url': f"/api/products?page={top_level_categories.next_num}&page_size={per_page}" if top_level_categories.has_next else None,
            'offset': (top_level_categories.page - 1) * per_page,
            'prev_page_url': f"/api/products?page={top_level_categories.prev_num}&page_size={per_page}" if top_level_categories.has_prev else None,
            'requested_page_size': per_page,
            'total_items_count': top_level_categories.total,
            'total_pages_count': top_level_categories.pages
        }
        
        # Wrap the response data
        response_data = {
            'categories': category_tree,
            'page_meta': page_meta
        }   
        
        return success_response("Products by categories fetched successfully.", data=response_data)

    except Exception as e:
        return error_response(f"Error fetching products by categories: {str(e)}")

@product_bp.route('/products/<product_slug>/slug', methods=['GET'])
@jwt_required(optional=True)
@limiter.exempt
def by_slug(product_slug):
    """
    Retrieve a product by its slug.

    :param product_slug: The slug of the product to retrieve.
    :return: JSON response with product data or error message.
    """
    try:
        product = Product.query.filter_by(slug=product_slug).first()
        if not product:
            return error_response(f"Product <{product_slug}> not found.", status_code=404)
        return success_response("Product fetched successfully.", data=product.get_summary())
    except Exception as e:
        traceback.print_exc()
        return error_response(f"An error occurred: {str(e)}", status_code=500)

@product_bp.route('/products/<int:user_id>/user', methods=['GET'])
@jwt_required(optional=False)
@limiter.exempt
def by_user(user_id):
    """
    Fetch products associated with a specific user.

    :param user_id: The ID of the user to filter products.
    :return: JSON response with paginated product data for the user.
    """
    try:
        user = current_user
        
        if not user:
            return error_response("User not found.", status_code=404)

        # Pagination parameters: Default page = 1, page_size = 5
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 5, type=int)

        # Fetch products associated with the user
        products = Product.query.filter(Product.users.any(id=user_id)).order_by(desc(Product.created_at)).paginate(page=page, per_page=page_size)

        # Serialize the paginated result using PageSerializer
        data = PageSerializer(pagination_obj=products, resource_name="products", context_id=user_id, include_user=True).get_data()

        return success_response("Products fetched successfully.", data=data)

    except Exception as e:
        traceback.print_exc()
        return error_response(f"An error occurred: {str(e)}", status_code=500)
    
@product_bp.route('/products/<page_id>/page', methods=['GET'])
@jwt_required(optional=True)
@limiter.exempt
def by_page(page_id):
    """
    Fetch products associated with a specific page.

    :param page_id: The ID of the page to filter products.
    :return: JSON response with paginated product data for the page.
    """
    try:
        # Pagination parameters: Default page = 1, page_size = 5
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 5, type=int)

        # Fetch products associated with the page
        products = Product.query.filter(Product.pages.any(id=page_id)).order_by(desc(Product.created_at)).paginate(page=page, per_page=page_size)

        # Serialize the paginated result using PageSerializer
        data = PageSerializer(pagination_obj=products, resource_name="products", context_id=page_id, include_user=True, include_page=True).get_data()

        return success_response("Products fetched successfully.", data=data)

    except Exception as e:
        traceback.print_exc()
        return error_response(f"An error occurred: {str(e)}", status_code=500)

@product_bp.route('/products/<int:category_id>/category', methods=['GET'])
@jwt_required()
def by_category(category_id):
    """
    Fetch products associated with a specific category.

    :param category_id: The ID of the category to filter products.
    :return: JSON response with paginated product data for the category.
    """
    try:
        category = Category.query.get(category_id)
        if not category:
            return error_response("Category not found.", status_code=404)

        # Pagination parameters: Default page = 1, page_size = 5
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 5, type=int)

        # Fetch products associated with the category
        products = Product.query.filter(Product.categories.any(id=category_id)).order_by(desc(Product.created_at)).paginate(page=page, per_page=page_size)

        # Serialize the paginated result using PageSerializer
        data = PageSerializer(pagination_obj=products, resource_name="products", context_id=category_id).get_data()

        return success_response("Products fetched successfully.", data=data)

    except Exception as e:
        traceback.print_exc()
        return error_response(f"An error occurred: {str(e)}", status_code=500)

# @product_bp.route('/products', methods=['POST'])
# @jwt_required()
# def create():
#     """
#     Create a new product.

#     Accepts product data in JSON or multipart/form-data format and saves it to the database.

#     :return: JSON response indicating success or failure.
#     """
#     try:
#         if request.content_type == 'application/json':
#             data = request.get_json()
#         elif 'multipart/form-data' in request.content_type:
#             data = request.form.to_dict()
#         else:
#             return error_response("Content-Type must be application/json or multipart/form-data")
        
#         if not data:
#             return error_response("No data received to publish your product.")

#         print(data, request.files)
        
#         # Validate product data
#         try:
#             data['price'] = int(data.get('price', 0))  # Default to 0 if 'price' is missing
#             # data['price'] = int(data['price'])  # Convert to integer
#             data['stock'] = int(data.get('stock', 0))
#             validate(instance=data, schema=product_schema)
#         except ValidationError as e:
#             traceback.print_exc()
#             return error_response(f"Validation error: {e.message}")

#         # Retrieve product details from the request
#         product_name = data.get('name')
#         description = data.get('description')
#         price = data.get('price')
#         stock = data.get('stock')

#         tags = []
#         categories = []

#         # Process tags and categories from the request
#         for header_key in data.keys():
#             if 'tags[' in header_key:
#                 index = re.search(r'\[(\d+)\]', header_key).group(1)
#                 if 'name' in header_key:
#                     tag_name = data[header_key]
#                     tag_description = data.get(f'tags[{index}][description]', tag_name)
#                     tags.append(get_or_create(db.session, Tag, {'description': tag_description}, name=tag_name)[0])

#             if 'categories[' in header_key:
#                 index = re.search(r'\[(\d+)\]', header_key).group(1)
#                 if 'name' in header_key:
#                     category_name = data[header_key]
#                     category_description = data.get(f'categories[{index}][description]', category_name)
#                     categories.append(get_or_create(db.session, Category, {'description': category_description}, name=category_name)[0])

#         # Create the product instance
#         product = Product(
#             name=product_name, 
#             description=description, 
#             price=price, 
#             stock=stock,
#             is_deleted=data.get('is_deleted', False),
#             tags=tags, 
#             categories=categories
#         )

#         # Assign product to the current user
#         product.users.append(current_user)

#         # Check if a page ID is provided in the request
#         page_id = data.get('page_id')
#         if page_id:
#             page = Page.query.get(page_id)
#             if page:
#                 product.pages.append(page)
#             else:
#                 return error_response("The specified page does not exist.", status_code=404)
#         else:
#             # Use the first page associated with the current user if no page ID is provided
#             if current_user.pages.count() > 0:
#                 page = current_user.pages[0]
#                 product.pages.append(page)

#         # Handle image uploads
#         if 'images[]' in request.files:
#             dir_path = os.getenv('IMAGES_LOCATION')
#             dir_path = os.path.join(dir_path, 'products')

#             for image in request.files.getlist('images[]'):
#                 if image and validate_file_upload(image.filename):
#                     file_name = secure_filename(image.filename)
#                     file_path = uploader(image, upload_dir=dir_path)
#                     file_size = image.content_length or os.stat(file_path).st_size

#                     product_image = ProductImage(
#                         file_path=file_path, 
#                         file_name=file_name,
#                         original_name=image.filename, 
#                         file_size=file_size
#                     )
                    
#                     product.images.append(product_image)

#         # Save the product to the database
#         db.session.add(product)
#         db.session.commit()

#         data = product.get_summary()
#         return success_response('Product created successfully', data=data)
    
#     except IntegrityError as e:
#         if 'Duplicate entry' in str(e.orig):
#             return error_response("Duplicate entry for slug. Product already exists.", status_code=409)
#         else:
#             return error_response("Database error. Please try again.")
        
#     except Exception as e:
#         traceback.print_exc()
#         return error_response(f'Error creating product: {e}', status_code=400)

@product_bp.route('/products', methods=['POST'])
@jwt_required()
def create():
    """
    Create a new product.

    Accepts product data in JSON or multipart/form-data format and saves it to the database.

    :return: JSON response indicating success or failure.
    """
    try:
        # Parse request data based on content type
        if request.content_type == 'application/json':
            data = request.get_json()
        elif 'multipart/form-data' in request.content_type:
            data = request.form.to_dict()
        else:
            return error_response("Content-Type must be application/json or multipart/form-data", status_code=400)
        
        if not data:
            return error_response("No data received to publish your product.", status_code=400)

        # Validate and process product data
        try:
            data['price'] = int(data.get('price', 0))  # Default to 0 if 'price' is missing
            data['stock'] = int(data.get('stock', 0))  # Default to 0 if 'stock' is missing
            data['is_deleted'] = bool(data.get('is_deleted', False))  # Default to False if 'is_deleted' is missing
            validate(instance=data, schema=product_schema)
        except ValidationError as e:
            traceback.print_exc()
            return error_response(f"Validation error: {e.message}", status_code=400)

        # Retrieve product details from the request
        product_name = data.get('name')
        description = data.get('description')
        price = data.get('price')
        stock = data.get('stock')

        # Process tags and categories from the request
        tags = []
        categories = []

        for header_key in data.keys():
            if 'tags[' in header_key:
                index = re.search(r'\[(\d+)\]', header_key).group(1)
                if 'name' in header_key:
                    tag_name = data[header_key]
                    tag_description = data.get(f'tags[{index}][description]', tag_name)
                    tag = get_or_create(db.session, Tag, {'description': tag_description}, name=tag_name)[0]
                    tags.append(tag)

            if 'categories[' in header_key:
                index = re.search(r'\[(\d+)\]', header_key).group(1)
                if 'name' in header_key:
                    category_name = data[header_key]
                    category_description = data.get(f'categories[{index}][description]', category_name)
                    category = get_or_create(db.session, Category, {'description': category_description}, name=category_name)[0]
                    categories.append(category)

        # Create the product instance
        product = Product(
            name=product_name,
            description=description,
            price=price,
            stock=stock,
            is_deleted=data.get('is_deleted', False),
            tags=tags,
            categories=categories
        )

        print(request.files)
        # return 

        # # Handle image uploads
        # if 'images[]' in request.files:
        #     dir_path = os.getenv('IMAGES_LOCATION', 'uploads')
        #     dir_path = os.path.join(dir_path, 'products')

        #     for image in request.files.getlist('images[]'):
        #         if image and validate_file_upload(image.filename):
        #             file_name = secure_filename(image.filename)
        #             # file_path = uploader(image, upload_dir=dir_path)
        #             file_path = uploader(image)
        #             file_size = image.content_length or os.stat(file_path).st_size

        #             print(f"file_path: {file_path}")
        #             return 
        #             product_image = ProductImage(
        #                 file_path=file_path,
        #                 file_name=file_name,
        #                 original_name=image.filename,
        #                 file_size=file_size
        #             )
        #             product.images.append(product_image)

        # Handle image uploads - get accessible URLs
        if 'images[]' in request.files:
            # Create products directory if it doesn't exist
            # base_dir = os.getenv('IMAGES_LOCATION', 'uploads')
            # products_dir = os.path.join(base_dir, 'products')
            # os.makedirs(products_dir, exist_ok=True)
            
            # for image in request.files.getlist('images[]'):
            #     if image and image.filename and validate_file_upload(image.filename):
            #         try:
            #             # Upload image and get accessible URL
            #             accessible_url = uploader(image, upload_dir=products_dir)
                        
            #             # Get file size from the uploaded file
            #             # We need to extract the local path from the URL to get file size
            #             domain = os.getenv("APP_DOMAIN", "http://localhost:5001")
            #             relative_path = accessible_url.replace(domain + "/", "")
            #             local_path = os.path.join(app.root_path, relative_path)
            #             file_size = os.path.getsize(local_path)
                        
            #             # Create product image with accessible URL
            #             product_image = ProductImage(
            #                 file_path=accessible_url,  # Store the accessible URL
            #                 file_name=os.path.basename(accessible_url),
            #                 original_name=image.filename,
            #                 file_size=file_size
            #             )
            #             product.images.append(product_image)
            #         except Exception as e:
            #             traceback.print_exc()
            #             app.logger.error(f"Failed to process image {image.filename}: {str(e)}")
            #             # continue
            handle_product_media(product, request.files.getlist('images[]'))
        
        # Save the product to the database
        db.session.add(product)
        db.session.commit()

        # Return success response with product summary
        data = product.get_summary()
        return success_response('Product created successfully', data=data, status_code=201)
    
    except IntegrityError as e:
        traceback.print_exc()
        db.session.rollback()
        if 'Duplicate entry' in str(e.orig):
            return error_response("Duplicate entry for slug. Product already exists.", status_code=409)
        else:
            return error_response("Database error. Please try again.", status_code=500)
        
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(f'Error creating product: {e}', status_code=400)

def handle_product_media(product, media_info):
    """Professional media handling with proper session management"""
    if not media_info:
        return

    try:
        media_root = Path(app.root_path) / app.config['MEDIA_LOCATION'].strip('/')
        fs_upload_dir = media_root / 'products'
        fs_upload_dir.mkdir(parents=True, exist_ok=True)

        # Handle both file objects and existing media URLs
        media_items = media_info if isinstance(media_info, list) else [media_info]
        media_files = []
        existing_urls = []
        
        # Separate new files from existing URLs
        for item in media_items:
            if hasattr(item, 'filename') and item.filename:  # It's a file object
                media_files.append(item)
            elif isinstance(item, dict) and 'url' in item:  # Existing media URL
                existing_urls.append(item['url'])
            elif isinstance(item, str):  # Direct URL string
                existing_urls.append(item)
        
        # Process new files
        for idx, file in enumerate(media_files):
            if not validate_file_upload(file.filename):
                raise ValueError(f"Invalid file type: {file.filename}")

            file_url, error = uploader(file)
            if error:   
                raise ValueError(error)

            # is_cover = (idx == 0 and not existing_urls)
            product_image = ProductImage(
                file_path=file_url,
                file_name=secure_filename(file.filename),
                original_name=file.filename,
                file_size=file.content_length,
                # is_cover=is_cover
            )
            db.session.add(product_image)
            product.images.append(product_image)
        
        # Process existing URLs
        for url in existing_urls:
            # Create ProductImage for existing URL
            filename = url.split('/')[-1].split('?')[0]  # Extract filename from URL
            product_image = ProductImage(
                file_path=url,
                file_name=secure_filename(filename),
                original_name=filename,
                file_size=0,  # Unknown size
                # is_cover=False  # Will be set later
            )
            db.session.add(product_image)
            product.images.append(product_image)
            
        # Set first image as cover if none exists
        # if product.images and not any(img.is_cover for img in product.images):
        #     product.images[0].is_cover = True
            
    except Exception as e:
        traceback.print_exception(e)
        raise ValueError(f"Media processing failed: {str(e)}")

def handle_media_delete(media_ids):
    """Safe media deletion with filesystem cleanup"""
    try:
        images_to_delete = ProductImage.query.filter(
            ProductImage.id.in_(media_ids)
        ).all()

        for image in images_to_delete:
            if os.path.exists(image.file_path):
                os.remove(image.file_path)
            db.session.delete(image)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Media deletion failed: {str(e)}")
        raise error_response("Could not delete media items")

@product_bp.route('/products/<int:pro_id>/images/<img_id>', methods=['DELETE'])
@jwt_required()
@limiter.exempt
def delete_media(pro_id, img_id):

    try:

        product = Product.get_product(pro_id)
        if product is None:
            return error_response(f'Product not found <{pro_id}>', status_code=404)

        if not isinstance(img_id, list):
            imgfor_delete = [img_id]
            
        handle_media_delete(media_ids=imgfor_delete)
        
        # Save the product to the database
        db.session.commit()

        data = product.get_summary()
        return success_response("Product image deleted successfully", data=data)

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(f'Error updating product: {e}', status_code=400)


@product_bp.route('/products/<product_slug>', methods=['PUT'])
@jwt_required()
@limiter.exempt
def update(product_slug):
    """
    Update an existing product.

    Accepts product data in JSON or multipart/form-data format and updates the product in the database.

    :param product_slug: The slug of the product to update.
    :return: JSON response indicating success or failure.
    """
    try:
        if request.content_type == 'application/json':
            data = request.get_json()
        elif 'multipart/form-data' in request.content_type:
            data = request.form.to_dict()
        else:
            return error_response("Content-Type must be application/json or multipart/form-data")
        
        if not data:
            return error_response("No data received to update your product.")

        print(data, request.files)
        
        # Validate product data
        try:
            data['price'] = int(data.get('price', 0))  # Default to 0 if 'price' is missing
            data['stock'] = int(data.get('stock', 0))  # Default to 0 if 'stock' is missing
            data['is_deleted'] = bool(data.get('is_deleted', False))  # Default to False if 'is_deleted' is missing
            validate(instance=data, schema=product_schema)
        except ValidationError as e:
            traceback.print_exc()
            return error_response(f"Validation error: {e.message}")

        product = Product.get_product(product_slug)
        if product is None:
            return error_response(f'Product not found <{data.get("name", product_slug)}>', status_code=404)

        # Update product attributes
        product.name = data.get('name', product.name)
        product.description = data.get('description', product.description)
        product.price = data.get('price', product.price)
        product.stock = data.get('stock', product.stock)

        # Process tags and categories from form data (similar to create endpoint)
        tags = []
        categories = []

        # Handle tags from form data format (like in create endpoint)
        for header_key in data.keys():
            if 'tags[' in header_key:
                index = re.search(r'\[(\d+)\]', header_key).group(1)
                if 'name' in header_key:
                    tag_name = data[header_key]
                    tag_description = data.get(f'tags[{index}][description]', tag_name)
                    tag = get_or_create(db.session, Tag, {'description': tag_description}, name=tag_name)[0]
                    tags.append(tag)

            if 'categories[' in header_key:
                index = re.search(r'\[(\d+)\]', header_key).group(1)
                if 'name' in header_key:
                    category_name = data[header_key]
                    category_description = data.get(f'categories[{index}][description]', category_name)
                    category = get_or_create(db.session, Category, {'description': category_description}, name=category_name)[0]
                    categories.append(category)

        # Handle tags and categories from JSON format (existing logic)
        tags_input = data.get('tags')
        categories_input = data.get('categories')
        
        if categories_input and not categories:  # Only use JSON if form data didn't provide categories
            for category in categories_input:
                categories.append(
                    get_or_create(
                        db.session, 
                        Category, 
                        {'description': category.get('description', None)},
                        name=category['name']
                    )[0]
                )

        if tags_input and not tags:  # Only use JSON if form data didn't provide tags
            for tag in tags_input:
                tags.append(
                    get_or_create(
                        db.session, Tag, 
                        {'description': tag.get('description')}, 
                        name=tag['name']
                    )[0]
                )

        # Update tags and categories if provided
        if tags:
            product.tags = tags
        if categories:
            product.categories = categories

        # Handle image uploads (same as create endpoint)
        if 'images[]' in request.files:
            handle_product_media(product, request.files.getlist('images[]'))
        
        # Save the product to the database
        db.session.commit()

        data = product.get_summary()
        return success_response("Product updated successfully", data=data)
    
    except exc.IntegrityError as e:
        traceback.print_exc()
        db.session.rollback()  # Rollback the session to prevent further issues
        if 'Duplicate entry' in str(e.orig):
            return error_response("Duplicate entry for slug. Product already exists.", status_code=409)
        else:
            return error_response("Database error. Please try again.", status_code=500)
    
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(f'Error updating product: {e}', status_code=400)



# @product_bp.route('/products/<product_slug>', methods=['PUT'])
# @jwt_required()
# @limiter.exempt
# def update(product_slug):
#     """
#     Update an existing product.

#     Accepts product data in JSON or multipart/form-data format and updates the product in the database.

#     :param product_slug: The slug of the product to update.
#     :return: JSON response indicating success or failure.
#     """
#     try:
#         if request.content_type == 'application/json':
#             data = request.get_json()
#         elif 'multipart/form-data' in request.content_type:
#             data = request.form.to_dict()
#         else:
#             return error_response("Content-Type must be application/json or multipart/form-data")
        
#         if not data:
#             return error_response("No data received to update your product.")

#         print(data, request.files)
        
#         # Validate product data
#         try:
#             data['price'] = int(data.get('price', 0))  # Default to 0 if 'price' is missing
#             data['stock'] = int(data.get('stock', 0))  # Default to 0 if 'stock' is missing
#             data['is_deleted'] = bool(data.get('is_deleted', False))  # Default to False if 'is_deleted' is missing
#             validate(instance=data, schema=product_schema)
#         except ValidationError as e:
#             traceback.print_exc()
#             return error_response(f"Validation error: {e.message}")

#         product = Product.get_product(product_slug)
#         if product is None:
#             return error_response(f'Product not found <{data.get("name", product_slug)}>', status_code=404)

#         # Update product attributes
#         product.name = data.get('name', product.name)
#         product.description = data.get('description', product.description)
#         product.price = data.get('price', product.price)
#         product.stock = data.get('stock', product.stock)

#         # Process tags and categories
#         tags_input = data.get('tags')
#         categories_input = data.get('categories')
#         tags = []
#         categories = []
        
#         if categories_input:
#             for category in categories_input:
#                 categories.append(
#                     get_or_create(
#                         db.session, 
#                         Category, 
#                         {'description': category.get('description', None)},
#                         name=category['name']
#                     )[0]
#                 )

#         if tags_input:
#             for tag in tags_input:
#                 tags.append(
#                     get_or_create(
#                         db.session, Tag, 
#                         {'description': tag.get('description')}, 
#                         name=tag['name']
#                     )[0]
#                 )

#         product.tags = tags
#         product.categories = categories
#         db.session.commit()

#         data = product.get_summary()
#         return success_response("Product updated successfully", data=data)
    
#     except exc.IntegrityError as e:
#         traceback.print_exc()
#         db.session.rollback()  # Rollback the session to prevent further issues
#         return error_response("A product with this slug already exists. Please choose a different name.", status_code=400)
    
#     except Exception as e:
#         traceback.print_exc()
#         return error_response(f'Error updating product: {e}', status_code=400)


@product_bp.route('/products/<identifier>', methods=['DELETE'])
@jwt_required()
@limiter.exempt
def destroy(identifier):
    """
    Delete a product by its slug or ID.

    :param identifier: The product slug or ID.
    :return: JSON response indicating success or failure.
    """
    try:
        # Attempt to find the product by ID first
        product = Product.query.get(identifier)
        
        # If no product is found by ID, try to find it by slug
        if product is None:
            product = Product.query.filter_by(slug=identifier).first()
        
        # If product is still None, return a 404 error
        if product is None:
            return error_response(f'Product not found <{identifier}>', status_code=404)

        # Delete the product and commit the transaction
        db.session.delete(product)
        db.session.commit()
        return success_response('Product deleted successfully')
    
    except Exception as e:
        traceback.print_exc()
        return error_response(f'Error deleting product: {e}', status_code=400)