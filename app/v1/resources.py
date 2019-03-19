from flask import Blueprint, url_for
from flask_restful import Resource, abort, reqparse

from app.extensions import api
from app.models import User, Follow

from .auth import auth, email_confirm_required, permission_required
from .schemas import user_schema, items_schema

api_bp = Blueprint('api', __name__)


class UserRegister(Resource):

    def post(self):
        """ 注册新用户
        """
        parser = reqparse.RequestParser()
        parser.add_argument('username', location='form')
        parser.add_argument('email', location='form')
        parser.add_argument('password', location='form')
        args = parser.parse_args()

        if User.create_user(username=args['username'], email=args['email'], password=args['password']):
            return{
                'message': 'Registered User Succeed.',
                'username': args['username']
            }
        else:
            abort(403, message='Registered User Failed.')


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
    def get(self, username, cate):
        if cate.lower() not in ['followers', 'following']:
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

        if cate.lower() == 'followers':
            pagination = Follow.objects(followed=user, is_deleted=False).paginate(
                page=args['page'], per_page=args['per_page'])
            items = [user_schema(follow.follower)
                     for follow in pagination.items]

        if cate.lower() == 'following':
            pagination = Follow.objects(follower=user, is_deleted=False).paginate(
                page=args['page'], per_page=args['per_page'])
            items = [user_schema(follow.followed)
                     for follow in pagination.items]

        prev = None
        if pagination.has_prev:
            prev = url_for('.userfollow', username=username, cate=cate,
                           page=args['page']-1, per_page=args['per_page'], _external=True)

        next = None
        if pagination.has_next:
            next = url_for('.userfollow', username=username, cate=cate,
                           page=args['page']+1, per_page=args['per_page'], _external=True)

        first = url_for('.userfollow', username=username, cate=cate,
                        page=1, per_page=args['per_page'], _external=True)
        last = url_for('.userfollow', username=username, cate=cate,
                       page=pagination.pages, per_page=args['per_page'], _external=True)

        return items_schema(items, prev, next, first, last, pagination)


api.add_resource(UserFollow, '/users/<username>/<cate>')
