# transaction.py

import datetime
import traceback
from decimal import Decimal

from app.config import config
from app.errors.errors import NotFoundError
from app.libs.logger import Logger
from app.models.transaction import CustomerStatus
from app.models.transaction import Transaction


class TransactionService:
    """
    Class contains functions and attributes for transaction service
    """

    @staticmethod
    def add_transaction(data):
        try:
            transaction_data = Transaction()
            transaction_data.cheque_number = data['cheque_number'].strip()
            transaction_data.account_number = data['account_number'].strip()
            if 'msisdn' in data:
                transaction_data.msisdn = data['msisdn']
            transaction_data.payee_name = data['payee_name'].strip()
            transaction_data.currency = data['currency'].strip()
            transaction_data.amount = Decimal(data['amount'])
            transaction_data.reference = data['reference'].strip()
            transaction_data.institution = data.get('institution') or None
            transaction_data.processed_branch = data.get('processed_branch') or None
            if data.get('pre_approved') is True:
                transaction_data.msisdn = data['msisdn']
                transaction_data.pre_approved = data['pre_approved']
                transaction_data.customer_status = CustomerStatus.APPROVED.value
                transaction_data.customer_response_at = datetime.datetime.now()
            if 'initiated_by' in data:
                transaction_data.initiated_by = data['initiated_by']
                transaction_data.initiated_at = datetime.datetime.now()

            transaction_data.save()

            transaction_data = transaction_data.to_dict()
            Logger.info(__name__, "add_transaction", "00", "Transaction added successfully!", transaction_data)
        except KeyError as kex:
            Logger.error(__name__, "add_transaction", "02", "KeyError: {}".format(str(kex)), traceback.format_exc())
            raise kex
        except Exception as ex:
            Logger.error(__name__, "add_transaction", "02", "Exception occurred: {}".format(str(ex)), traceback.format_exc())
            raise ex

        return transaction_data

    @staticmethod
    def get_by_id(uid, minimal=False):

        try:
            transaction_data = Transaction.objects(id=uid).first()
            if transaction_data is not None:
                transaction_data = transaction_data.to_dict(minimal=minimal)
        except Exception as ex:
            transaction_data = None
            Logger.error(__name__, "get_by_id", "02", "Exception occurred: {}".format(ex), traceback.format_exc())

        return transaction_data

    @staticmethod
    def find_transactions(order_by='-created_at', paginate=True, minimal=True, **filter_parameters):
        try:
            query = {}
            for field, value in filter_parameters.items():
                if field.split('__')[0] in Transaction._fields and value != '':
                    query[field] = value

            if 'size' not in filter_parameters:
                filter_parameters['size'] = config.DEFAULT_LIMIT
            if 'page' not in filter_parameters:
                filter_parameters['page'] = config.DEFAULT_PAGE

            Logger.debug(__name__, "find_transactions", "00", "Filter query: %s" % str(query))

            if filter_parameters.get('start_date') and not filter_parameters.get('end_date'):
                transaction_data = Transaction.objects(
                    created_at__gte=datetime.datetime.strptime(filter_parameters['start_date'], '%Y-%m-%d')) \
                    .filter(**query).order_by(order_by)
            elif not filter_parameters.get('start_date') and filter_parameters.get('end_date'):
                transaction_data = Transaction.objects(
                    created_at__lt=datetime.datetime.strptime(filter_parameters['end_date'], "%Y-%m-%d") + datetime.timedelta(days=1)
                ).filter(**query).order_by(order_by)
            elif filter_parameters.get('start_date') and filter_parameters.get('end_date'):
                transaction_data = Transaction.objects(
                    created_at__gte=datetime.datetime.strptime(filter_parameters['start_date'], '%Y-%m-%d'),
                    created_at__lt=datetime.datetime.strptime(filter_parameters['end_date'], '%Y-%m-%d') + datetime.timedelta(days=1)
                ).filter(**query).order_by(order_by)
            else:
                transaction_data = Transaction.objects.filter(**query).order_by(order_by)

            # Paginate, if pagination requested
            transaction_list = []
            nav = None
            if paginate:
                transaction_data = transaction_data.paginate(int(filter_parameters['page']), int(filter_parameters['size']))
                nav = {
                    'current_page': int(filter_parameters['page']),
                    'next_page': transaction_data.next_num,
                    'prev_page': transaction_data.prev_num,
                    'total_pages': transaction_data.pages,
                    'total_records': transaction_data.total,
                    'size': int(filter_parameters['size'])
                }

                for transaction in transaction_data.items:
                    transaction_list.append(transaction.to_dict(minimal=minimal))
            else:
                for transaction in transaction_data:
                    transaction_list.append(transaction.to_dict(minimal=minimal))

            return transaction_list, nav
        except Exception as ex:
            Logger.error(__name__, "find_transactions", "02", "Error while finding transactions", traceback.format_exc())
            raise ex

    @staticmethod
    def count_transactions(**filter_parameters):
        try:
            query = {}
            for field, value in filter_parameters.items():
                if field.split('__')[0] in Transaction._fields and value != '':
                    query[field] = value

            Logger.debug(__name__, "count_transactions", "00", "Filter query: %s" % str(query))

            if 'start_date' in filter_parameters and 'end_date' not in filter_parameters:
                transaction_count = Transaction.objects(
                    created_at__gte=datetime.datetime.strptime(filter_parameters['start_date'], '%Y-%m-%d')) \
                    .filter(**query).count()
            elif 'start_date'not in filter_parameters and 'end_date' in filter_parameters:
                transaction_count = Transaction.objects(
                    created_at__lt=datetime.datetime.strptime(filter_parameters['end_date'], "%Y-%m-%d") + datetime.timedelta(days=1)
                ).filter(**query).count()
            elif 'start_date' in filter_parameters and 'end_date' in filter_parameters:
                transaction_count = Transaction.objects(
                    created_at__gte=datetime.datetime.strptime(filter_parameters['start_date'], '%Y-%m-%d'),
                    created_at__lt=datetime.datetime.strptime(filter_parameters['end_date'], '%Y-%m-%d') + datetime.timedelta(days=1)
                ).filter(**query).count()
            else:
                transaction_count = Transaction.objects.filter(**query).count()

            return transaction_count
        except Exception as ex:
            Logger.error(__name__, "count_transactions", "02", "Error while counting transactions", traceback.format_exc())
            raise ex

    @staticmethod
    def update_transaction(uid, update_data):
        try:
            transaction_data = Transaction.objects(id=uid).first()
            if transaction_data is None:
                Logger.warn(__name__, "update_transaction", "01", "Transaction [{}] not found".format(uid))
                raise NotFoundError('Administrator not found')

            if 'msisdn' in update_data:
                transaction_data.msisdn = update_data['msisdn']
            if 'customer_name' in update_data:
                transaction_data.customer_name = update_data['customer_name'].strip()
            if 'payee_name' in update_data:
                transaction_data.payee_name = update_data['payee_name'].strip()
            if 'balance' in update_data:
                transaction_data.balance = update_data['balance']
            if 'mandate' in update_data:
                transaction_data.mandate = update_data['mandate'].strip()
            if 'cheque_instructions' in update_data:
                transaction_data.cheque_instructions = update_data['cheque_instructions'].strip()
            if 'institution' in update_data:
                transaction_data.institution = update_data['institution'].strip()
            if 'processed_branch' in update_data:
                transaction_data.processed_branch = update_data['processed_branch'].strip()
            if 'approval_sms_sent' in update_data:
                transaction_data.approval_sms_sent = update_data['approval_sms_sent']
            if 'approval_retries' in update_data:
                transaction_data.approval_retries = update_data['approval_retries']
            if 'customer_status' in update_data:
                transaction_data.customer_status = update_data['customer_status']
                if update_data['customer_status'] in (CustomerStatus.APPROVED.value, CustomerStatus.DECLINED.value):
                    transaction_data.customer_response_at = datetime.datetime.now()
                elif update_data['customer_status'] == CustomerStatus.EXPIRED.value:
                    transaction_data.expired_at = datetime.datetime.now()
            if 'customer_remarks' in update_data:
                transaction_data.customer_remarks = update_data['customer_remarks'].strip()
            if 'bank_status' in update_data:
                transaction_data.bank_status = update_data['bank_status']
            if 'bank_remarks' in update_data:
                transaction_data.bank_remarks = update_data['bank_remarks'].strip()
            if 'payment_status' in update_data:
                transaction_data.payment_status = update_data['payment_status']
            if 'cheque_resubmission_flag' in update_data:
                transaction_data.cheque_resubmission_flag = update_data['cheque_resubmission_flag']
            if 'approved_by' in update_data:
                transaction_data.approved_by = update_data['approved_by']
            if 'paid_by' in update_data:
                transaction_data.paid_by = update_data['paid_by']
            if 'payout_type' in update_data:
                transaction_data.payout_type = update_data['payout_type']

            transaction_data.modified_at = datetime.datetime.utcnow()  # TODO: Auto-set modified_at on update(with on_update)
            transaction_data.save()
            administrator = transaction_data.to_dict()
        except KeyError as kex:
            Logger.error(__name__, "update_transaction", "02", "KeyError: {}".format(str(kex)), traceback.format_exc())
            raise kex
        except Exception as ex:
            Logger.error(__name__, "update_transaction", "02", "Exception occurred: {}".format(str(ex)), traceback.format_exc())
            raise ex

        return administrator
