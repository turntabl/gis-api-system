# __init__.py

import os
import sys

from app.config.base import BaseConfig

env = os.environ.get('APP_ENV', 'default')
print('APP ENVIRONMENT: [%s]' % env)

if env == 'test':
    config = TestConfig
elif env == 'prod':
    config = ProdConfig
elif env in ('default', 'dev'):
    config = BaseConfig
else:
    print('*** Unknown application environment: [%s]. Exiting...' % env)
    sys.exit(4)