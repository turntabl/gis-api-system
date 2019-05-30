# administrator.py

import datetime
import enum

from app.application import db
from app.libs.utils import DateUtils
from app.services.v1.branch import BranchService
from app.services.v1.institution import InstitutionService
from app.services.v1.role import RoleService


class Status(enum.Enum):
    INACTIVE = 'INACTIVE'
    ACTIVE = 'ACTIVE'
    SUSPENDED = 'SUSPENDED'

    @staticmethod
    def values():
        return [s.value for s in Status]


class Administrator(db.Document):
    username = db.StringField(required=True, unique=True)
    first_name = db.StringField(required=True)
    last_name = db.StringField(required=True)
    email = db.StringField(required=True, unique_with='institution')
    phone_number = db.LongField(null=True, default=None)
    password = db.StringField(required=True)
    institution = db.StringField(required=True, unique_with='email')
    branch = db.StringField(required=True)
    role = db.StringField(required=True)
    status = db.StringField(required=True, default=Status.INACTIVE.value, choices=Status.values())
    consecutive_wrong_logins = db.IntField(default=0)
    session_token = db.StringField(required=False, null=True, default=None)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    modified_at = db.DateTimeField(null=True, default=None, onupdate=datetime.datetime.utcnow)
    last_login_date = db.DateTimeField(null=True, default=None)
    password_last_changed_at = db.DateTimeField(null=True, default=None)

    meta = {
        'strict': False,
        'indexes': [
            'phone_number',
            'institution',
            'branch',
            'status',
            {
                'fields': ['username'],
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
                'fields': ['email'],
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
        return '<Administrator %r>' % self.id

    def to_dict(self, include_password=False, minimal=False):
        dict_obj = {}
        for column, value in self._fields.items():
            if column == "institution":
                dict_obj[column] = InstitutionService.get_by_id(getattr(self, column), minimal=True)
            elif column == "branch":
                dict_obj[column] = BranchService.get_by_branch_id(getattr(self, column), minimal=True)
            elif column == "role":
                dict_obj[column] = RoleService.get_by_id(getattr(self, column), minimal=True)
            elif column in ("created_at", "modified_at", "last_login_date", "password_last_changed_at"):
                dict_obj[column] = DateUtils.format_datetime(getattr(self, column)) if getattr(self, column) is not None else None
            elif column == 'password':
                if include_password:
                    dict_obj[column] = getattr(self, column)
            else:
                dict_obj[column] = getattr(self, column)

        if "id" in dict_obj:
            dict_obj["id"] = str(dict_obj["id"])

        return dict_obj
