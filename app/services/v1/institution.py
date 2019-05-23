# institution.py

import datetime
import traceback

from app.config import config
from app.errors.errors import NotFoundError
from app.libs.logger import Logger
from app.models.institution import Institution


class InstitutionService:
    """
    Class contains functions and attributes for institution service
    """

    @staticmethod
    def add_institution(data):
        try:
            institution_data = Institution()
            institution_data.name = data['name'].strip()
            institution_data.country = data['country'].strip().upper()
            institution_data.short_name = data['short_name'].strip().upper()
            institution_data.description = data.get('description') or ''
            institution_data.contact_email = data.get('contact_email')
            institution_data.phone_numbers = data.get('phone_numbers') or []

            institution_data.save()

            institution = institution_data.to_dict()
            Logger.info(__name__, "add_institution", "00", "Institution added successfully!", institution)
        except KeyError as kex:
            Logger.error(__name__, "add_institution", "02", "KeyError: {}".format(str(kex)), traceback.format_exc())
            raise kex
        except Exception as ex:
            Logger.error(__name__, "add_institution", "02", "Exception occurred: {}".format(str(ex)), traceback.format_exc())
            raise ex

        return institution

    @staticmethod
    def get_by_id(uid, minimal=False):

        try:
            institution_data = Institution.objects(id=uid).first()
            if institution_data is not None:
                institution_data = institution_data.to_dict(minimal=minimal)
        except Exception as ex:
            institution_data = None
            Logger.error(__name__, "get_by_id", "02", "Exception occurred: {}".format(ex), traceback.format_exc())

        return institution_data

    @staticmethod
    def get_by_short_name(short_name, minimal=True):

        try:
            institution_data = Institution.objects(short_name=short_name.strip().upper()).first()
            if institution_data is not None:
                institution_data = institution_data.to_dict(minimal=minimal)
        except Exception as ex:
            institution_data = None
            Logger.error(__name__, "get_by_short_name", "02", "Exception occurred: {}".format(ex), traceback.format_exc())

        return institution_data

    @staticmethod
    def update_institution(uid, update_data):
        try:
            institution_data = Institution.objects(id=uid).first()
            if institution_data is None:
                Logger.warn(__name__, "update_institution", "01", "Institution [{}] not found".format(uid))
                raise NotFoundError('Institution not found')

            if 'name' in update_data:
                institution_data.name = update_data['name'].strip()
            if 'contact_email' in update_data:
                institution_data.contact_email = update_data['contact_email'].strip()
            if 'phone_numbers' in update_data:
                institution_data.phone_numbers = update_data['phone_numbers']
            if 'description' in update_data:
                institution_data.description = update_data['description'].strip()
            if 'status' in update_data:
                institution_data.status = update_data['status'].strip()

            institution_data.modified_at = datetime.datetime.utcnow()  # TODO: Auto-set updated_at on update(with on_update)
            institution_data.save()
            institution = institution_data.to_dict()
        except KeyError as kex:
            Logger.error(__name__, "update_institution", "02", "KeyError: {}".format(str(kex)), traceback.format_exc())
            raise kex
        except Exception as ex:
            Logger.error(__name__, "update_institution", "02", "Exception occurred: {}".format(str(ex)), traceback.format_exc())
            raise ex

        return institution

    @staticmethod
    def get_institution_ids(**filter_parameters):
        try:
            query = {}
            for field, value in filter_parameters.items():
                if field.split('__')[0] in Institution._fields:
                    query[field] = value

            if 'start_date' in filter_parameters and 'end_date' not in filter_parameters:
                institution_data = Institution.objects(
                    created_at__gte=datetime.datetime.strptime(filter_parameters['start_date'], '%Y-%m-%d')) \
                    .filter(**query)
            elif 'start_date'not in filter_parameters and 'end_date' in filter_parameters:
                institution_data = Institution.objects(
                    created_at__lt=datetime.datetime.strptime(filter_parameters['end_date'], "%Y-%m-%d") + datetime.timedelta(days=1)
                ).filter(**query)
            elif 'start_date' in filter_parameters and 'end_date' in filter_parameters:
                institution_data = Institution.objects(
                    created_at__gte=datetime.datetime.strptime(filter_parameters['start_date'], '%Y-%m-%d'),
                    created_at__lt=datetime.datetime.strptime(filter_parameters['end_date'], '%Y-%m-%d') + datetime.timedelta(days=1)
                ).filter(**query)
            else:
                institution_data = Institution.objects.filter(**query)

            institution_list = []
            for institution in institution_data:
                institution_list.append(str(institution.id))

            return institution_list
        except Exception as ex:
            Logger.error(__name__, "get_institution_ids", "02", "Error while finding institutions", traceback.format_exc())
            raise ex

    @staticmethod
    def find_institutions(order_by='-created_at', paginate=True, minimal=True, **filter_parameters):
        try:
            query = {}
            for field, value in filter_parameters.items():
                if field.split('__')[0] in Institution._fields:
                    query[field] = value

            if 'size' not in filter_parameters:
                filter_parameters['size'] = config.DEFAULT_LIMIT
            if 'page' not in filter_parameters:
                filter_parameters['page'] = config.DEFAULT_PAGE

            Logger.debug(__name__, "find_institutions", "00", "Filter query: %s" % str(query))

            if 'start_date' in filter_parameters and 'end_date' not in filter_parameters:
                institution_data = Institution.objects(
                    created_at__gte=datetime.datetime.strptime(filter_parameters['start_date'], '%Y-%m-%d')) \
                    .filter(**query).order_by(order_by)
            elif 'start_date'not in filter_parameters and 'end_date' in filter_parameters:
                institution_data = Institution.objects(
                    created_at__lt=datetime.datetime.strptime(filter_parameters['end_date'], "%Y-%m-%d") + datetime.timedelta(days=1)
                ).filter(**query).order_by(order_by)
            elif 'start_date' in filter_parameters and 'end_date' in filter_parameters:
                institution_data = Institution.objects(
                    created_at__gte=datetime.datetime.strptime(filter_parameters['start_date'], '%Y-%m-%d'),
                    created_at__lt=datetime.datetime.strptime(filter_parameters['end_date'], '%Y-%m-%d') + datetime.timedelta(days=1)
                ).filter(**query).order_by(order_by)
            else:
                institution_data = Institution.objects.filter(**query).order_by(order_by)

            # Paginate, if pagination requested
            institution_list = []
            nav = None
            if paginate:
                institution_data = institution_data.paginate(int(filter_parameters['page']), int(filter_parameters['size']))
                nav = {
                    'current_page': int(filter_parameters['page']),
                    'next_page': institution_data.next_num,
                    'prev_page': institution_data.prev_num,
                    'total_pages': institution_data.pages,
                    'total_records': institution_data.total,
                    'size': int(filter_parameters['size'])
                }

                for institution in institution_data.items:
                    institution_list.append(institution.to_dict(minimal=minimal))
            else:
                for institution in institution_data:
                    institution_list.append(institution.to_dict(minimal=minimal))

            return institution_list, nav
        except Exception as ex:
            Logger.error(__name__, "find_institutions", "02", "Error while finding institutions", traceback.format_exc())
            raise ex
