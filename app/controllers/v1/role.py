# role.py

import json

from flask import g
from flask import request

from app.controllers import api
from app.controllers import api_request
from app.controllers import JsonResponse
from app.libs.logger import Logger
from app.services.v1.role import RoleService


@api.route('/v1/roles', methods=['POST'])
@api_request.json
@api_request.required_body_params('name', 'privileges')
def add_role():
    # admin_data = g.admin
    admin_data = {'username': 'creator'}

    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    Logger.debug(__name__, "add_role", "00", "Received request to add role", request_data)
    name = request_data['name'].strip()
    privileges = request_data['privileges'].strip()

    # Validate request data
    if not isinstance(privileges, dict):
        Logger.warn(__name__, "add_role", "01", "Privileges is not a dict. Type: [%s]" % type(privileges))
        return JsonResponse.bad_request()

    # Build role object
    role_request = {
        'name': name,
        'privileges': privileges,
        'created_by': admin_data['username']
    }

    Logger.debug(__name__, "add_role", "00", "Adding role [%s]" % name)
    try:
        role_data = RoleService.add_role(role_request)
        Logger.info(__name__, "add_role", "00", "Role [%s] saved successfully!" % name)
    except Exception as ex:
        Logger.warn(__name__, "add_role", "01", "Could not save role [%s]: %s" % (name, ex))
        return JsonResponse.server_error('Role could not be saved')

    return JsonResponse.success(data=role_data)


@api.route('/v1/roles', methods=['GET'])
def get_roles():
    Logger.debug(__name__, "get_roles", "00", "Received request to get roles")
    params = request.args.to_dict()
    Logger.debug(__name__, "get_roles", "00", "Param(s) received: %s" % params)
    minimal = False
    paginate = True

    if 'minimal' in params:
        minimal = params.pop('minimal').lower() == 'true'
    if 'paginate' in params:
        paginate = params.pop('paginate').lower() != 'false'

    role_list, nav = RoleService.find_roles(paginate=paginate, minimal=minimal, **params)

    return JsonResponse.success(data=role_list, nav=nav)
