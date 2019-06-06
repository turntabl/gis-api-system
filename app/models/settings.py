# settings.py

import datetime

from app.application import db
from app.libs.utils import DateUtils


class Settings(db.Document):
    pre_approval_expiry_hours = db.IntField(required=True, null=False)
    approval_expiry_hours = db.IntField(required=True, null=False)
    approval_reminder_interval = db.IntField(required=True, null=False)
    approval_reminder_frequency = db.IntField(required=True, null=False)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    modified_at = db.DateTimeField(null=True, default=None, onupdate=datetime.datetime.utcnow)

    meta = {
        'strict': False
    }

    def __repr__(self):
        return '<Settings %r>' % self.id

    def to_dict(self, minimal=False):
        dict_obj = {}

        if minimal:
            dict_obj['id'] = self.id
            dict_obj['pre_approval_expiry_hours'] = self.pre_approval_expiry_hours
            dict_obj['approval_expiry_hours'] = self.approval_expiry_hours
            dict_obj['approval_reminder_interval'] = self.approval_reminder_interval
            dict_obj['approval_reminder_frequency'] = self.approval_reminder_frequency
        else:
            for column, value in self._fields.items():
                if column in('created_at', 'modified_at'):
                    dict_obj[column] = DateUtils.format_datetime(getattr(self, column)) if getattr(self, column) is not None else None
                else:
                    dict_obj[column] = getattr(self, column)

        if 'id' in dict_obj:
            dict_obj['id'] = str(dict_obj['id'])

        return dict_obj
