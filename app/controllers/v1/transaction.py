# transaction.py

import json

from flask import request

from app.config import config
from app.controllers import api
from app.controllers import api_request
from app.controllers import JsonResponse
from app.libs.logger import Logger
from app.libs.utils import Utils
from app.models.transaction import BankStatus
from app.models.transaction import CustomerStatus
from app.models.transaction import PaymentStatus
from app.models.transaction import PayoutType
from app.services.v1.transaction import TransactionService


@api.route('/v1/transactions/initiate', methods=['POST'])
@api_request.json
@api_request.required_body_params('cheque_number', 'account_number', 'payee_name', 'currency', 'amount', 'reference')
def initiate_transaction():
    # admin_data = g.admin
    admin_data = {'username': 'creator', 'institution': {'short_name': 'BANK1'}, 'branch': {'branch_id': 'BK1001'}}

    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    Logger.debug(__name__, "initiate_transaction", "00", "Received request to initiate transaction", request_data)
    cheque_number = request_data['cheque_number'].strip()
    account_number = request_data['account_number'].strip()
    payee_name = request_data['payee_name'].strip()
    currency = request_data['currency'].strip()
    amount = request_data['amount']
    reference = request_data['reference'].strip()

    # Validate parameters
    if not isinstance(cheque_number, str):
        Logger.warn(__name__, "initiate_transaction", "01", "Cheque number is not a string. Type: [%s]" % type(cheque_number))
        return JsonResponse.bad_request('Cheque number should be a string')
    if not cheque_number.isdigit() or len(cheque_number) != 6:
        Logger.warn(__name__, "initiate_transaction", "01", "Cheque number is not digits only or has more than 6 digits")
        return JsonResponse.bad_request('Cheque number should have exactly 6 digits')

    if not isinstance(account_number, str):
        Logger.warn(__name__, "initiate_transaction", "01", "Account number is not a string. Type: [%s]" % type(account_number))
        return JsonResponse.bad_request('Account number should be a string')
    if not account_number.isdigit() or len(account_number) < 9 or len(account_number) > 13:
        Logger.warn(__name__, "initiate_transaction", "01", "Account number is not digits only or has less than 9 or more than 13 digits")
        return JsonResponse.bad_request('Account number should have between 9 to 13 digits')

    try:
        decimal_amount = float(amount)
    except ValueError:
        Logger.warn(__name__, "initiate_transaction", "01", "Amount is not a decimal. Type: [%s]" % type(amount))
        return JsonResponse.bad_request('Amount should be a decimal')

    if not isinstance(reference, str):
        Logger.warn(__name__, "initiate_transaction", "01", "Reference is not a string. Type: [%s]" % type(cheque_number))
        return JsonResponse.bad_request('Reference should be a string')

    # Form cheque code (cheque_number:account_number)
    cheque_code = '%s:%s' % (cheque_number, account_number)

    # Check if cheque can be resubmitted
    Logger.debug(__name__, "initiate_transaction", "00", "Checking if cheque [%s] can be resubmitted" % cheque_code)
    transaction_filter = {
        'cheque_number': cheque_number,
        'account_number': account_number,
        'cheque_resubmission_flag': False
    }
    transaction_list, nav = TransactionService.find_transactions(paginate=False, **transaction_filter)
    if transaction_list:
        Logger.warn(__name__, "initiate_transaction", "01", "Cheque [%s] cannot be resubmitted" % cheque_code)
        return JsonResponse.failed('This cheque cannot be resubmitted')
    Logger.info(__name__, "initiate_transaction", "00", "Cheque [%s] can be resubmitted" % cheque_code)

    # Get last record of cheque
    transaction_filter = {
        'cheque_number': cheque_number,
        'account_number': account_number
    }
    transaction_list, nav = TransactionService.find_transactions(paginate=False, **transaction_filter)
    if transaction_list:
        # Get last record of transaction
        last_transaction = transaction_list[0]
        if not last_transaction['pre_approved']:
            if last_transaction['customer_status'] is None and last_transaction['bank_status'] is None:
                Logger.warn(__name__, "initiate_transaction", "01", "Transaction [%s] has been initiated" % cheque_code)
                return JsonResponse.failed('Transaction has been initiated already')
            elif last_transaction['customer_status'] == CustomerStatus.PENDING_APPROVAL.value:
                Logger.warn(__name__, "initiate_transaction", "01", "Transaction [%s] is pending customer approval" % cheque_code)
                return JsonResponse.failed('Transaction is pending customer approval')
            elif last_transaction['bank_status'] == BankStatus.PENDING_BANK_APPROVAL.value:
                Logger.warn(__name__, "initiate_transaction", "01", "Transaction [%s] is pending bank approval" % cheque_code)
                return JsonResponse.failed('Transaction is pending bank approval')
    else:
        Logger.info(__name__, "initiate_transaction", "00", "No records of transaction [%s] found" % cheque_code)

    # Save transaction with initiator
    transaction_request = {
        **transaction_filter,
        'payee_name': payee_name,
        'currency': currency,
        'amount': decimal_amount,
        'reference': reference,
        'initiated_by': admin_data['username'],
        'institution': admin_data['institution']['short_name'],
        'processed_branch': admin_data['branch']['branch_id']
    }

    try:
        transaction_data = TransactionService.add_transaction(transaction_request)
    except Exception as ex:
        Logger.error(__name__, "initiate_transaction", "02", "Could not initiate transaction [%s]: %s" % (cheque_code, ex))
        return JsonResponse.server_error('Could not initiate transaction')

    # TODO: Check core banking and get details of account
    is_partner_bank = False
    has_account_details = False
    account_details = {}

    resp_data = {
        'id': transaction_data['id'],
        'account_number': transaction_data['account_number'],
        'pre_approved': transaction_data['pre_approved'],
        'is_partner_bank': is_partner_bank,
        'has_account_details': has_account_details,
        'account_details': account_details
    }
    return JsonResponse.success(msg='Transaction initiated', data=resp_data)


