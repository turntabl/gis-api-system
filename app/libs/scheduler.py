# scheduler.py

import datetime

from app.application import celery
from app.config import config
from app.libs.logger import Logger
from app.libs.utils import Utils
from app.models.transaction import CustomerStatus
from app.services.v1.transaction import TransactionService


class Scheduler:

    @staticmethod
    @celery.task
    def expire_cheque_pending_customer(transaction_id):
        Logger.debug(__name__, "expire_cheque_pending_customer", "00", "Expiring cheque if it has not been approved")
        transaction_data = TransactionService.get_by_id(transaction_id)
        if transaction_data is None:
            Logger.warn(__name__, "expire_cheque_pending_customer", "01", "Transaction [%s] not found" % transaction_id)
            return
        if transaction_data['customer_status'] != CustomerStatus.PENDING_APPROVAL.value:
            Logger.warn(__name__, "expire_cheque_pending_customer", "01",
                        "Transaction [%s] not pending customer approval. CustomerStatus: [%s]" % (transaction_id, transaction_data['customer_status']))
            return
        Logger.debug(__name__, "expire_cheque_pending_customer", "00", "Updating transaction [%s] to expired" % transaction_id)
        transaction_update = {'customer_status': CustomerStatus.EXPIRED.value}
        try:
            updated_transaction_data = TransactionService.update_transaction(transaction_id, transaction_update)
            Logger.info(__name__, "expire_cheque_pending_customer", "00", "Transaction [%s] expired" % transaction_id)
        except Exception as ex:
            Logger.error(__name__, "expire_cheque_pending_customer", "02",
                         "Error while updating transaction [%s] to expired: %s" % (transaction_id, ex))
            # Reschedule expiry
            retry_at = datetime.datetime.now() + datetime.timedelta(minutes=5)
            Scheduler.expire_cheque_pending_customer.apply_sync(args=[transaction_id], eta=retry_at)

    @staticmethod
    @celery.task
    def expire_pre_approved_cheque(transaction_id):
        Logger.debug(__name__, "expire_pre_approved_cheque", "00", "Expiring pre-approved cheque if it has not been processed")
        transaction_data = TransactionService.get_by_id(transaction_id)
        if transaction_data is None:
            Logger.warn(__name__, "expire_pre_approved_cheque", "01", "Transaction [%s] not found" % transaction_id)
            return
        if not transaction_data['pre_approved'] or transaction_data['customer_status'] != CustomerStatus.APPROVED.value:
            Logger.warn(__name__, "expire_pre_approved_cheque", "01",
                        "Transaction [%s] not pending customer approval. CustomerStatus: [%s]" % (transaction_id, transaction_data['customer_status']))
            return
        Logger.debug(__name__, "expire_pre_approved_cheque", "00", "Updating transaction [%s] to expired" % transaction_id)
        transaction_update = {'customer_status': CustomerStatus.EXPIRED.value}
        try:
            updated_transaction_data = TransactionService.update_transaction(transaction_id, transaction_update)
            Logger.info(__name__, "expire_pre_approved_cheque", "00", "Transaction [%s] expired" % transaction_id)
        except Exception as ex:
            Logger.error(__name__, "expire_pre_approved_cheque", "02",
                         "Error while updating transaction [%s] to expired: %s" % (transaction_id, ex))
            # Reschedule expiry
            retry_at = datetime.datetime.now() + datetime.timedelta(minutes=5)
            Scheduler.expire_cheque_pending_customer.apply_async(args=[transaction_id], eta=retry_at)

    @staticmethod
    @celery.task
    def send_approval_reminder(transaction_id):
        Logger.debug(__name__, "send_approval_reminder", "00", "Sending approval reminder for transaction [%s]" % transaction_id)
        transaction_data = TransactionService.get_by_id(transaction_id)
        if transaction_data is None:
            Logger.warn(__name__, "send_approval_reminder", "01", "Transaction [%s] not found" % transaction_id)
            return
        if transaction_data['customer_status'] != CustomerStatus.PENDING_APPROVAL.value:
            Logger.warn(__name__, "send_approval_reminder", "01",
                        "Transaction [%s] not pending customer approval. CustomerStatus: [%s]" % (transaction_id, transaction_data['customer_status']))
            return
        # Resend notification
        # Account owner msisdn
        msisdn = transaction_data['msisdn']

        # Send approval request SMS to msisdn linked to account number
        Logger.debug(__name__, "send_approval_reminder", "00", "Sending cheque approval SMS to [%s]" % msisdn)
        sms_sent = Utils.send_sms(msisdn, config.CHEQUE_APPROVAL_SMS)
        if sms_sent:
            try:
                transaction_update = {
                    'approval_retries': transaction_data['approval_retries'] + 1
                }
                updated_transaction_data = TransactionService.update_transaction(transaction_id, transaction_update)
                Logger.info(__name__, "send_approval_reminder", "00", "Cheque approval SMS sent to [%s]" % msisdn)
            except Exception as ex:
                Logger.error(__name__, "send_approval_reminder", "02", "Updating transaction [%s] approval retrjes failed: %s" % (transaction_id, ex))
                return
        else:
            Logger.warn(__name__, "send_approval_reminder", "00", "Sending cheque approval SMS to [%s] failed" % msisdn)
            return
        Logger.debug(__name__, "send_approval_reminder", "00", "Updating transaction [%s] to expired" % transaction_id)
        transaction_update = {'customer_status': CustomerStatus.EXPIRED.value}
        try:
            updated_transaction_data = TransactionService.update_transaction(transaction_id, transaction_update)
            Logger.info(__name__, "send_approval_reminder", "00", "Transaction [%s] expired" % transaction_id)
        except Exception as ex:
            Logger.error(__name__, "send_approval_reminder", "02",
                         "Error while updating transaction [%s] to expired: %s" % (transaction_id, ex))
            # Reschedule expiry
            retry_at = datetime.datetime.now() + datetime.timedelta(minutes=5)
            Scheduler.expire_cheque_pending_customer.apply_sync(args=[transaction_id], eta=retry_at)

