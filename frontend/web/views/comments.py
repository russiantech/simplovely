from flask import render_template
import traceback
from web.apis.utils.serializers import error_response
from web.apis import api_bp as comments_bp

@comments_bp.route('/comments')
def comments():
    try:
        context= {}
        return render_template('comments/comments.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))
    