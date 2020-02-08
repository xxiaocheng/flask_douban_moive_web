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

from .auth import auth, permission_required
from .schemas import items_schema, user_schema, user_summary_schema


class UserRegister(Resource):
    def post(self):
        """ 注册新用户
        """
        parser = reqparse.RequestParser()
        parser.add_argument("username", required=True, type=str, location="form")
        parser.add_argument("email", required=True, type=str, location="form")
        parser.add_argument("password", required=True, type=str, location="form")
        args = parser.parse_args()

        # 验证用户名,邮箱和密码合法性
        username_rex = re.compile("^[a-zA-Z0-9\_]{6,16}$")
        password_rex = re.compile("^[0-9a-zA-Z\_\.\!\@\#\$\%\^\&\*]{6,20}$")
        email_rex = re.compile("[^@]+@[^@]+\.[^@]+")
        if (
            (not username_rex.match(args["username"]))
            or (not password_rex.match(args["password"]))
            or (not email_rex.match(args["email"]))
        ):
            return {"message": "illegal username, password or email."}, 403
        user = User.create_user(
            username=args["username"], email=args["email"], password=args["password"]
        )
        if user:
            send_confirm_email_task = email_task(user, cate=Operations.CONFIRM)
            add_email_task_to_redis(send_confirm_email_task)
            return {
                "message": "Registered User Succeed,please confirm your email of the count.",
                "username": user.username,
            }
        else:
            abort(403, message="Registered User Failed.")

    @auth.login_required
    def get(self):
        """返回当前用户所有信息
        """
        parser = reqparse.RequestParser()
        parser.add_argument(
            "type", default="detail", choices=["detail", "summary"], location="args"
        )
        args = parser.parse_args()
        current_user = g.current_user
        if args.type == "detail":
            return user_schema(current_user)
        return user_summary_schema(current_user)

    @auth.login_required
    def delete(self):
        """注销当前用户,注销前验证用户密码
        """
        parser = reqparse.RequestParser()
        parser.add_argument("password", required=True, location="form")
        args = parser.parse_args()
        if not g.current_user.validate_password(args["password"]):
            return {"message": "illegal password"}, 403

        g.current_user.delete_self()

        return {"message": "succeed"}

    @auth.login_required
    def patch(self):
        """更改用户资料
        """
        parser = reqparse.RequestParser()
        parser.add_argument("username", location="form")
        parser.add_argument("location", location="form")
        parser.add_argument("signature", location="form")
        args = parser.parse_args()
        user = g.current_user
        username_modified = location_modified = signature_modified = False
        if args.username:
            username_rex = re.compile("^[a-zA-Z0-9\_]{6,16}$")
            if username_rex.match(args["username"]):
                if User.objects(username=args.username, is_deleted=False).first():
                    if args.username == user.username:
                        username_modified = True
                    else:
                        username_modified = False
                else:
                    user.update(username=args.username)
                    username_modified = True

        if args.location:
            if "." in args.location:
                with open(
                    os.path.join(
                        current_app.config["AREA_DATA_PATH"], "area-data.json"
                    ),
                    "r",
                ) as f:
                    local_dict = json.load(f)
                local_list = args.location.split(".")
                try:
                    if local_list[1] == "undefined":
                        local_dict["86"][local_list[0]]
                    else:
                        local_dict[local_list[0]][local_list[1]]
                    location_modified = True
                    user.update(location=args.location)
                except:
                    pass

        if args.signature:
            if len(args["signature"]) <= 50:
                user.update(signature=args.signature)
                signature_modified = True

        return {
            "username_modified": username_modified,
            "location_modified": location_modified,
            "signature_modiied": signature_modified,
        }


api.add_resource(UserRegister, "/user")


class UserInfo(Resource):
    # 返回用户信息
    @auth.login_required
    def get(self, username):
        parser = reqparse.RequestParser()
        parser.add_argument(
            "type", default="detail", choices=["detail", "summary"], location="args"
        )
        args = parser.parse_args()
        user = User.objects(username=username, is_deleted=False).first()
        if not user:
            return {"message": "user not found"}, 404
        if args.type == "detail":
            return user_schema(user)
        else:
            return user_summary_schema(user)


api.add_resource(UserInfo, "/user/<username>")


class UserFriends(Resource):

    # 用户 好友关系
    @auth.login_required
    def get(self, username, follower_or_following):
        if follower_or_following.lower() not in ["follower", "following"]:
            return {"message": "type error"}, 404

        parser = reqparse.RequestParser()
        parser.add_argument("page", default=1, type=int, location="args")
        parser.add_argument("per_page", default=20, type=int, location="args")
        args = parser.parse_args()
        user = User.objects(username=username, is_deleted=False).first()
        if not user:
            return {"message": "user not found"}, 404

        if follower_or_following.lower() == "follower":
            pagination = Follow.objects(followed=user, is_deleted=False).paginate(
                page=args["page"], per_page=args["per_page"]
            )
            items = [
                user_summary_schema(follow.follower) for follow in pagination.items
            ]

        if follower_or_following.lower() == "following":
            pagination = Follow.objects(follower=user, is_deleted=False).paginate(
                page=args["page"], per_page=args["per_page"]
            )
            items = [
                user_summary_schema(follow.followed) for follow in pagination.items
            ]

        prev = None
        if pagination.has_prev:
            prev = url_for(
                ".userfriends",
                username=username,
                follower_or_following=follower_or_following,
                page=args["page"] - 1,
                per_page=args["per_page"],
                _external=True,
            )

        next = None
        if pagination.has_next:
            next = url_for(
                ".userfriends",
                username=username,
                follower_or_following=follower_or_following,
                page=args["page"] + 1,
                per_page=args["per_page"],
                _external=True,
            )

        first = url_for(
            ".userfriends",
            username=username,
            follower_or_following=follower_or_following,
            page=1,
            per_page=args["per_page"],
            _external=True,
        )
        last = url_for(
            ".userfriends",
            username=username,
            follower_or_following=follower_or_following,
            page=pagination.pages,
            per_page=args["per_page"],
            _external=True,
        )

        return items_schema(
            items, prev, next, first, last, pagination.total, pagination.pages
        )


