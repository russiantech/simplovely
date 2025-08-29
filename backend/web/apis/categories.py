# import os
# import traceback
# from flask_jwt_extended import jwt_required
# from flask import request
# from jsonschema import ValidationError, validate
# from sqlalchemy.exc import IntegrityError, SQLAlchemyError
# from werkzeug.utils import secure_filename
# from web.apis.utils.decorators import access_required
# from web.apis.utils.serializers import PageSerializer, error_response, success_response
# from web.extensions import db, limiter
# from web.apis.models.categories import Category
# from web.apis.models.file_uploads import CategoryImage
# from web.apis.utils.helpers import validate_file_upload
# from web.apis import api_bp as categories_bp
# from web.apis.utils.uploader import uploader
# from web.apis.schemas.categories import category_schema

# @categories_bp.route('/categories', methods=['POST'])
# @jwt_required(optional=True)
# # @access_required('admin', 'dev')
# @limiter.exempt
# def create_category():
#     try:
#         if request.content_type == 'application/json':
#             data = request.get_json()
#         elif 'multipart/form-data' in request.content_type:
#             data = request.form.to_dict()
#         else:
#             return error_response("Content-Type must be application/json or multipart/form-data")

#         try:
#             validate(instance=data, schema=category_schema)
#         except ValidationError as e:
#             return error_response(f"Validation error: {e.message}")

#         # Create the category
#         category = Category(
#             name=data.get('name'),
#             description=data.get('description', ''),
#             parent_id=data.get('parent_id')  # Set parent_id for nested categories
#         )

#         # Handle images
#         if 'images[]' in request.files:
#             dir_path = os.getenv('IMAGES_LOCATION')
#             dir_path = os.path.join(dir_path, 'categories')

#             for image in request.files.getlist('images[]'):
#                 if image and validate_file_upload(image.filename):
#                     file_name = secure_filename(image.filename)
#                     file_path = uploader(image, upload_dir=dir_path)
#                     file_size = image.content_length or os.stat(file_path).st_size

#                     ci = CategoryImage(
#                         file_path=file_path,
#                         file_name=file_name,
#                         original_name=image.filename,
#                         file_size=file_size
#                     )
#                     category.images.append(ci)

#         db.session.add(category)
#         db.session.commit()
#         return success_response("Category created successfully.", data=category.get_summary())

#     except IntegrityError:
#         db.session.rollback()
#         return error_response(f"Integrity error. <{data.get('name')}> already exists.")

#     except SQLAlchemyError as e:
#         db.session.rollback()
#         return error_response(f"Database error: {str(e)}")

#     except Exception as e:
#         return error_response(f"Unexpected error: {str(e)}")

# @categories_bp.route('/categories', methods=['GET'])
# @categories_bp.route('/categories/<int:category_id>', methods=['GET'])
# @limiter.exempt
# def get_categories(category_id=None):
#     try:
#         if category_id:
#             category = Category.query.get(category_id)
#             if not category:
#                 return error_response("Category not found.")
#             return success_response("Category fetched successfully.", data=category.get_summary(include_products=True))

#         # Pagination
#         page = request.args.get('page', 1, type=int)
#         per_page = request.args.get('per_page', 10, type=int)

#         categories = Category.query.order_by(Category.created_at.desc()).paginate(
#             page=page, per_page=per_page, error_out=False
#         )
        
#         data = PageSerializer(pagination_obj=categories, resource_name='categories').get_data()
#         return success_response("Categories fetched successfully.", data=data)

#     except Exception as e:
#         return error_response(f"Error fetching categories: {str(e)}")

# @categories_bp.route('/categories/<int:category_id>', methods=['PUT'])
# @jwt_required(optional=True)
# # @access_required('admin', 'dev')
# @limiter.exempt
# def update_category(category_id):
#     try:
#         category = Category.query.get(category_id)
#         if not category:
#             return error_response("Category not found.")

