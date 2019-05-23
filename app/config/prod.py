# prod.py

from app.config.base import BaseConfig


class ProdConfig(BaseConfig):

    DEBUG = False

    PORTAL_URL = ''

    # Account Management Configuration
    PASSWORD_RESET_URL = '%s/changePassword?token=<token>&email=<email>' % PORTAL_URL