@api.route('/v1/transactions/pre-approval', methods=['POST'])
@api_request.json
@api_request.required_body_params('cheque_number', 'account_number', 'currency', 'amount', 'pin')
def pre_approve_cheque():
    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    Logger.debug(__name__, "pre_approve_cheque", "00", "Received request to initiate transaction", request_data)
    cheque_number = request_data['cheque_number'].strip()
    account_number = request_data['account_number'].strip()
    currency = request_data['currency'].strip()
    amount = request_data['amount']

    # Validate parameters
    if not isinstance(cheque_number, str):
        Logger.warn(__name__, "pre_approve_cheque", "01", "Cheque number is not a string. Type: [%s]" % type(cheque_number))
        return JsonResponse.bad_request('Cheque number should be a string')
    if not cheque_number.isdigit() or len(cheque_number) != 6:
        Logger.warn(__name__, "pre_approve_cheque", "01", "Cheque number is not digits only or has more than 6 digits")
        return JsonResponse.bad_request('Cheque number should have exactly 6 digits')

    if not isinstance(account_number, str):
        Logger.warn(__name__, "pre_approve_cheque", "01", "Account number is not a string. Type: [%s]" % type(account_number))
        return JsonResponse.bad_request('Account number should be a string')
    if not account_number.isdigit() or len(account_number) < 9 or len(account_number) > 13:
        Logger.warn(__name__, "pre_approve_cheque", "01", "Account number is not digits only or has less than 9 or more than 13 digits")
        return JsonResponse.bad_request('Account number should have between 9 to 13 digits')

    try:
        decimal_amount = float(amount)
    except ValueError:
        Logger.warn(__name__, "pre_approve_cheque", "01", "Amount is not a decimal. Type: [%s]" % type(amount))
        return JsonResponse.bad_request('Amount should be a decimal')

    # Form cheque code (cheque_number:account_number)
    cheque_code = '%s:%s' % (cheque_number, account_number)

    # Check if cheque can be resubmitted
    Logger.debug(__name__, "pre_approve_cheque", "00", "Checking if cheque [%s] can be resubmitted" % cheque_code)
    transaction_filter = {
        'cheque_number': cheque_number,
        'account_number': account_number,
        'cheque_resubmission_flag': False
    }
    transaction_list, nav = TransactionService.find_transactions(paginate=False, **transaction_filter)
    if transaction_list:
        Logger.warn(__name__, "pre_approve_cheque", "01", "Cheque [%s] cannot be resubmitted" % cheque_code)
        return JsonResponse.failed('This cheque cannot be resubmitted')
    Logger.info(__name__, "pre_approve_cheque", "00", "Cheque [%s] can be resubmitted" % cheque_code)

    # Check if pre-approval already exists for this cheque
    transaction_filter = {
        'cheque_number': cheque_number,
        'account_number': account_number,
        'pre_approved': True
    }
    transaction_list, nav = TransactionService.find_transactions(paginate=False, **transaction_filter)
    if transaction_list:
        Logger.warn(__name__, "pre_approve_cheque", "01", "Pre-approval already exists for cheque [%s]" % cheque_code)
        return JsonResponse.failed('This cheque has been pre-approved already')
    else:
        Logger.info(__name__, "pre_approve_cheque", "00", "Cheque [%s] has not been pre-approved" % cheque_code)

    # Get last record of cheque
    transaction_filter = {
        'cheque_number': cheque_number,
        'account_number': account_number
    }
    transaction_list, nav = TransactionService.find_transactions(paginate=False, **transaction_filter)
    if transaction_list:
        # Get last record of transaction
        last_transaction = transaction_list[0]
        if last_transaction['customer_status'] is None and last_transaction['bank_status'] is None:
            Logger.warn(__name__, "pre_approve_cheque", "01", "Transaction [%s] has been initiated" % cheque_code)
            return JsonResponse.failed('Transaction has been initiated already')
        elif last_transaction['customer_status'] == CustomerStatus.PENDING_APPROVAL.value:
            Logger.warn(__name__, "pre_approve_cheque", "01", "Transaction [%s] is pending customer approval" % cheque_code)
            return JsonResponse.failed('Transaction is pending customer approval')
        elif last_transaction['bank_status'] == BankStatus.PENDING_BANK_APPROVAL.value:
            Logger.warn(__name__, "pre_approve_cheque", "01", "Transaction [%s] is pending bank approval" % cheque_code)
            return JsonResponse.failed('Transaction is pending bank approval')
    else:
        Logger.info(__name__, "pre_approve_cheque", "00", "No record of transaction [%s] found" % cheque_code)

    # Save transaction with initiator
    transaction_request = {
        **transaction_filter,
        'payee_name': '',
        'currency': currency,
        'amount': decimal_amount,
        'reference': '',
        'pre_approved': True,
        'customer_status': CustomerStatus.APPROVED.value
    }

    try:
        transaction_data = TransactionService.add_transaction(transaction_request)
    except Exception as ex:
        Logger.error(__name__, "pre_approve_cheque", "02", "Could not initiate transaction [%s]: %s" % (cheque_code, ex))
        return JsonResponse.server_error('Could not initiate transaction')

    # TODO: Check core banking and get details of account
    is_partner_bank = False
    has_account_details = False
    account_details = {}

    resp_data = {
        'id': transaction_data['id'],
        'account_number': transaction_data['account_number']
    }
    return JsonResponse.success(msg='Transaction initiated', data=resp_data)