#         data = request.json
#         category.name = data.get('name', category.name)
#         category.description = data.get('description', category.description)

#         db.session.commit()
#         return success_response("Category updated successfully.")

#     except SQLAlchemyError as e:
#         db.session.rollback()
#         return error_response(f"Database error: {str(e)}")

#     except Exception as e:
#         return error_response(f"Unexpected error: {str(e)}")

# @categories_bp.route('/categories/<int:category_id>', methods=['DELETE'])
# @jwt_required()
# @access_required('admin', 'dev')
# @limiter.exempt
# def delete_category(category_id):
#     try:
#         category = Category.query.get(category_id)
#         if not category:
#             return error_response("Category not found.")

#         db.session.delete(category)
#         db.session.commit()
#         return success_response("Category deleted successfully.")

#     except SQLAlchemyError as e:
#         db.session.rollback()
#         return error_response(f"Database error: {str(e)}")

#     except Exception as e:
#         return error_response(f"Unexpected error: {str(e)}")


# V2
import os
import re
import traceback
from flask import current_app as app, request
from flask_jwt_extended import jwt_required, current_user
from jsonschema import ValidationError, validate
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc, exc
from werkzeug.utils import secure_filename
from web.extensions import db, limiter
from web.apis.models.categories import Category
from web.apis.models.products import Product
from web.apis.schemas.categories import category_schema
from web.apis.utils.helpers import validate_file_upload
from web.apis.utils.serializers import PageSerializer, error_response, success_response
from web.apis import api_bp as category_bp

@category_bp.route('/categories', methods=['GET'])
@jwt_required(optional=True)
@limiter.exempt
def categories():
    """
    Retrieve a paginated list of categories.

    Returns a list of categories, paginated by the specified page and page size.
    If no categories are found, an empty list is returned.

    :return: JSON response with paginated category data.
    """
    try:
        # Pagination parameters: Default page = 1, page_size = 10
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)

        # Base query
        query = Category.query

        # Search filter
        search_query = request.args.get('search')
        if search_query:
            query = query.filter(Category.name.ilike(f'%{search_query}%'))

        # Fetch categories with pagination
        categories = query.order_by(desc(Category.created_at)).paginate(page=page, per_page=page_size)

        # Serialize the paginated result using PageSerializer
        data = PageSerializer(pagination_obj=categories, resource_name="categories").get_data()
        
        return success_response("Categories fetched successfully.", data=data)

    except Exception as e:
        return error_response(f"An error occurred: {str(e)}", status_code=500)

@category_bp.route('/categories/<category_id>', methods=['GET'])
@jwt_required()
@limiter.exempt
def by_category_id(category_id):
    """
    Retrieve a category by its ID.

    :param category_id: The ID of the category to retrieve.
    :return: JSON response with category data or error message.
    """
    try:
        category = Category.query.get_or_404(category_id)
        return success_response("Category fetched successfully", data=category.get_summary())
    except Exception as e:
        return error_response(f"An error occurred: {str(e)}", status_code=500)

@category_bp.route('/categories/<category_slug>/slug', methods=['GET'])
@jwt_required(optional=True)
@limiter.exempt
def by_category_slug(category_slug):
    """
    Retrieve a category by its slug.

    :param category_slug: The slug of the category to retrieve.
    :return: JSON response with category data or error message.
    """
    try:
        category = Category.query.filter_by(slug=category_slug).first()
        if not category:
            return error_response(f"Category <{category_slug}> not found.", status_code=404)
        return success_response("Category fetched successfully.", data=category.get_summary())
    except Exception as e:
        traceback.print_exc()
        return error_response(f"An error occurred: {str(e)}", status_code=500)

