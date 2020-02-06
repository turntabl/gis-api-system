import googlemaps
from app.config import config
import traceback
import json
import psycopg2
import psycopg2.extras

class IzoneModel:
    @staticmethod
    def connectiondb():
        try:
            conn = psycopg2.connect(database=config.DB_NAME, user=config.DB_USERNAME, password=config.DB_PASSWORD, host=config.DB_HOST, port=config.DB_PORT)
            return conn
        except Exception as e :
            print("Error connecting to db | ",e)
            conn.close()
    
    @staticmethod
    def get_nearest_store(address):
        # Find the distance within 5 km of point-of-interest
        response = {}
        finalList = []
        try:
            
            resp = IzoneModel.get_address_coordinates(address)
            print("Respond in get_nearest_store | {}".format(json.dumps(len(resp), indent=4, sort_keys=True)))
            if len(resp) != 0:
                km = 5000
                db_conn = IzoneModel.connectiondb()
                longitude = "{}".format(resp.get("lng"))
                latitude = "{}".format(resp.get("lat"))
                poi = (float(longitude),float(latitude))
                curs = db_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                curs.execute("""\
                SELECT label,contact,gpsname,landmark, ST_X(location::geometry) as longitude, ST_Y(location::geometry) as latitude
                FROM izone, (SELECT ST_MakePoint(%s, %s)::geography AS poi) AS f
                WHERE ST_DWithin(location, poi, {0});""".format(km), poi)
                
                for row in curs.fetchall():
                    finalList.append(dict(row))
                
                print("Printing nearby stores for | {0} | {1}".format(address,json.dumps(finalList, indent=4, sort_keys=True)))
                
                response = {
                    "code": "00",
                    "msg":"Data retrieved successfully",
                    "data":finalList
                }
            else:
                response = {
                    "code": "01",
                    "msg":"Could not get nearby stores for {}".format(address)
                }
            
        except Exception as e :
            print("Something went wrong | ",e)
        
        return response

    @staticmethod
    def get_address_coordinates(address):
        coords = {}
        try:
            print("Printing address in get_address_coordinates | {}".format(address))
            gmaps = googlemaps.Client(key=config.GOOGLE_API_KEY)
            geocode_result = gmaps.geocode(address + '(Ghana)')
            print("Respond from geocode server | {}".format(json.dumps(geocode_result, indent=4, sort_keys=True)))
            if len(geocode_result) != 0:
                coords = geocode_result[0]['geometry']['location']
        except Exception as e :
            print("Something went wrong | ",e)
            
        return coords