@api.route('/v1/transactions/<transaction_id>/initiate/complete', methods=['POST'])
@api_request.json
@api_request.required_body_params('name', 'msisdn', 'balance', 'mandate', 'cheque_instructions')
def complete_transaction_initiation(transaction_id):
    # admin_data = g.admin
    admin_data = {'username': 'creator', 'institution': {'short_name': 'BANK1'}, 'branch': {'branch_id': 'BK1001'}}

    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    Logger.debug(__name__, "complete_transaction_initiation", "00", "Received request to complete transaction initiation", request_data)
    name = request_data['name'].strip()
    msisdn = request_data['msisdn']
    balance = request_data['balance']
    mandate = request_data['mandate'].strip()
    cheque_instructions = request_data['cheque_instructions'].strip()

    if not isinstance(name, str):
        Logger.warn(__name__, "complete_transaction_initiation", "01", "Name is not a string. Type: [%s]" % type(name))
        return JsonResponse.bad_request('Name should be a string')

    try:
        decimal_balance = float(balance)
    except ValueError:
        Logger.warn(__name__, "complete_transaction_initiation", "01", "Balance is not a decimal. Type: [%s]" % type(balance))
        return JsonResponse.bad_request('Balance should be a decimal')

    try:
        long_msisdn = int(msisdn)
    except ValueError:
        Logger.warn(__name__, "complete_transaction_initiation", "01", "Balance is not a decimal. Type: [%s]" % type(msisdn))
        return JsonResponse.bad_request('Balance should be a decimal')

    if not isinstance(mandate, str):
        Logger.warn(__name__, "complete_transaction_initiation", "01", "Mandate is not a string. Type: [%s]" % type(mandate))
        return JsonResponse.bad_request('Mandate should be a string')
    if not isinstance(cheque_instructions, str):
        Logger.warn(__name__, "complete_transaction_initiation", "01", "Cheque instructions is not a string. Type: [%s]" % type(cheque_instructions))
        return JsonResponse.bad_request('Cheque instructions should be a string')

    # Get transaction details
    Logger.debug(__name__, "complete_transaction_initiation", "00", "Finding details for transaction [%s]" % transaction_id)
    transaction_data = TransactionService.get_by_id(transaction_id)
    if transaction_data is None:
        Logger.warn(__name__, "complete_transaction_initiation", "01", "Transaction [%s] does not exist" % transaction_id)
        return JsonResponse.failed('Transaction not found')
    if transaction_data['customer_status'] is not None or transaction_data['bank_status'] is not None:
        Logger.warn(__name__, "complete_transaction_initiation", "01", "Transaction [%s] has been completely initiated" % transaction_id)
        return JsonResponse.failed('Transaction has been completely initiated')

    # Update transaction
    transaction_update = {
        'msisdn': long_msisdn,
        'customer_name': name,
        'balance': decimal_balance,
        'mandate': mandate,
        'cheque_instructions': cheque_instructions,
        'bank_status': BankStatus.INITIATED.value
    }
    try:
        updated_transaction_data = TransactionService.update_transaction(transaction_id, transaction_update)
    except Exception as ex:
        Logger.error(__name__, "complete_transaction_initiation", "02", "Could not complete transaction [%s] initiation" % transaction_id)
        return JsonResponse.server_error('Transaction initiation could not be completed')

    # Account owner msisdn
    msisdn = updated_transaction_data['msisdn']

    # Send approval request SMS to msisdn linked to account number
    Logger.debug(__name__, "complete_transaction_initiation", "00", "Sending cheque approval SMS to [%s]" % msisdn)
    sms_sent = Utils.send_sms(msisdn, config.CHEQUE_APPROVAL_SMS)
    if sms_sent:
        try:
            transaction_update = {
                'customer_status': CustomerStatus.PENDING_APPROVAL.value,
                'bank_status': BankStatus.PENDING_CUSTOMER_APPROVAL.value,
                'approval_sms_sent': sms_sent
            }
            updated_transaction_data = TransactionService.update_transaction(transaction_id, transaction_update)
            Logger.info(__name__, "complete_transaction_initiation", "00", "Cheque approval SMS sent to [%s] and approval_sms_sent status updated" % msisdn)
        except Exception as ex:
            Logger.error(__name__, "complete_transaction_initiation", "02", "Updating transaction [%s] with approval_sms_sent status failed: %s" % (transaction_id, ex))
            return JsonResponse.server_error('Sending approval request to customer failed')
    else:
        Logger.warn(__name__, "send_approval_request", "00", "Sending cheque approval SMS to [%s] failed" % msisdn)
        return JsonResponse.failed('Sending approval request to customer failed')

    resp_msg = 'Initiation completed and approval request sent to %s' % msisdn
    resp_data = {
        'id': updated_transaction_data['id'],
        'customer_status': updated_transaction_data['customer_status'],
        'bank_status': updated_transaction_data['bank_status'],
        'approval_sms_sent': updated_transaction_data['approval_sms_sent']
    }
    return JsonResponse.success(msg=resp_msg, data=resp_data)


