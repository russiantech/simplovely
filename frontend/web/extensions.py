
from web.views.utils.services import *

# Load environment variables
from dotenv import load_dotenv
load_dotenv()
from os import getenv

# Initialize extensions
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()

from flask_cors import CORS
cors = CORS()

def config_app(app, config_name):
    """Configure app settings based on environment."""
    from web.config import app_config
    app.config.from_object(app_config[config_name])

def init_ext(app):
    """Initialize all extensions."""
    csrf.init_app(app)
    cors.init_app(app)

def make_available():
    """Provide application metadata."""

    data = {
        'app_name': 'Simply Lovely',
        'hype': 'Fashion & Laundry.',
        'app_desc': 'Elite software engr team with special interest in artificial intelligence, data and hacking..',
        'app_desc_long': 'Elite software engr team with special interest in artificial intelligence, data and hacking..\n\
            Techa m-powers people & powers businesses to stay relevant with technologies and advancements.',
        'app_location': 'Graceland Estate, Lekki, Lagos, Nigeria.',
        'app_email': 'info@simplylovely.ng',
        'app_logo': getenv('LOGO_URL'),
        'site_logo': getenv('LOGO_URL'),
        'site_link': 'https://www.simplylovely.ng/',
        'whatsapp_link': 'https://www.simplylovely.ng/',
        'terms_link': 'https://www.simplylovely.ng/terms',
        'policy_link': 'https://www.simplylovely.ng/policy',
        'cookie_link': 'https://www.simplylovely.ng/cookie',
        'x_link': 'https://twitter.com/chris_jsmes',
        'instagram_link': 'https://www.instagram.com/chrisjsmz/',
        'linkedin_link': 'https://www.linkedin.com/in/chrisjsm',
        'youtube_link': 'https://www.youtube.com/@russian_developer',
    }
    
    # Add services to the data dictionary
    data['laundry_services'] = laundry_services
    data['fashion_services'] = fashion_services
    
    # datas = {**data, **services}
    return data

