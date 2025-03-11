from flask import render_template
import traceback
from web.apis.utils.serializers import error_response
from web.apis import api_bp as roles_bp

@roles_bp.route('/roles')
def roles():
    try:
        context= {}
        return render_template('roles/roles.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))

