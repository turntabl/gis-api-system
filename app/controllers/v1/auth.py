# auth.py

from datetime import datetime
from datetime import timedelta
import json
import traceback

from flask import g
from flask import request

from app.config import config
from app.controllers import api
from app.controllers import api_request
from app.controllers import JsonResponse
from app.errors.errors import GenericError
from app.errors.errors import InputError
from app.libs.logger import Logger
from app.libs.utils import DateUtils
from app.libs.utils import Utils
from app.services.v1.administrator import AdministratorService
from app.services.v1.branch import BranchService
from app.services.v1.institution import InstitutionService
from app.services.v1.user_token import UserTokenService
from app.models.administrator import Status as AdminStatus
from app.models.user_token import Status as UserTokenStatus
from app.models.user_token import Type as UserTokenType


@api.route('/v1/login', methods=['POST'])
@api_request.json
@api_request.required_body_params('username', 'password')
def login():
    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    username = request_data['username']
    password = request_data['password']
    Logger.debug(__name__, "login", "00", "Received request to login user [%s]" % username)

    # Find user
    user_data = AdministratorService.find_by_username_password(username, password)

    if user_data is None:
        Logger.warn(__name__, "login", "01", "Invalid username and/or password")
        return JsonResponse.failed('Invalid username and/or password')

    user_data = user_data.to_dict()
    user_institution = user_data['institution']
    user_branch = user_data['branch']

    if user_data['status'] == AdminStatus.INACTIVE.value:
        Logger.warn(__name__, "login", "01", "User [%s] account has not been activated" % username)
        return JsonResponse.inactive_user()
    elif user_data['status'] == AdminStatus.SUSPENDED.value:
        Logger.warn(__name__, "login", "01", "User [%s] account has been suspended" % username)
        return JsonResponse.forbidden('This account has been deactivated')
    elif user_data['status'] != AdminStatus.ACTIVE.value:
        Logger.warn(__name__, "login", "01", "User has invalid status: [%s]" % user_data['status'])
        return JsonResponse.forbidden('Login not allowed')

    # Check if user institution exists and is active
    institution_data = InstitutionService.get_by_id(user_institution['id'])
    if institution_data is None:
        Logger.warn(__name__, "login", "01", "User [%s] institution [%s] does not exist" % (username, user_institution['id']))
        return JsonResponse.failed('No institution found for this account')
    elif not institution_data['status']:
        Logger.warn(__name__, "login", "01", "User [%s] institution [%s] is not active" % (username, user_institution['id']))
        return JsonResponse.forbidden('The institution linked to this account is not active')

    # Check if user branch exists and is active
    branch_data = BranchService.get_institution_branch(user_institution['id'], user_branch['branch_id'])
    if branch_data is None:
        Logger.warn(__name__, "login", "01", "User [%s] branch [%s] does not exist" % (username, user_branch['id']))
        return JsonResponse.failed('No branch found for this account')
    elif not branch_data['status']:
        Logger.warn(__name__, "login", "01", "User [%s] branch [%s] is not active" % (username, user_branch['id']))
        return JsonResponse.forbidden('The branch linked to this account is not active')

    # Check if password has expired
    password_last_change_date = DateUtils.parse_datetime(user_data['password_last_changed_at'])
    password_expiry_date = password_last_change_date + timedelta(days=config.PASSWORD_EXPIRY_DAYS)
    if password_expiry_date < datetime.utcnow():
        Logger.warn(__name__, "login", "01", "User password expired at [%s]" % password_expiry_date)
        return JsonResponse.password_expired()

    data = {'session_token': Utils.generate_session_token()}

    # Update session
    try:
        user_data = AdministratorService.update_administrator(user_data['id'], data)
    except Exception as ex:
        Logger.error(__name__, "login", "02", "Error while updating admin [%s] session token: %s" % (username, ex))
        return JsonResponse.server_error('Login failed')

    return JsonResponse.success(msg='Login successful!', data=user_data)


@api.route('/v1/logout', methods=['GET'])
@api_request.user_authenticate
def logout():
    user_data = g.admin
    Logger.debug(__name__, "logout", "00", "Received request to logout user [%s]" % user_data['username'])

    # Set session_token in Administrator object to None
    try:
        AdministratorService.update_administrator(user_data['id'], {'session_token': None})
    except Exception:
        Logger.error(__name__, "logout", "02", "Error while expiring session", traceback.format_exc())
        return JsonResponse.server_error('Something went wrong')

    return JsonResponse.success(msg='Logout successful!')


