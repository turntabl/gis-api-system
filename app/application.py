# application.py

import os

from flask import Flask
from flask import jsonify
from flask_cors import CORS, cross_origin
from app.config import config

app = Flask(__name__)

from app.controllers import api

# Allowing Cross Origin
CORS(app)

# Register blueprint(s)
app.register_blueprint(api)


# HTTP error handling
@app.errorhandler(404)
def not_found(error):
    return jsonify(code="404", msg="Resource not found"), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify(code="405", msg="Method not allowed"), 405
