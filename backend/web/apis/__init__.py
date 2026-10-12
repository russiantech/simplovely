from flask import Blueprint

api_bp = Blueprint("apis", __name__)

# Import order matters only for readability; importing registers models and routes.
from . import (  # noqa: E402,F401
    addresses,
    categories,
    comments,
    pays,
    plans,
    products,
    services,
    transactions,
    users,
)
