# fusion.py

from app.config import config
from app.errors.errors import InputError
from app.libs import http
from app.libs.logger import Logger


class Fusion:

    @staticmethod
    def add_fs_institution(request_data):
        Logger.debug(__name__, "add_fs_institution", "00", "Adding institution on Fusion")
        if request_data['inst_type'] == 'institution':
            return Fusion.__add_institution(request_data)
        elif request_data['inst_type'] == 'merchant':
            return Fusion.__add_institution(request_data)
        elif request_data['inst_type'] == 'thirdparty':
            return Fusion.__add_institution(request_data)
        elif request_data['inst_type'] == 'wallet':
            return Fusion.__add_institution(request_data)
        else:
            raise InputError('Invalid institution type')

    @staticmethod
    def __add_institution(request_data):
        req_data = {
            "profileName": request_data['name'],
            "profileShrtName": request_data['short_name'],
            "cntryID": request_data['country'],
            "contactName": '%s %s' % (request_data['first_name'], request_data['last_name']),
            "phoneNum": request_data['contact_phone'],
            "supprtMail": request_data['contact_email'],
            "show": True
        }

        if request_data['extras'].get('fusion') is not None:
            req_data['ip'] = request_data['extras']['fusion'].get('ip') or '0.0.0.0'
            req_data['type'] = request_data['extras']['fusion'].get('type') or 'BK'

        # headers = {'auth-key': config.FUSION_PORTAL_AUTH_KEY, 'Content-type': 'application/x-www-form-urlencoded'}
        headers = {'auth-key': config.FUSION_PORTAL_AUTH_KEY}
        url = config.PRODUCTS_APIS['FUSION']['INST']
        print('FUSION INSTITUTION URL: %s <<>> DATA: %s' % (url, req_data))
        response = http.make_request(url, method='post', json_=req_data, headers=headers)
        if response is not None:
            Logger.debug(__name__, "__add_institution", "00", "Fusion RESP: %s" % response.text)
            resp_json = response.json()
            if resp_json['code'] == '00':
                return resp_json['msg']

        return None

    @staticmethod
    def __add_merchant(request_data):
        req_data = {
            "profileName": request_data['name'],
            "profileShrtName": request_data['short_name'],
            "cntryID": request_data['country'],
            "contactName": '%s %s' % (request_data['first_name'], request_data['last_name']),
            "phoneNum": request_data['contact_phone'],
            "supprtMail": request_data['contact_email']
        }

        if request_data['extras'].get('fusion') is not None:
            req_data['ip'] = request_data['extras']['fusion'].get('ip') or '0.0.0.0'

        # headers = {'auth-key': config.FUSION_PORTAL_AUTH_KEY, 'Content-type': 'application/x-www-form-urlencoded'}
        headers = {'auth-key': config.FUSION_PORTAL_AUTH_KEY}
        url = config.PRODUCTS_APIS['FUSION']['MERCHANT']
        response = http.make_request(url, method='post', data=req_data, headers=headers)
        if response is not None:
            resp_json = response.json()
            Logger.debug(__name__, "__add_merchant", "00", "Fusion RESP: %s" % resp_json)
            if resp_json['code'] == '00':
                return resp_json['msg']

        return None

    @staticmethod
    def __add_third_party(request_data):
        req_data = {
            "profileName": request_data['name'],
            "profileShrtName": request_data['short_name'],
            "cntryID": request_data['country'],
            "contactName": '%s %s' % (request_data['first_name'], request_data['last_name']),
            "phoneNum": request_data['contact_phone'],
            "supprtMail": request_data['contact_email']
        }

        if request_data['extras'].get('fusion') is not None:
            req_data['ip'] = request_data['extras']['fusion'].get('ip') or '0.0.0.0'
            req_data['catType'] = request_data['extras']['fusion'].get('catType') or 'BK'
            req_data['catName'] = request_data['extras']['fusion'].get('catName') or 'institution'

        # headers = {'auth-key': config.FUSION_PORTAL_AUTH_KEY, 'Content-type': 'application/x-www-form-urlencoded'}
        headers = {'auth-key': config.FUSION_PORTAL_AUTH_KEY}
        url = config.PRODUCTS_APIS['FUSION']['THIRD_PARTY']
        response = http.make_request(url, method='post', data=req_data, headers=headers)
        if response is not None:
            resp_json = response.json()
            Logger.debug(__name__, "__add_third_party", "00", "Fusion RESP: %s" % resp_json)
            if resp_json['code'] == '00':
                return resp_json['msg']

        return None

    @staticmethod
    def __add_wallet(request_data):
        req_data = {
            "profileName": request_data['name'],
            "profileShrtName": request_data['short_name'],
            "cntryID": request_data['country'],
            "contactName": '%s %s' % (request_data['first_name'], request_data['last_name']),
            "phoneNum": request_data['contact_phone'],
            "supprtMail": request_data['contact_email'],
            "inst_type": request_data['inst_type']
        }

        if request_data['extras'].get('fusion') is not None:
            req_data['ip'] = request_data['extras']['fusion'].get('ip') or '0.0.0.0'
            req_data['ip'] = request_data['extras']['fusion'].get('institutionType') or 'BK'

        # headers = {'auth-key': config.FUSION_PORTAL_AUTH_KEY, 'Content-type': 'application/x-www-form-urlencoded'}
        headers = {'auth-key': config.FUSION_PORTAL_AUTH_KEY}
        url = config.PRODUCTS_APIS['FUSION']['WALLET']
        response = http.make_request(url, method='post', data=req_data, headers=headers)
        if response is not None:
            resp_json = response.json()
            Logger.debug(__name__, "__add_wallet", "00", "Fusion RESP: %s" % resp_json)
            if resp_json['code'] == '00':
                return resp_json['msg']

        return None