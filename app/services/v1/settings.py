# settings.py

import datetime
import traceback

from app.config import config
from app.errors.errors import NotFoundError
from app.libs.logger import Logger
from app.models.settings import Settings


class SettingsService:
    """
    Class contains functions and attributes for settings service
    """

    @staticmethod
    def add_settings(data):
        try:
            settings_data = Settings()
            settings_data.pre_approval_expiry_hours = data['pre_approval_expiry_hours']
            settings_data.approval_expiry_hours = data['approval_expiry_hours']
            settings_data.approval_reminder_interval = data['approval_reminder_interval']
            settings_data.approval_reminder_frequency = data['approval_reminder_frequency']

            settings_data.save()

            settings = settings_data.to_dict()
            Logger.info(__name__, "add_settings", "00", "Settings added successfully!", settings)
        except KeyError as kex:
            Logger.error(__name__, "add_settings", "02", "KeyError: {}".format(str(kex)), traceback.format_exc())
            raise kex
        except Exception as ex:
            Logger.error(__name__, "add_settings", "02", "Exception occurred: {}".format(str(ex)), traceback.format_exc())
            raise ex

        return settings

    @staticmethod
    def get_by_id(uid, minimal=False):

        try:
            settings_data = Settings.objects(id=uid).first()
            if settings_data is not None:
                settings_data = settings_data.to_dict(minimal=minimal)
        except Exception as ex:
            settings_data = None
            Logger.error(__name__, "get_by_id", "02", "Exception occurred: {}".format(ex), traceback.format_exc())

        return settings_data

    @staticmethod
    def find_one(minimal=False):
        settings_list, nav = SettingsService.find_settings(page=1, size=1, minimal=minimal)
        if not settings_list:
            return None
        return settings_list[0]

    @staticmethod
    def update_settings(uid, update_data):
        try:
            settings_data = Settings.objects(id=uid).first()
            if settings_data is None:
                Logger.warn(__name__, "update_settings", "01", "Settings [{}] not found".format(uid))
                raise NotFoundError('Settings not found')

            if 'pre_approval_expiry_hours' in update_data:
                settings_data.pre_approval_expiry_hours = update_data['pre_approval_expiry_hours']
            if 'approval_expiry_hours' in update_data:
                settings_data.approval_expiry_hours = update_data['approval_expiry_hours']
            if 'approval_reminder_interval' in update_data:
                settings_data.approval_reminder_interval = update_data['approval_reminder_interval']
            if 'approval_reminder_frequency' in update_data:
                settings_data.approval_reminder_frequency = update_data['approval_reminder_frequency']

            settings_data.modified_at = datetime.datetime.utcnow()  # TODO: Auto-set modified_at on update(with on_update)
            settings_data.save()
            settings = settings_data.to_dict()
        except KeyError as kex:
            Logger.error(__name__, "update_settings", "02", "KeyError: {}".format(str(kex)), traceback.format_exc())
            raise kex
        except Exception as ex:
            Logger.error(__name__, "update_settings", "02", "Exception occurred: {}".format(str(ex)), traceback.format_exc())
            raise ex

        return settings

    @staticmethod
    def find_settings(order_by='-created_at', paginate=True, minimal=True, **filter_parameters):
        try:
            query = {}
            for field, value in filter_parameters.items():
                if field.split('__')[0] in Settings._fields and value != '':
                    query[field] = value

            if 'size' not in filter_parameters:
                filter_parameters['size'] = config.DEFAULT_LIMIT
            if 'page' not in filter_parameters:
                filter_parameters['page'] = config.DEFAULT_PAGE

            # Remove start_date and end_date from query, if empty
            if 'start_date' in filter_parameters and not filter_parameters.get('start_date'):
                del filter_parameters['start_date']
            if 'end_date' in filter_parameters and not filter_parameters.get('end_date'):
                del filter_parameters['end_date']

            Logger.debug(__name__, "find_settings", "00", "Filter query: %s" % str(query))

            if 'start_date' in filter_parameters and 'end_date' not in filter_parameters:
                settings_data = Settings.objects(
                    created_at__gte=datetime.datetime.strptime(filter_parameters['start_date'], '%Y-%m-%d')) \
                    .filter(**query).order_by(order_by)
            elif 'start_date'not in filter_parameters and 'end_date' in filter_parameters:
                settings_data = Settings.objects(
                    created_at__lt=datetime.datetime.strptime(filter_parameters['end_date'], "%Y-%m-%d") + datetime.timedelta(days=1)
                ).filter(**query).order_by(order_by)
            elif 'start_date' in filter_parameters and 'end_date' in filter_parameters:
                settings_data = Settings.objects(
                    created_at__gte=datetime.datetime.strptime(filter_parameters['start_date'], '%Y-%m-%d'),
                    created_at__lt=datetime.datetime.strptime(filter_parameters['end_date'], '%Y-%m-%d') + datetime.timedelta(days=1)
                ).filter(**query).order_by(order_by)
            else:
                settings_data = Settings.objects.filter(**query).order_by(order_by)

            # Paginate, if pagination requested
            settings_list = []
            nav = None
            if paginate:
                settings_data = settings_data.paginate(int(filter_parameters['page']), int(filter_parameters['size']))
                nav = {
                    'current_page': int(filter_parameters['page']),
                    'next_page': settings_data.next_num,
                    'prev_page': settings_data.prev_num,
                    'total_pages': settings_data.pages,
                    'total_records': settings_data.total,
                    'size': int(filter_parameters['size'])
                }

                for settings in settings_data.items:
                    settings_list.append(settings.to_dict(minimal=minimal))
            else:
                for settings in settings_data:
                    settings_list.append(settings.to_dict(minimal=minimal))

            return settings_list, nav
        except Exception as ex:
            Logger.error(__name__, "find_settings", "02", "Error while finding settingses", traceback.format_exc())
            raise ex
