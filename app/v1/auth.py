from flask import Blueprint,g,jsonify
from flask_restful import Resource, abort, reqparse
from flask_httpauth import HTTPTokenAuth

from app.extensions import api
from app.models import User
from functools import wraps

auth_bp = Blueprint('auth', __name__)

auth=HTTPTokenAuth(scheme='Bearer')

class AuthTokenAPI(Resource):
    
    def post(self):
        """返回 token
        """
        parser = reqparse.RequestParser()
        parser.add_argument('grant_type', location='form')
        parser.add_argument('username', location='form')
        parser.add_argument('password', location='form')
        args = parser.parse_args()

        if args['grant_type'] is None or args['grant_type'].lower() != 'password':
            return abort(http_status_code=400, message='The grant type must be password.')

        user = User.objects(username=args['username']).first()
        if user is None or not user.validate_password(args['password']):
            return abort(http_status_code=400, message='Either the username or password was invalid.')

        expiration = 3600
        token = user.generate_token(expiration=expiration)

        return{
            'access_token': token,
            'token_type': 'bearer',
            'expires_in': expiration
        }, 201, {
            'Cache-Control': 'no-store',
            'Pragma': 'no-cache'
        }

api.add_resource(AuthTokenAPI, '/oauth/token')

@auth.verify_token
def verify_token(token):
    if User.verify_auth_token(token):
        return True
    return False

def permission_required(permission_name):
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            if not g.current_user.check_permission(permission_name):
                response=jsonify(message='%s Permission Required'%permission_name)
                response.status_code=403
                return response
            return func(*args, **kwargs)
        return decorated_function
    return decorator

def email_confirm_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not g.current_user.confirmed_email:
            response=jsonify(message='Email Confirm Required.')
            response.status_code=403
            return response
        return func(*args, **kwargs)
    return decorated_function

#上面的三个装饰器示例
# class TestToken(Resource):

#     @auth.login_required
#     @permission_required('UPLOAD')
#     @email_confirm_required
#     def post(self):
#         return 'hello !'

# api.add_resource(TestToken,'/test')



