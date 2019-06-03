# administrator.py

import datetime
import re
import traceback

from mongoengine.queryset.visitor import Q

from app.config import config
from app.errors.errors import NotFoundError
from app.libs.logger import Logger
from app.libs.utils import Utils
from app.models.administrator import Administrator


class AdministratorService:
    """
    Class contains functions and attributes for administrator service
    """

    @staticmethod
    def add_administrator(data):
        try:
            admin_data = Administrator()
            admin_data.username = data['username'].strip()
            admin_data.first_name = data['first_name'].strip()
            admin_data.last_name = data['last_name'].strip()
            admin_data.email = data['email'].strip()
            admin_data.phone_number = data.get('phone_number')
            admin_data.password = data['password']
            admin_data.institution = data['institution']
            admin_data.branch = data['branch']
            admin_data.role = data['role']
            admin_data.password_last_changed_at = datetime.datetime.utcnow()

            admin_data.save()

            admin_data = admin_data.to_dict()
            Logger.info(__name__, "add_administrator", "00", "Administrator added successfully!", admin_data)
        except KeyError as kex:
            Logger.error(__name__, "add_administrator", "02", "KeyError: {}".format(str(kex)), traceback.format_exc())
            raise kex
        except Exception as ex:
            Logger.error(__name__, "add_administrator", "02", "Exception occurred: {}".format(str(ex)), traceback.format_exc())
            raise ex

        return admin_data

    @staticmethod
    def get_by_id(uid, minimal=False):

        try:
            username_regex = re.compile('^'+re.escape(uid.strip())+'$', re.IGNORECASE)
            administrator_data = Administrator.objects(Q(username=username_regex) | Q(id=uid)).first()
            if administrator_data is not None:
                administrator_data = administrator_data.to_dict(minimal=minimal)
        except Exception as ex:
            administrator_data = None
            Logger.error(__name__, "get_by_id", "02", "Exception occurred: {}".format(ex), traceback.format_exc())

        return administrator_data

    @staticmethod
    def find_by_username(username: str, include_password=False, include_session=False):
        try:
            username_regex = re.compile('^'+re.escape(username.strip())+'$', re.IGNORECASE)
            admin_data = Administrator.objects(username=username_regex).first()
            if admin_data is not None:
                admin_data = admin_data.to_dict(include_password=include_password, include_session=include_session)
        except Exception as ex:
            admin_data = None
            Logger.error(__name__, "find_by_username", "02", "Exception occurred: {}".format(ex), traceback.format_exc())

        return admin_data

    @staticmethod
    def find_by_email(email: str):
        try:
            email_regex = re.compile('^'+re.escape(email.strip())+'$', re.IGNORECASE)
            admin_data = Administrator.objects(email=email_regex).first()
            if admin_data is not None:
                admin_data = admin_data.to_dict()
        except Exception as ex:
            admin_data = None
            Logger.error(__name__, "find_by_email", "02", "Exception occurred: {}".format(ex), traceback.format_exc())

        return admin_data

    @staticmethod
    def find_by_email_and_institution(email: str, institution: str):
        try:
            email_regex = re.compile('^'+re.escape(email.strip())+'$', re.IGNORECASE)
            admin_data = Administrator.objects(email=email_regex, institution=institution).first()
            if admin_data is not None:
                admin_data = admin_data.to_dict()
        except Exception as ex:
            admin_data = None
            Logger.error(__name__, "find_by_email_and_institution", "02", "Exception occurred: {}".format(ex), traceback.format_exc())

        return admin_data

    @staticmethod
    def find_by_username_password(username: str, password: str):
        try:
            password_hash = Utils.hash_password(password)
            username_regex = re.compile('^'+re.escape(username.strip())+'$', re.IGNORECASE)
            admin_data = Administrator.objects(username=username_regex, password=password_hash).first()
        except Exception as ex:
            admin_data = None
            Logger.error(__name__, "find_by_username_password", "02", "Exception occurred: {}".format(ex), traceback.format_exc())

        return admin_data

    @staticmethod
    def find_administrators(order_by='-created_at', paginate=True, minimal=True, **filter_parameters):
        try:
            query = {}
            for field, value in filter_parameters.items():
                if field.split('__')[0] in Administrator._fields and value != '':
                    query[field] = value

            if 'size' not in filter_parameters:
                filter_parameters['size'] = config.DEFAULT_LIMIT
            if 'page' not in filter_parameters:
                filter_parameters['page'] = config.DEFAULT_PAGE

            Logger.debug(__name__, "find_administrators", "00", "Filter query: %s" % str(query))

            if filter_parameters.get('start_date') and not filter_parameters.get('end_date'):
                administrator_data = Administrator.objects(
                    created_at__gte=datetime.datetime.strptime(filter_parameters['start_date'], '%Y-%m-%d')) \
                    .filter(**query).order_by(order_by)
            elif not filter_parameters.get('start_date') and filter_parameters.get('end_date'):
                administrator_data = Administrator.objects(
                    created_at__lt=datetime.datetime.strptime(filter_parameters['end_date'], "%Y-%m-%d") + datetime.timedelta(days=1)
                ).filter(**query).order_by(order_by)
            elif filter_parameters.get('start_date') and filter_parameters.get('end_date'):
                administrator_data = Administrator.objects(
                    created_at__gte=datetime.datetime.strptime(filter_parameters['start_date'], '%Y-%m-%d'),
                    created_at__lt=datetime.datetime.strptime(filter_parameters['end_date'], '%Y-%m-%d') + datetime.timedelta(days=1)
                ).filter(**query).order_by(order_by)
            else:
                administrator_data = Administrator.objects.filter(**query).order_by(order_by)

            # Paginate, if pagination requested
            administrator_list = []
            nav = None
            if paginate:
                administrator_data = administrator_data.paginate(int(filter_parameters['page']), int(filter_parameters['size']))
                nav = {
                    'current_page': int(filter_parameters['page']),
                    'next_page': administrator_data.next_num,
                    'prev_page': administrator_data.prev_num,
                    'total_pages': administrator_data.pages,
                    'total_records': administrator_data.total,
                    'size': int(filter_parameters['size'])
                }

                for administrator in administrator_data.items:
                    administrator_list.append(administrator.to_dict(minimal=minimal))
            else:
                for administrator in administrator_data:
                    administrator_list.append(administrator.to_dict(minimal=minimal))

            return administrator_list, nav
        except Exception as ex:
            Logger.error(__name__, "find_administrators", "02", "Error while finding administrators", traceback.format_exc())
            raise ex

    @staticmethod
    def update_administrator(uid, update_data):
        try:
            admin_data = Administrator.objects(id=uid).first()
            if admin_data is None:
                Logger.warn(__name__, "update_administrator", "01", "Administrator [{}] not found".format(uid))
                raise NotFoundError('Administrator not found')

            if 'first_name' in update_data:
                admin_data.first_name = update_data['first_name'].strip()
            if 'last_name' in update_data:
                admin_data.last_name = update_data['last_name'].strip()
            if 'phone_number' in update_data:
                admin_data.phone_number = update_data['phone_number']
            if 'status' in update_data:
                admin_data.status = update_data['status']
            if 'branch' in update_data:
                admin_data.branch = update_data['branch']
            if 'role' in update_data:
                admin_data.role = update_data['role']
            if 'session_token' in update_data:
                admin_data.session_token = update_data['session_token']
                admin_data.last_login_date = datetime.datetime.utcnow()
            if 'password' in update_data:
                admin_data.password = update_data['password']
                admin_data.password_last_changed_at = datetime.datetime.utcnow()

            admin_data.modified_at = datetime.datetime.utcnow()  # TODO: Auto-set modified_at on update(with on_update)
            admin_data.save()
            administrator = admin_data.to_dict()
        except KeyError as kex:
            Logger.error(__name__, "update_administrator", "02", "KeyError: {}".format(str(kex)), traceback.format_exc())
            raise kex
        except Exception as ex:
            Logger.error(__name__, "update_administrator", "02", "Exception occurred: {}".format(str(ex)), traceback.format_exc())
            raise ex

        return administrator

    @staticmethod
    def update_last_login(admin_id):
        try:
            admin_data = Administrator.objects(id=admin_id).first()
            if admin_data is None:
                raise NotFoundError('Administrator not found')

            admin_data.last_login_at = datetime.datetime.utcnow()
            admin_data.modified_at = datetime.datetime.utcnow()  # TODO: Auto-set modified_at on update(with on_update)
            admin_data.save()

            return admin_data.to_dict()
        except Exception as ex:
            Logger.error(__name__, "update_last_login", "02", "Error while updating admin last login date", traceback.format_exc())
            raise ex
