# user_token.py

import datetime
import traceback

from mongoengine.errors import NotUniqueError
from pymongo.errors import DuplicateKeyError

from app.errors.errors import AlreadyExistsError
from app.errors.errors import InputError
from app.errors.errors import NotFoundError
from app.libs.logger import Logger
from app.models.user_token import UserToken
from app.models.user_token import Status


class UserTokenService:

    @staticmethod
    def insert(username, token, token_type):
        user_token = None

        try:
            user_token_data = UserToken()
            user_token_data.username = username
            user_token_data.token = token
            user_token_data.type = token_type

            user_token_data.save()

            user_token = user_token_data.to_dict()
            Logger.info(__name__, "insert", "00", "User token added successfully!")
        except KeyError as kex:
            Logger.error(__name__, "insert", "02", "KeyError: {}".format(str(kex)), traceback.format_exc())
        except (DuplicateKeyError, NotUniqueError) as dx:
            Logger.error(__name__, "insert", "02", "Duplicate error occurred: {}".format(str(dx)), traceback.format_exc())
            raise AlreadyExistsError('Token already exists')
        except Exception as ex:
            Logger.error(__name__, "insert", "02", "Exception occurred: {}".format(str(ex)), traceback.format_exc())

        return user_token

    @staticmethod
    def update_token_status(uid, status):
        try:
            user_token_data = UserToken.objects(id=uid).first()
            if user_token_data is None:
                raise NotFoundError('Email token not found')

            # Validate new token status
            status = status.upper()
            if status not in Status.values():
                raise InputError('Invalid status: %s' % status)

            user_token_data.update(status=status, modified_at=datetime.datetime.utcnow())  # FIXME: Get updated document on update (with modified_at)
            return user_token_data.to_dict()
        except Exception as ex:
            Logger.error(__name__, "update_token_status", "02", "Error while updating user token", traceback.format_exc())
            raise ex

    @staticmethod
    def find(**kwargs):
        query = {}
        for field, value in kwargs.items():
            if field.split('__')[0] in UserToken._fields:
                query[field] = value

        if not query:
            raise InputError('No filters found')

        user_token_data = UserToken.objects().filter(**query)

        user_token_list = []
        for token in user_token_data:
            user_token_list.append(token.to_dict())

        return user_token_list
