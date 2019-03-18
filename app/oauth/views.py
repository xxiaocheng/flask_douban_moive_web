from flask_restful import Resource
from app.extensions import api

class AuthTokenApi(Resource):
    def get(self):
        return {'hello':'world'}

api.add_resource(AuthTokenApi,'/token/')