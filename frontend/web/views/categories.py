from flask import render_template
import traceback
from web.apis.utils.serializers import error_response
from web.apis import api_bp as categories_bp

@categories_bp.route('/categories')
def categories():
    try:
        context= {}
        return render_template('categories/categories.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))
    