@api.route('/v1/auth/setup', methods=['POST'])
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


@api.route('/v1/users/notification/resend', methods=['POST'])
@api_request.admin_authenticate('admin.update_admin')
@api_request.json
@api_request.required_body_params('username')
def resend_new_user_notification():
    admin_data = g.admin
    admin_inst_data = admin_data['institution']['id']
    Logger.debug(__name__, "resend_new_user_notification", "00", "Received request to resend new user notification")
    request_data = json.loads(request.data.decode('utf-8'))
    username = request_data['username'].strip()

    # Find user using username
    user_data = AdministratorService.find_by_username(username)
    if user_data is None:
        Logger.warn(__name__, "resend_new_user_notification", "01", "User with username [%s] not found" % username)
        return JsonResponse.failed(msg='User does not exist')
    elif user_data['status'] != AdminStatus.INACTIVE.value:
        Logger.warn(__name__, "resend_new_user_notification", "01",
                    "This is not a new user, cannot resend new user notification")
        return JsonResponse.failed(msg='This user is not a new user')

    # Generate random password for first time login
    random_password = Utils.generate_alphanum_password()
    Logger.debug(__name__, "resend_new_user_notification", "00", "Generated user [%s] password: [%s]" % (username, random_password))

    # Save user with hashed password
    hashed_password = Utils.hash_password(random_password)

    # Update user password
    AdministratorService.update_administrator(user_data['id'], {'password': hashed_password})

    try:
        Utils.send_email_confirmation(user_data['email'], username, random_password)
    except Exception:
        Logger.error(__name__, "add_institution_user", "02",
                     "Error while sending confirmation email to [%s]" % user_data['email'], traceback.format_exc())
        return JsonResponse.server_error('Resend notification to new user failed. Please try again')

    return JsonResponse.success(msg='Notification resent successfully!')


@api.route('/v1/password/reset', methods=['POST'])
@api_request.json
@api_request.required_body_params('username')
def initiate_password_reset():
    Logger.debug(__name__, "initiate_password_reset", "00", "Received request to initiate password reset")
    request_data = json.loads(request.data.decode('utf-8'))
    username = request_data['username'].strip()

    # Find user using username
    user_data = AdministratorService.find_by_username(username)
    if user_data is None:
        Logger.warn(__name__, "initiate_password_reset", "01", "User with username [%s] not found" % username)
        return JsonResponse.failed(msg='User with this username does not exist')
    elif user_data['status'] == AdminStatus.INACTIVE.value:
        Logger.warn(__name__, "initiate_password_reset", "01",
                    "User has not been confirmed, cannot initiate password reset")
        return JsonResponse.inactive_user(msg='User account has not been confirmed')
    elif user_data['status'] != AdminStatus.ACTIVE.value:
        Logger.warn(__name__, "initiate_password_reset", "01", "User is not active. Status: [%s]" % user_data['status'])
        return JsonResponse.failed(msg='User account is not active')

    # Generate password reset token to be included in URL
    reset_token = Utils.generate_reset_token()

    # Save token against username (valid for n minutes)
    try:
        UserTokenService.insert(username, reset_token, UserTokenType.PASSWORD_RESET.value)
    except Exception as ex:
        Logger.error(__name__, "initiate_password_reset", "02", "Could not save password reset request: %s" % ex)
        return JsonResponse.server_error('Could not initiate password reset')

    # Build password reset url and send reset email
    pwd_reset_url = Utils.build_url(config.PASSWORD_RESET_URL, username=username, token=reset_token)
    Utils.send_password_reset_email(user_data['email'], pwd_reset_url)

    return JsonResponse.success(msg='An email with a password reset link has been sent to %s' % user_data['email'])


