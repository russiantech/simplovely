
from flask import render_template
import traceback
from web.views.utils.serializers import error_response
from web.views import api_bp as orders_bp

@orders_bp.route('/order')
def order():
    try:
        context= {}
        return render_template('order/order.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))
