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

        with app.app_context():
            db.create_all()  # Create all tables

        return app
    
    except Exception as e:
        print(f"Error initializing app: {e}")
        raise
