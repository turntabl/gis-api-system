# utils.py

import asyncio
import csv
import datetime
import hashlib
import io
import json
import ntpath
import os
import random
import re
import requests
import string

from app.config import config
from app.errors.errors import GenericError
from app.errors.errors import InputError
from app.errors.errors import ServerError
from app.libs.logger import Logger

SYMBOLS = '!#$%&()*+,-:;<=>?@[]^_{|}~'
CHARS = string.ascii_uppercase + SYMBOLS + string.ascii_lowercase + string.digits
CHARS_WITHOUT_SYMBOLS = string.ascii_uppercase + string.ascii_lowercase + string.digits

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_WITH_MICROSECOND_FORMAT = '%Y%m%d%H%M%S%f'
MONGO_DATE_FORMAT = '%Y-%m-%d %H:%M:%S.%f'


class Utils:

    @staticmethod
    def is_valid_email(email):
        import re
        return re.search('^[A-Za-z0-9+_.\-]+@(.+)\.(.+)$', email) is not None

    @staticmethod
    def password_satisfies_policy(password):
        if password is not None:
            if len(password) >= config.MINIMUM_PASSWORD_LENGTH:
                if config.ENFORCE_PASSWORD_POLICY:
                    if re.search(r'\d', password) is not None:
                        if re.search(r'[A-Z]', password) is not None:
                            if re.search(r'[a-z]', password) is not None:
                                if re.search(r'\W', password) is not None:
                                    return
                                raise InputError('Password should contain at least 1 symbol')
                            raise InputError('Password should contain at least 1 lowercase letter')
                        raise InputError('Password should contain at least 1 uppercase letter')
                    raise InputError('Password should contain at least 1 number')
                return
            raise InputError('Password should have at least {} characters'.format(config.MINIMUM_PASSWORD_LENGTH))
        raise InputError('No password')

    @staticmethod
    def generate_password(length=12):
        return ''.join(random.choice(CHARS) for _ in range(length))

    @staticmethod
    def generate_alphanum_password(length=12):
        return ''.join(random.choice(CHARS_WITHOUT_SYMBOLS) for _ in range(length))

    @staticmethod
    def hash_string(s, salt: str=None, algorithm='sha256'):
        if algorithm not in hashlib.algorithms_available:
            raise GenericError('Unknown hashing algorithm')
        h = hashlib.new(algorithm)
        if salt is not None and isinstance(salt, str):
            h.update(salt.encode('utf-8'))
        h.update(s.encode('utf-8'))
        return h.hexdigest()

    @staticmethod
    def hash_password(pwd):
        return Utils.hash_string(pwd, salt=config.SALT)

    @staticmethod
    def generate_session_token(length=16):
        chars = string.ascii_letters + string.digits
        return ''.join((random.choice(chars)) for _ in range(length))

    @staticmethod
    def generate_reset_token():
        return Utils.hash_string(DateUtils.format_full_date(datetime.datetime.utcnow()),
                                 ''.join(random.choice(CHARS_WITHOUT_SYMBOLS) for _ in range(8)),
                                 'md5')

    @staticmethod
    async def send_email(recipients, subject, message, sender_name=None, file_paths=None):
        sender_name = config.EMAIL_SENDER if sender_name is None else sender_name
        # Build multipart data dict
        multipart_dict = {
            'sender_name': (None, sender_name),
            'subject': (None, subject),
            'recipients': (None, ','.join(r for r in recipients) if isinstance(recipients, list) else recipients),
            'message': (None, message.strip()),
            'signature': (None, ''),
            'sender_email': (None, ''),
            'password': (None, '')
        }

        if file_paths and isinstance(file_paths, list):
            filename = Utils.get_filename_from_path(file_paths[0])
            multipart_dict['file'] = (filename, open(file_paths[0], 'rb'))
            for i in range(1, len(file_paths)):
                filename = Utils.get_filename_from_path(file_paths[i])
                multipart_dict['file{}'.format(i)] = (filename, open(file_paths[i], 'rb'))

        # Make request
        # response = requests.post(config.config.EMAIL_API_URL, files=multipart_dict)
        response = await Utils.make_async_multipart_request(config.EMAIL_API_URL, multipart_dict)
        return response and response.status_code == 200 and response.json() and response.json().get('code') == '00'

    @staticmethod
    async def make_async_multipart_request(url, files):
        if url is None:
            raise GenericError('No URL')

        response = requests.post(url, files=files)

        return response

    @staticmethod
    def send_email_confirmation(email, username, otp):
        # Get confirm_email template file
        confirm_email_tmpl_file = os.path.join(config.ROOT_DIR, 'static/confirm_account.html')
        msg_template = Utils.read_file(confirm_email_tmpl_file)
        # If template is empty, raise error
        if msg_template is None:
            Logger.warn(__name__, "send_email_confirmation", "01",
                        "Email confirmation template message could not be obtained")
            raise ServerError('Email confirmation could not be initiated')
        # Render template with actual values for placeholders
        message = StringUtils.render_template(msg_template, username=username, otp=otp, portal_url=config.PORTAL_URL)
        # Send email (async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        email_sent = loop.run_until_complete(Utils.send_email(email, 'Confirm your PayPrompt account', message))
        loop.close()
        if not email_sent:
            raise ServerError('Email confirmation could not be sent')
        Logger.info(__name__, "send_email_confirmation", "00", "Email confirmation email sent to [{}] successfully!".format(email))

    @staticmethod
    def send_password_reset_email(email, pwd_reset_url, subject='PayPrompt Password Reset'):
        # Get password reset template file
        pwd_reset_tmpl_file = os.path.join(config.ROOT_DIR, 'static/reset_password_email.html')
        Logger.debug(__name__, "send_password_reset_email", "00", "PATH: [%s]" % pwd_reset_tmpl_file)
        msg_template = Utils.read_file(pwd_reset_tmpl_file)
        # If template is empty, raise error
        if msg_template is None:
            Logger.warn(__name__, "send_password_reset_email", "01", "Password reset template message could not be obtained")
            raise ServerError('Password reset could not be initiated')
        # Render template with actual values for placeholders
        message = StringUtils.render_template(msg_template, action_url=pwd_reset_url)
        # Send email (async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        email_sent = loop.run_until_complete(Utils.send_email(email, subject, message))
        loop.close()
        if not email_sent:
            raise ServerError('Password reset email could not be sent')
        Logger.info(__name__, "send_password_reset_email", "00", "Password reset email sent to [%s] successfully!" % email)

    @staticmethod
    def get_filename_from_path(filepath):
        head, tail = ntpath.split(filepath)
        return tail or ntpath.basename(head)  # tail will be empty, if path ends with /

    @staticmethod
    def read_file(filepath):
        content = None
        if os.path.isfile(filepath):
            with open(filepath, 'r') as f:
                content = ''.join(line for line in f.readlines())
                f.close()
        return content

    @staticmethod
    def build_url(uri_template, **kwargs):
        full_uri = uri_template
        if uri_template is not None and uri_template.strip() != '':
            for key, value in kwargs.items():
                full_uri = full_uri.replace('<'+key+'>', value)

        return full_uri

    @staticmethod
    def send_sms(recipient, message):
        headers = {'Content-Type': 'application/json', 'X-SMS-Apikey': config.SMS_API_KEY}
        body = {'sender': config.SMS_SENDER, 'recipient': str(recipient), 'message': message}

        try:
            response = requests.post(url=config.SEND_SMS_URL, headers=headers, data=json.dumps(body))
            # response = {'code': '00', 'msg': 'Message queued!', 'data': {'id': 'adasaknlsdknsksad'}}
        except Exception as ex:
            Logger.error(__name__, "send_sms", "02", "Error while sending SMS: %s" % ex, body)
            return False

        if response is not None:
            resp_text = response.text
            try:
                resp_json = json.loads(resp_text)
                # resp_json = response
            except Exception as e:
                Logger.error(__name__, "send_sms", "02", "Error while parsing SMS API response: %s" % e, body)
                return False

            if resp_json.get('code') != '00':
                Logger.warn(__name__, "send_sms", "01", "Sending SMS failed. Response: [%s]" % resp_json, body)
                return False

            return True
        else:
            Logger.warn(__name__, "send_sms", "01", "No response from SMS API", body)
            return False

    @staticmethod
    def write_transaction_data_to_csv(data_list):
        csv_io = io.StringIO()
        headers = ['Account Number', 'Customer Name', 'Balance', 'Institution', 'Bank Status', 'Payment Status', 'Inititated By', 'Approved By', 'Inititated At']
        writer = csv.writer(csv_io, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)
        for data in data_list:
            writer.writerow(
                [data['account_number'], data['customer_name'], data['balance'], data['institution'], data['bank_status'], data['payment_status'],
                 data['initiated_by'], data['approved_by'], data['initiated_at']]
            )

        # Creating the byteIO object from the StringIO Object
        mem = io.BytesIO()
        mem.write(csv_io.getvalue().encode('utf-8'))
        mem.seek(0)
        csv_io.close()
        return mem


