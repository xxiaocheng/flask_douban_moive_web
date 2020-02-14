from flask import g
from flask_restful import Resource, inputs, marshal, reqparse

from app.const import AccountOperations
from app.extensions import sql_db
from app.sql_models import Role
from app.sql_models import User as UserModel
from app.tasks.email import (
    send_change_email_email,
    send_confirm_email,
    send_reset_password_email,
)
from app.utils.auth_decorator import auth, permission_required
from app.utils.auth_utils import (
    generate_email_confirm_token,
    validate_email_confirm_token,
)
from app.utils.redis_utils import test_limit_of_send_email
from app.v2.responses import (
    ErrorCode,
    error,
    get_item_pagination,
    get_pagination_resource_fields,
    ok,
    user_resource_fields,
)


class AuthToken(Resource):
    def post(self):
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument(
            "grant_type",
            type=str,
            choices=["password"],
            help="grant_type must be in ['password'] ",
            required=True,
            location="form",
        )
        parser.add_argument(
            "username",
            type=inputs.regex("^[a-zA-Z0-9\_]{6,16}$"),
            required=True,
            help="username cannot be blank!",
            location="form",
        )
        parser.add_argument(
            "password",
            type=inputs.regex("^[0-9a-zA-Z\_\.\!\@\#\$\%\^\&\*]{6,20}$"),
            required=True,
            help="password cannot be blank!",
            location="form",
        )
        args = parser.parse_args()
        user = UserModel.query.filter_by(username=args["username"]).first()
        if not user or not user.validate_password(args["password"]):
            return error(ErrorCode.USERNAME_OR_PASSWORD_ERROR, 400)
        if user.is_locked:
            return error(ErrorCode.ACCOUNT_IS_LOCKED, 403)
        if not user.email_confirmed:
            return error(ErrorCode.EMAIL_NOT_CONFIRMED, 403)
        expire_in = 60 * 60 * 24
        data = {
            "access_token": user.generate_token(expire_in),
            "token_type": "bearer",
            "expires_in": expire_in,
            "role": user.role_name,
        }
        return data, 201, {"Cache-Control": "no-store", "Pragma": "no-cache"}

    @auth.login_required
    def delete(self):
        current_user = g.current_user
        current_user.revoke_auth_token()
        return ok("revoke auth token")


class Users(Resource):
    def post(self):
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument(
            "username",
            type=inputs.regex("^[a-zA-Z0-9\_]{6,16}$"),
            required=True,
            help="username is not formatted",
            location="form",
        )
        parser.add_argument(
            "password",
            type=inputs.regex("^[0-9a-zA-Z\_\.\!\@\#\$\%\^\&\*]{6,20}$"),
            required=True,
            help="password is not formatted",
            location="form",
        )
        parser.add_argument(
            "email",
            type=inputs.regex("[^@]+@[^@]+\.[^@]+"),
            required=True,
            help="email is not formatted",
            location="form",
        )
        args = parser.parse_args()
        user = UserModel.create_one(args["username"], args["email"], args["password"])
        if not user:
            return error(ErrorCode.USER_ALREADY_EXISTS, 403)
        sql_db.session.add(user)
        sql_db.session.commit()
        token = generate_email_confirm_token(
            user.username, AccountOperations.CONFIRM, email=user.email
        )
        send_confirm_email.delay(token, user.email, user.username)
        return ok(
            "register user succeed",
            http_status_code=201,
            username=user.username,
            role_name=user.role_name,
        )

    @auth.login_required
    def get(self):
        return marshal(g.current_user, user_resource_fields)


class User(Resource):
    @auth.login_required
    def get(self, username):
        user = UserModel.query.filter_by(username=username).first()
        if user:
            return ok(
                "ok",
                data=marshal(user, user_resource_fields),
                followed=user.is_following(g.current_user),
                follow=user.is_followed_by(g.current_user),
            )
        else:
            return error(ErrorCode.USER_NOT_FOUND, 404)

    @auth.login_required
    def delete(self, username):
        if username != g.current_user.username:
            return error(ErrorCode.FORBIDDEN, 403)
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument(
            "password",
            type=inputs.regex("^[0-9a-zA-Z\_\.\!\@\#\$\%\^\&\*]{6,20}$"),
            required=True,
            help="password cannot be blank!",
            location="form",
        )
        args = parser.parse_args()
        if not g.current_user.validate_password(args.password):
            return error(ErrorCode.FORBIDDEN, 403)
        sql_db.session.delete(g.current_user)
        sql_db.session.commit()
        return ok("删除用户成功")

    @auth.login_required
    def patch(self, username):
        if username != g.current_user.username:
            return error(ErrorCode.FORBIDDEN, 403)
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument(
            "username",
            required=False,
            type=inputs.regex("^[a-zA-Z0-9\_]{6,16}$"),
            location="form",
        )
        parser.add_argument("city_id", location="form")
        parser.add_argument(
            "signature", type=inputs.regex("^.{1,64}$"), location="form"
        )
        parser.add_argument("avatar_url_last", type=str, location="form")
        args = parser.parse_args()
        user = g.current_user
        if args.username:
            if not user.change_username(args.username):
                return error(ErrorCode.USER_ALREADY_EXISTS, 403)
        if args.city_id:
            user.city_id = args.city_id
        if args.signature:
            user.signature = args.signature
        if args.avatar_url_last:
            user.avatar_url_last = args.avatar_url_last
        sql_db.session.commit()
        return ok(
            "ok",
            username=user.username,
            city_name=user.city.name,
            signature=user.signature,
        )


