from flask_restful import Resource
from app.extensions import api
from flask import Blueprint

api_bp=Blueprint('api',__name__)

class AuthTokenAPI(Resource):
    def get(self,id):
        return{'say':'hi'+str(id)}

api.add_resource(AuthTokenAPI,'/token/<int:id>')
