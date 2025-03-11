
from flask import render_template
import traceback
from web.apis.utils.serializers import error_response
from web.apis import api_bp as favorites_bp

@favorites_bp.route('/favorite')
def favorite():
    try:
        context= {}
        return render_template('favorite/favorite.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))
    