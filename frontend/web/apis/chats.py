from flask import render_template
import traceback
from web.apis.utils.serializers import error_response
from web.apis import api_bp as chats_bp

@chats_bp.route('/chat')
def chat():
    try:
        context= {}
        return render_template('chat/chat.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))
    