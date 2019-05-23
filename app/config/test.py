# test.py

from app.config.base import BaseConfig


class TestConfig(BaseConfig):

    FLUENTD_HOST = "stats.nsano.com"
    FLUENTD_PORT = 24224

    PORTAL_URL = 'https://payprompt.nsano.com'

    # Account Management Configuration
    PASSWORD_RESET_URL = '%s/changePassword?token=<token>&username=<username>' % PORTAL_URL