@api.route('/v1/password', methods=['POST'])
@api_request.json
@api_request.required_body_params('username', 'token', 'password')
def create_password_from_reset():
    Logger.debug(__name__, "create_password_from_reset", "00", 'Received request to set new password for user')
    request_data = json.loads(request.data.decode('utf-8'))
    username = request_data['username']
    # Get user data
    user_data = AdministratorService.find_by_username(username)
    if user_data is None:
        Logger.warn(__name__, "create_password_from_reset", "00", "Details for user [%s] not found" % username)
        return JsonResponse.failed('User does not exist')

    # Check if password satisfies policy
    try:
        Utils.password_satisfies_policy(request_data['password'])
    except InputError as ie:
        Logger.warn(__name__, "create_password_from_reset", "01", "New password does not satisfy policy. MSG: %s" % ie)
        return JsonResponse.failed(ie.message)

    # Get password reset token
    pwd_reset_token_list = UserTokenService.find(username=username, type=UserTokenType.PASSWORD_RESET.value,
                                                 token=request_data['token'])
    password_reset_token = pwd_reset_token_list[0] if pwd_reset_token_list else None
    if password_reset_token is None:
        Logger.warn(__name__, "create_password_from_reset", "01", "No password reset token found for user [%s]", username)
        return JsonResponse.failed('Password reset not initiated for this user')
    if password_reset_token['status'] != UserTokenStatus.PENDING.value:
        Logger.warn(__name__, "create_password_from_reset", "01",
                    "Invalid status for password reset for user [%s]: %s" % (username, password_reset_token['status']))
        return JsonResponse.failed('Password reset request is not active')
    # Check if token hasn't expired
    token_expiry_date = DateUtils.mongo_date_to_object(password_reset_token['created_at']) \
                        + timedelta(minutes=config.PASSWORD_RESET_ACTIVE_MINUTES)
    Logger.debug(__name__, "create_password_from_reset", "00", "TOKEN_EXPIRY_DATE: %s" % token_expiry_date)
    if datetime.utcnow() > token_expiry_date:
        Logger.warn(__name__, "create_password_from_reset", "01",
                    "User [%s] password reset token expired at [%s]" % (username, token_expiry_date))
        return JsonResponse.failed('Request has expired. Initiate password reset again')
    elif request_data['token'] != password_reset_token['token']:
        Logger.warn(__name__, "create_password_from_reset", "01",
                    "Token in request [%s] is different from reset token generated" % request_data['token'])
        return JsonResponse.failed('Invalid password reset request')

    # Password token matched successfully, update reset_token to USED
    try:
        UserTokenService.update_token_status(password_reset_token['id'], UserTokenStatus.USED.value)
    except GenericError as ge:
        Logger.warn(__name__, "create_password_from_reset", "01", "GenericError occurred: %s" % ge)
        return JsonResponse.failed(ge.message)

    # Update user data
    Logger.debug(__name__, "create_password_from_reset", "00", "Setting new password for user [%s]" % username)
    try:
        admin_update = {'password': Utils.hash_password(request_data['password'])}
        AdministratorService.update_administrator(user_data['id'], admin_update)
    except Exception as ex:
        Logger.warn(__name__, "create_password_from_reset", "01", "Error while changing password: %s" % ex)
        return JsonResponse.server_error("Password reset could not be completed. Please initiate password reset again")
    Logger.info(__name__, "create_password_from_reset", "00", "New password set for user [%s]" % username)

    # Return success response
    return JsonResponse.success('New password set successfully!')


@api.route('/v1/password', methods=['PUT'])
@api_request.user_authenticate
@api_request.json
@api_request.required_body_params('old_password', 'new_password')
def change_password():
    request_data = json.loads(request.data.decode('utf-8'))
    # Get user data from request context
    user_data = g.admin
    username = user_data['username']
    Logger.debug(__name__, "change_password", "00", "Received request to change user [%s] password" % username)

    # Check if new password is not the same as the old password
    if request_data['old_password'] == request_data['new_password']:
        Logger.warn(__name__, "change_password", "01", "New password is the same as the old password")
        return JsonResponse.failed('New password is the same as the old one')

    # Check if password satisfies policy
    try:
        Utils.password_satisfies_policy(request_data['new_password'])
    except InputError as ie:
        Logger.warn(__name__, "change_password", "01", "New password does not satisfy policy. MSG: %s" % ie)
        return JsonResponse.failed(ie.message)

    old_password_hash = Utils.hash_password(request_data['old_password'])
    if old_password_hash != user_data['password']:
        Logger.warn(__name__, "change_password", "01", "Old password in request does not match user [%s] password" % username)
        return JsonResponse.failed('Old password is wrong')

    # Update user with new password
    new_password_hash = Utils.hash_password(request_data['new_password'])
    try:
        user_data = AdministratorService.update_administrator(user_data['id'], {'password': new_password_hash})
    except GenericError as ge:
        return JsonResponse.failed(ge.message)
    except Exception:
        return JsonResponse.server_error('Changing password failed')

    # Return success response
    return JsonResponse.success(msg='Password changed successfully!', data=user_data)
