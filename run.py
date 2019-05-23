# run.py

from app.application import app
from app.libs.logger import Logger
from app.config import config

if __name__ == '__main__':
    Logger.log(__name__, "start main server", "EVENT", "00", "STARTING API SERVER", {}, stash=False)
    app.run(host='0.0.0.0', port=config.PORT, debug=config.DEBUG)