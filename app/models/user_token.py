# user_token.py

import datetime
import enum

from app.application import db


class Status(enum.Enum):
    PENDING = 'PENDING'
    USED = 'USED'

    @classmethod
    def values(cls):
        return [s.value for s in Status]


class Type(enum.Enum):
    PASSWORD_RESET = 'PASSWORD_RESET'


class UserToken(db.Document):
    username = db.StringField(required=True, unique_with='token')
    token = db.StringField(required=True, unique_with='username')
    type = db.StringField(required=True)
    status = db.StringField(required=True, default=Status.PENDING.value)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    modified_at = db.DateTimeField(null=True, default=None, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return '<UserToken %r>' % self.username

    def to_dict(self):
        dict_obj = {}
        for column, value in self._fields.items():
            if column == 'created_at':
                dict_obj[column] = str(getattr(self, column))
            elif column == 'modified_at' and getattr(self, column) is not None:
                dict_obj[column] = str(getattr(self, column))
            else:
                dict_obj[column] = getattr(self, column)

        if 'id' in dict_obj:
            dict_obj['id'] = str(dict_obj['id'])
        return dict_obj
