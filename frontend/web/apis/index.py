
from flask import render_template
import traceback
from web.apis.utils.serializers import error_response
from web.apis import api_bp as index_bp

@index_bp.route('/fashion-bak')
def fashion_bak():
    try:
        context= {}
        return render_template('fashion.bak.html', **context)
    except Exception as e:
        traceback.format_exc() 
        return error_response(str(e))
    
@index_bp.route('/')
@index_bp.route('/index')
def index():
    try:
        context= {}
        return render_template('index.html', **context)
    except Exception as e:
        traceback.format_exc() 
        return error_response(str(e))
    
@index_bp.route('/fashion')
def fashion():
    try:
        context= {}
        return render_template('fashion.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))
    
@index_bp.route('/fashion-crud')
def fashion_crud():
    try:
        context= {}
        return render_template('fashion_crud.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))
    
@index_bp.route('/fashion-crud-bak')
def fashion_crud_bak():
    try:
        context= {}
        return render_template('fashion_crud.bak.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))
    
@index_bp.route('/laundry')
def laundry():
    try:
        context= {}
        return render_template('laundry.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))
    
@index_bp.route('/contact')
def contact():
    try:
        context= {}
        return render_template('contact.html', **context)
    except Exception as e:
        traceback.format_exc()
        return error_response(str(e))