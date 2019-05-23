# decorators.py

import datetime
import json
import traceback
from functools import wraps

from flask import g
from flask import jsonify
from flask import request

from app.libs.logger import Logger
from app.models.administrator import Administrator
from app.models.administrator import Status as AdminStatus
from app.services.v1.administrator import AdministratorService
from app.services.v1.application import ApplicationService


class ApiRequest:

    def json(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            request_headers = dict(request.headers)
            if 'Content-Type' not in request_headers or 'application/json' not in request_headers['Content-Type']:
                return jsonify(code='02', msg='This API requires JSON')
            elif request.data is None:
                return jsonify(code='02', msg='No JSON data')

            try:
                json_data = json.loads(request.data.decode('utf8'))
            except Exception:
                return jsonify(code='02', msg='Malformed JSON')

            return func(*args, **kwargs)

        return wrapper

    def api_authenticate(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            Logger.debug(__name__, "api_authenticate", "00", "Authenticating application")
            request_headers = dict(request.headers)
            Logger.debug(__name__, "api_authenticate", "00", "Request Headers: %s" % request_headers)

            if not request_headers or 'App-Token' not in request_headers:
                return jsonify(code='03', msg='Unauthorized')

            # Get application authentication header value
            api_key = request_headers['App-Token']

            # Find application and verify that application is ACTIVE
            application_data = ApplicationService.find_by_api_key(api_key, minimal=True)
            if application_data is None:
                Logger.error(__name__, "api_authenticate", "02", "Invalid API Key in request")
                return jsonify(code='03', msg='Unauthorized')
            elif not application_data['active']:
                Logger.warn(__name__, "api_authenticate", "01", "Application is not active")
                return jsonify(code='04', msg='Forbidden')

            # Check if application is restricted to a set of IPs
            # If yes, check if the source IP is allowed to access API
            if '*' not in application_data['allowed_ips']:
                client_ip = request.remote_addr
                if client_ip not in application_data['allowed_ips']:
                    Logger.warn(__name__, "api_authenticate", "01", "Source IP [%s] not allowed to consume API" % client_ip)
                    return jsonify(code='04', msg='Forbidden')

            return func(*args, **kwargs)

        return wrapper

    def user_authenticate(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            Logger.debug(__name__, "user_authenticate", "00", "Authenticating User")
            request_headers = dict(request.headers)
            Logger.debug(__name__, "user_authenticate", "00", "Request Headers: %s" % request_headers)
            if not request_headers:
                return jsonify(code='03', msg='Unauthorized')
            elif 'Token' not in request_headers or 'User' not in request_headers:
                return jsonify(code='03', msg='Unauthorized')

            # Get user authentication header values
            token = request_headers['Token']
            user = request_headers['User']

            # Find user and verify that user is ACTIVE
            user_data = AdministratorService.find_by_username(user, include_password=True)
            if user_data is None:
                Logger.error(__name__, "user_authenticate", "02", "Valid session found but user not found")
                return jsonify(code='03', msg='Unauthorized')
            elif user_data['status'] != AdminStatus.ACTIVE.value:
                Logger.warn(__name__, "user_authenticate", "01", "User is not active. Status: [%s]" % user_data['status'])
                return jsonify(code='04', msg='Forbidden')

            # Check if user's institution is active
            if user_data['institution'] is None:
                Logger.warn(__name__, "user_authenticate", "01", "User institution [%s] not found" % user_data['institution'])
                return jsonify(code='04', msg='User institution not found')
            elif not user_data['institution']['active']:
                Logger.warn(__name__, "user_authenticate", "01", "User institution [%s] is not active" % user_data['institution'])
                return jsonify(code='04', msg='User institution is not active')

            # Set request context attributes
            g.admin = user_data

            return func(*args, **kwargs)

        return wrapper

    def admin_authenticate(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            Logger.debug(__name__, "admin_authenticate", "00", "Authenticating super_admin/admin")
            request_headers = dict(request.headers)
            Logger.debug(__name__, "admin_authenticate", "00", "Request Headers: %s" % request_headers)
            if not request_headers:
                return jsonify(code='03', msg='Unauthorized')
            elif 'Token' not in request_headers or 'User' not in request_headers:
                return jsonify(code='03', msg='Unauthorized')

            # Get user authentication header values
            token = request_headers['Token']
            user = request_headers['User']

            # Find user and verify that user has admin rights and is ACTIVE
            user_data = AdministratorService.find_by_username(user, include_password=True)
            if user_data is None:
                Logger.error(__name__, "admin_authenticate", "02", "Valid session found but user not found")
                return jsonify(code='03', msg='Unauthorized')
            elif user_data['status'] != AdminStatus.ACTIVE.value:
                Logger.warn(__name__, "admin_authenticate", "01", "User is not active. Status: [%s]" % user_data['status'])
                return jsonify(code='04', msg='Forbidden')

            # Check if user's institution is active
            if user_data['institution'] is None:
                Logger.warn(__name__, "user_authenticate", "01", "User institution [%s] not found" % user_data['institution'])
                return jsonify(code='04', msg='User institution not found')
            elif not user_data['institution']['active']:
                Logger.warn(__name__, "user_authenticate", "01", "User institution [%s] is not active" % user_data['institution'])
                return jsonify(code='04', msg='User institution is not active')

            # Set request context attributes
            g.admin = user_data

            return func(*args, **kwargs)

        return wrapper

    def required_body_params(self, *required_params):
        """
        Utility function for checking request body parameters flagged as required
        """
        def wrapper(f):

            @wraps(f)
            def wrapped(*args, **kwargs):
                Logger.debug(__name__, "required_body_params", "00", "Required Parameter(s): {}".format(required_params))
                try:
                    # extract the json body into a python dict
                    request_data = json.loads(request.data.decode('utf-8'))
                except Exception as e:
                    traceback.print_exc()
                    Logger.error(__name__, "required_body_params", "02", "Malformed JSON Body passed", traceback.format_exc())
                    response = {'code': '02', 'msg': 'Malformed JSON', 'data': {}}
                    return jsonify(**response), 200

                # check the parameters received against the required parameters, add missing/blank parameters to list
                missing_params = []
                for param in required_params:
                    if param not in request_data or str(request_data[param]) == '':
                        missing_params.append(param)

                # display the missing parameters
                if len(missing_params) > 0:
                    response = {'code': '02',
                                'msg': 'Missing and/or blank parameters: {}'.format(', '.join(missing_params))
                                }
                    return jsonify(**response), 200
                return f(*args, **kwargs)

            return wrapped

        return wrapper

    def required_form_params(self, *required_params):
        """
        Utility function for checking request body parameters flagged as required
        """
        def wrapper(f):

            @wraps(f)
            def wrapped(*args, **kwargs):
                Logger.debug(__name__, "required_form_params", "00", "Required Parameter(s): {}".format(required_params))
                try:
                    # extract form data into python dict
                    form_data = dict(request.form)
                except Exception as e:
                    traceback.print_exc()
                    Logger.error(__name__, "required_form_params", "02", "Invalid form data", traceback.format_exc())
                    response = {'code': '02', 'msg': 'Invalid form', 'data': {}}
                    return jsonify(**response), 200

                # check the parameters received against the required parameters, add missing/blank parameters to list
                missing_params = []
                for param in required_params:
                    if param not in form_data or str(form_data[param]) == '':
                        missing_params.append(param)

                # display the missing parameters
                if len(missing_params) > 0:
                    response = {'code': '02',
                                'msg': 'Missing and/or blank parameters: {}'.format(', '.join(missing_params))
                                }
                    return jsonify(**response), 200
                return f(*args, **kwargs)

            return wrapped

        return wrapper

    def required_query_params(self, *required_params):
        """
        Utility function for checking request body parameters flagged as required
        """
        def wrapper(f):

            @wraps(f)
            def wrapped(*args, **kwargs):
                Logger.debug(__name__, "required_query_params", "00", "Required Parameter(s): {}".format(required_params))
                try:
                    # extract the json body into a python dict
                    request_params = request.args.to_dict()
                except Exception as e:
                    traceback.print_exc()
                    Logger.error(__name__, "required_query_params", "02", "Error while getting query params", traceback.format_exc())
                    response = {'code': '02', 'msg': 'Could not get query parameters', 'data': {}}
                    return jsonify(**response), 200

                # check the parameters received against the required parameters, add missing/blank parameters to list
                missing_params = []
                for param in required_params:
                    if param not in request_params or str(request_params[param]) == '':
                        missing_params.append(param)

                # display the missing parameters
                if len(missing_params) > 0:
                    response = {
                        'code': '02',
                        'msg': 'Missing and/or blank parameters: {}'.format(', '.join(missing_params))
                    }
                    return jsonify(**response), 200
                return f(*args, **kwargs)

            return wrapped

        return wrapper