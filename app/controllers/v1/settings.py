# settings.py

import json

from flask import request

from app.config import config
from app.controllers import api
from app.controllers import api_request
from app.controllers import JsonResponse
from app.libs.logger import Logger
from app.services.v1.settings import SettingsService


@api.route('/v1/settings', methods=['PUT'])
# @api_request.api_authenticate
# @api_request.admin_authenticate('settings.manage_settings')
@api_request.json
def add_or_update_settings():
    admin_data = {'username': 'creator'}
    request_data = json.loads(request.data.decode('utf-8'))
    Logger.debug(__name__, "add_or_update_settings", "00", "Received request to add or update settings", request_data)
    pre_approval_expiry_hours = request_data.get('pre_approval_expiry_hours') or config.PRE_APPROVAL_EXPIRY_HOURS
    approval_expiry_hours = request_data.get('approval_expiry_hours') or config.APPROVAL_EXPIRY_HOURS
    approval_reminder_interval = request_data.get('approval_reminder_interval') or config.APPROVAL_REMINDER_INTERVAL
    approval_reminder_frequency = request_data.get('approval_reminder_frequency') or config.APPROVAL_REMINDER_FREQUENCY

    # Validate request data
    params = ['pre_approval_expiry_hours', 'approval_expiry_hours', 'approval_reminder_interval', 'approval_reminder_frequency']
    parsed_data = {}
    for param in params:
        try:
            parsed_data[param] = int(request_data[param])
        except ValueError:
            Logger.warn(__name__, "add_or_update_settings", "01", "Invalid value for %s" % param)
            return JsonResponse.bad_request()

    # Check if settings already exist
    existing_settings = SettingsService.find_one()

    # If settings exist, add else update
    if not existing_settings:
        try:
            settings_data = SettingsService.add_settings(parsed_data)
            Logger.info(__name__, "add_or_update_settings", "00", "Settings added successfully!")
        except Exception as ex:
            Logger.error(__name__, "add_or_update_settings", "02", "Error while adding settings: %s" % ex)
            return JsonResponse.server_error('Settings could not be added')
    else:
        try:
            settings_data = SettingsService.update_settings(existing_settings['id'], parsed_data)
            Logger.info(__name__, "add_or_update_settings", "00", "Settings updated successfully!")
        except Exception as ex:
            Logger.error(__name__, "add_or_update_settings", "02", "Error while adding settings: %s" % ex)
            return JsonResponse.server_error('Settings could not be updated')

    return JsonResponse.success(data=settings_data)


@api.route('/v1/settings', methods=['GET'])
# @api_request.api_authenticate
# @api_request.admin_authenticate('settings.view_settings')
def get_settings():
    # admin_data = g.admin

    Logger.debug(__name__, "get_settings", "00", "Received request to get settings")

    settings_data = SettingsService.find_one()
    if not settings_data:
        Logger.warn(__name__, "get_settings", "01", "Settings could not be found")
        return JsonResponse.failed('Settings does not exist')
    Logger.info(__name__, "get_settings", "00", "Settings found!")

    return JsonResponse.success(data=settings_data)