@api.route('/v1/transactions/<transaction_id>/request-approval', methods=['POST'])
def send_approval_request(transaction_id):
    Logger.debug(__name__, "send_approval_request", "00", "Received request to send approval request for transaction [%s]" % transaction_id)
    # Get transaction details
    Logger.debug(__name__, "send_approval_request", "00", "Finding details for transaction [%s]" % transaction_id)
    transaction_data = TransactionService.get_by_id(transaction_id)
    if transaction_data is None:
        Logger.warn(__name__, "send_approval_request", "01", "Transaction [%s] does not exist" % transaction_id)
        return JsonResponse.failed('Transaction not found')
    if transaction_data['customer_status'] is not None or transaction_data['bank_status'] != BankStatus.INITIATED.value:
        Logger.warn(__name__, "send_approval_request", "01",
                    "Transaction [%s] not pending approval request. CustomerStatus: [%s] BankStatus: [%s]"
                    % (transaction_id, transaction_data['customer_status'], transaction_data['bank_status']))
        return JsonResponse.failed('Transaction not pending approval request')
    Logger.info(__name__, "send_approval_request", "00", "Transaction [%s] found and pending approval request" % transaction_id)

    # Update transaction accordingly
    Logger.debug(__name__, "send_approval_request", "00", "Updating transaction [%s] to pending customer approval" % transaction_id)
    transaction_update = {
        'customer_status': CustomerStatus.PENDING_APPROVAL.value,
        'bank_status': BankStatus.PENDING_CUSTOMER_APPROVAL.value
    }
    try:
        updated_transaction_data = TransactionService.update_transaction(transaction_id, transaction_update)
        Logger.info(__name__, "send_approval_request", "00", "Transaction [%s] updated with customer approval status" % transaction_id)
    except Exception as ex:
        Logger.error(__name__, "send_approval_request", "02", "Could not update transaction [%s] with customer approval status: %s" % (transaction_id, ex))
        return JsonResponse.server_error('Approval request could not be sent to customer')

    # Account owner msisdn
    msisdn = updated_transaction_data['msisdn']

    # Send approval request SMS to account number
    Logger.debug(__name__, "send_approval_request", "00", "Sending cheque approval SMS to [%s]" % msisdn)
    sms_sent = Utils.send_sms(msisdn, config.CHEQUE_APPROVAL_SMS)
    if sms_sent:
        try:
            updated_transaction_data = TransactionService.update_transaction(transaction_id, {'approval_sms_sent': sms_sent})
            Logger.info(__name__, "send_approval_request", "00", "Cheque approval SMS sent to [%s] and approval_sms_sent status updated" % msisdn)
        except Exception as ex:
            Logger.warn(__name__, "send_approval_request", "01", "Updating transaction [%s] with approval_sms_sent status failed: %s" % (transaction_id, ex))
    else:
        Logger.warn(__name__, "send_approval_request", "00", "Sending cheque approval SMS to [%s] failed" % msisdn)

    resp_msg = 'Request to approve cheque sent to %s' % msisdn
    resp_data = {
        'id': updated_transaction_data['id'],
        'customer_status': updated_transaction_data['customer_status'],
        'bank_status': updated_transaction_data['bank_status'],
        'approval_sms_sent': updated_transaction_data['approval_sms_sent']
    }
    return JsonResponse.success(msg=resp_msg, data=resp_data)


