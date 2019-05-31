# role.py

import datetime

from app.application import db
from app.libs.utils import DateUtils


class DashboardPrivileges(db.EmbeddedDocument):
    view_dashboard = db.BooleanField(required=True, default=False)


class AdminPrivileges(db.EmbeddedDocument):
    add_admin = db.BooleanField(required=True, default=False)
    view_admin = db.BooleanField(required=True, default=False)
    update_admin = db.BooleanField(required=True, default=False)


class RolePrivileges(db.EmbeddedDocument):
    add_role = db.BooleanField(required=True, default=False)
    view_role = db.BooleanField(required=True, default=False)
    update_role = db.BooleanField(required=True, default=False)


class BranchPrivileges(db.EmbeddedDocument):
    add_branch = db.BooleanField(required=True, default=False)
    view_branch = db.BooleanField(required=True, default=False)
    update_branch = db.BooleanField(required=True, default=False)


class TransactionPrivileges(db.EmbeddedDocument):
    initiate_cheque = db.BooleanField(required=True, default=False)
    approve_cheque = db.BooleanField(required=True, default=False)
    pay_cheque = db.BooleanField(required=True, default=False)


class ReportPrivileges(db.EmbeddedDocument):
    view_report = db.BooleanField(required=True, default=False)
    export_report = db.BooleanField(required=True, default=False)


class Privileges(db.EmbeddedDocument):
    dashboard = db.EmbeddedDocumentField(DashboardPrivileges, required=True)
    admin = db.EmbeddedDocumentField(AdminPrivileges, required=True)
    roles = db.EmbeddedDocumentField(RolePrivileges, required=True)
    branch = db.EmbeddedDocumentField(BranchPrivileges, required=True)
    transaction = db.EmbeddedDocumentField(TransactionPrivileges, required=True)
    report = db.EmbeddedDocumentField(ReportPrivileges, required=True)


class Role(db.Document):
    name = db.StringField(required=True)
    privileges = db.EmbeddedDocumentField(Privileges, required=True)
    created_by = db.StringField(required=True, null=False)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    modified_at = db.DateTimeField(null=True, default=None, onupdate=datetime.datetime.utcnow)

    meta = {
        'strict': False
    }

    def __repr__(self):
        return '<Role %r>' % self.id

    def to_dict(self, minimal=False):
        dict_obj = {}

        if minimal:
            dict_obj['id'] = self.id
            dict_obj['name'] = self.name
            dict_obj['privileges'] = self.privileges
        else:
            for column, value in self._fields.items():
                if column in ('created_at', 'modified_at'):
                    dict_obj[column] = DateUtils.format_datetime(getattr(self, column)) if getattr(self, column) is not None else None
                else:
                    dict_obj[column] = getattr(self, column)

        if 'id' in dict_obj:
            dict_obj['id'] = str(dict_obj['id'])

        return dict_obj
