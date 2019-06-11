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


@api.route('/v1/administrators', methods=['POST'])
# @api_request.api_authenticate
# @api_request.admin_authenticate('admin.add_admin')
@api_request.json
@api_request.required_body_params('first_name', 'last_name', 'email', 'username', 'role', 'branch')
def add_administrator():
    # admin_data = g.admin
    admin_data = {'username': 'creator', 'institution': {'id': '5cdea422feb488013bde8b9e', 'short_name': 'BANK1'}, 'branch': {'branch_id': 'BK1001'}}
    admin_username = admin_data['username']
    admin_branch_code = admin_data['branch']['branch_id']

    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    Logger.debug(__name__, "add_administrator", "00", "Received request to add admin", request_data)

    email = request_data['email']
    username = request_data['username'].strip()
    role = request_data['role']
    branch = request_data['branch']

    institution_id = admin_data['institution']['id']

    # Validate email
    if not Utils.is_valid_email(email):
        Logger.warn(__name__, "add_administrator", "01", "Invalid email address: [%s]" % email)
        return JsonResponse.bad_request('Invalid email address')

    # Validate username, make sure it doesn't already exist
    Logger.debug(__name__, "add_administrator", "00", "Checking if admin with username [%s] already exist" % username)
    existing_admin = AdministratorService.find_by_username(username)
    if existing_admin is not None:
        Logger.warn(__name__, "add_administrator", "01", "Admin with username [%s] already exists" % username)
        return JsonResponse.bad_request('Admin with username already exist')
    Logger.info(__name__, "add_administrator", "00", "Admin with username [%s] does not exist" % username)

    # Validate email address, make sure it doesn't already exist
    Logger.debug(__name__, "add_administrator", "00", "Checking if admin with email [%s] already exist" % email)
    existing_admin = AdministratorService.find_by_email(email)
    if existing_admin is not None:
        Logger.warn(__name__, "add_administrator", "01", "Admin with email [%s] already exists" % email)
        return JsonResponse.bad_request('Admin with email already exist')
    Logger.info(__name__, "add_administrator", "00", "Admin with email [%s] does not exist" % email)

    # Check if institution exists and is active
    Logger.debug(__name__, "add_administrator", "00", "Checking if institution [%s] exists" % institution_id)
    institution_data = InstitutionService.get_by_id(institution_id, minimal=True)
    if institution_data is None:
        Logger.warn(__name__, "add_administrator", "01", "Institution [%s] does not exists" % institution_id)
        return JsonResponse.failed('Institution does not exist')
    elif institution_data['status'] != InstitutionStatus.ACTIVE.value:
        Logger.warn(__name__, "add_administrator", "01", "Institution [%s] exists, but is %s" % (institution_id, institution_data['status']))
        return JsonResponse.failed('Institution is %s' % institution_data['status'].lower())
    Logger.info(__name__, "add_administrator", "00", "Institution [%s] exists and is active" % institution_id)

    # Check if branch exists, and belongs to institution in request and is active
    Logger.debug(__name__, "add_administrator", "00", "Checking if branch [%s] exists" % branch)
    branch_data = BranchService.get_institution_branch(institution_id, branch, minimal=True)
    if branch_data is None:
        Logger.warn(__name__, "add_administrator", "01", "Branch [%s] for institution [%s] does not exists" % (branch, institution_id))
        return JsonResponse.failed('Branch does not exist')
    elif branch_data['status'] != BranchStatus.ACTIVE.value:
        Logger.warn(__name__, "add_administrator", "01", "Branch [%s] exists, but is %s" % (branch, branch_data['status']))
        return JsonResponse.failed('Branch is %s' % branch_data['status'].lower())
    Logger.info(__name__, "add_administrator", "00", "Branch [%s] exists and is active" % branch)

    # If admin does not belong to ALL branch, limit adding admin to their branch only
    if admin_branch_code != 'ALL' and branch != admin_branch_code:
        Logger.warn(__name__, "add_administrator", "00", "Admin [%s] not allowed to add admin to branch [%s]" % (admin_username, branch))
        return JsonResponse.forbidden('You cannot add an admin to this branch')

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
        request_data['institution'] = admin_data['institution']['id']
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


@api.route('/v1/administrators', methods=['GET'])
# @api_request.api_authenticate
# @api_request.admin_authenticate('admin.view_admin')
def get_administrators():
    # admin_data = g.admin
    admin_data = {'username': 'creator', 'institution': {'id': '5cdea422feb488013bde8b9e', 'short_name': 'BANK1'}, 'branch': {'branch_id': 'BK1001'}}
    # institution_data = admin_data['institution']
    is_branch_admin = admin_data['branch']['branch_id'] == 'ALL'

    Logger.debug(__name__, "get_administrators", "00", "Received request to get administrators")
    params = request.args.to_dict()
    Logger.debug(__name__, "get_administrators", "00", "Param(s) received: %s" % params)
    minimal = False
    paginate = True

    if 'minimal' in params:
        minimal = params.pop('minimal').lower() == 'true'
    if 'paginate' in params:
        paginate = params.pop('paginate').lower() != 'false'

    # By default, filter by institution
    params['institution'] = admin_data['institution']['id']

    # Limit administrators user can see depending on their institution and branch
    # if not is_branch_admin:
    #     params['branch'] = admin_data['branch']['branch_id']

    admin_list, nav = AdministratorService.find_administrators(paginate=paginate, minimal=minimal, **params)

    return JsonResponse.success(data=admin_list, nav=nav)


