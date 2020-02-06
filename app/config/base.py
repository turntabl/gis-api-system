# base.py

import os


class BaseConfig(object):

    # Statement for enabling the development environment
    DEBUG = True

    # Application port
    PORT = 5004

    # Define the application directory
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # Define the application root directory
    ROOT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))

    # Enable protection against *Cross-site Request Forgery (CSRF)*
    CSRF_ENABLED = True

    # Use a secure, unique and absolutely secret key for
    # signing the data.
    CSRF_SESSION_KEY = "Y~XHH!jmN]LWX/,?RT"

    # Secret key for signing cookies
    SECRET_KEY = "A0Zr08j/3yX Y~XHH!jmN]LWX/,?RT"

    # Flask-session configs
    SESSION_TYPE = 'filesystem'
    COOKIE_VALUE = 'sess'

    # Multi-Language Configurations
    DEFAULT_LANG = "en"

    # External APIs
    API_URL = ""
    DEF_HEADER = ""

    #Google Map API Key
    GOOGLE_API_KEY =  os.environ.get('GOOGLE_API_KEY')

    
    #POSTRGRES CREDENTIALS
    DB_NAME = os.environ.get('DB_NAME')
    DB_USERNAME = os.environ.get('DB_USERNAME')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_HOST = os.environ.get('DB_HOST') 
    DB_PORT = os.environ.get('DB_PORT')
