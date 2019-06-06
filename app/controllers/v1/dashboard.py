# dashboard.py

from flask import g
from flask import request

from app.controllers import api
from app.controllers import api_request
from app.controllers import JsonResponse
from app.libs.logger import Logger
from app.models.transaction import BankStatus
from app.models.transaction import CustomerStatus
from app.models.transaction import PaymentStatus
from app.services.v1.transaction import TransactionService


@api.route('/v1/dashboard', methods=['GET'])
# @api_request.api_authenticate
# @api_request.admin_authenticate('dashboard.view_dashboard')
def get_metrics():
    # admin_data = g.admin
    admin_data = {'username': 'creator', 'institution': {'id': '5cdea422feb488013bde8b9e', 'short_name': 'BANK1'}, 'branch': {'branch_id': 'BK1001'}}
    params = request.args.to_dict()
    Logger.debug(__name__, "get_metrics", "00", "Received request to get dashboard metrics", params)
    # Get date params if present
    filter_params = {key: params[key] for key in params if key in ('start_date', 'end_date')}
    # Get approved cheques (bank approved, customer approved)
    bank_approved_cheques = TransactionService.count_transactions(bank_status=BankStatus.PAYMENT_APPROVED.value,
                                                                  payment_status=PaymentStatus.UNPAID.value,
                                                                  **filter_params)
    customer_approved_cheques = TransactionService.count_transactions(customer_status=CustomerStatus.APPROVED.value,
                                                                      payment_status=PaymentStatus.UNPAID.value,
                                                                      **filter_params)
    # Get declined cheques (bank declined, customer declined)
    bank_declined_cheques = TransactionService.count_transactions(bank_status=BankStatus.DECLINED.value,
                                                                  payment_status=PaymentStatus.UNPAID.value,
                                                                  **filter_params)
    customer_declined_cheques = TransactionService.count_transactions(customer_status=CustomerStatus.DECLINED.value,
                                                                      payment_status=PaymentStatus.UNPAID.value,
                                                                      **filter_params)
    # Get pending cheques (pending bank, pending customer)
    pending_bank_cheques = TransactionService.count_transactions(bank_status=BankStatus.PENDING_PAYMENT_APPROVAL.value,
                                                                 payment_status=PaymentStatus.UNPAID.value,
                                                                 **filter_params)
    pending_customer_cheques = TransactionService.count_transactions(customer_status=CustomerStatus.PENDING_APPROVAL.value,
                                                                     payment_status=PaymentStatus.UNPAID.value,
                                                                     **filter_params)
    data = {
        'approved_cheques': {
            'bank_approved': bank_approved_cheques,
            'customer_approved': customer_approved_cheques,
        },
        'declined_cheques': {
            'bank_declined': bank_declined_cheques,
            'customer_declined': customer_declined_cheques,
        },
        'pending_cheques': {
            'pending_bank': pending_bank_cheques,
            'pending_customer': pending_customer_cheques,
        },
    }

    return JsonResponse.success(data=data)
