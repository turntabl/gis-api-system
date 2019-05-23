# institution.py

import json
import traceback

from flask import g
from flask import request

from app.config import config
from app.controllers import api
from app.controllers import api_request
from app.controllers import JsonResponse
from app.libs.logger import Logger
from app.models.institution import Status
from app.services.v1.administrator import AdministratorService
from app.services.v1.branch import BranchService
from app.services.v1.institution import InstitutionService
from app.libs.utils import Utils


@api.route('/v1/institutions', methods=['POST'])
# @api_request.admin_authenticate
@api_request.json
@api_request.required_body_params('name', 'country', 'short_name', 'contact_email', 'username', 'first_name', 'last_name')
def add_institution():
    # admin_data = g.user
    admin_data = {'username': 'creator'}
    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    Logger.debug(__name__, "add_institution", "00", "Received request to add institution", request_data)
    inst_short_name = request_data['short_name'].strip()
    email = request_data['contact_email']
    phone_numbers = request_data['phone_numbers']
    username = request_data['username']
    # default_branch_name = request_data['default_branch_name'].strip()

    # if admin_data['user_type'] != UserType.SUPER_ADMIN.value:
    #     Logger.warn(__name__, "add_institution", "01", "This user type cannot add institution")
    #     return JsonResponse.forbidden()

    # Validate email
    if not Utils.is_valid_email(email):
        Logger.warn(__name__, "add_institution", "01", "Invalid email address: [%s]" % email)
        return JsonResponse.bad_request('Invalid email address')

    # Validate phone_numbers
    if not isinstance(phone_numbers, list):
        Logger.warn(__name__, "add_institution", "01", "Phone number must be a list, got %s" % type(phone_numbers))
        return JsonResponse.bad_request('Phone numbers must be a list')

    # Check if short name exists
    existing_institution = InstitutionService.get_by_short_name(inst_short_name)
    if existing_institution is not None:
        Logger.warn(__name__, "add_institution", "01",
                    "Institution with short name [%s] already exists" % inst_short_name)
        return JsonResponse.failed('Institution with short name already exists')

    # Add institution
    Logger.debug(__name__, "add_institution", "00", "Adding institution [%s]" % inst_short_name)
    try:
        institution_data = InstitutionService.add_institution(request_data)
        if institution_data is None:
            Logger.warn(__name__, "add_institution", "01", "Institution [%s] could not be saved" % inst_short_name)
            return JsonResponse.server_error('Institution could not be added')
        Logger.info(__name__, "add_institution", "00", "Institution [%s] added!" % inst_short_name)
    except Exception as ex:
        Logger.error(__name__, "add_institution", "02", "Error while adding institution: %s" % ex)
        return JsonResponse.server_error('Institution could not be saved')

    # Create ALL branch for institution
    branch_req = {
        'name': 'All branches',
        'branch_id': 'ALL',
        'institution': institution_data['id'],
        'created_by': admin_data['username']
    }
    try:
        branch_data = BranchService.add_branch(branch_req)
        if branch_data is None:
            Logger.error(__name__, "add_institution", "02", "Default branch for institution [%s] could not be added" % (inst_short_name))
            return JsonResponse.server_error('Could not add default branch for institution')
    except Exception as ex:
        Logger.error(__name__, "add_institution", "02", "Could not add default branch for institution [%s]: %s" % (inst_short_name, ex))
        return JsonResponse.server_error('Could not add default branch for institution')

    # Generate random password for first time login
    random_password = Utils.generate_alphanum_password()
    Logger.debug(__name__, "add_institution", "00", "Generated user [%s] password: [%s]" % (username, random_password))

    # Save user with hashed password
    hashed_password = Utils.hash_password(random_password)

    # Add default admin
    admin_req = {
        'first_name': request_data['first_name'],
        'last_name': request_data['last_name'],
        'email': email,
        'username': username,
        'password': hashed_password,
        'institution': institution_data['id'],
        'branch': branch_data['id'],
        'role': 'defaultRole',
        'phone_number': request_data.get('contact_phone')
    }
    try:
        new_admin_data = AdministratorService.add_administrator(admin_req)
        if new_admin_data is None:
            Logger.warn(__name__, "add_institution", "01", "Institution created, but creating admin failed")
            return JsonResponse.server_error('Institution and branch created, but admin could not be created')
    except Exception as ex:
        Logger.warn(__name__, "add_institution", "01", "Institution created, but creating admin failed: %s" % ex)
        return JsonResponse.server_error('Institution and branch created, but admin could not be created')

    try:
        Utils.send_email_confirmation(email, username, random_password)
    except Exception:
        Logger.error(__name__, "add_institution", "02",
                     "Error while sending confirmation email to [%s]" % email, traceback.format_exc())
        return JsonResponse.new_user_not_notified('Admin created, but notification could not be sent. Kindly resend notification')

    # Build response data
    data = {'institution': institution_data, 'user': new_admin_data}

    return JsonResponse.success(data=data)


@api.route('/v1/institutions', methods=['GET'])
# @api_request.admin_authenticate
def get_institutions():
    # admin_data = g.admin
    # admin_inst_data = admin_data['institution']

    Logger.debug(__name__, "get_institutions", "00", "Received request to get institutions")
    params = request.args.to_dict()
    Logger.debug(__name__, "get_institutions", "00", "Param(s) received: %s" % params)
    minimal = False
    paginate = True

    if 'minimal' in params:
        minimal = params.pop('minimal').lower() == 'true'
    if 'paginate' in params:
        paginate = params.pop('paginate').lower() != 'false'

    institutions_list, nav = InstitutionService.find_institutions(paginate=paginate, minimal=minimal, **params)

    return JsonResponse.success(data=institutions_list, nav=nav)


