# http.py

import json

import requests


def make_request(url, method, params=None, headers=None, data=None, json_=None, verify=False):
    if url is None:
        raise Exception('No URL')
    elif method is None:
        raise Exception('No request method')
    elif method.lower() not in ('post', 'get', 'put', 'delete', 'head', 'patch'):
        raise Exception('Invalid request method: {}'.format(method.upper()))

    data_ = data
    if data is not None and isinstance(data, dict) \
            and headers is not None and 'content-type' in headers and 'application/json' in headers.get('content-type'):
        data_ = json.dumps(data)

    if headers is None:
        headers = {}

    if json is None:
        response = requests.request(method, url, params=params, headers=headers, data=data_, verify=verify)
    else:
        response = requests.request(method, url, params=params, headers=headers, json=json_, verify=verify)

    return response