@api.route('/v1/transactions/accounts/<account_number>/pending', methods=['GET'])
def get_pending_approvals_for_account(account_number):
    Logger.debug(__name__, "get_pending_approvals_for_account", "00", "Received request to get approvals for account [%s]" % account_number)
    # Validate account number
    if not isinstance(account_number, str):
        Logger.warn(__name__, "get_pending_approvals_for_account", "01", "Account number is not a string. Type: [%s]" % type(account_number))
        return JsonResponse.bad_request('Account number should be a string')
    if not account_number.isdigit() or len(account_number) < 9 or len(account_number) > 13:
        Logger.warn(__name__, "get_pending_approvals_for_account", "01", "Account number is not digits only or has less than 9 or more than 13 digits")
        return JsonResponse.bad_request('Account number should have between 9 to 13 digits')

    # Filter transactions by account number
    Logger.debug(__name__, "get_pending_approvals_for_account", "00", "Getting pending approvals for account [%s]" % account_number)
    transaction_filter = {
        'account_number': account_number,
        'pre_approved': False,
        'customer_status': CustomerStatus.PENDING_APPROVAL.value,
        'payment_status': PaymentStatus.UNPAID.value
    }
    try:
        transaction_list, nav = TransactionService.find_transactions(**transaction_filter)
        Logger.info(__name__, "get_pending_approvals_for_account", "00", "Found %s approval(s) for account [%s]" % (nav.get('total_records'), account_number))
    except Exception:
        Logger.error(__name__, "get_pending_approvals_for_account", "02", "Could not get pending approvals for [%s]" % account_number)
        return JsonResponse.server_error('Could not get pending approvals')

    return JsonResponse.success(data=transaction_list, nav=nav)


@api.route('/v1/transactions/msisdn/<msisdn>/pending', methods=['GET'])
def get_pending_approvals_for_msisdn(msisdn):
    Logger.debug(__name__, "get_pending_approvals_for_msisdn", "00", "Received request to get approvals for msisdn [%s]" % msisdn)
    # Validate msisdn
    if not isinstance(msisdn, str):
        Logger.warn(__name__, "get_pending_approvals_for_msisdn", "01", "Msisdn is not a string. Type: [%s]" % type(msisdn))
        return JsonResponse.bad_request('Account number should be a string')
    if not msisdn.isdigit() or len(msisdn) != 12:
        Logger.warn(__name__, "get_pending_approvals_for_msisdn", "01", "Msisdn is not digits only or does not have exactly 12 digits")
        return JsonResponse.bad_request('Msisdn should be of long format')

    # Filter transactions by account number
    Logger.debug(__name__, "get_pending_approvals_for_msisdn", "00", "Getting pending approvals for msisdn [%s]" % msisdn)
    transaction_filter = {
        'msisdn': msisdn,
        'pre_approved': False,
        'customer_status': CustomerStatus.PENDING_APPROVAL.value,
        'payment_status': PaymentStatus.UNPAID.value
    }
    try:
        transaction_list, nav = TransactionService.find_transactions(**transaction_filter)
        Logger.info(__name__, "get_pending_approvals_for_msisdn", "00", "Found %s approval(s) for msisdn [%s]" % (nav.get('total_records'), msisdn))
    except Exception:
        Logger.error(__name__, "get_pending_approvals_for_msisdn", "02", "Could not get pending approvals for [%s]" % msisdn)
        return JsonResponse.server_error('Could not get pending approvals')

    return JsonResponse.success(data=transaction_list, nav=nav)


@api.route('/v1/transactions/accounts/<account_number>/cheques/<cheque_number>', methods=['GET'])
def get_cheque_history(account_number, cheque_number):
    cheque_code = '%s:%s' % (cheque_number, account_number)
    Logger.debug(__name__, "get_cheque_history", "00", "Received request to get cheque history [%s]" % cheque_code)

    # Validate account number
    if not isinstance(account_number, str):
        Logger.warn(__name__, "get_cheque_history", "01", "Account number is not a string. Type: [%s]" % type(account_number))
        return JsonResponse.bad_request('Account number should be a string')
    if not account_number.isdigit() or len(account_number) < 9 or len(account_number) > 13:
        Logger.warn(__name__, "get_cheque_history", "01", "Account number is not digits only or has less than 9 or more than 13 digits")
        return JsonResponse.bad_request('Account number should have between 9 to 13 digits')

    # Validate cheque number
    if not isinstance(cheque_number, str):
        Logger.warn(__name__, "initiate_transaction", "01", "Cheque number is not a string. Type: [%s]" % type(cheque_number))
        return JsonResponse.bad_request('Cheque number should be a string')
    if not cheque_number.isdigit() or len(cheque_number) != 6:
        Logger.warn(__name__, "initiate_transaction", "01", "Cheque number is not digits only or has more than 6 digits")
        return JsonResponse.bad_request('Cheque number should have exactly 6 digits')

    # Filter transactions by account number and cheque_id
    Logger.debug(__name__, "get_cheque_history", "00", "Getting history for cheque [%s]" % cheque_code)
    transaction_filter = {
        'account_number': account_number,
        'cheque_number': cheque_number
    }
    try:
        transaction_list, nav = TransactionService.find_transactions(**transaction_filter)
        Logger.info(__name__, "get_cheque_history", "00", "Found %s transaction(s) for cheque [%s]" % (nav.get('total_records'), cheque_code))
    except Exception:
        Logger.error(__name__, "get_cheque_history", "02", "Could not get history for account [%s]" % account_number)
        return JsonResponse.server_error('Could not get pending approvals')

    return JsonResponse.success(data=transaction_list, nav=nav)