@api.route('/v1/institutions/<institution_id>', methods=['GET'])
# @api_request.admin_authenticate
def get_institution(institution_id):
    # admin_data = g.admin
    # admin_inst_data = admin_data['institution']

    Logger.debug(__name__, "get_institution", "00", "Received request to get institution [%s]" % institution_id)

    institution_data = InstitutionService.get_by_id(institution_id)
    Logger.info(__name__, "get_institution", "00", "Institution [%s] found!" % institution_id)

    return JsonResponse.success(data=institution_data)


@api.route('/v1/institutions/<institution_id>', methods=['PUT'])
@api_request.admin_authenticate
@api_request.json
def update_institution_profile(institution_id):
    # admin_data = g.admin
    admin_data = {'username': 'creator'}

    # if admin_data['user_type'] != UserType.SUPER_ADMIN.value:
    #     Logger.warn(__name__, "update_institution_profile", "01", "This user type cannot update institution profile")
    #     return JsonResponse.forbidden()

    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    name = request_data.get('name')
    contact_email = request_data.get('contact_email')
    phone_numbers = request_data.get('phone_numbers')

    # Validate body params
    if name is None and contact_email is None and phone_numbers is None:
        Logger.warn(__name__, "update_institution_profile", "01", "Name, contact email nor phone numbers not present in request")
        return JsonResponse.failed('Nothing to update')
    elif not isinstance(name, str):
        Logger.warn(__name__, "update_institution_profile", "01", "Name is not string: [%s]" % name)
        return JsonResponse.bad_request('Invalid name')
    elif contact_email is not None and not Utils.is_valid_email(contact_email):
        Logger.warn(__name__, "update_institution_profile", "01", "Invalid contact email: [%s]" % contact_email)
        return JsonResponse.bad_request('Invalid contact email')
    elif phone_numbers is not None and not isinstance(phone_numbers, list):
        Logger.warn(__name__, "update_institution_profile", "01", "Invalid phone number list: [%s]" % phone_numbers)
        return JsonResponse.bad_request('Invalid phone number list')

    # Check if institution exists
    inst_to_update = InstitutionService.get_by_id(institution_id)
    if inst_to_update is None:
        Logger.warn(__name__, "update_institution_profile", "01", "Institution [%s] does not exist" % institution_id)
        return JsonResponse.failed('Institution does not exist')
    if inst_to_update['status'] != Status.ACTIVE.value:
        Logger.warn(__name__, "update_institution_profile", "01", "Institution [%s] is not active" % institution_id)
        return JsonResponse.failed('Institution is not active')

    update_data = {}
    if name is not None and name != inst_to_update['name']:
        update_data['name'] = name

    if contact_email is not None and contact_email != inst_to_update['contact_email']:
        update_data['contact_email'] = contact_email

    if phone_numbers is not None and phone_numbers != inst_to_update['contact_phone']:
        update_data['phone_numbers'] = phone_numbers

    # If update_data dict is empty, nothing to update - return error
    if not update_data:
        Logger.warn(__name__, "update_institution_profile", "01", "Nothing to update, new value(s) may be the same as existing data")
        return JsonResponse.failed('Nothing to update')

    try:
        updated_institution_data = InstitutionService.update_institution(institution_id, update_data)
    except Exception as ex:
        Logger.error(__name__, "update_institution_profile", "02", "Error while updating institution: %s" % ex)
        return JsonResponse.server_error('Institution update failed')

    return JsonResponse.success('Institution updated successfully!', data=updated_institution_data)


@api.route('/v1/institutions/<institution_id>/status', methods=['PUT'])
@api_request.admin_authenticate
@api_request.json
@api_request.required_body_params('active')
def update_institution_status(institution_id):
    # Get user data from request context
    admin_data = g.user
    admin_username = admin_data['username']
    Logger.debug(__name__, "update_institution_status", "00",
                 "Admin [%s] requesting to change institution [%s] status" % (admin_username, institution_id))

    # if admin_data['user_type'] != UserType.SUPER_ADMIN.value:
    #     Logger.warn(__name__, "update_institution_status", "01", "This user type cannot update institution status")
    #     return JsonResponse.forbidden()

    request_data = json.loads(request.data.decode('utf-8'))
    status = request_data['status'].strip().upper()

    # Validate 'status' parameter
    if not isinstance(status, str):
        Logger.warn(__name__, "update_institution_status", "01", "Type for status parameter [%s]: [%s]" % (status, type(status)))
        return JsonResponse.bad_request()

    # Find institution to update
    institution_data = InstitutionService.get_by_id(institution_id)
    if institution_data is None:
        Logger.warn(__name__, "update_institution_status", "01", "Institution to update not found")
        return JsonResponse.failed('Institution does not exist')

    # Prevent super admin from deactivating him/her own institution
    if admin_data['institution']['id'] == institution_id:
        Logger.warn(__name__, "update_institution_status", "01", "Admin cannot update status of their own institution")
        return JsonResponse.failed("You cannot update status your own institution")

    if institution_data['status'] == status:
        Logger.warn(__name__, "update_institution_status", "01", "Nothing to change. Institution is already %s" % status)
        return JsonResponse.failed('Institution is already %s' % status.lower())

    try:
        institution_data = InstitutionService.update_institution(institution_id, {'status': status})
        Logger.info(__name__, "update_institution_status", "00",
                    "Institution [%s] set to %s by admin [%s]" % (institution_id, status, admin_username))
    except Exception as ex:
        Logger.warn(__name__, "update_institution_status", "01", "Error occurred while updating institution status: %s" % ex)
        return JsonResponse.server_error('Updating institution status failed')

    resp_msg = 'Institution set to %s successfully!' % status.lower()
    return JsonResponse.success(resp_msg, data=institution_data)
