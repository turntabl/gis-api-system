# administrator.py

import json
import traceback

from flask import g
from flask import request

from app.controllers import api
from app.controllers import api_request
from app.controllers import JsonResponse
from app.errors.errors import InputError
from app.libs.logger import Logger
from app.libs.utils import Utils
from app.models.administrator import Status as AdminStatus
from app.models.branch import Status as BranchStatus
from app.models.institution import Status as InstitutionStatus
from app.services.v1.administrator import AdministratorService
from app.services.v1.branch import BranchService
from app.services.v1.institution import InstitutionService
from app.services.v1.role import RoleService


@api.route('/v1/admins', methods=['POST'])
# @api_request.admin_authenticate
@api_request.json
@api_request.required_body_params('first_name', 'last_name', 'email', 'username', 'role', 'institution', 'branch')
def add_administrator():
    admin_data = g.admin

    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    Logger.debug(__name__, "add_administrator", "00", "Received request to add admin", request_data)

    email = request_data['email']
    username = request_data['username'].strip()
    role = request_data['role']
    institution = request_data['institution']
    branch = request_data['branch']

    # Validate username, make sure it doesn't already exist
    Logger.debug(__name__, "add_administrator", "00", "Checking if admin with username [%s] already exist" % username)
    existing_admin = AdministratorService.find_by_username(username)
    if existing_admin is not None:
        Logger.warn(__name__, "add_administrator", "01", "Admin with username [%s] already exists" % username)
        return JsonResponse.bad_request('Admin with username already exist')
    Logger.info(__name__, "add_administrator", "00", "Admin with username [%s] does not exist" % username)

    # Validate email
    if not Utils.is_valid_email(email):
        Logger.warn(__name__, "add_administrator", "01", "Invalid email address: [%s]" % email)
        return JsonResponse.bad_request('Invalid email address')

    # Check if institution exists and is active
    Logger.debug(__name__, "add_administrator", "00", "Checking if institution [%s] exists" % institution)
    institution_data = InstitutionService.get_by_id(institution, minimal=True)
    if institution_data is None:
        Logger.warn(__name__, "add_administrator", "01", "Institution [%s] does not exists" % institution)
        return JsonResponse.failed('Institution does not exist')
    elif institution_data['status'] != InstitutionStatus.ACTIVE.value:
        Logger.warn(__name__, "add_administrator", "01", "Institution [%s] exists, but is %s" % (institution, institution_data['status']))
        return JsonResponse.failed('Institution is %s' % institution_data['status'].lower())
    Logger.info(__name__, "add_administrator", "00", "Institution [%s] exists and is active" % institution)

    # Check if branch exists, and belongs to institution in request and is active
    Logger.debug(__name__, "add_administrator", "00", "Checking if branch [%s] exists" % branch)
    branch_data = BranchService.get_institution_branch(institution, branch, minimal=True)
    if branch_data is None:
        Logger.warn(__name__, "add_administrator", "01", "Branch [%s] for institution [%s] does not exists" % (branch, institution))
        return JsonResponse.failed('Branch does not exist')
    elif branch_data['status'] != BranchStatus.ACTIVE.value:
        Logger.warn(__name__, "add_administrator", "01", "Branch [%s] exists, but is %s" % (branch, branch_data['status']))
        return JsonResponse.failed('Branch is %s' % branch_data['status'].lower())
    Logger.info(__name__, "add_administrator", "00", "Branch [%s] exists and is active" % branch)

    # Check if ROLE exists and is active
    Logger.debug(__name__, "add_administrator", "00", "Checking if role [%s] exists" % role)
    role_data = RoleService.get_by_id(role)
    if role_data is None:
        Logger.warn(__name__, "add_administrator", "01", "Role [%s] does not exist" % role)
        return JsonResponse.failed('Invalid role')
    Logger.info(__name__, "add_administrator", "00", "Role [%s] exists" % role)

    # Generate random password for first time login
    random_password = Utils.generate_alphanum_password()
    # Logger.debug(__name__, "add_administrator", "00", "Generated user [%s] password: [%s]" % (username, random_password))

    # Save user with hashed password
    hashed_password = Utils.hash_password(random_password)
    request_data['password'] = hashed_password

    try:
        new_admin_data = AdministratorService.add_administrator(request_data)
        if new_admin_data is None:
            Logger.warn(__name__, "add_administrator", "01", "Administrator [%s] could not be added" % username)
            return JsonResponse.server_error('Administrator could not be added')
    except Exception as ex:
        Logger.warn(__name__, "add_administrator", "01", "Could not add administrator [%s]: %s" % (username, ex))
        return JsonResponse.server_error('Administrator could not be added')

    Logger.debug(__name__, "add_administrator", "00", "Sending confirmation email to [%s]" % email)
    try:
        Utils.send_email_confirmation(email, username, random_password)
        Logger.info(__name__, "add_administrator", "00", "Confirmation email to [%s] successfully!" % email)
    except Exception:
        Logger.error(__name__, "add_administrator", "02",
                     "Error while sending confirmation email to [%s]" % email, traceback.format_exc())
        return JsonResponse.new_user_not_notified('Admin created, but notification could not be sent. Kindly resend notification')

    return JsonResponse.success(data=new_admin_data)


