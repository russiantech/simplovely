
from flask import Blueprint
api_bp = Blueprint('apis', __name__)

import sys
sys.stdout.write('[+] Registering routes for: \n')

# web/apis/models/__init__.py
from . import products
from . import categories
from . import users
from . import addresses
from . import comments                       
from . import plans                       
from . import pays                       
from . import transactions                       
from . import services                       

__all__ = [
    
    "users",
    "products",
    "categories",
    
    "addresses",
    "product",
    "services",
    "plans",
    "pays",
    "transactions",
    "comments",
    
    "FileUpload",
    "TagImage",
    "CategoryImage",
    "ProductImage",

    "Role",
    "UserRole",
    "users_roles",

]
