import re
from functools import wraps

from flask import current_app, g, jsonify
from flask_httpauth import HTTPTokenAuth
from flask_restful import Resource, abort, reqparse

from app.extensions import api
from app.helpers.utils import validate_email_confirm_token
from app.models import User
from app.settings import Operations
from app.helpers.redis_utils import resent_confirm_email

auth = HTTPTokenAuth(scheme='Bearer')


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

        if user.is_locked():
            return{
                "message": "user is locked"
            }, 403
        if user.is_deleted:
            return{
                "message": "user not found"
            }, 404
        if not user.confirmed_email:
            return{
                'message': 'email not confirmed,please check you email.'
            }, 403,
        expiration = current_app.config['EXPIRATION']
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
                response = jsonify(
                    message='%s Permission Required' % permission_name)
                response.status_code = 403
                return response
            return func(*args, **kwargs)
        return decorated_function
    return decorator


def email_confirm_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not g.current_user.confirmed_email:
            response = jsonify(message='Email Confirm Required.')
            response.status_code = 403
            return response
        return func(*args, **kwargs)
    return decorated_function

# 上面的三个装饰器示例
# class TestToken(Resource):

#     @auth.login_required
#     @permission_required('UPLOAD')
#     @email_confirm_required
#     def post(self):
#         return 'hello !'

# api.add_resource(TestToken,'/test')


class account(Resource):

    def post(self, type_name):
        parser = reqparse.RequestParser()
        parser.add_argument('token', required=True, location='form')

        if type_name == Operations.CONFIRM:
            args = parser.parse_args()
            flag = validate_email_confirm_token(
                token=args['token'], operation=Operations.CONFIRM)
            if flag:
                return{
                    'message': 'email had confirmed'
                }
            else:
                return{
                    'message': 'error'
                },
        elif type_name == Operations.RESET_PASSWORD:
            parser.add_argument('newpassword', required=True, location='form')
            parser.add_argument('newpassword2', required=True, location='form')
            args = parser.parse_args()
            if args['newpassword'] != args['newpassword2']:
                return{
                    'message': 'two password not equal'
                }, 403

            password_rex = re.compile(
                '^[0-9a-zA-Z\_\.\!\@\#\$\%\^\&\*]{6,20}$')
            if not password_rex.match(args['newpassword']):
                return{
                    'message': 'illegal password'
                }, 403

            if not validate_email_confirm_token(token=args['token'], operation=Operations.RESET_PASSWORD, new_password=args['newpassword']):
                return{
                    'message': 'token error'
                }, 404
            else:
                return{
                    'message': 'password had changed'
                }
        elif type_name == Operations.CHANGE_EMAIL:
            parser.add_argument('newemail', required=True, location='form')
            args = parser.parse_args()
            if not validate_email_confirm_token(token=args['token'], operation=Operations.CHANGE_EMAIL, new_email=args['newemail']):
                return{
                    'message': 'error'
                }, 400
            else:
                return{
                    'message': 'email had changed, please check you new email to confirm it .'
                }
        else:
            abort(404)


api.add_resource(account, '/account/<type_name>')


class ResentConfirmEmail(Resource):
    def post(self):
        """重新发送确认邮件 
        """
        parser = reqparse.RequestParser()
        parser.add_argument('username', location='form')
        parser.add_argument('password', location='form')
        args = parser.parse_args()
        user = User.objects(username=args['username']).first()
        if user is None or not user.validate_password(args['password']):
            return abort(http_status_code=400, message='Either the username or password was invalid.')
        
        if user.confirmed_email :
            return {
                'message':'your email had confirmed.'
            },403

        flag=resent_confirm_email(user)
        if flag==-2:
            return{
                'message':'confirm email resent succeed.'
            }
        else:
            return{
                'message':'please resent in %d seconds.' %flag,
                'seconds':flag
            },403


api.add_resource(ResentConfirmEmail,'/account/resent-confirm')
