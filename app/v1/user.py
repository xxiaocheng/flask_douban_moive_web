import os
import re

from flask import current_app, g, url_for
from flask_restful import Resource, abort, reqparse
from werkzeug.datastructures import FileStorage

from app.extensions import api
from app.helpers.redis_utils import *
from app.helpers.utils import rename_image
from app.models import Follow, Role, User
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

        # 验证用户名,邮箱和密码合法性
        username_rex = re.compile('^[a-zA-Z0-9\_]{6,16}$')
        password_rex = re.compile('^[0-9a-zA-Z\_\.\!\@\#\$\%\^\&\*]{6,20}$')
        email_rex=re.compile('[^@]+@[^@]+\.[^@]+')
        if not (username_rex.match(args['username']) and password_rex.match(args['password']) and email_rex.match(args['email'])):
            return {
                "message": "illegal username, password or email."
            }, 403
        user = User.create_user(
            username=args['username'], email=args['email'], password=args['password'])
        if user:
            send_confirm_email_task = email_task(user, cate=Operations.CONFIRM)
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
                "message": "illegal password"
            }, 403

        g.current_user.update(is_deleted=True)
        return{
            "message": 'succeed'
        }

    @auth.login_required
    def patch(self):
        """更改用户资料
        """
        parser = reqparse.RequestParser()
        parser.add_argument('username', location='form')
        parser.add_argument('location', location='form')
        parser.add_argument('signature', location='form')
        args = parser.parse_args()
        user = g.current_user
        if args.username:
            if User.objects(username=args.username, is_deleted=False).first():
                username_modified = False
            else:
                user.update(username=args.username)
                username_modified = True
        if args.location:
            user.update(location=args.location)
        if args.signature:
            user.update(signature=args.signature)

        return{
            'message': 'profile had changed.'
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

        return items_schema(items, prev, next, first, last, pagination.total, pagination.pages)


api.add_resource(UserFollow, '/users/<username>/<follow_or_unfollow>')


class FriendShip(Resource):

    @auth.login_required
    def post(self, follow_or_unfollow):
        if follow_or_unfollow not in ['follow', 'unfollow']:
            return{
                "message": "type error"
            }, 400
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
            }, 403


api.add_resource(FriendShip, '/users/<follow_or_unfollow>')


class ChangePassword(Resource):

    @auth.login_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('oldpassword', required=True, location='form')
        parser.add_argument('newpassword', required=True, location='form')
        parser.add_argument('newpassword2', required=True, location='form')
        args = parser.parse_args()
        user = g.current_user
        if args['newpassword'] != args['newpassword2']:
            return{
                'message': 'two password not equal'
            }, 403
        if user.validate_password(args['oldpassword']):
            user.set_password(args['newpassword'])
            return{
                'message': 'change password successfuly'
            }
        return {
            'message': 'password check failed'
        }, 403


api.add_resource(ChangePassword, '/user/change-password')


class ResetPassword(Resource):
    """重置密码
    """

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('email', required=True, location='form')
        args = parser.parse_args()

        user = User.objects(email=args['email'], is_deleted=False).first()
        if not user:
            return{
                'message': 'no user found'
            }, 404

        task = email_task(user=user, cate=Operations.RESET_PASSWORD)
        add_email_task_to_redis(task)
        return{
            'message': 'the reset-password email will be  sent to user\'s email soon'
        }


api.add_resource(ResetPassword, '/user/reset-password')


class ChangeEmail(Resource):
    """
    更改邮箱
    """
    @auth.login_required
    def post(self):
        user = g.current_user
        task = email_task(user=user, cate=Operations.CHANGE_EMAIL)
        add_email_task_to_redis(task)
        return{
            'message': 'th link for change email had sent to your email.'
        }


api.add_resource(ChangeEmail, '/user/change-email')


class UploadAvatar(Resource):

    @auth.login_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('avatar_file', required=True,
                            type=FileStorage, location='files')
        args = parser.parse_args()
        user = g.current_user
        ext = os.path.splitext(args['avatar_file'].filename)[1]
        if ext not in current_app.config['UPLOAD_IMAGE_EXT']:
            return{
                'message': 'file type error',
                'type': ext
            }, 403

        new_filename = rename_image(args['avatar_file'].filename)

        with open(os.path.join(current_app.config['AVATAR_UPLOAD_PATH'], new_filename), 'wb') as f:
            args['avatar_file'].save(f)

        user.update(avatar_raw=new_filename)
        return {
            'filemame': 'change avatar successfuly.'
        }


api.add_resource(UploadAvatar, '/user/upload-avatar')


class UserRole(Resource):

    # @login_required
    # @permission_required('SET_ROLE')
    def get(self, username):
        """
        @return 用户权限名称
        """
        user = User.objects(username=username, is_deleted=False).first()
        if not user:
            return{
                'message': 'user not found.'
            }
        return{
            'role_id': str(user.role.id),
            'role_name': user.role.name
        }

    # @login_required
    # # @permission_required('SET_ROLE')
    def post(self, username):
        """修改用户权限
        """
        parser = reqparse.RequestParser()
        parser.add_argument('role_id', required=True, choices=[str(
            role.id) for role in Role.objects() if role], type=str, location='form')
        args = parser.parse_args()
        user = User.objects(username=username, is_deleted=False).first()
        if not user:
            return{
                'message': 'user not found.'
            }
        new_role=Role.objects(id=args.role_id).first()
        user.update(role=new_role)
        return{
            'message':'user role changed',
            'new_role_name':new_role.name,
            'new_role_id':str(new_role.id)
        }

api.add_resource(UserRole, '/user/<username>/role')


class ListRole(Resource):

    # @auth.login_required
    # @permission_required('SET_ROLE')
    def get(self):
        
        return{
            'roles':[
                {
                    'role_id':str(role.id),
                    'role_name':role.name,
                    'permissions':role.permissions
                } for role in Role.objects() if role 
            ],
            'count':Role.objects().count()
        }

api.add_resource(ListRole,'/role')


class ImportDouban(Resource):

    @auth.login_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('douban_id',required=True,location='form')
        args = parser.parse_args()
        user=g.current_user
        if user.douban_imported:
            return {
                'message':'you had imported it already.'
            },403
        task=import_info_from_douban_task(user,args.douban_id)
        add_import_info_from_douban_task_to_redis(task)
        user.update(douban_imported=True)

        return{
            'message':'task added.'
        }


api.add_resource(ImportDouban,'/douban_import')


class ValidUserExists(Resource):

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('username',location='args')
        args = parser.parse_args()
        if not args.username:
            return {
                'message':'username is None'
            },400

        user=User.objects(username=args.username,is_deleted=False).first()
        if user:
            return{
                'message':'this username existed.'
            },403
        return{
            'message':'this username ok.'
        }

api.add_resource(ValidUserExists,'/user/validate-username')