# test.py

from app.config.base import BaseConfig


class TestConfig(BaseConfig):

    FLUENTD_HOST = "stats.nsano.com"
    FLUENTD_PORT = 24224

    # RabbitMQ Configuration
    RABBITMQ_HOST = 'sandbox.nsano.com'
    RABBITMQ_PORT = 5672
    RABBITMQ_USERNAME = 'brokeradmin'
    RABBITMQ_PASSWORD = 'bPqVb3cR5a5STQ8K'
    AMQP_URL = 'amqp://{}:{}@{}:{}/%2F'.format(RABBITMQ_USERNAME, RABBITMQ_PASSWORD, RABBITMQ_HOST, RABBITMQ_PORT)

    PORTAL_URL = 'https://payprompt.nsano.com'

    # Account Management Configuration
    PASSWORD_RESET_URL = '%s/changePassword?token=<token>&username=<username>' % PORTAL_URL