@api.route('/v1/transactions/msisdn/<msisdn>/cheques', methods=['GET'])
def get_cheque_history_for_msisdn(msisdn):
    Logger.debug(__name__, "get_cheque_history_for_msisdn", "00", "Received request to get cheque historiy for msisdn [%s]" % msisdn)

    # Validate msisdn
    if not isinstance(msisdn, str):
        Logger.warn(__name__, "get_cheque_history_for_msisdn", "01", "Msisdn is not a string. Type: [%s]" % type(msisdn))
        return JsonResponse.bad_request('Account number should be a string')
    if not msisdn.isdigit() or len(msisdn) != 12:
        Logger.warn(__name__, "get_cheque_history_for_msisdn", "01", "Msisdn is not digits only or does not have exactly 12 digits")
        return JsonResponse.bad_request('Msisdn should be of long format')

    # Filter transactions by msisdn
    Logger.debug(__name__, "get_cheque_history_for_msisdn", "00", "Getting cheque history for msisdn [%s]" % msisdn)
    transaction_filter = {
        'msisdn': msisdn
    }
    try:
        transaction_list, nav = TransactionService.find_transactions(**transaction_filter)
        Logger.info(__name__, "get_cheque_history_for_msisdn", "00", "Found %s transaction(s) for msisdn [%s]" % (nav.get('total_records'), msisdn))
    except Exception:
        Logger.error(__name__, "get_cheque_history_for_msisdn", "02", "Could not get cheque history for msisdn [%s]" % msisdn)
        return JsonResponse.server_error('Could not get pending approvals')

    return JsonResponse.success(data=transaction_list, nav=nav)


@api.route('/v1/transactions/<transaction_id>', methods=['GET'])
def get_transaction_details(transaction_id):
    Logger.debug(__name__, "get_transaction_details", "00", "Received request to get transaction [%s]" % transaction_id)

    transaction_data = TransactionService.get_by_id(transaction_id)
    if transaction_data is None:
        Logger.warn(__name__, "get_transaction_details", "01", "Transaction [%s] does not exist" % transaction_id)
        return JsonResponse.failed('Transaction does not exist')
    Logger.info(__name__, "get_transaction_details", "00", "Transaction [%s] found!" % transaction_id)

    return JsonResponse.success(data=transaction_data)


@api.route('/v1/transactions/<transaction_id>/customer-approval', methods=['POST'])
@api_request.json
@api_request.required_body_params('status')
def customer_approval_decline(transaction_id):
    Logger.debug(__name__, "customer_approval_decline", "00", "Received request to approve/decline transaction [%s]" % transaction_id)
    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    status = request_data['status'].strip()
    comment = request_data.get('comment') or ''

    # Get transaction details
    Logger.debug(__name__, "customer_approval_decline", "00", "Finding details for transaction [%s]" % transaction_id)
    transaction_data = TransactionService.get_by_id(transaction_id)
    if transaction_data is None:
        Logger.warn(__name__, "customer_approval_decline", "01", "Transaction [%s] does not exist" % transaction_id)
        return JsonResponse.failed('Transaction not found')
    if transaction_data['customer_status'] != CustomerStatus.PENDING_APPROVAL.value \
            or transaction_data['bank_status'] != BankStatus.PENDING_CUSTOMER_APPROVAL.value:
        Logger.warn(__name__, "customer_approval_decline", "01",
                    "Transaction [%s] not pending customer approval/decline. CustomerStatus: [%s] BankStatus: [%s]"
                    % (transaction_id, transaction_data['customer_status'], transaction_data['bank_status']))
        if transaction_data['customer_status'] == CustomerStatus.APPROVED.value:
            return JsonResponse.failed('Transaction has been approved already')
        elif transaction_data['customer_status'] == CustomerStatus.DECLINED.value:
            return JsonResponse.failed('Transaction has been declined already')
        return JsonResponse.failed('Transaction not pending customer approval')

    Logger.info(__name__, "customer_approval_decline", "00", "Transaction [%s] found and pending customer approval/decline" % transaction_id)

    # Validate status parameter in request data
    if status not in (CustomerStatus.APPROVED.value, CustomerStatus.DECLINED.value):
        Logger.warn(__name__, "customer_approval_decline", "01", "Invalid customer approval status: [%s]" % status)
        return JsonResponse.failed('Invalid approval status')

    # Update transaction with customer_status in request
    Logger.debug(__name__, "customer_approval_decline", "00", "Updating transaction [%s] customer status to %s" % (transaction_id, status))
    transaction_update = {
        'customer_status': status,
        'bank_status': BankStatus.PENDING_BANK_APPROVAL.value,
        'customer_remarks': comment
    }
    try:
        updated_transaction_data = TransactionService.update_transaction(transaction_id, transaction_update)
        Logger.info(__name__, "customer_approval_decline", "00", "Transaction [%s] customer status set to %s" % (transaction_id, status))
    except Exception as ex:
        Logger.error(__name__, "customer_approval_decline", "02", "Could not update transaction [%s] customer status: %s" % (transaction_id, ex))
        return JsonResponse.server_error('%s transaction failed' % ('Approving' if status == CustomerStatus.APPROVED.value else 'Declining'))

    # TODO: Send approval/decline notification to portal

    resp_msg = 'Transaction %s successfully!' % status.lower()
    resp_data = {
        'id': updated_transaction_data['id'],
        'customer_status': updated_transaction_data['customer_status'],
        'bank_status': updated_transaction_data['bank_status']
    }
    return JsonResponse.success(msg=resp_msg, data=resp_data)


