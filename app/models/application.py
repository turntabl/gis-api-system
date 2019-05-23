# application.py

import datetime

from app.application import db
from app.libs.utils import DateUtils


class Application(db.Document):
    name = db.StringField(required=True)
    api_key = db.StringField(required=True, unique=True)
    allowed_ips = db.ListField(db.StringField(), default=[])
    functions = db.ListField(default=[])
    active = db.BooleanField(required=True, default=True)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    modified_at = db.DateTimeField(null=True, default=None, onupdate=datetime.datetime.utcnow)

    meta = {
        'strict': False
    }

    def __repr__(self):
        return '<Application %r>' % self.id

    def to_dict(self):
        dict_obj = {}
        for column, value in self._fields.items():
            if column in ('created_at', 'modified_at'):
                dict_obj[column] = DateUtils.format_datetime(getattr(self, column)) if getattr(self, column) is not None else None
            else:
                dict_obj[column] = getattr(self, column)

        if 'id' in dict_obj:
            dict_obj['id'] = str(dict_obj['id'])

        return dict_obj
