# branch.py

import datetime
import enum

from app.application import db
from app.services.v1.institution import InstitutionService
from app.libs.utils import DateUtils


class Status(enum.Enum):
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'

    @staticmethod
    def values():
        return [s.value for s in Status]


class Branch(db.Document):
    name = db.StringField(required=True)
    branch_id = db.StringField(required=True, unique_with='institution')
    institution = db.StringField(required=True, unique_with='branch_id')
    status = db.StringField(required=True, default=Status.ACTIVE.value, choices=Status.values())
    created_by = db.StringField(required=True, null=False)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    modified_at = db.DateTimeField(null=True, default=None, onupdate=datetime.datetime.utcnow)

    meta = {
        'strict': False,
        'indexes': [
            'institution'
        ]
    }

    def __repr__(self):
        return '<Branch %r>' % self.id

    def to_dict(self, minimal=False):
        dict_obj = {}

        if minimal:
            dict_obj['id'] = self.id
            dict_obj['name'] = self.name
            dict_obj['branch_id'] = self.branch_id
            dict_obj['institution'] = self.institution
            dict_obj['status'] = self.status
        else:
            for column, value in self._fields.items():
                if column in('created_at', 'modified_at'):
                    dict_obj[column] = DateUtils.format_datetime(getattr(self, column)) if getattr(self, column) is not None else None
                elif column == 'institution':
                    dict_obj[column] = InstitutionService.get_by_id(getattr(self, column), minimal=True)
                else:
                    dict_obj[column] = getattr(self, column)

        if 'id' in dict_obj:
            dict_obj['id'] = str(dict_obj['id'])

        return dict_obj
