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
@api_request.api_authenticate
@api_request.admin_authenticate('roles.add_role')
@api_request.json
@api_request.required_body_params('name', 'privileges')
def add_role():
    admin_data = g.admin

    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    Logger.debug(__name__, "add_role", "00", "Received request to add role", request_data)
    name = request_data['name'].strip()
    privileges = request_data['privileges']

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
@api_request.api_authenticate
@api_request.admin_authenticate('roles.view_role')
def get_roles():
    admin_data = g.admin
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


@api.route('/v1/roles/<role_id>', methods=['GET'])
@api_request.api_authenticate
@api_request.admin_authenticate('roles.view_role')
def get_role(role_id):
    admin_data = g.admin

    Logger.debug(__name__, "get_role", "00", "Received request to get role [%s]" % role_id)

    role_data = RoleService.get_by_id(role_id)
    if role_data is None:
        Logger.warn(__name__, "get_role", "01", "Role [%s] could not be found" % role_id)
        return JsonResponse.failed('Role does not exist')
    Logger.info(__name__, "get_role", "00", "Role [%s] found!" % role_id)

    return JsonResponse.success(data=role_data)


@api.route('/v1/roles/<role_id>', methods=['PUT'])
@api_request.api_authenticate
@api_request.admin_authenticate('roles.update_role')
@api_request.json
def update_role(role_id):
    admin_data = g.admin

    # if admin_data['user_type'] != UserType.SUPER_ADMIN.value:
    #     Logger.warn(__name__, "update_role", "01", "This user type cannot update institution profile")
    #     return JsonResponse.forbidden()

    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    name = request_data.get('name')
    privileges = request_data.get('privileges')

    # Validate body params
    if name is None and privileges is None:
        Logger.warn(__name__, "update_role", "01", "Neither name nor privileges present in request")
        return JsonResponse.failed('Nothing to update')
    elif not isinstance(name, str):
        Logger.warn(__name__, "update_role", "01", "Name is not string: [%s]" % name)
        return JsonResponse.bad_request('Invalid name')
    elif not isinstance(privileges, dict):
        Logger.warn(__name__, "update_role", "01", "Privileges is not a dict. Type: [%s]" % type(privileges))
        return JsonResponse.bad_request()

    # Check if role exists
    role_to_update = RoleService.get_by_id(role_id)
    if role_to_update is None:
        Logger.warn(__name__, "update_role", "01", "Role [%s] does not exist" % role_id)
        return JsonResponse.failed('Role does not exist')

    update_data = {}
    if name is not None and name != role_to_update['name']:
        update_data['name'] = name

    if privileges is not None and privileges != role_to_update['privileges']:
        update_data['privileges'] = privileges

    # If update_data dict is empty, nothing to update - return error
    if not update_data:
        Logger.warn(__name__, "update_role", "01", "Nothing to update, new value(s) may be the same as existing data")
        return JsonResponse.failed('Nothing to update')

    try:
        updated_role_data = RoleService.update_role(role_id, update_data)
    except Exception as ex:
        Logger.error(__name__, "update_role", "02", "Error while updating role [%s]: %s" % (role_id, ex))
        return JsonResponse.server_error('Role update failed')

    return JsonResponse.success('Role updated successfully!', data=updated_role_data)