@api.route('/v1/administrators/setup', methods=['POST'])
@api_request.json
@api_request.required_body_params('username', 'old_password', 'new_password')
def setup_new_admin():
    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    Logger.debug(__name__, "setup_new_admin", "00", "Received request to add setup inactive admin [%s]" % request_data['username'])

    username = request_data['username'].strip()
    old_password = request_data['old_password'].strip()
    new_password = request_data['new_password'].strip()

    # Get administrator by username
    Logger.debug(__name__, "setup_new_admin", "00", "Getting administrator [%s]" % username)
    admin_data = AdministratorService.find_by_username_password(username, old_password)
    if admin_data is None:
        Logger.warn(__name__, "setup_new_admin", "01", "Invalid user [%s] and/or password" % username)
        return JsonResponse.failed('Invalid username and/or password')
    elif admin_data['status'] != AdminStatus.INACTIVE.value:
        Logger.warn(__name__, "setup_new_admin", "01", "Admin [%s] is not a new user. Status: [%s]" % (username, admin_data['status']))
        return JsonResponse.failed('Account has already been confirmed')

    # Check if password satisfies policy
    try:
        Utils.password_satisfies_policy(new_password)
    except InputError as ie:
        Logger.warn(__name__, "setup_new_admin", "01", "User failed policy check: %s" % ie.message)
        return JsonResponse.failed(ie.message)

    # Update user password and set status to ACTIVE
    hashed_password = Utils.hash_password(new_password)

    # Check if old_password is the same as new_password
    if old_password == new_password:
        Logger.warn(__name__, "setup_new_admin", "01", "Old password cannot be the same as new password")
        return JsonResponse.failed('New password cannot be the same as the old one')

    # Save password and save login session token
    admin_update = {
        'password': hashed_password,
        'status': AdminStatus.ACTIVE.value,
        'session_token': Utils.generate_session_token()
    }
    try:
        admin_data = AdministratorService.update_administrator(admin_data['id'], admin_update)
    except Exception as ex:
        Logger.warn(__name__, "setup_new_admin", "01", "Updating admin [%s] password failed: %s" % (username, ex))
        return JsonResponse.failed('Password could not be updated')

    return JsonResponse.success(msg='Admin setup successful!', data=admin_data)


@api.route('/v1/administrators', methods=['GET'])
@api_request.user_authenticate
def get_administrators():
    admin_data = g.admin
    institution_data = admin_data['institution']

    Logger.debug(__name__, "get_administrators", "00", "Received request to get administrators")
    params = request.args.to_dict()
    Logger.debug(__name__, "get_administrators", "00", "Param(s) received: %s" % params)
    minimal = False
    paginate = True

    if 'minimal' in params:
        minimal = params.pop('minimal').lower() == 'true'
    if 'paginate' in params:
        paginate = params.pop('paginate').lower() != 'false'

    # TODO: Limit administrators user can see depending on their institution and branch

    # if institution_data['short_name'] == config.PARENT_INST_SHORT_NAME and admin_data['user_type'] == UserType.SUPER_ADMIN.value:
    #     pass
    # elif admin_data['user_type'] == UserType.ADMIN.value:
    #     nsano_country_inst = config.PARENT_INST_SHORT_NAME + institution_data['country']
    #     if institution_data['short_name'] == nsano_country_inst:
    #         institution_ids = InstitutionService.get_institution_ids(country=institution_data['country'])
    #         params['country__in'] = institution_ids
    #     else:
    #         params['institution'] = institution_data['id']
    # else:
    #     params['institution'] = institution_data['id']

    admin_list, nav = AdministratorService.find_administrators(paginate=paginate, minimal=minimal, **params)

    return JsonResponse.success(data=admin_list, nav=nav)


