
from flask import Blueprint
api_bp = Blueprint('apis', __name__)

# web/apis/__init__.py
from . import products
# from . import pages
from . import index
from . import users
from . import baskets
from . import orders
from . import addresses
from . import favorites
from . import comments
from . import roles
from . import tags 
# from .tags import Tag, ProductTag, products_tags
from . import chats
# from .categories import Category, products_categories
from . import categories
# from .transactions import Transaction

__all__ = [
    
    "users",
    "products",
    "basket",
    
    "addresses",
    "product",
    
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
