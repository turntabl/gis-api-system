# branch.py

import json
import traceback

from flask import g
from flask import request

from app.controllers import api
from app.controllers import api_request
from app.controllers import JsonResponse
from app.libs.logger import Logger
from app.libs.utils import Utils
from app.models.branch import Branch
from app.models.branch import Status as BranchStatus
from app.models.role import RoleDefaults
from app.services.v1.administrator import AdministratorService
from app.services.v1.branch import BranchService
from app.services.v1.institution import InstitutionService
from app.services.v1.role import RoleService


@api.route('/v1/branches', methods=['POST'])
@api_request.json
@api_request.required_body_params('name', 'branch_id', 'institution', 'username', 'email', 'first_name', 'last_name')
def add_branch():
    admin_data = {'username': 'creator'}
    request_data = json.loads(request.data.decode('utf-8'))
    Logger.debug(__name__, "add_branch", "00", "Received request to add branch", request_data)
    branch_name = request_data['name']
    branch_id = request_data['branch_id']
    institution_id = request_data['institution']
    username = request_data['username']
    email = request_data['email']

    # Check if institution exists
    Logger.debug(__name__, "add_branch", "00", "Checking if institution [%s] exists" % institution_id)
    institution_data = InstitutionService.get_by_id(institution_id)
    if institution_data is None:
        Logger.warn(__name__, "add_branch", "01", "Institution [%s] does not exist" % institution_id)
        return JsonResponse.failed('Institution does not exist')
    Logger.info(__name__, "add_branch", "00", "Institution [%s] exists!" % institution_id)

    # Check if branch id already exists for institution
    Logger.debug(__name__, "add_branch", "00", "Checking if branch [%s] exists for institution [%s]" % (branch_id, institution_id))
    existing_branch = BranchService.get_institution_branch(institution_id, branch_id, minimal=True)
    if existing_branch is not None:
        Logger.warn(__name__, "add_branch", "01", "Branch [%s] already exists for institution [%s]" % (branch_id, institution_id))
        return JsonResponse.failed('Branch already exists for this institution')
    Logger.info(__name__, "add_branch", "00", "Branch [%s] does not exist for institution [%s]!" % (branch_id, institution_id))

    # Set admin username as 'created_by'
    request_data['created_by'] = admin_data['username']

    # Save branch
    Logger.debug(__name__, "add_branch", "00", "Saving branch [%s] for institution [%s]" % (branch_id, institution_id))
    try:
        branch_data = BranchService.add_branch(request_data)
        Logger.info(__name__, "add_branch", "00", "Branch [%s] added successfully!" % branch_id)
    except Exception as ex:
        Logger.warn(__name__, "add_branch", "02", "Could not save branch [%s]: %s" % (branch_id, ex))
        return JsonResponse.server_error('Branch could not be added')

    # Get default role for branch
    Logger.debug(__name__, "add_branch", "00", "Getting default role to assign to branch admin")
    default_branch_role = RoleService.get_default_role(RoleDefaults.BRANCH.value)
    if default_branch_role is None:
        Logger.warn(__name__, "add_branch", "01", "Default role for branch admin does not exist")
        return JsonResponse.failed('No role to assign branch admin')
    Logger.info(__name__, "add_branch", "00", "Default role for branch admin found!")

    # Generate random password for first time login
    random_password = Utils.generate_alphanum_password()
    # Logger.debug(__name__, "add_branch", "00", "Generated user [%s] password: [%s]" % (username, random_password))

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
        'branch': branch_data['branch_id'],
        'role': default_branch_role['id'],
        'phone_number': request_data.get('phone_number')
    }
    try:
        new_admin_data = AdministratorService.add_administrator(admin_req)
        if new_admin_data is None:
            Logger.warn(__name__, "add_branch", "01", "Institution created, but creating admin failed")
            return JsonResponse.server_error('Institution and branch created, but admin could not be created')
    except Exception as ex:
        Logger.warn(__name__, "add_branch", "01", "Institution created, but creating admin failed: %s" % ex)
        return JsonResponse.server_error('Institution and branch created, but admin could not be created')

    try:
        Utils.send_email_confirmation(email, username, random_password)
    except Exception:
        Logger.error(__name__, "add_branch", "02",
                     "Error while sending confirmation email to [%s]" % email, traceback.format_exc())
        return JsonResponse.new_user_not_notified('Admin created, but notification could not be sent. Kindly resend notification')

    return JsonResponse.success(data=branch_data)


