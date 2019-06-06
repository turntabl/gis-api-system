# role.py

import datetime
import traceback

from app.config import config
from app.errors.errors import NotFoundError
from app.libs.logger import Logger
from app.models.role import AdminPrivileges
from app.models.role import BranchPrivileges
from app.models.role import DashboardPrivileges
from app.models.role import Privileges
from app.models.role import ReportPrivileges
from app.models.role import RolePrivileges
from app.models.role import SettingsPrivileges
from app.models.role import TransactionPrivileges
from app.models.role import Role


class RoleService:
    """
    Class contains functions and attributes for role service
    """

    @staticmethod
    def add_role(data):
        try:
            role_data = Role()
            role_data.name = data['name'].strip()
            role_data.created_by = data['created_by']
            # Build privileges
            privileges = Privileges()
            if 'privileges' in data:
                for module in data['privileges']:
                    module_priv_map = data['privileges'][module]
                    if module == 'dashboard':
                        dashboard_priv = DashboardPrivileges()
                        dashboard_priv.view_dashboard = module_priv_map.get('view_dashboard') or False
                        privileges.dashboard = dashboard_priv
                    elif module == 'admin':
                        admin_priv = AdminPrivileges()
                        admin_priv.add_admin = module_priv_map.get('add_admin') or False
                        admin_priv.view_admin = module_priv_map.get('view_admin') or False
                        admin_priv.update_admin = module_priv_map.get('update_admin') or False
                        privileges.admin = admin_priv
                    elif module == 'roles':
                        roles_priv = RolePrivileges()
                        roles_priv.add_role = module_priv_map.get('add_role') or False
                        roles_priv.view_role = module_priv_map.get('view_role') or False
                        roles_priv.update_role = module_priv_map.get('update_role') or False
                        privileges.roles = roles_priv
                    elif module == 'branch':
                        branch_priv = BranchPrivileges()
                        branch_priv.add_branch = module_priv_map.get('add_branch') or False
                        branch_priv.view_branch = module_priv_map.get('view_branch') or False
                        branch_priv.update_branch = module_priv_map.get('update_branch') or False
                        privileges.branch = branch_priv
                    elif module == 'transaction':
                        transaction_priv = TransactionPrivileges()
                        transaction_priv.initiate_cheque = module_priv_map.get('initiate_cheque') or False
                        transaction_priv.view_pre_approvals = module_priv_map.get('view_pre_approvals') or False
                        transaction_priv.approve_cheque = module_priv_map.get('approve_cheque') or False
                        transaction_priv.pay_cheque = module_priv_map.get('pay_cheque') or False
                        privileges.transaction = transaction_priv
                    elif module == 'report':
                        report_priv = ReportPrivileges()
                        report_priv.view_report = module_priv_map.get('view_report') or False
                        report_priv.export_report = module_priv_map.get('export_report') or False
                        privileges.report = report_priv
                    elif module == 'settings':
                        settings_priv = SettingsPrivileges()
                        settings_priv.view_settings = module_priv_map.get('view_settings') or False
                        settings_priv.manage_settings = module_priv_map.get('manage_settings') or False
                        privileges.settings = settings_priv

            role_data.privileges = privileges
            role_data.save()

            role_data = role_data.to_dict()
            Logger.info(__name__, "add_role", "00", "Role added successfully!", role_data)
        except KeyError as kex:
            Logger.error(__name__, "add_role", "02", "KeyError: {}".format(str(kex)), traceback.format_exc())
            raise kex
        except Exception as ex:
            Logger.error(__name__, "add_role", "02", "Exception occurred: {}".format(str(ex)), traceback.format_exc())
            raise ex

        return role_data

    @staticmethod
    def get_by_id(uid, minimal=False):

        try:
            role_data = Role.objects(id=uid).first()
            if role_data is not None:
                role_data = role_data.to_dict(minimal=minimal)
        except Exception as ex:
            role_data = None
            Logger.error(__name__, "get_by_id", "02", "Exception occurred: {}".format(ex), traceback.format_exc())

        return role_data

    @staticmethod
    def find_roles(order_by='-created_at', paginate=True, minimal=True, **filter_parameters):
        try:
            query = {}
            for field, value in filter_parameters.items():
                if field.split('__')[0] in Role._fields:
                    query[field] = value

            if 'size' not in filter_parameters:
                filter_parameters['size'] = config.DEFAULT_LIMIT
            if 'page' not in filter_parameters:
                filter_parameters['page'] = config.DEFAULT_PAGE

            Logger.debug(__name__, "find_roles", "00", "Filter query: %s" % str(query))

            if 'start_date' in filter_parameters and 'end_date' not in filter_parameters:
                role_data = Role.objects(
                    created_at__gte=datetime.datetime.strptime(filter_parameters['start_date'], '%Y-%m-%d')) \
                    .filter(**query).order_by(order_by)
            elif 'start_date'not in filter_parameters and 'end_date' in filter_parameters:
                role_data = Role.objects(
                    created_at__lt=datetime.datetime.strptime(filter_parameters['end_date'], "%Y-%m-%d") + datetime.timedelta(days=1)
                ).filter(**query).order_by(order_by)
            elif 'start_date' in filter_parameters and 'end_date' in filter_parameters:
                role_data = Role.objects(
                    created_at__gte=datetime.datetime.strptime(filter_parameters['start_date'], '%Y-%m-%d'),
                    created_at__lt=datetime.datetime.strptime(filter_parameters['end_date'], '%Y-%m-%d') + datetime.timedelta(days=1)
                ).filter(**query).order_by(order_by)
            else:
                role_data = Role.objects.filter(**query).order_by(order_by)

            # Paginate, if pagination requested
            role_list = []
            nav = None
            if paginate:
                role_data = role_data.paginate(int(filter_parameters['page']), int(filter_parameters['size']))
                nav = {
                    'current_page': int(filter_parameters['page']),
                    'next_page': role_data.next_num,
                    'prev_page': role_data.prev_num,
                    'total_pages': role_data.pages,
                    'total_records': role_data.total,
                    'size': int(filter_parameters['size'])
                }

                for role in role_data.items:
                    role_list.append(role.to_dict(minimal=minimal))
            else:
                for role in role_data:
                    role_list.append(role.to_dict(minimal=minimal))

            return role_list, nav
        except Exception as ex:
            Logger.error(__name__, "find_roles", "02", "Error while finding roles", traceback.format_exc())
            raise ex

    @staticmethod
    def update_role(uid, update_data):
        try:
            role_data = Role.objects(id=uid).first()
            if role_data is None:
                Logger.warn(__name__, "update_role", "01", "Role [{}] not found".format(uid))
                raise NotFoundError('Role not found')

            if 'name' in update_data:
                role_data.name = update_data['name'].strip()
            if 'privileges' in update_data:
                # Build privileges
                privileges = Privileges()
                for module in update_data['privileges']:
                    module_priv_map = update_data['privileges'][module]
                    if module == 'dashboard':
                        dashboard_priv = DashboardPrivileges()
                        dashboard_priv.view_dashboard = module_priv_map.get('view_dashboard') or False
                        privileges.dashboard = dashboard_priv
                    elif module == 'admin':
                        admin_priv = AdminPrivileges()
                        admin_priv.add_admin = module_priv_map.get('add_admin') or False
                        admin_priv.view_admin = module_priv_map.get('view_admin') or False
                        admin_priv.update_admin = module_priv_map.get('update_admin') or False
                        privileges.admin = admin_priv
                    elif module == 'roles':
                        roles_priv = RolePrivileges()
                        roles_priv.add_role = module_priv_map.get('add_role') or False
                        roles_priv.view_role = module_priv_map.get('view_role') or False
                        roles_priv.update_role = module_priv_map.get('update_role') or False
                        privileges.roles = roles_priv
                    elif module == 'branch':
                        branch_priv = BranchPrivileges()
                        branch_priv.add_branch = module_priv_map.get('add_branch') or False
                        branch_priv.view_branch = module_priv_map.get('view_branch') or False
                        branch_priv.update_branch = module_priv_map.get('update_branch') or False
                        privileges.branch = branch_priv
                    elif module == 'transaction':
                        transaction_priv = TransactionPrivileges()
                        transaction_priv.initiate_cheque = module_priv_map.get('initiate_cheque') or False
                        transaction_priv.view_pre_approvals = module_priv_map.get('view_pre_approvals') or False
                        transaction_priv.approve_cheque = module_priv_map.get('approve_cheque') or False
                        transaction_priv.pay_cheque = module_priv_map.get('pay_cheque') or False
                        privileges.transaction = transaction_priv
                    elif module == 'report':
                        report_priv = ReportPrivileges()
                        report_priv.view_report = module_priv_map.get('view_report') or False
                        report_priv.export_report = module_priv_map.get('export_report') or False
                        privileges.report = report_priv
                    elif module == 'settings':
                        settings_priv = SettingsPrivileges()
                        settings_priv.view_settings = module_priv_map.get('view_settings') or False
                        settings_priv.manage_settings = module_priv_map.get('manage_settings') or False
                        privileges.settings = settings_priv

                role_data.privileges = privileges

            role_data.modified_at = datetime.datetime.utcnow()  # TODO: Auto-set modified_at on update(with on_update)
            role_data.save()
            role = role_data.to_dict()
        except KeyError as kex:
            Logger.error(__name__, "update_role", "02", "KeyError: {}".format(str(kex)), traceback.format_exc())
            raise kex
        except Exception as ex:
            Logger.error(__name__, "update_role", "02", "Exception occurred: {}".format(str(ex)), traceback.format_exc())
            raise ex

        return role
