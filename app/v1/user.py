import re

from flask import g, url_for
from flask_restful import Resource, abort, reqparse

from app.extensions import api
from app.helpers.redis_utils import *
from app.models import Follow, User
from app.settings import Operations

from .auth import auth, email_confirm_required, permission_required
from .schemas import items_schema, user_schema


class UserRegister(Resource):

    def post(self):
        """ 注册新用户
        """
        parser = reqparse.RequestParser()
        parser.add_argument('username', location='form')
        parser.add_argument('email', location='form')
        parser.add_argument('password', location='form')
        args = parser.parse_args()

        #验证用户名和密码合法性
        username_rex=re.compile('^[a-zA-Z0-9\_]{6,16}$')
        password_rex=re.compile('^[0-9a-zA-Z\_\.\!\@\#\$\%\^\&\*]{6,20}$')
        if not (username_rex.match(args['username']) and password_rex.match(args['password'])):
            return {
                "message":"illegal username or password"
            },403
        user=User.create_user(username=args['username'], email=args['email'], password=args['password'])
        if user:
            send_confirm_email_task=email_task(user,cate=Operations.CHANGE_EMAIL)
            add_email_task_to_redis(send_confirm_email_task)
            return{
                'message': 'Registered User Succeed,please confirm your email of the count.',
                'username': user.username
            }
        else:
            abort(403, message='Registered User Failed.')

    @auth.login_required
    def get(self):
        """返回当前用户所有信息
        """
        current_user = g.current_user
        return user_schema(current_user)

    @auth.login_required
    def delete(self):
        """注销当前用户,注销前验证用户密码
        """
        parser = reqparse.RequestParser()
        parser.add_argument('password', location='form')
        args = parser.parse_args()
        if not g.current_user.validate_password(args['password']):
            return{
                "message":"illegal password"
            },403

        g.current_user.update(is_deleted=True)
        return{
            "message":'succeed'
        }


api.add_resource(UserRegister, '/user')


class UserInfo(Resource):

    @auth.login_required
    def get(self, username):
        user = User.objects(username=username, is_deleted=False).first()
        if not user:
            return{
                "message": "user not found"
            }, 404
        return user_schema(user)


api.add_resource(UserInfo, '/user/<username>')


class UserFollow(Resource):

    @auth.login_required
    def get(self, username, follow_or_unfollow):
        if follow_or_unfollow.lower() not in ['followers', 'following']:
            return{
                "message": 'type error'
            }, 404

        parser = reqparse.RequestParser()
        parser.add_argument('page', default=1, type=int, location='args')
        parser.add_argument('per_page', default=20, type=int, location='args')
        args = parser.parse_args()
        user = User.objects(username=username, is_deleted=False).first()
        if not user:
            return{
                "message": "user not found"
            }, 404

        if follow_or_unfollow.lower() == 'followers':
            pagination = Follow.objects(followed=user, is_deleted=False).paginate(
                page=args['page'], per_page=args['per_page'])
            items = [user_schema(follow.follower)
                     for follow in pagination.items]

        if follow_or_unfollow.lower() == 'following':
            pagination = Follow.objects(follower=user, is_deleted=False).paginate(
                page=args['page'], per_page=args['per_page'])
            items = [user_schema(follow.followed)
                     for follow in pagination.items]

        prev = None
        if pagination.has_prev:
            prev = url_for('.userfollow', username=username, follow_or_unfollow=follow_or_unfollow,
                           page=args['page']-1, per_page=args['per_page'], _external=True)

        next = None
        if pagination.has_next:
            next = url_for('.userfollow', username=username, follow_or_unfollow=follow_or_unfollow,
                           page=args['page']+1, per_page=args['per_page'], _external=True)

        first = url_for('.userfollow', username=username, follow_or_unfollow=follow_or_unfollow,
                        page=1, per_page=args['per_page'], _external=True)
        last = url_for('.userfollow', username=username, follow_or_unfollow=follow_or_unfollow,
                       page=pagination.pages, per_page=args['per_page'], _external=True)

        return items_schema(items, prev, next, first, last, pagination.total,pagination.pages)


api.add_resource(UserFollow, '/users/<username>/<follow_or_unfollow>')


class FriendShip(Resource):

    @auth.login_required
    def post(self, follow_or_unfollow):
        if follow_or_unfollow not in ['follow','unfollow']:
            return{
                "message":"type error"
            },400
        parser = reqparse.RequestParser()
        parser.add_argument('username', required=True)
        args = parser.parse_args()
        user = User.objects(
            username=args['username'], is_deleted=False).first()
        if not user:
            return{
                "message": "user not fount"
            }, 400

        if follow_or_unfollow.lower() == 'follow':
            flag = g.current_user.follow(user)

        if follow_or_unfollow.lower() == 'unfollow':
            flag = g.current_user.unfollow(user)

        if flag:
            return{
                "message": "ok"
            }
        else:
            return{
                "message": "error"
            },403


api.add_resource(FriendShip, '/users/<follow_or_unfollow>')

class ChangePassword(Resource):
    
    @auth.login_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('oldpassword', required=True  ,location='form')
        parser.add_argument('newpassword', required=True  ,location='form')
        parser.add_argument('newpassword2', required=True  ,location='form')
        args = parser.parse_args()
        user=g.current_user
        if args['newpassword']!=args['newpassword2']:
            return{
                'message':'two password not equal'
            },403
        if user.validate_password(args['oldpassword']):
            user.set_password(args['newpassword'])
            return{
                'message':'change password successfuly'
            }
        return {
            'message':'password check failed'
        },403
        

api.add_resource(ChangePassword,'/user/change-password')


class ResetPassword(Resource):

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('email', required=True  ,location='form')
        args = parser.parse_args()
        
        user=User.objects(email=args['email'],is_deleted=False).first()
        if not user:
            return{
                'message':'no user found'
            },404
        
        task=email_task(user=user,cate=Operations.RESET_PASSWORD)
        add_email_task_to_redis(task)
        return{
            'message':'the reset-password email will be  sent to user\'s email soon'
        }
                
api.add_resource(ResetPassword,'/user/reset-password')

class ChangeEmail(Resource):
    
    @auth.login_required
    def post(self):
        user=g.current_user
        task=email_task(user=user.username,cate=Operations.CHANGE_EMAIL)
        add_email_task_to_redis(task)
        return{
            'message':'th link for change email had sent to your email.'
        }

api.add_resource(ChangeEmail,'/user/change-email')