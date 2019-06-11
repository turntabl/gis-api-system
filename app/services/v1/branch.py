# branch.py

import datetime
import traceback

from app.config import config
from app.errors.errors import NotFoundError
from app.libs.logger import Logger
from app.models.branch import Branch


class BranchService:
    """
    Class contains functions and attributes for branch service
    """

    @staticmethod
    def add_branch(data):
        try:
            branch_data = Branch()
            branch_data.name = data['name'].strip()
            branch_data.branch_id = data['branch_id'].strip().upper()
            branch_data.institution = data['institution']
            branch_data.created_by = data['created_by']

            branch_data.save()

            branch = branch_data.to_dict()
            Logger.info(__name__, "add_branch", "00", "Branch added successfully!", branch)
        except KeyError as kex:
            Logger.error(__name__, "add_branch", "02", "KeyError: {}".format(str(kex)), traceback.format_exc())
            raise kex
        except Exception as ex:
            Logger.error(__name__, "add_branch", "02", "Exception occurred: {}".format(str(ex)), traceback.format_exc())
            raise ex

        return branch

    @staticmethod
    def get_by_id(uid, minimal=False):

        try:
            branch_data = Branch.objects(id=uid).first()
            if branch_data is not None:
                branch_data = branch_data.to_dict(minimal=minimal)
        except Exception as ex:
            branch_data = None
            Logger.error(__name__, "get_by_id", "02", "Exception occurred: {}".format(ex), traceback.format_exc())

        return branch_data

    @staticmethod
    def get_by_branch_id(branch_id, minimal=True):

        try:
            branch_data = Branch.objects(branch_id=branch_id.strip().upper()).first()
            if branch_data is not None:
                branch_data = branch_data.to_dict(minimal=minimal)
        except Exception as ex:
            branch_data = None
            Logger.error(__name__, "get_by_branch_id", "02", "Exception occurred: {}".format(ex), traceback.format_exc())

        return branch_data

    @staticmethod
    def get_institution_branch(institution_id, branch_id, minimal=True):

        try:
            branch_data = Branch.objects(institution=institution_id, branch_id=branch_id.strip().upper()).first()
            if branch_data is not None:
                branch_data = branch_data.to_dict(minimal=minimal)
        except Exception as ex:
            branch_data = None
            Logger.error(__name__, "get_institution_branch", "02", "Exception occurred: {}".format(ex), traceback.format_exc())

        return branch_data

    @staticmethod
    def update_branch(uid, update_data):
        try:
            branch_data = Branch.objects(id=uid).first()
            if branch_data is None:
                Logger.warn(__name__, "update_branch", "01", "Branch [{}] not found".format(uid))
                raise NotFoundError('Branch not found')

            if 'name' in update_data:
                branch_data.name = update_data['name'].strip()
            if 'status' in update_data:
                branch_data.status = update_data['status'].strip()

            branch_data.modified_at = datetime.datetime.utcnow()  # TODO: Auto-set modified_at on update(with on_update)
            branch_data.save()
            branch = branch_data.to_dict()
        except KeyError as kex:
            Logger.error(__name__, "update_branch", "02", "KeyError: {}".format(str(kex)), traceback.format_exc())
            raise kex
        except Exception as ex:
            Logger.error(__name__, "update_branch", "02", "Exception occurred: {}".format(str(ex)), traceback.format_exc())
            raise ex

        return branch

    @staticmethod
    def find_branches(order_by='-created_at', paginate=True, minimal=True, **filter_parameters):
        try:
            query = {}
            for field, value in filter_parameters.items():
                if field.split('__')[0] in Branch._fields and value != '':
                    if field == 'branch_id':
                        value = value.upper()
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

            Logger.debug(__name__, "find_branches", "00", "Filter query: %s" % str(query))

            if 'start_date' in filter_parameters and 'end_date' not in filter_parameters:
                branch_data = Branch.objects(
                    created_at__gte=datetime.datetime.strptime(filter_parameters['start_date'], '%Y-%m-%d')) \
                    .filter(**query).order_by(order_by)
            elif 'start_date'not in filter_parameters and 'end_date' in filter_parameters:
                branch_data = Branch.objects(
                    created_at__lt=datetime.datetime.strptime(filter_parameters['end_date'], "%Y-%m-%d") + datetime.timedelta(days=1)
                ).filter(**query).order_by(order_by)
            elif 'start_date' in filter_parameters and 'end_date' in filter_parameters:
                branch_data = Branch.objects(
                    created_at__gte=datetime.datetime.strptime(filter_parameters['start_date'], '%Y-%m-%d'),
                    created_at__lt=datetime.datetime.strptime(filter_parameters['end_date'], '%Y-%m-%d') + datetime.timedelta(days=1)
                ).filter(**query).order_by(order_by)
            else:
                branch_data = Branch.objects.filter(**query).order_by(order_by)

            # Paginate, if pagination requested
            branch_list = []
            nav = None
            if paginate:
                branch_data = branch_data.paginate(int(filter_parameters['page']), int(filter_parameters['size']))
                nav = {
                    'current_page': int(filter_parameters['page']),
                    'next_page': branch_data.next_num,
                    'prev_page': branch_data.prev_num,
                    'total_pages': branch_data.pages,
                    'total_records': branch_data.total,
                    'size': int(filter_parameters['size'])
                }

                for branch in branch_data.items:
                    branch_list.append(branch.to_dict(minimal=minimal))
            else:
                for branch in branch_data:
                    branch_list.append(branch.to_dict(minimal=minimal))

            return branch_list, nav
        except Exception as ex:
            Logger.error(__name__, "find_branches", "02", "Error while finding branches", traceback.format_exc())
            raise ex
