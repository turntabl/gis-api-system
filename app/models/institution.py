# institution.py

import datetime
import enum

from app.application import db
from app.libs.utils import DateUtils


class Status(enum.Enum):
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'

    @staticmethod
    def values():
        return [s.value for s in Status]


class Institution(db.Document):
    name = db.StringField(required=True)
    country = db.StringField(required=True)
    short_name = db.StringField(required=True, unique=True)
    description = db.StringField(default='')
    contact_email = db.StringField(required=True)
    phone_numbers = db.ListField(db.LongField(), default=[])
    status = db.StringField(required=True, default=Status.ACTIVE.value, choices=Status.values())
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    modified_at = db.DateTimeField(null=True, default=None, onupdate=datetime.datetime.utcnow)

    meta = {
        'strict': False,
        'indexes': [
            'status',
            {
                'fields': ['short_name'],
                'collation': {
                    'locale': 'en',
                    'caseLevel': False,
                    'caseFirst': 'off',
                    'strength': 2,
                    'numericOrdering': False,
                    'alternate': 'non-ignorable',
                    'maxVariable': 'punct'
                }
            },
            {
                'fields': ['country'],
                'collation': {
                    'locale': 'en',
                    'caseLevel': False,
                    'caseFirst': 'off',
                    'strength': 2,
                    'numericOrdering': False,
                    'alternate': 'non-ignorable',
                    'maxVariable': 'punct'
                }
            }
        ]
    }

    def __repr__(self):
        return '<Institution %r>' % self.id

    def to_dict(self, minimal=False):
        dict_obj = {}

        if minimal:
            dict_obj['id'] = self.id
            dict_obj['name'] = self.name
            dict_obj['short_name'] = self.short_name
            dict_obj['country'] = self.country
            dict_obj['status'] = self.status
        else:
            for column, value in self._fields.items():
                if column in('created_at', 'modified_at'):
                    dict_obj[column] = DateUtils.format_datetime(getattr(self, column)) if getattr(self, column) is not None else None
                else:
                    dict_obj[column] = getattr(self, column)

        if 'id' in dict_obj:
            dict_obj['id'] = str(dict_obj['id'])

        return dict_obj