api.add_resource(UserFriends, "/users/<username>/<follower_or_following>")


class FriendShip(Resource):
    """关注或者取消关注某人
    """

    @auth.login_required
    def post(self, follow_or_unfollow):
        if follow_or_unfollow not in ["follow", "unfollow"]:
            return {"message": "type error"}, 400
        parser = reqparse.RequestParser()
        parser.add_argument("username", required=True)
        args = parser.parse_args()
        user = User.objects(username=args["username"], is_deleted=False).first()
        if not user:
            return {"message": "user not found"}, 400

        if follow_or_unfollow.lower() == "follow":
            flag = g.current_user.follow(user)

        if follow_or_unfollow.lower() == "unfollow":
            flag = g.current_user.unfollow(user)

        if flag:
            return {"message": "ok"}
        else:
            return {"message": "error"}, 403


api.add_resource(FriendShip, "/users/<follow_or_unfollow>")


class UploadAvatar(Resource):
    """
    上传头像
    """

    @auth.login_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument(
            "raw_file", required=True, type=FileStorage, location="files"
        )
        parser.add_argument("l_file", required=True, type=FileStorage, location="files")
        args = parser.parse_args()
        user = g.current_user
        raw_ext = os.path.splitext(args["raw_file"].filename)[1]
        l_ext = os.path.splitext(args.l_file.filename)[1]

        if (
            raw_ext not in current_app.config["UPLOAD_IMAGE_EXT"]
            or l_ext not in current_app.config["UPLOAD_IMAGE_EXT"]
        ):
            return {"message": "file type error", "type": raw_ext}, 403

        raw_filename = rename_image(args["raw_file"].filename)
        l_filename = raw_filename.split(".")[0] + "_l." + raw_filename.split(".")[1]

        with open(
            os.path.join(current_app.config["AVATAR_UPLOAD_PATH"], raw_filename), "wb"
        ) as f:
            args["raw_file"].save(f)
        with open(
            os.path.join(current_app.config["AVATAR_UPLOAD_PATH"], l_filename), "wb"
        ) as f:
            args["l_file"].save(f)

        user.update(avatar_raw=raw_filename, avatar_l=l_filename)
        return {"filemame": "change avatar successfuly."}


api.add_resource(UploadAvatar, "/user/upload-avatar")


class UserRole(Resource):

    # 返回当前用户的角色
    @auth.login_required
    @permission_required("SET_ROLE")
    def get(self, username):
        """
        @return 用户权限名称
        """
        user = User.objects(username=username, is_deleted=False).first()
        if not user:
            return {"message": "user not found."}
        return {"role_id": str(user.role.id), "role_name": user.role.name}

    @auth.login_required
    @permission_required("SET_ROLE")
    def post(self, username):
        """修改用户权限
        """
        parser = reqparse.RequestParser()
        parser.add_argument(
            "role_id",
            required=True,
            choices=[str(role.id) for role in Role.objects() if role],
            type=str,
            location="form",
        )
        args = parser.parse_args()
        user = User.objects(username=username, is_deleted=False).first()
        if not user:
            return {"message": "user not found."}
        new_role = Role.objects(id=args.role_id).first()
        user.update(role=new_role)
        return {
            "message": "user role changed",
            "new_role_name": new_role.name,
            "new_role_id": str(new_role.id),
        }


api.add_resource(UserRole, "/user/<username>/role")


class ListRole(Resource):
    @auth.login_required
    @permission_required("SET_ROLE")
    def get(self):
        return {
            "roles": [
                {
                    "role_id": str(role.id),
                    "role_name": role.name,
                    "permissions": role.permissions,
                }
                for role in Role.objects()
                if role
            ],
            "count": Role.objects().count(),
        }


api.add_resource(ListRole, "/roles")


class ImportDouban(Resource):
    @auth.login_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("douban_id", required=True, location="form")
        args = parser.parse_args()
        user = g.current_user
        if user.douban_imported:
            return {"message": "you had imported it already."}, 403
        task = import_info_from_douban_task(user, args.douban_id)
        add_import_info_from_douban_task_to_redis(task)
        user.update(douban_imported=True)

        return {"message": "task added."}


api.add_resource(ImportDouban, "/douban_import")


class ValidExists(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument(
            "type_name", choices=["username", "email"], required=True, location="args"
        )
        parser.add_argument("value", required=True, location="args")
        args = parser.parse_args()
        if args.type_name == "username":
            user = User.objects(username=args.value, is_deleted=False).first()
            if user:
                return {"message": "this username existed."}, 403
            return {"message": "this username ok."}
        if args.type_name == "email":
            user = User.objects(email=args.value, is_deleted=False).first()
            if user:
                return {"message": "this email existed."}, 403
            return {"message": "this email ok."}


api.add_resource(ValidExists, "/user/validate")
