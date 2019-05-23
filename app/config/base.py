# base.py

import os


class BaseConfig(object):

    # Statement for enabling the development environment
    DEBUG = False

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

    # Pagination configs
    DEFAULT_PAGE = 1
    DEFAULT_SKIP = 0
    DEFAULT_LIMIT = 10

    # Logging Configuration
    ACCESS_LOG_PATH = "logs/access.log"
    EVENT_LOG_PATH = "logs/event.log"
    ERROR_LOG_PATH = "logs/error.log"
    LOG_URL = ""

    # Define the database connections for various dbs
    # MongoDB Connection variables
    MONGODB_DB = "payprompt_db"
    MONGODB_HOST = "127.0.0.1"
    MONGODB_PORT = 27017
    MONGODB_USERNAME = ""
    MONGODB_PASSWORD = ""

    # LOGSTASH_HOST = "stats.nsano.com"
    LOGSTASH_HOST = "127.0.0.1"
    LOGSTASH_PORT = 7000
    LOGSTASH_APPLICATION_NAME = "PAYPROMPT"
    LOGSTASH_CHANNEL = "ENGINE"
    LOGSTASH_SQL_CACHE = "logs/cache_log.db"

    FLUENTD_HOST = "stats.nsano.com"
    FLUENTD_PORT = 24224

    # Email notification config
    EMAIL_API_URL = "http://45.79.139.232:7474/sendmail"
    EMAIL_USERNAME = "notify@nsano.com"
    EMAIL_PASSWORD = ""
    EMAIL_SENDER = "PayPrompt"
    ALERT_LIST = ["p.tuffour@nsano.com"]

    # GRAPHITE CONFIGURATION
    GRAPHITE_URL = "monitor.nsano.com:2004"
    GRAPHITE_HOST = "monitor.nsano.com"
    GRAPHITE_PORT = 2004
    GRAPHITE_PREFIX = "NSURE"

    PORTAL_URL = 'http://192.168.0.62:5072'

    # Account Management Configuration
    ENFORCE_PASSWORD_POLICY = True
    MINIMUM_PASSWORD_LENGTH = 8
    PASSWORD_RESET_URL = '%s/changePassword?token=<token>&username=<username>' % PORTAL_URL
    # Password reset activity period
    PASSWORD_RESET_ACTIVE_MINUTES = 1440

    PASSWORD_EXPIRY_DAYS = 30

    # Other configuration
    SALT = '$<NBc2W33M;OYl{z'
    SESSION_EXPIRY_HOURS = 12

    PARENT_INST_SHORT_NAME = 'NSANO'

    SEND_SMS_URL = 'https://mysms.nsano.com/api/v1/sms/single'
    SMS_API_KEY = '610821a7152b390255eb765450e8d000'

    SMS_SENDER = 'PayPrompt'
    CHEQUE_APPROVAL_SMS = 'Dear customer, you have a request to approve this cheque. Dial *XXX*XX# to approve/decline.'
