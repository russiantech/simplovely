from urllib import request

from flask import Flask
from web.extensions import db, config_app, init_ext, make_available

# from web.apis.models import *

def create_app(config_name=None):
    app = Flask(__name__, instance_relative_config=False)

    try:
        # Configure the app
        config_app(app, config_name)
        init_ext(app)
        app.context_processor(make_available) # make some-data available in the context through-out
        
        # Register Blueprints
        from web.apis import api_bp
        app.register_blueprint(api_bp, url_prefix='/api')
        
        # error-bp
        from web.apis.errors.handlers import error_bp
        app.register_blueprint(error_bp)
        
        # cors
        # AFTER all blueprints are registered, add CORS error handler
        @app.after_request
        def after_request(response):
            # Ensure CORS headers are present on every response
            origin = request.headers.get('Origin')
            allowed_origins = [
                "https://simplylovely.ng",
                "https://www.simplylovely.ng",
                "http://localhost:5000",
                "http://localhost:5001",
            ]
            
            if origin in allowed_origins:
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Client-Callback-Url, X-Requested-With, Accept, Origin'
            return response
        

        with app.app_context():
            db.create_all()  # Create all tables

        return app
    
    except Exception as e:
        print(f"Error initializing app: {e}")
        raise
