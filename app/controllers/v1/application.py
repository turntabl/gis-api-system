# application.py

import json

from flask import request

from app.controllers import api
from app.controllers import api_request
from app.controllers import JsonResponse
from app.libs.logger import Logger
from app.libs.utils import GeneratorUtils
from app.services.v1.application import ApplicationService


@api.route('/v1/applications', methods=['POST'])
@api_request.json
@api_request.required_body_params('name')
def add_application():
    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    Logger.debug(__name__, "add_application", "00", "Received request to add application", request_data)
    name = request_data['name'].strip()

    # Generate api key
    api_key = GeneratorUtils.generate_api_key()

    # Build application object
    app_request = {
        'name': name,
        'api_key': api_key,
        'allowed_ips': request_data.get('allowed_ips') or [],
        'functions': request_data.get('functions') or []
    }

    Logger.debug(__name__, "add_application", "00", "Adding application [%s]" % name)
    try:
        application_data = ApplicationService.add_application(app_request)
        Logger.info(__name__, "add_application", "00", "Application [%s] saved successfully!" % name)
    except Exception as ex:
        Logger.warn(__name__, "add_application", "01", "Could not save application [%s]: %s" % (name, ex))
        return JsonResponse.server_error('Application could not be saved')

    return JsonResponse.success(data=application_data)


@api.route('/v1/applications', methods=['GET'])
def get_applications():
    Logger.debug(__name__, "get_applications", "00", "Received request to get applications")
    params = request.args.to_dict()
    Logger.debug(__name__, "get_applications", "00", "Param(s) received: %s" % params)
    minimal = False
    paginate = True

    if 'minimal' in params:
        minimal = params.pop('minimal').lower() == 'true'
    if 'paginate' in params:
        paginate = params.pop('paginate').lower() != 'false'

    application_list, nav = ApplicationService.find_applications(paginate=paginate, minimal=minimal, **params)

    return JsonResponse.success(data=application_list, nav=nav)


@api.route('/v1/applications/<application_id>', methods=['GET'])
def get_application(application_id):
    Logger.debug(__name__, "get_application", "00", "Received request to get application [%s]" % application_id)

    application_data = ApplicationService.get_by_id(application_id)
    if application_data is None:
        Logger.warn(__name__, "get_application", "01", "Application [%s] does not exist" % application_id)
        return JsonResponse.failed('Application does not exist')

    return JsonResponse.success(data=application_data)


@api.route('/v1/applications/<application_id>', methods=['PUT'])
# @api_request.admin_authenticate
@api_request.json
def update_application(application_id):
    # admin_data = g.admin
    admin_data = {'username': 'creator'}

    # if admin_data['user_type'] != UserType.SUPER_ADMIN.value:
    #     Logger.warn(__name__, "update_application", "01", "This user type cannot update institution profile")
    #     return JsonResponse.forbidden()

    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    name = request_data.get('name')
    allowed_ips = request_data.get('allowed_ips')
    functions = request_data.get('functions')

    # Validate body params
    if name is None and allowed_ips is None and functions is None:
        Logger.warn(__name__, "update_application", "01", "Name, allowed IPs nor functions not present in request")
        return JsonResponse.failed('Nothing to update')
    elif not isinstance(name, str):
        Logger.warn(__name__, "update_application", "01", "Name is not string: [%s]" % name)
        return JsonResponse.bad_request('Invalid name')
    elif allowed_ips is not None and not isinstance(allowed_ips, list):
        Logger.warn(__name__, "update_application", "01", "Invalid allowed IPs: [%s]" % allowed_ips)
        return JsonResponse.bad_request('Invalid value for allowed IPs')
    elif functions is not None and not isinstance(functions, list):
        Logger.warn(__name__, "update_application", "01", "Invalid functions: [%s]" % functions)
        return JsonResponse.bad_request('Invalid value for functions')

    # Check if application exists
    app_to_update = ApplicationService.get_by_id(application_id)
    if app_to_update is None:
        Logger.warn(__name__, "update_application", "01", "Application [%s] does not exist" % application_id)
        return JsonResponse.failed('Application does not exist')
    if not app_to_update['active']:
        Logger.warn(__name__, "update_application", "01", "Application [%s] is not active" % application_id)
        return JsonResponse.failed('Application is not active')

    update_data = {}
    if name is not None and name != app_to_update['name']:
        update_data['name'] = name

    if allowed_ips is not None and allowed_ips != app_to_update['allowed_ips']:
        update_data['allowed_ips'] = allowed_ips

    if functions is not None and functions != app_to_update['functions']:
        update_data['functions'] = functions

    # If update_data dict is empty, nothing to update - return error
    if not update_data:
        Logger.warn(__name__, "update_application", "01", "Nothing to update, new value(s) may be the same as existing data")
        return JsonResponse.failed('Nothing to update')

    try:
        updated_app_data = ApplicationService.update_application(application_id, update_data)
    except Exception as ex:
        Logger.error(__name__, "update_application", "02", "Error while updating application [%s]: %s" % (application_id, ex))
        return JsonResponse.server_error('Application update failed')

    return JsonResponse.success(msg='Application updated successfully!', data=updated_app_data)


@api.route('/v1/applications/<application_id>/status',  methods=['PUT'])
@api_request.json
@api_request.required_body_params('active')
def update_application_status(application_id):
    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    active = request_data['active']
    Logger.debug(__name__, "update_application_status", "00", "Received request to update application [%s] status" % application_id, request_data)

    # Validate active value
    if not isinstance(active, bool):
        Logger.warn(__name__, "update_application_status", "01", "Type for active attribute [%s]: [%s]" % (active, type(active)))
        return JsonResponse.bad_request('Invalid status')

    # Get application to update
    application_data = ApplicationService.get_by_id(application_id)
    if application_data is None:
        Logger.warn(__name__, "update_application_status", "01", "Application [%s] does not exist" % application_id)
        return JsonResponse.failed('Application does not exist')

    if application_data['active'] == active:
        Logger.warn(__name__, "update_application_status", "01", "Application [%s] is already %s" % (application_id, "active" if active else "not active"))
        return JsonResponse.failed('Application is already %s' % ('active' if active else 'not active'))

    # Update status
    Logger.debug(__name__, "update_application_status", "00", "Setting application [%s] active to [%s]" % (application_id, active))
    try:
        application_data = ApplicationService.update_application(application_id, {'active': active})
        Logger.info(__name__, "update_application_status", "00", "Application [%s] %s successfully" % (application_id, "activated" if active else "deactivated"))
    except Exception as ex:
        Logger.error(__name__, "update_application_status", "02", "Could not update application [%s] status: %s" % (application_id, ex))
        return JsonResponse.server_error('Application could not be %s' % 'activated' if active else 'deactivated')

    return JsonResponse.success(data=application_data)