class StringUtils:
    @staticmethod
    def render_template(template, **kwargs):
        rendered = template
        if template is not None and template.strip() != '':
            for key, value in kwargs.items():
                rendered = rendered.replace('{{'+key+"}}", value)

        return rendered


class GeneratorUtils:
    @staticmethod
    def generate_string(length=16, symbols=False):
        if symbols:
            return ''.join(random.choice(CHARS) for _ in range(length))
        return ''.join(random.choice(CHARS_WITHOUT_SYMBOLS) for _ in range(length))

    @staticmethod
    def generate_api_key():
        salt = GeneratorUtils.generate_string(length=16)
        return Utils.hash_string(str(DateUtils.get_timestamp()), salt, algorithm='md5')


class DateUtils:
    @staticmethod
    def get_timestamp(date_obj=datetime.datetime.utcnow()):
        return int(date_obj.timestamp() * 1000000)

    @staticmethod
    def set_session_expiry():
        return datetime.datetime.utcnow() + datetime.timedelta(hours=config.SESSION_EXPIRY_HOURS)

    @staticmethod
    def format_full_date(date_obj):
        return datetime.datetime.strftime(date_obj, DATETIME_WITH_MICROSECOND_FORMAT)

    @staticmethod
    def mongo_date_to_object(date_str):
        return datetime.datetime.strptime(date_str, MONGO_DATE_FORMAT)

    @staticmethod
    def format_datetime(date_obj):
        return datetime.datetime.strftime(date_obj, DATETIME_FORMAT)