@api.route('/v1/administrators/me', methods=['PUT'])
@api_request.user_authenticate
@api_request.json
def update_me():
    admin_data = g.admin

    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    first_name = request_data.get('first_name')
    last_name = request_data.get('last_name')

    if first_name is None and last_name is None:
        Logger.warn(__name__, "update_me", "01", "First name and/or last name not present in request")
        return JsonResponse.failed('Nothing to update')
    elif not isinstance(first_name, str):
        Logger.warn(__name__, "update_me", "01", "First name is not string: [%s]" % first_name)
        return JsonResponse.bad_request('Invalid first name')
    elif not isinstance(last_name, str):
        Logger.warn(__name__, "update_me", "01", "Last name is not string: [%s]" % last_name)
        return JsonResponse.bad_request('Invalid last name')

    update_data = {}
    if first_name is not None and first_name != admin_data['first_name']:
        update_data['first_name'] = first_name

    if last_name is not None and last_name != admin_data['last_name']:
        update_data['last_name'] = last_name

    # If update_data dict is empty, nothing to update - return error
    if not update_data:
        Logger.warn(__name__, "update_me", "01", "Nothing to update, new value(s) may be the same as existing data")
        return JsonResponse.failed('Nothing to update')

    try:
        updated_admin_data = AdministratorService.update_administrator(admin_data['id'], update_data)
    except Exception as ex:
        Logger.error(__name__, "update_me", "02", "Error while updating admin [%s]: %s" % (admin_data['username'], ex))
        return JsonResponse.server_error('Admin update failed')

    return JsonResponse.success('Admin updated successfully!', data=updated_admin_data)


@api.route('/v1/administrators/<admin_id>', methods=['PUT'])
@api_request.user_authenticate
@api_request.json
def update_admin_profile(admin_id):
    admin_data = g.admin
    institution_data = admin_data['institution']

    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    first_name = request_data.get('first_name')
    last_name = request_data.get('last_name')

    if first_name is None and last_name is None:
        Logger.warn(__name__, "update_admin_profile", "01", "First name and/or last name not present in request")
        return JsonResponse.failed('Nothing to update')
    elif not isinstance(first_name, str):
        Logger.warn(__name__, "update_admin_profile", "01", "First name is not string: [%s]" % first_name)
        return JsonResponse.bad_request('Invalid first name')
    elif not isinstance(last_name, str):
        Logger.warn(__name__, "update_admin_profile", "01", "Last name is not string: [%s]" % last_name)
        return JsonResponse.bad_request('Invalid last name')

    # Check if user exists
    admin_to_update = AdministratorService.get_by_id(admin_id)
    if admin_to_update is None:
        Logger.warn(__name__, "update_admin_profile", "01", "Admin [%s] does not exist" % admin_id)
        return JsonResponse.failed('Admin does not exist')
    if admin_to_update['status'] != AdminStatus.ACTIVE.value:
        Logger.warn(__name__, "update_admin_profile", "01", "Admin [%s] is not active. Status: [%s]" % (admin_id, admin_to_update['status']))
        return JsonResponse.failed('Admin is not active')

    # Check if admin user has access to perform update
    # if admin_data['user_type'] != UserType.SUPER_ADMIN.value:
    #     is_my_institution = institution_data['id'] == admin_to_update['institution']['id']
    #     if is_my_institution:
    #         if admin_data['user_type'] != UserType.ADMIN.value:
    #             Logger.warn(__name__, "update_admin_profile", "01", "User [%s] does not have enough privileges to update user" % admin_data['username'])
    #             return JsonResponse.forbidden('You cannot update this user\'s profile')
    #     else:
    #         Logger.warn(__name__, "update_admin_profile", "01", "User [%s] does not have enough privileges to update user" % admin_data['username'])
    #         return JsonResponse.forbidden('You cannot update this user\'s profile')

    update_data = {}
    if first_name is not None and first_name != admin_to_update['first_name']:
        update_data['first_name'] = first_name

    if last_name is not None and last_name != admin_to_update['last_name']:
        update_data['last_name'] = last_name

    # If update_data dict is empty, nothing to update - return error
    if not update_data:
        Logger.warn(__name__, "update_admin_profile", "01", "Nothing to update, new value(s) may be the same as existing data")
        return JsonResponse.failed('Nothing to update')

    try:
        updated_admin_data = AdministratorService.update_administrator(admin_id, update_data)
    except Exception as ex:
        Logger.error(__name__, "update_admin_profile", "02", "Error while updating admin [%s]: %s" % (admin_to_update['username'], ex))
        return JsonResponse.server_error('Admin update failed')

    return JsonResponse.success('Admin updated successfully!', data=updated_admin_data)