class Follow(Resource):
    @auth.login_required
    def get(self, username, follower_or_following):
        if follower_or_following.lower() not in ["follower", "following"]:
            return error(ErrorCode.INVALID_PARAMS, 400)
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument("page", default=1, type=inputs.positive, location="args")
        parser.add_argument(
            "per_page", default=20, type=inputs.positive, location="args"
        )
        args = parser.parse_args()
        this_user = UserModel.query.filter_by(username=username).first()
        if not this_user:
            return error(ErrorCode.USER_NOT_FOUND, 404)
        if follower_or_following.lower() == "follower":
            pagination = this_user.followers.paginate(args.page, args.per_page)
        if follower_or_following.lower() == "following":
            pagination = this_user.followed.paginate(args.page, args.per_page)
        p = get_item_pagination(
            pagination,
            "api.Follow",
            username=username,
            follower_or_following=follower_or_following,
        )

        return ok(
            "ok", data=marshal(p, get_pagination_resource_fields(user_resource_fields))
        )

    @auth.login_required
    def post(self, username, follower_or_following):
        """follow someone"""
        if follower_or_following.lower() != "follow":
            return error(ErrorCode.INVALID_PARAMS, 400)
        this_user = UserModel.query.filter_by(username=username).first()
        if not this_user:
            return error(ErrorCode.USER_NOT_FOUND, 404)
        if g.current_user.follow(this_user):
            sql_db.session.commit()
            return ok(message="关注成功", http_status_code=201)
        else:
            return error(ErrorCode.FOLLOW_ALREADY_EXISTS, 403)

    @auth.login_required
    def delete(self, username, follower_or_following):
        if follower_or_following.lower() != "unfollow":
            return error(ErrorCode.INVALID_PARAMS, 400)
        this_user = UserModel.query.filter_by(username=username).first()
        if not this_user:
            return error(ErrorCode.USER_NOT_FOUND, 404)
        if g.current_user.unfollow(this_user):
            sql_db.session.commit()
            return ok(message="取消关注成功")
        else:
            return error(ErrorCode.FOLLOW_NOT_EXISTS, 403)


class UserRole(Resource):
    @auth.login_required
    @permission_required("SET_ROLE")
    def get(self, username):
        this_user = UserModel.query.filter_by(username=username).first()
        if not this_user:
            return error(ErrorCode.USER_NOT_FOUND, 404)
        return ok(message="ok", role_name=this_user.role_name)

    @auth.login_required
    @permission_required("SET_ROLE")
    def put(self, username):
        this_user = UserModel.query.filter_by(username=username).first()
        if not this_user:
            return error(ErrorCode.USER_NOT_FOUND, 404)
        parse = reqparse.RequestParser(trim=True)
        parse.add_argument(
            "role_name",
            required=True,
            choices=[
                role[0]
                for role in Role.query.with_entities(Role.role_name).distinct().all()
            ],
            type=str,
            location="form",
        )
        args = parse.parse_args()
        this_user.change_role(args.role_name)
        sql_db.session.commit()
        return ok(message="修改权限成功")


class Roles(Resource):
    @auth.login_required
    @permission_required("SET_ROLE")
    def get(self):
        return ok(
            message="ok",
            data={
                "roles": [
                    role[0]
                    for role in Role.query.with_entities(Role.role_name)
                    .distinct()
                    .all()
                ],
                "count": Role.query.with_entities(Role.role_name).distinct().count(),
            },
        )


class ExistTest(Resource):
    def get(self, username_or_email):
        parser = reqparse.RequestParser()
        parser.add_argument("value", required=True, location="args")
        args = parser.parse_args()
        if username_or_email not in ["username", "email"]:
            return error(ErrorCode.INVALID_PARAMS, 400)

        if username_or_email == "username":
            if UserModel.query.filter_by(username=args.value).first():
                return ok("this username already existed")
            else:
                return error(ErrorCode.USER_NOT_FOUND, 404)
        if username_or_email == "email":
            if UserModel.query.filter_by(email=args.value).first():
                return ok("this username already existed")
            else:
                return error(ErrorCode.USER_NOT_FOUND, 404)


