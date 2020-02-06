# izone.py
import traceback
import json
from app.models.izone import IzoneModel

class IzoneService:

    @staticmethod
    def get_nearest_store(address):
        response = IzoneModel.get_nearest_store(address)
        return response

    

    