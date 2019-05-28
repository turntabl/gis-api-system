# transaction.py

import datetime
import enum

from app.application import db
from app.libs.utils import DateUtils


class CustomerStatus(enum.Enum):
    PENDING_APPROVAL = 'PENDING_APPROVAL'
    APPROVED = 'APPROVED'
    DECLINED = 'DECLINED'
    EXPIRED = 'EXPIRED'

    @staticmethod
    def values():
        return [c.value for c in CustomerStatus]


class BankStatus(enum.Enum):
    INITIATED = 'INITIATED'
    PENDING_CUSTOMER_APPROVAL = 'PENDING_CUSTOMER_APPROVAL'
    PENDING_BANK_APPROVAL = 'PENDING_BANK_APPROVAL'
    PENDING_PAYMENT_APPROVAL = 'PENDING_PAYMENT_APPROVAL'
    PAYMENT_APPROVED = 'PAYMENT_APPROVED'
    COMPLETED = 'COMPLETED'
    DECLINED = 'DECLINED'
    CANCELLED = 'CANCELLED'
    BOUNCED = 'BOUNCED'

    @staticmethod
    def values():
        return [b.value for b in BankStatus]


class PaymentStatus(enum.Enum):
    UNPAID = 'UNPAID'
    PAID = 'PAID'

    @staticmethod
    def values():
        return [p.value for p in PaymentStatus]


class PayoutType(enum.Enum):
    CASH = 'CASH'
    MOBILE_MONEY = 'MOBILE_MONEY'
    ACCOUNT_TRANSFER = 'ACCOUNT_TRANSFER'
    BANKERS_DRAFT = 'BANKERS_DRAFT'

    @staticmethod
    def values():
        return [po.value for po in PayoutType]


class Transaction(db.Document):
    transaction_id = db.StringField(null=True, default=None)
    cheque_number = db.StringField(required=True)
    account_number = db.StringField(required=True)
    reference = db.StringField(required=True)
    currency = db.StringField(required=True)
    amount = db.DecimalField(required=True, precision=4)
    msisdn = db.LongField(null=True, default=None)
    payee_name = db.StringField(required=False, default='')
    customer_name = db.StringField(required=False, default='')
    balance = db.DecimalField(null=True, default=None, precision=4)
    mandate = db.StringField(required=False, null=True, default=None)
    cheque_instructions = db.StringField(required=False, null=True, default=None)
    institution = db.StringField(null=True, default=None)
    processed_branch = db.StringField(null=True, default=None)
    pre_approved = db.BooleanField(required=True, default=False)
    approval_sms_sent = db.BooleanField(required=True, default=False)
    approval_retries = db.IntField(default=0)
    customer_status = db.StringField(null=True, default=None, choices=CustomerStatus.values())
    customer_remarks = db.StringField(required=False, default='')
    bank_status = db.StringField(null=True, default=None, choices=BankStatus.values())
    bank_remarks = db.StringField(required=False, default='')
    payment_status = db.StringField(required=True, default=PaymentStatus.UNPAID.value, choices=PaymentStatus.values())
    cheque_resubmission_flag = db.BooleanField(required=True, default=True)
    payout_type = db.StringField(null=True, default=None, choices=PayoutType.values())
    initiated_by = db.StringField(null=True, default=None)
    approved_by = db.StringField(null=True, default=None)
    paid_by = db.StringField(null=True, default=None)
    initiated_at = db.DateTimeField(null=True, default=None)
    customer_response_at = db.DateTimeField(null=True, default=None)
    expired_at = db.DateTimeField(null=True, default=None)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    modified_at = db.DateTimeField(null=True, default=None, onupdate=datetime.datetime.utcnow)

    meta = {
        'strict': False,
        'indexes': [
            'cheque_number',
            'account_number',
            'reference',
            'msisdn',
            'institution',
            'processed_branch',
            'pre_approved',
            'customer_status',
            'bank_status',
            'payment_status',
            'payout_type',
        ]
    }

    def __repr__(self):
        return '<Transaction %r>' % self.id

    def to_dict(self, minimal=False):
        dict_obj = {}

        for column, value in self._fields.items():
            if column in('created_at', 'modified_at', 'initiated_at', 'customer_response_at'):
                dict_obj[column] = DateUtils.format_datetime(getattr(self, column)) if getattr(self, column) is not None else None
            elif column in ('amount', 'balance'):
                dict_obj[column] = float(getattr(self, column)) if getattr(self, column) is not None else None
            else:
                dict_obj[column] = getattr(self, column)

        if 'id' in dict_obj:
            dict_obj['id'] = str(dict_obj['id'])

        return dict_obj