class UserEmail(Resource):
    @auth.login_required
    def put(self):
        """change email"""
        s = test_limit_of_send_email(g.current_user, AccountOperations.CHANGE_EMAIL)
        if s == -2:
            token = generate_email_confirm_token(
                g.current_user.username, AccountOperations.CHANGE_EMAIL
            )
            send_change_email_email.delay(
                token, g.current_user.email, g.current_user.username
            )
            return ok(message="请到 %s 查收邮件!" % g.current_user.email)
        else:
            return error(
                ErrorCode.SENDING_EMAIL_FREQUENTLY, http_status_code=403, second=s
            )

    def post(self):
        """resent email for confirm"""
        parser = reqparse.RequestParser()
        parser.add_argument(
            "username",
            type=inputs.regex("^[a-zA-Z0-9\_]{6,16}$"),
            required=True,
            location="form",
        )
        parser.add_argument(
            "password",
            type=inputs.regex("^[0-9a-zA-Z\_\.\!\@\#\$\%\^\&\*]{6,20}$"),
            required=True,
            location="form",
        )
        args = parser.parse_args()
        this_user = UserModel.query.filter_by(username=args.username).first()
        if not this_user:
            return error(ErrorCode.USER_NOT_FOUND, 404)
        if not this_user.validate_password(args.password):
            return error(ErrorCode.PASSWORD_VALIDATE_ERROR, 403)
        if this_user.email_confirmed:
            return error(ErrorCode.EMAIL_ALREADY_CONFIRMED, 403)
        s = test_limit_of_send_email(g.current_user, AccountOperations.RESET_PASSWORD)
        if s == -2:
            token = generate_email_confirm_token(
                g.current_user.username,
                AccountOperations.CONFIRM,
                email=this_user.email,
            )
            send_change_email_email.delay(
                token, g.current_user.email, g.current_user.username
            )
            return ok(message="请到 %s 查收邮件!" % g.current_user.email)
        else:
            return error(
                ErrorCode.SENDING_EMAIL_FREQUENTLY, http_status_code=403, second=s
            )


class UserPassword(Resource):
    @auth.login_required
    def patch(self):
        """change password"""
        parser = reqparse.RequestParser()
        parser.add_argument(
            "old_password",
            type=inputs.regex("^[0-9a-zA-Z\_\.\!\@\#\$\%\^\&\*]{6,20}$"),
            required=True,
            location="form",
        )
        parser.add_argument(
            "new_password",
            type=inputs.regex("^[0-9a-zA-Z\_\.\!\@\#\$\%\^\&\*]{6,20}$"),
            required=True,
            location="form",
        )
        args = parser.parse_args()
        current_user = g.current_user
        print(current_user.username)
        if current_user.validate_password(args.old_password):
            current_user.change_password(args.old_password)
            sql_db.session.commit()
            return ok("密码修改成功")
        else:
            print()
            return error(ErrorCode.PASSWORD_VALIDATE_ERROR, 403)

    def put(self):
        """reset password"""
        parser = reqparse.RequestParser()
        parser.add_argument(
            "email",
            type=inputs.regex("[^@]+@[^@]+\.[^@]+"),
            required=True,
            location="form",
        )
        args = parser.parse_args()
        this_user = UserModel.query.filter_by(email=args.email).first()
        if not this_user:
            return error(ErrorCode.USER_NOT_FOUND, 404)
        s = test_limit_of_send_email(this_user, AccountOperations.RESET_PASSWORD)
        if s == -2:
            token = generate_email_confirm_token(
                this_user.username, AccountOperations.RESET_PASSWORD
            )
            send_reset_password_email.delay(token, this_user.email, this_user.username)
            return ok(message="请到 %s 查收邮件!" % this_user.email)
        else:
            return error(
                ErrorCode.SENDING_EMAIL_FREQUENTLY, http_status_code=403, second=s
            )


class EmailToken(Resource):
    def post(self, operation):
        parser = reqparse.RequestParser()
        parser.add_argument("token", type=str, required=True, location="form")
        if operation == AccountOperations.CONFIRM:
            args = parser.parse_args()
            f = validate_email_confirm_token(args.token, AccountOperations.CONFIRM)
            if f:
                return ok("您的邮箱已确认!")
            else:
                return error(ErrorCode.INVALID_TOKEN, 403)
        elif operation == AccountOperations.RESET_PASSWORD:
            parser.add_argument(
                "password",
                type=inputs.regex("^[0-9a-zA-Z\_\.\!\@\#\$\%\^\&\*]{6,20}$"),
                required=True,
                location="form",
            )
            args = parser.parse_args()
            if validate_email_confirm_token(
                args.token, AccountOperations.RESET_PASSWORD, new_password=args.password
            ):
                return ok("您的密码已重置")
            else:
                return error(ErrorCode.INVALID_TOKEN, 403)
        elif operation == AccountOperations.CHANGE_EMAIL:
            parser.add_argument(
                "new_email",
                type=inputs.regex("[^@]+@[^@]+\.[^@]+"),
                required=True,
                location="form",
            )
            args = parser.parse_args()
            if UserModel.query.filter_by(email=args.new_email).first():
                return error(ErrorCode.EMAIL_ALREADY_EXISTS, 403)
            if validate_email_confirm_token(
                args.token, AccountOperations.CHANGE_EMAIL, new_email=args.new_email
            ):
                return ok("您的邮箱已修改")
            else:
                return error(ErrorCode.INVALID_TOKEN, 403)
        else:
            return error(ErrorCode.INVALID_PARAMS, 403)
