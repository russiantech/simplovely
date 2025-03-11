
from flask import render_template
import traceback
from web.apis.utils.serializers import error_response
from web.apis import api_bp as basket_bp

@basket_bp.route('/basket')
def basket():
    try:
        context= {}
        return render_template('basket/basket.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))
    

    