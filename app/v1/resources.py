from flask import Blueprint
from flask_restful import Resource,abort,reqparse
from app.models import User
from app.extensions import api

api_bp=Blueprint('api',__name__)

class Users(Resource):
    
    def post(self):
        """ 注册新用户
        """
        parser = reqparse.RequestParser()
        parser.add_argument('username', location='form')
        parser.add_argument('email', location='form')
        parser.add_argument('password', location='form')
        args = parser.parse_args()

        if User.create_user(username=args['username'],email=args['email'],password=args['password']):
            return{
                'message':'Registered User Succeed.'
            }
        else:
            abort(403,message='Registered User Failed.')

api.add_resource(Users, '/users')