@api.route('/v1/transactions/msisdn/pre-approved', methods=['GET'])
def get_pre_approved_transactions():
    # admin_data = g.admin
    admin_data = {'username': 'creator', 'institution': {'short_name': 'BANK1'}, 'branch': {'branch_id': 'BK1001'}}
    institution = admin_data['institution']['short_name']
    branch = admin_data['branch']['branch_id']

    params = request.args.to_dict()
    minimal = False
    paginate = True

    if 'minimal' in params:
        minimal = params.pop('minimal').lower() == 'true'
    if 'paginate' in params:
        paginate = params.pop('paginate').lower() != 'false'

    # Filter transactions by account number
    Logger.debug(__name__, "get_pre_approved_transactions", "00", "Getting pre-approved transactions", params)
    allowed_filters = {key: params[key] for key in params if key in ('account_number', 'msisdn', 'cheque_number', 'start_date', 'end_date')}
    transaction_filter = {
        **allowed_filters,
        'pre_approved': True,
        'customer_status': CustomerStatus.APPROVED.value,
        'payment_status': PaymentStatus.UNPAID.value
    }
    try:
        transaction_list, nav = TransactionService.find_transactions(paginate=paginate, **transaction_filter)
        Logger.info(__name__, "get_pre_approved_transactions", "00", "Found %s pre-approved transaction(s)" % nav.get('total_records'))
    except Exception:
        Logger.error(__name__, "get_pre_approved_transactions", "02", "Could not get pre-approved transactions")
        return JsonResponse.server_error('Could not get pre-approved transactions')

    return JsonResponse.success(data=transaction_list, nav=nav)


@api.route('/v1/transactions/customer-approved', methods=['GET'])
def get_approved_transactions():
    # admin_data = g.admin
    admin_data = {'username': 'creator', 'institution': {'short_name': 'BANK1'}, 'branch': {'branch_id': 'BK1001'}}
    institution = admin_data['institution']['short_name']
    branch = admin_data['branch']['branch_id']

    params = request.args.to_dict()
    minimal = False
    paginate = True

    if 'minimal' in params:
        minimal = params.pop('minimal').lower() == 'true'
    if 'paginate' in params:
        paginate = params.pop('paginate').lower() != 'false'

    # Filter transactions by account number
    Logger.debug(__name__, "get_approved_transactions", "00", "Getting approved transactions for branch [%s]" % branch, params)
    allowed_filters = {key: params[key] for key in params if key in ('account_number', 'msisdn', 'cheque_number', 'start_date', 'end_date')}
    transaction_filter = {
        **allowed_filters,
        'institution': institution,
        'processed_branch': branch,
        'customer_status': CustomerStatus.APPROVED.value,
        'payment_status': PaymentStatus.UNPAID.value
    }
    try:
        transaction_list, nav = TransactionService.find_transactions(paginate=paginate, **transaction_filter)
        Logger.info(__name__, "get_approved_transactions", "00", "Found %s approved transaction(s) for branch [%s]" % (nav.get('total_records'), branch))
    except Exception:
        Logger.error(__name__, "get_approved_transactions", "02", "Could not get approved transactions for branch [%s]" % branch)
        return JsonResponse.server_error('Could not get approved transactions')

    return JsonResponse.success(data=transaction_list, nav=nav)


