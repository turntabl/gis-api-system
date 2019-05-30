# application.py

import datetime
import traceback

from app.config import config
from app.errors.errors import NotFoundError
from app.libs.logger import Logger
from app.models.application import Application


class ApplicationService:
    """
    Class contains functions and attributes for application service
    """

    @staticmethod
    def add_application(data):
        try:
            application_data = Application()
            application_data.name = data['name'].strip()
            application_data.api_key = data['api_key'].strip()
            application_data.allowed_ips = data.get('allowed_ips') or []
            application_data.functions = data.get('functions') or []

            application_data.save()

            application = application_data.to_dict()
            Logger.info(__name__, "add_application", "00", "Application added successfully!", application)
        except KeyError as kex:
            Logger.error(__name__, "add_application", "02", "KeyError: {}".format(str(kex)), traceback.format_exc())
            raise kex
        except Exception as ex:
            Logger.error(__name__, "add_application", "02", "Exception occurred: {}".format(str(ex)), traceback.format_exc())
            raise ex

        return application

    @staticmethod
    def get_by_id(uid, minimal=False):

        try:
            application_data = Application.objects(id=uid).first()
            if application_data is not None:
                application_data = application_data.to_dict(minimal=minimal)
        except Exception as ex:
            application_data = None
            Logger.error(__name__, "get_by_id", "02", "Exception occurred: {}".format(ex), traceback.format_exc())

        return application_data

    @staticmethod
    def find_by_api_key(api_key, minimal=False):

        try:
            application_data = Application.objects(api_key=api_key.strip()).first()
            if application_data is not None:
                application_data = application_data.to_dict(minimal=minimal)
        except Exception as ex:
            application_data = None
            Logger.error(__name__, "find_by_api_key", "02", "Exception occurred: {}".format(ex), traceback.format_exc())

        return application_data

    @staticmethod
    def update_application(uid, update_data):
        try:
            application_data = Application.objects(id=uid).first()
            if application_data is None:
                Logger.warn(__name__, "update_application", "01", "Application [{}] not found".format(uid))
                raise NotFoundError('Application not found')

            if 'name' in update_data:
                application_data.name = update_data['name'].strip()
            if 'api_key' in update_data:
                application_data.api_key = update_data['api_key'].strip()
            if 'allowed_ips' in update_data:
                application_data.allowed_ips = update_data['allowed_ips']
            if 'functions' in update_data:
                application_data.functions = update_data['functions']
            if 'active' in update_data:
                application_data.active = update_data['active']

            application_data.modified_at = datetime.datetime.utcnow()  # TODO: Auto-set modified_at on update(with on_update)
            application_data.save()
            application = application_data.to_dict()
        except KeyError as kex:
            Logger.error(__name__, "update_application", "02", "KeyError: {}".format(str(kex)), traceback.format_exc())
            raise kex
        except Exception as ex:
            Logger.error(__name__, "update_application", "02", "Exception occurred: {}".format(str(ex)), traceback.format_exc())
            raise ex

        return application

    @staticmethod
    def find_applications(order_by='-created_at', paginate=True, minimal=True, **filter_parameters):
        try:
            query = {}
            for field, value in filter_parameters.items():
                if field.split('__')[0] in Application._fields:
                    query[field] = value

            if 'size' not in filter_parameters:
                filter_parameters['size'] = config.DEFAULT_LIMIT
            if 'page' not in filter_parameters:
                filter_parameters['page'] = config.DEFAULT_PAGE

            Logger.debug(__name__, "find_applications", "00", "Filter query: %s" % str(query))

            if 'start_date' in filter_parameters and 'end_date' not in filter_parameters:
                application_data = Application.objects(
                    created_at__gte=datetime.datetime.strptime(filter_parameters['start_date'], '%Y-%m-%d')) \
                    .filter(**query).order_by(order_by)
            elif 'start_date'not in filter_parameters and 'end_date' in filter_parameters:
                application_data = Application.objects(
                    created_at__lt=datetime.datetime.strptime(filter_parameters['end_date'], "%Y-%m-%d") + datetime.timedelta(days=1)
                ).filter(**query).order_by(order_by)
            elif 'start_date' in filter_parameters and 'end_date' in filter_parameters:
                application_data = Application.objects(
                    created_at__gte=datetime.datetime.strptime(filter_parameters['start_date'], '%Y-%m-%d'),
                    created_at__lt=datetime.datetime.strptime(filter_parameters['end_date'], '%Y-%m-%d') + datetime.timedelta(days=1)
                ).filter(**query).order_by(order_by)
            else:
                application_data = Application.objects.filter(**query).order_by(order_by)

            # Paginate, if pagination requested
            application_list = []
            nav = None
            if paginate:
                application_data = application_data.paginate(int(filter_parameters['page']), int(filter_parameters['size']))
                nav = {
                    'current_page': int(filter_parameters['page']),
                    'next_page': application_data.next_num,
                    'prev_page': application_data.prev_num,
                    'total_pages': application_data.pages,
                    'total_records': application_data.total,
                    'size': int(filter_parameters['size'])
                }

                for application in application_data.items:
                    application_list.append(application.to_dict(minimal=minimal))
            else:
                for application in application_data:
                    application_list.append(application.to_dict(minimal=minimal))

            return application_list, nav
        except Exception as ex:
            Logger.error(__name__, "find_applications", "02", "Error while finding applications", traceback.format_exc())
            raise ex
