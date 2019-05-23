# application.py

import os

from flask import Flask
from flask import jsonify
from flask import send_from_directory
from flask_mongoengine import MongoEngine

from app.config import config

app = Flask(__name__)
static_file_dir = os.path.join(config.ROOT_DIR, 'static')

# Set app config
app.config['MONGODB_DB'] = config.MONGODB_DB
app.config['MONGODB_HOST'] = config.MONGODB_HOST
app.config['MONGODB_PORT'] = config.MONGODB_PORT
app.config['MONGODB_USERNAME'] = config.MONGODB_USERNAME
app.config['MONGODB_PASSWORD'] = config.MONGODB_PASSWORD

# Setup DB
db = MongoEngine(app)

from app.controllers import api

# Register blueprint(s)
app.register_blueprint(api)


@app.route('/media/<path:path>', methods=['GET'])
def serve_static_file(path):

    if not os.path.isfile(os.path.join(static_file_dir, path)):
        path = os.path.join(path, 'index.html')

    return send_from_directory(static_file_dir, path)


# HTTP error handling
@app.errorhandler(404)
def not_found(error):
    return jsonify(code="404", msg="Resource not found"), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify(code="405", msg="Method not allowed"), 405
