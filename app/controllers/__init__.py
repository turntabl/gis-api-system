# __init__.py

"""
    Init for controllers
"""

from flask import Blueprint
from flask import jsonify

from app.libs.decorators import ApiRequest

api = Blueprint('api', __name__, url_prefix='/api')

api_request = ApiRequest()


class JsonResponse:
    @staticmethod
    def success(msg='Success', data={}, nav=None):
        if nav is not None:
            return jsonify(code='00', msg=msg, data=data, nav=nav)
        else:
            return jsonify(code='00', msg=msg, data=data)

    @staticmethod
    def failed(msg):
        return jsonify(code='01', msg=msg)

    @staticmethod
    def bad_request(msg='Bad Request'):
        return jsonify(code='02', msg=msg)

    @staticmethod
    def unauthorized(msg='Unauthorized'):
        return jsonify(code='03', msg=msg)

    @staticmethod
    def forbidden(msg='You cannot perform this action'):
        return jsonify(code='04', msg=msg)

    @staticmethod
    def server_error(msg='Server Error'):
        return jsonify(code='05', msg=msg)

    @staticmethod
    def inactive_user(msg='Inactive account'):
        return jsonify(code='113', msg=msg)

    @staticmethod
    def password_expired(msg='Password has expired'):
        return jsonify(code='13', msg=msg)

    @staticmethod
    def new_user_not_notified(msg='New user, but notification not sent'):
        return jsonify(code='23', msg=msg)


from app.controllers.v1 import auth
from app.controllers.v1 import institution
from app.controllers.v1 import branch
from app.controllers.v1 import administrator
from app.controllers.v1 import application
from app.controllers.v1 import report
from app.controllers.v1 import role
from app.controllers.v1 import settings
from app.controllers.v1 import transaction


@api.route('/', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_base():
    return jsonify(code='00', msg='PayPrompt Entry', data={})
