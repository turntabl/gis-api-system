# report.py

from flask import request

from app.controllers import api
from app.controllers import api_request
from app.controllers import JsonResponse
from app.libs.utils import Logger
from app.models.transaction import BankStatus
from app.models.transaction import CustomerStatus
from app.models.transaction import PaymentStatus
from app.services.v1.transaction import TransactionService


@api.route('/v1/reports/transactions', methods=['GET'])
def get_cheques():
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

    # Filter transactions
    Logger.debug(__name__, "get_cheques", "00", "Getting transactions for branch [%s]" % branch, params)
    # allowed_filters = {key: params[key] for key in params if key in ('account_number', 'msisdn', 'cheque_number', 'start_date', 'end_date', 'page', 'size')}
    params['institution'] = institution
    if branch != 'ALL':
        params['processed_branch'] = branch

    try:
        transaction_list, nav = TransactionService.find_transactions(paginate=paginate, **params)
        Logger.info(__name__, "get_cheques", "00", "Found %s transaction(s) for branch [%s]" % (nav.get('total_records'), branch), params)
    except Exception:
        Logger.error(__name__, "get_cheques", "02", "Could not get bounced transactions for branch [%s]" % branch, params)
        return JsonResponse.server_error('Could not get transactions')

    return JsonResponse.success(data=transaction_list, nav=nav)


@api.route('/v1/reports/transactions/bounced', methods=['GET'])
def get_bounced_cheques():
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

    # Filter transactions
    Logger.debug(__name__, "get_bounced_cheques", "00", "Getting bounced transactions for branch [%s]" % branch, params)
    allowed_filters = {key: params[key] for key in params if key in ('account_number', 'msisdn', 'cheque_number', 'start_date', 'end_date', 'page', 'size')}
    transaction_filter = {
        **allowed_filters,
        'institution': institution,
        'processed_branch': branch,
        'bank_status': BankStatus.BOUNCED.value,
        'payment_status': PaymentStatus.UNPAID.value
    }
    try:
        transaction_list, nav = TransactionService.find_transactions(paginate=paginate, **transaction_filter)
        Logger.info(__name__, "get_bounced_cheques", "00", "Found %s bounced transaction(s) for branch [%s]" % (nav.get('total_records'), branch))
    except Exception:
        Logger.error(__name__, "get_bounced_cheques", "02", "Could not get bounced transactions for branch [%s]" % branch)
        return JsonResponse.server_error('Could not get approved transactions')

    return JsonResponse.success(data=transaction_list, nav=nav)

