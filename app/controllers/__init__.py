# __init__.py

"""
    Init for controllers
"""

from flask import Blueprint
from flask import jsonify

from app.libs.api_call import ApiCall
from app.libs.decorators import ApiRequest

api = Blueprint('api', __name__, url_prefix='/api')

api_call = ApiCall()
api_request = ApiRequest()

from app.controllers.v1 import izone



@api.route('/', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_base():
    return jsonify(code='00', msg='GIS API Entry', data={})
