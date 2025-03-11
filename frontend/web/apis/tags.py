from flask import render_template
import traceback
from web.apis.utils.serializers import error_response
from web.apis import api_bp as tags_bp

@tags_bp.route('/tags')
def tags():
    try:
        context= {}
        return render_template('tags/tags.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))