@category_bp.route('/categories/<int:category_id>/products', methods=['GET'])
@jwt_required(optional=True)
def category_products(category_id):
    """
    Fetch products associated with a specific category with pagination.

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
        products = Product.query.filter(Product.categories.any(id=category_id))\
                               .order_by(desc(Product.created_at))\
                               .paginate(page=page, per_page=page_size)

        # Serialize the paginated result using PageSerializer
        data = PageSerializer(
            pagination_obj=products,
            resource_name="products",
            context_id=category_id,
            include_category=True
        ).get_data()

        return success_response("Category products fetched successfully.", data=data)

    except Exception as e:
        traceback.print_exc()
        return error_response(f"An error occurred: {str(e)}", status_code=500)

@category_bp.route('/categories', methods=['POST'])
@jwt_required(optional=True)
@limiter.exempt
def create_categories():
    """
    Create a new category.

    Accepts category data in JSON format and saves it to the database.

    :return: JSON response indicating success or failure.
    """
    try:
        data = request.get_json()
        
        if not data:
            return error_response("No data received to create category.")

        # Validate category data
        try:
            validate(instance=data, schema=category_schema)
        except ValidationError as e:
            return error_response(f"Validation error: {e.message}")

        # Check for existing category with same name
        existing_category = Category.query.filter_by(name=data['name']).first()
        if existing_category:
            return error_response("A category with this name already exists.", status_code=409)

        # Create the category instance
        category = Category(
            name=data['name'],
            description=data.get('description'),
            # is_active=data.get('is_active', True)
        )

        # Save the category to the database
        db.session.add(category)
        db.session.commit()

        return success_response('Category created successfully', data=category.get_summary())
    
    except IntegrityError as e:
        if 'Duplicate entry' in str(e.orig):
            return error_response("Duplicate entry for slug. Category already exists.", status_code=409)
        else:
            return error_response("Database error. Please try again.")
        
    except Exception as e:
        traceback.print_exc()
        return error_response(f'Error creating category: {e}', status_code=400)

@category_bp.route('/categories/<category_id>', methods=['PUT'])
@jwt_required(optional=True)
@limiter.exempt
def update_categories(category_id):
    """
    Update an existing category.

    Accepts category data in JSON format and updates the category in the database.

    :param category_id: The ID of the category to update.
    :return: JSON response indicating success or failure.
    """
    try:
        data = request.get_json()
        print(data)
        if not data:
            return error_response("No data received to update category.")

        # Validate category data
        try:
            validate(instance=data, schema=category_schema)
        except ValidationError as e:
            return error_response(f"Validation error: {e.message}")

        category = Category.query.get_or_404(category_id)

        # Check for existing category with same name (excluding current category)
        existing_category = Category.query.filter(
            Category.name == data['name'],
            Category.id != category.id
        ).first()
        if existing_category:
            return error_response("A category with this name already exists.", status_code=409)

        # Update category attributes
        category.name = data.get('name', category.name)
        category.description = data.get('description', category.description)
        # category.is_active = data.get('is_active', category.is_active) // This is'nt necessary for this small project

        db.session.commit()

        return success_response("Category updated successfully", data=category.get_summary())
    
    except exc.IntegrityError as e:
        db.session.rollback()
        return error_response("A category with this slug already exists. Please choose a different name.", status_code=400)
    
    except Exception as e:
        traceback.print_exc()
        return error_response(f'Error updating category: {e}', status_code=400)

@category_bp.route('/categories/<category_id>', methods=['DELETE'])
@jwt_required(optional=True)
@limiter.exempt
def destroy_categories(category_id):
    """
    Delete a category by its ID.

    :param category_id: The ID of the category to delete.
    :return: JSON response indicating success or failure.
    """
    try:
        category = Category.query.get_or_404(category_id)
        
        # Check if category has associated products
        if category.products.count() > 0:
            return error_response("Cannot delete category with associated products. Remove products first.", status_code=400)

        db.session.delete(category)
        db.session.commit()

        return success_response("Category deleted successfully")
    except Exception as e:
        traceback.print_exc()
        return error_response(f'Error deleting category: {e}', status_code=400)