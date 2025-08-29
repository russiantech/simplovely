
# import web.apis.user
# import sys
# sys.stdout.write('[+] Registering routes for user\n')

from flask import Blueprint
api_bp = Blueprint('apis', __name__)

# web/apis/models/__init__.py
from . import products
from . import categories
# from . import pages
from . import users
from . import addresses
from . import comments                       
from . import plans                       
from . import pays                       
from . import services                       

__all__ = [
    
    "users",
    "products",
    "categories",
    "basket",
    
    "addresses",
    "product",
    "services",
    
    "Page",
    "products_pages",
    "users_pages",
    
    "User",
    "Basket",
    "Favorite",
    "Comment",
    
    "FileUpload",
    "TagImage",
    "CategoryImage",
    "ProductImage",
    
    "Order",
    "OrderItem",
    
    "Role",
    "UserRole",
    "users_roles",
    
    "Tag",
    "ProductTag",
    "products_tags",
    
    "Chat",
    
    "Category",
    "products_categories",
    
    "Transaction"
    
]
