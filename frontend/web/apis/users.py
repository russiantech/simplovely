
from flask import render_template
import traceback
from web.apis.utils.serializers import error_response
from web.apis import api_bp as users_bp

@users_bp.route('/signup')
def signup():
    try:
        context= {}
        return render_template('auth/signup.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))
    
@users_bp.route('/signin')
def signin():
    try:
        context= {}
        
        return render_template('auth/signin.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))
    
@users_bp.route('/account')
def account():
    try:
        context= {}
        return render_template('users/account.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))
    
@users_bp.route('/settings')
def settings():
    try:
        context= {}
        return render_template('users/settings.html', **context)
        # return render_template('users/user.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))
