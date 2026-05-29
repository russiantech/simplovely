
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

        return render_template('users/account.html')
        # return render_template('users/account_1.html', **context)
        # return render_template('users/accountv2.html', **context)
        # return render_template('users/accountv3.html', **context)
        # return render_template('users/accountv4.html', **context)
        # return render_template('users/accountv5.html', **context)
        # return render_template('users/accountv6.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))

@users_bp.route('/plans')
def plans():
    try:
        return render_template('users/plans.html')
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))

@users_bp.route('/usage')
def usage():
    try:
        return render_template('users/usage.html')
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))

@users_bp.route('/transactions')
def transactions():
    try:
        # return render_template('users/transactions_0.html')
        return render_template('users/transactions.html')
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))

@users_bp.route('/settings')
def settings():
    try:
        return render_template('users/settings.html')
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))

@users_bp.route('/addresses')
def addresses():
    try:
        return render_template('users/addresses.html')
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))
    