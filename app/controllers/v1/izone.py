# administrator.py

import json
import traceback

from flask import request
from flask import jsonify

from app.controllers import api
from app.controllers import api_call
from app.controllers import api_request
from app.services.v1.izone import IzoneService

@api.route('/v1/nearest/store/<address>', methods=['GET'])
def get_store_by_address(address):
    resp = IzoneService.get_nearest_store(address)
    print("Response Server | ", resp)
    return jsonify(resp)







