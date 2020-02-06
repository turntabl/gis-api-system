# run.py

from app.application import app
from app.config import config

if __name__ == '__main__':
    print("**************Server Starting**************")
    app.run(host='0.0.0.0', port=config.PORT, debug=config.DEBUG)