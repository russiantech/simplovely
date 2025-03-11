from flask import render_template
import traceback
from web.apis.utils.serializers import error_response
from web.apis import api_bp as addresses_bp

@addresses_bp.route('/addresses')
@addresses_bp.route('/users/addresses')
def addresses():
    try:
        context= {}
        # return render_template('users/index.html', **context)
        return render_template('users/addresses.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))
    