@api.route('/v1/transactions/<transaction_id>/bank/update', methods=['POST'])
@api_request.json
@api_request.required_body_params('status', 'comment')
def post_customer_approval_update(transaction_id):
    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    status = request_data['status'].strip()
    comment = request_data.get('comment') or ''
    Logger.debug(__name__, "post_customer_approval_update", "00", "Received bank request to update transaction [%s]" % transaction_id, request_data)

    # Get transaction details
    Logger.debug(__name__, "post_customer_approval_update", "00", "Finding details for transaction [%s]" % transaction_id)
    transaction_data = TransactionService.get_by_id(transaction_id)
    if transaction_data is None:
        Logger.warn(__name__, "post_customer_approval_update", "01", "Transaction [%s] does not exist" % transaction_id)
        return JsonResponse.failed('Transaction not found')
    if transaction_data['customer_status'] != CustomerStatus.APPROVED.value:
        Logger.warn(__name__, "post_customer_approval_update", "01",
                    "Transaction [%s] has not been approved by customer. CustomerStatus: [%s] BankStatus: [%s]"
                    % (transaction_id, transaction_data['customer_status'], transaction_data['bank_status']))
        return JsonResponse.failed('Transaction not approved by customer')

    # Update transaction with bank_status in request
    Logger.debug(__name__, "post_customer_approval_update", "00", "Updating transaction [%s] bank status to %s" % (transaction_id, status))
    transaction_update = {
        'bank_status': status,
        'bank_remarks': comment
    }
    try:
        updated_transaction_data = TransactionService.update_transaction(transaction_id, transaction_update)
        Logger.info(__name__, "post_customer_approval_update", "00", "Transaction [%s] bank status set to %s" % (transaction_id, status))
    except Exception as ex:
        Logger.error(__name__, "post_customer_approval_update", "02", "Could not update transaction [%s] bank status: %s" % (transaction_id, ex))
        return JsonResponse.server_error('%s transaction failed' % ('Approving' if status == CustomerStatus.APPROVED.value else 'Declining'))

    # TODO: Send approval/decline notification to portal

    resp_msg = 'Transaction %s successfully!' % status.lower()
    resp_data = {
        'id': updated_transaction_data['id'],
        'customer_status': updated_transaction_data['customer_status'],
        'bank_status': updated_transaction_data['bank_status']
    }
    return JsonResponse.success(msg=resp_msg, data=resp_data)


@api.route('/v1/transactions/<transaction_id>/confirm-payout', methods=['POST'])
@api_request.json
@api_request.required_body_params('payout_type')
def confirm_payout(transaction_id):
    # admin_data = g.admin
    admin_data = {'username': 'creator', 'institution': {'short_name': 'BANK1'}, 'branch': {'branch_id': 'BK1001'}}
    # Get request data
    request_data = json.loads(request.data.decode('utf-8'))
    payout_type = request_data['payout_type'].strip()
    Logger.debug(__name__, "confirm_payout", "00", "Received request to confirm payout for transaction [%s]" % transaction_id, request_data)

    # Get transaction details
    Logger.debug(__name__, "confirm_payout", "00", "Finding details for transaction [%s]" % transaction_id)
    transaction_data = TransactionService.get_by_id(transaction_id)
    if transaction_data is None:
        Logger.warn(__name__, "confirm_payout", "01", "Transaction [%s] does not exist" % transaction_id)
        return JsonResponse.failed('Transaction not found')
    if transaction_data['customer_status'] != CustomerStatus.APPROVED.value:
        Logger.warn(__name__, "confirm_payout", "01",
                    "Transaction [%s] has not been approved by customer. CustomerStatus: [%s] BankStatus: [%s]"
                    % (transaction_id, transaction_data['customer_status'], transaction_data['bank_status']))
        return JsonResponse.failed('Transaction not approved by customer')
    if transaction_data['bank_status'] != BankStatus.PENDING_PAYMENT_APPROVAL.value:
        Logger.warn(__name__, "confirm_payout", "01",
                    "Transaction [%s] not pending bank payment approval. CustomerStatus: [%s] BankStatus: [%s]"
                    % (transaction_id, transaction_data['customer_status'], transaction_data['bank_status']))
        return JsonResponse.failed('Transaction not pending payment approval')

    # Validate payout type
    if payout_type not in PayoutType.values():
        Logger.warn(__name__, "confirm_payout", "01", "Invalid payout type: [%s]" % payout_type)
        return JsonResponse.failed('Invalid payout type')

    # Update transaction with bank_status in request
    Logger.debug(__name__, "confirm_payout", "00", "Completing transaction [%s]" % transaction_id)
    transaction_update = {
        'payout_type': payout_type,
        'bank_status': BankStatus.COMPLETED.value,
        'payment_status': PaymentStatus.PAID.value,
        'cheque_resubmission_flag': False
    }
    try:
        updated_transaction_data = TransactionService.update_transaction(transaction_id, transaction_update)
        Logger.info(__name__, "confirm_payout", "00", "Transaction [%s] paid and completed successfully!" % transaction_id)
    except Exception as ex:
        Logger.error(__name__, "confirm_payout", "02", "Could not pay and complete transaction [%s]: %s" % (transaction_id, ex))
        return JsonResponse.server_error('Could not confirm payout for transaction')

    resp_data = {
        'id': updated_transaction_data['id'],
        'bank_status': updated_transaction_data['bank_status'],
        'payout_type': updated_transaction_data['payout_type'],
        'payment_status': updated_transaction_data['payment_status']
    }
    return JsonResponse.success(msg='Payout completed!', data=resp_data)