@api.route('/v1/branches', methods=['GET'])
def get_branches():
    # admin_data = g.admin
    # admin_inst_data = admin_data['institution']

    Logger.debug(__name__, "get_branches", "00", "Received request to get branches")
    params = request.args.to_dict()
    Logger.debug(__name__, "get_branches", "00", "Param(s) received: %s" % params)
    minimal = False
    paginate = True

    if 'minimal' in params:
        minimal = params.pop('minimal').lower() == 'true'
    if 'paginate' in params:
        paginate = params.pop('paginate').lower() != 'false'

    # params['institution'] = admin_inst_data['id']

    branch_list, nav = BranchService.find_branches(paginate=paginate, minimal=minimal, **params)

    return JsonResponse.success(data=branch_list, nav=nav)


@api.route('/v1/branches/<branch_uid>', methods=['GET'])
def get_branch(branch_uid):
    # admin_data = g.admin

    Logger.debug(__name__, "get_branch", "00", "Received request to get branch [%s]" % branch_uid)

    branch_data = BranchService.get_by_id(branch_uid)
    if branch_data is None:
        Logger.warn(__name__, "get_branch", "01", "Branch [%s] could not be found" % branch_uid)
        return JsonResponse.failed('Branch does not exist')
    Logger.info(__name__, "get_branch", "00", "Branch [%s] found!" % branch_uid)

    return JsonResponse.success(data=branch_data)


@api.route('/v1/branches/<branch_uid>/status', methods=['PUT'])
@api_request.json
@api_request.required_body_params('status')
def update_branch_status(branch_uid):
    # Get admin data from request context
    admin_data = {'username': 'creator', 'institution': {'id': '5cdea422feb488013bde8b9e'}, 'branch': {'branch_id': 'ALL'}}
    admin_username = admin_data['username']
    Logger.debug(__name__, "update_branch_status", "00",
                 "Admin [%s] requesting to change branch [%s] status" % (admin_username, branch_uid))

    request_data = json.loads(request.data.decode('utf-8'))
    status = request_data['status'].strip().upper()

    # Validate 'status' parameter
    if status not in BranchStatus.values():
        Logger.warn(__name__, "update_branch_status", "01", "Invalid status value [%s]" % status)
        return JsonResponse.bad_request(msg='Invalid status')

    # Find branch to update
    branch_data = BranchService.get_by_id(branch_uid, minimal=True)
    if branch_data is None:
        Logger.warn(__name__, "update_branch_status", "01", "Branch [%s] to update not found" % branch_uid)
        return JsonResponse.failed('Branch does not exist')

    # Check if admin belongs to same institution as branch
    if admin_data['institution']['id'] != branch_data['institution']:
        Logger.warn(__name__, "update_branch_status", "01", "Admin cannot update status of another institution")
        return JsonResponse.forbidden("You cannot update status of this branch")

    # Prevent admin who does not belong to ALL branch to update status of branch
    if admin_data['branch']['branch_id'] != 'ALL':
        Logger.warn(__name__, "update_branch_status", "01", "Admin does not belong to ALL to update branch status")
        return JsonResponse.forbidden()

    if branch_data['status'] == status:
        Logger.warn(__name__, "update_branch_status", "01", "Nothing to change. Branch is already %s" % status)
        return JsonResponse.failed('Branch is already %s' % status.lower())

    Logger.debug(__name__, "update_branch_status", "00", "Setting status of branch [%s] to [%s]" % (branch_uid, status))
    try:
        branch_data = BranchService.update_branch(branch_uid, {'status': status})
        Logger.info(__name__, "update_branch_status", "00",
                    "Branch [%s] set to %s by admin [%s]" % (branch_uid, status, admin_username))
    except Exception as ex:
        Logger.warn(__name__, "update_branch_status", "01", "Could not update branch [%s] status: %s" % (branch_uid, ex))
        return JsonResponse.server_error('Branch status could not be updated')

    resp_msg = 'Branch %s successfully!' % ("activated" if status == BranchStatus.ACTIVE.value else "deactivated")
    return JsonResponse.success(resp_msg, data=branch_data)