@api.route('/v1/administrators/<admin_id>/status', methods=['PUT'])
# @api_request.admin_authenticate
@api_request.json
@api_request.required_body_params('status')
def update_admin_status(admin_id):
    # Get user data from request context
    admin_data = g.user
    admin_username = admin_data['username']
    Logger.debug(__name__, "update_admin_status", "00",
                 "Admin [%s] requesting to change account [%s] status" % (admin_username, admin_id))

    request_data = json.loads(request.data.decode('utf-8'))
    status = request_data['status'].strip().upper()

    # Find admin to update
    admin_to_update = AdministratorService.get_by_id(admin_id)
    if admin_to_update is None:
        Logger.warn(__name__, "update_admin_status", "01", "Administrator to update not found")
        return JsonResponse.failed('Admin to update not found')

    # if admin_data['user_type'] != UserType.SUPER_ADMIN.value:
    #     if admin_data['institution']['id'] != admin_to_update['institution']['id']:
    #         Logger.warn(__name__, "update_admin_status", "01", "Attempting to update status of user of another account")
    #         return JsonResponse.forbidden()

    # Check if status is valid
    if status not in (AdminStatus.ACTIVE.value, AdminStatus.SUSPENDED.value):
        Logger.warn(__name__, "update_admin_status", "01", "Attempting to update to invalid status: [%s]" % status)
        return JsonResponse.failed('Cannot update admin to invalid status')
    # Prevent user deactivating him/herself
    if admin_data['id'] == admin_id:
        Logger.warn(__name__, "update_admin_status", "01", "Admin cannot update status of their own account")
        return JsonResponse.failed("You cannot %s your own account" % ("activate" if (status == 'ACTIVE') else "deactivate"))
    if admin_to_update['status'] == status:
        Logger.warn(__name__, "update_admin_status", "01", "Nothing to change. Admin is already %s" % status)
        return JsonResponse.failed('Admin is already %s' % status.lower())

    # If admin is inactive, prevent account activation
    if admin_to_update['status'] == AdminStatus.INACTIVE.value and status == AdminStatus.ACTIVE.value:
        Logger.warn(__name__, "update_admin_status", "01", "Admin [%s] has not confirmed account" % admin_to_update['username'])
        return JsonResponse.failed('Admin account is pending confirmation')

    try:
        updated_admin_data = AdministratorService.update_administrator(admin_id, {'status': status})
        Logger.info(__name__, "update_admin_status", "00",
                    "Account [%s] set to %s by admin [%s]" % (admin_id, status, admin_username))
    except Exception:
        Logger.warn(__name__, "update_admin_status", "01", "Error occurred while updating admin [%s] status" % admin_to_update['username'])
        return JsonResponse.server_error('Updating admin status failed')

    resp_msg = 'Admin %s successfully!' % (status.lower() if status != 'ACTIVE' else 'activated')
    return JsonResponse.success(resp_msg, data=updated_admin_data)