@api.route('/v1/administrators/<admin_id>', methods=['GET'])
# @api_request.api_authenticate
# @api_request.admin_authenticate('admin.view_admin')
def get_administrator(admin_id):
    # admin_data = g.admin
    admin_data = {'username': 'creator', 'institution': {'id': '5cdea422feb488013bde8b9e', 'short_name': 'BANK1'}, 'branch': {'branch_id': 'BK1001'}}
    is_branch_admin = admin_data['branch']['branch_id'] == 'ALL'
    Logger.debug(__name__, "get_administrator", "00", "Received request to get administrator [%s]" % admin_id)

    administrator_data = AdministratorService.get_by_id(admin_id)
    if administrator_data is None:
        Logger.warn(__name__, "get_administrator", "01", "Administrator [%s] could not be found" % admin_id)
        return JsonResponse.failed('Administrator does not exist')
    # if administrator_data['institution']['id'] != admin_data['institution']['id']:
    #     Logger.warn(__name__, "get_administrator", "01", "Admin forbidden from getting details of admin in another institution")
    #     return JsonResponse.forbidden()
    # if not is_branch_admin and admin_data['branch']['branch_id'] != administrator_data['branch']['branch_id']:
    #     Logger.warn(__name__, "get_administrator", "01", "Admin forbidden from getting details of admin in another branch")
    #     return JsonResponse.forbidden()
    Logger.info(__name__, "get_administrator", "00", "Administrator [%s] found!" % admin_id)

    return JsonResponse.success(data=administrator_data)


@api.route('/v1/administrators/me', methods=['PUT'])
# @api_request.api_authenticate
# @api_request.user_authenticate
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
# @api_request.api_authenticate
# @api_request.admin_authenticate('admin.update_admin')
@api_request.json
def update_admin_profile(admin_id):
    # admin_data = g.admin
    admin_data = {'username': 'creator', 'institution': {'id': '5cdea422feb488013bde8b9e', 'short_name': 'BANK1'}, 'branch': {'branch_id': 'BK1001'}}
    institution_data = admin_data['institution']
    admin_branch = admin_data['branch']

    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    first_name = request_data.get('first_name')
    last_name = request_data.get('last_name')
    phone_number = request_data.get('phone_number')

    if first_name is None and last_name is None:
        Logger.warn(__name__, "update_admin_profile", "01", "First name and/or last name not present in request")
        return JsonResponse.failed('Nothing to update')
    elif not isinstance(first_name, str):
        Logger.warn(__name__, "update_admin_profile", "01", "First name is not string: [%s]" % first_name)
        return JsonResponse.bad_request('Invalid first name')
    elif not isinstance(last_name, str):
        Logger.warn(__name__, "update_admin_profile", "01", "Last name is not string: [%s]" % last_name)
        return JsonResponse.bad_request('Invalid last name')
    try:
        long_phone_number = int(phone_number)
    except ValueError:
        Logger.warn(__name__, "update_admin_profile", "01", "Phone number is not long: [%s]" % last_name)
        return JsonResponse.bad_request('Invalid phone number')

    # Check if user exists
    admin_to_update = AdministratorService.get_by_id(admin_id)
    if admin_to_update is None:
        Logger.warn(__name__, "update_admin_profile", "01", "Admin [%s] does not exist" % admin_id)
        return JsonResponse.failed('Admin does not exist')
    if admin_to_update['status'] != AdminStatus.ACTIVE.value:
        Logger.warn(__name__, "update_admin_profile", "01", "Admin [%s] is not active. Status: [%s]" % (admin_id, admin_to_update['status']))
        return JsonResponse.failed('Admin is not active')

    # Check if admin user has access to perform update
    if admin_data['branch']['branch_id'] != 'ALL':
        is_same_branch = admin_branch['branch_id'] == admin_to_update['branch']['branch_id']
        if not is_same_branch:
            Logger.warn(__name__, "update_admin_profile", "01", "Admin [%s] cannot update admin in another branch" % admin_data['username'])
            return JsonResponse.forbidden('You cannot update this admin\'s profile')

    update_data = {}
    if first_name is not None and first_name != admin_to_update['first_name']:
        update_data['first_name'] = first_name

    if last_name is not None and last_name != admin_to_update['last_name']:
        update_data['last_name'] = last_name

    if phone_number is not None and long_phone_number != admin_to_update['phone_number']:
        update_data['phone_number'] = long_phone_number

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
# @api_request.api_authenticate
# @api_request.admin_authenticate('admin.update_admin')
@api_request.json
@api_request.required_body_params('status')
def update_admin_status(admin_id):
    # Get admin data from request context
    # admin_data = g.admin
    admin_data = {'username': 'creator', 'institution': {'id': '5cdea422feb488013bde8b9e', 'short_name': 'BANK1'}, 'branch': {'branch_id': 'BK1001'}}
    admin_username = admin_data['username']
    admin_branch = admin_data['branch']
    Logger.debug(__name__, "update_admin_status", "00",
                 "Admin [%s] requesting to change account [%s] status" % (admin_username, admin_id))

    request_data = json.loads(request.data.decode('utf-8'))
    status = request_data['status'].strip().upper()

    # Find admin to update
    admin_to_update = AdministratorService.get_by_id(admin_id)
    if admin_to_update is None:
        Logger.warn(__name__, "update_admin_status", "01", "Administrator to update not found")
        return JsonResponse.failed('Admin to update not found')

    # Check if admin user has access to perform update
    if admin_data['branch']['branch_id'] != 'ALL':
        is_same_branch = admin_branch['branch_id'] == admin_to_update['branch']['branch_id']
        if not is_same_branch:
            Logger.warn(__name__, "update_admin_profile", "01", "Admin [%s] cannot update admin in another branch" % admin_data['username'])
            return JsonResponse.forbidden('You cannot update this admin\'s profile')

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
