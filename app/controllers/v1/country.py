# country.py

import json

from flask import request

from app.controllers import api
from app.controllers import api_request
from app.controllers import JsonResponse
from app.libs.logger import Logger
from app.services.v1.country import CountryService


@api.route('/v1/countries', methods=['POST'])
@api_request.required_body_params('name', 'code', 'url')
def add_country():
    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    country_code = request_data['code']
    Logger.debug(__name__, "add_country", "00", "Received request to add country", request_data)

    existing_country = CountryService.get_country_by_code(country_code)
    if existing_country is not None:
        Logger.warn(__name__, "add_country", "01", "Country with code [%s] already exists" % country_code)
        return JsonResponse.failed('Country with code %s already exists' % country_code)

    try:
        country_data = CountryService.add_country(request_data)
    except Exception as ex:
        Logger.warn(__name__, "add_country", "00", "Error occurred while adding country: %s" % ex)
        return JsonResponse.server_error('Country could not be added')

    if country_data is None:
        Logger.warn(__name__, "add_country", "00", "Country was not added")
        return JsonResponse.server_error('Country was not added')

    return JsonResponse.success(data=country_data)


@api.route('/v1/countries/<country_id>', methods=['GET'])
def get_country(country_id):
    Logger.debug(__name__, "get_country", "00", "Received request to get country [%s]" % country_id)

    country_data = CountryService.get_country_by_id(country_id)
    if country_data is None:
        Logger.warn(__name__, "get_country", "01", "Country [%s] does not exist" % country_id)
        return JsonResponse.failed('Country does not exist')

    return JsonResponse.success(data=country_data)


@api.route('/v1/countries', methods=['GET'])
def get_countries():
    Logger.debug(__name__, "get_countries", "00", "Received request to get countries")
    params = request.args.to_dict()
    Logger.debug(__name__, "get_countries", "00", "Param(s) received: %s" % params)
    minimal = False
    paginate = True

    if 'minimal' in params:
        minimal = params.pop('minimal').lower() == 'true'
    if 'paginate' in params:
        paginate = params.pop('paginate').lower() != 'false'

    country_list, nav = CountryService.find(paginate=paginate, minimal=minimal, **params)

    return JsonResponse.success(data=country_list, nav=nav)


@api.route('/v1/countries/<country_id>/status',  methods=['PUT'])
@api_request.json
@api_request.required_body_params('active')
def update_country_status(country_id):
    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    active = request_data['active']
    Logger.debug(__name__, "update_country_status", "00", "Received request to update country status", request_data)

    # Validate active value
    if not isinstance(active, bool):
        Logger.warn(__name__, "update_country_status", "01", "Type for active attribute [%s]: [%s]" % (active, type(active)))
        return JsonResponse.bad_request('Invalid status')

    # Get country to update
    country_data = CountryService.get_country_by_id(country_id)
    if country_data is None:
        Logger.warn(__name__, "update_country_status", "01", "Country [%s] does not exist" % country_id)
        return JsonResponse.failed('Country does not exist')

    if country_data['active'] == active:
        Logger.warn(__name__, "update_country_status", "01", "Country [%s] is already %s" % (country_id, "active" if active else "not active"))
        return JsonResponse.failed('Country is already %s' % ('active' if active else 'not active'))

    # Update status
    try:
        country_data = CountryService.update_country(country_id, {'active': active})
        Logger.info(__name__, "update_country_status", "00", "Country [%s] %s successfully" % (country_data['code'], "activated" if active else "deactivated"))
    except Exception as ex:
        Logger.warn(__name__, "update_country_status", "01", "Error while updating country status: %s" % ex)
        return JsonResponse.server_error('Country could not be %s' % 'activated' if active else 'deactivated')

    return JsonResponse.success(data=country_data)