from flask import render_template
import traceback
from web.apis.utils.serializers import error_response
from web.apis import api_bp as products_bp

@products_bp.route('/products')
def products():
    try:
        context= {}
        return render_template('products/products.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))


