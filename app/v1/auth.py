import re
from functools import wraps

from flask import current_app, g, jsonify
from flask_httpauth import HTTPTokenAuth
from flask_restful import Resource, abort, reqparse

from app.extensions import api
from app.helpers.utils import validate_email_confirm_token
from app.models import User
from app.settings import AccountOperations
from app.helpers.redis_utils import send_email_limit

auth = HTTPTokenAuth(scheme="Bearer")


class AuthTokenAPI(Resource):
    def post(self):
        """返回 token
        """
        parser = reqparse.RequestParser()
        parser.add_argument("grant_type", location="form")
        parser.add_argument("username", location="form")
        parser.add_argument("password", location="form")
        args = parser.parse_args()

        if args["grant_type"] is None or args["grant_type"].lower() != "password":
            return abort(
                http_status_code=400, message="The grant type must be password."
            )

        user = User.objects(username=args["username"], is_deleted=False).first()
        if user is None or not user.validate_password(args["password"]):
            return abort(http_status_code=400, message="账户名或密码错误!", error_code=1001)

        if user.is_locked():
            return {"message": "用户被封禁,请联系管理员!"}, 403
        if not user.confirmed_email:
            return {"message": "请验证邮箱!", "error_code": 1000}, 403
        expiration = current_app.config["EXPIRATION"]
        token = user.generate_token(expiration=expiration)
        role = user.role.name

        # 错误吗1001 密码错误, 1000 未验证邮箱
        return (
            {
                "access_token": token,
                "token_type": "bearer",
                "expires_in": expiration,
                "role": role.lower(),
            },
            201,
            {"Cache-Control": "no-store", "Pragma": "no-cache"},
        )


api.add_resource(AuthTokenAPI, "/oauth/token")


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
                response = jsonify(message="%s Permission Required" % permission_name)
                response.status_code = 403
                return response
            return func(*args, **kwargs)

        return decorated_function

    return decorator


def email_confirm_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not g.current_user.confirmed_email:
            response = jsonify(message="Email Confirm Required.")
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
        parser.add_argument("token", required=True, location="form")

        if type_name == AccountOperations.CONFIRM:
            args = parser.parse_args()
            flag = validate_email_confirm_token(
                token=args["token"], operation=AccountOperations.CONFIRM
            )
            if flag:
                return {"message": "您的账户已确认!"}
            else:
                return {"message": "错误的 token!"}, 403
        elif type_name == AccountOperations.RESET_PASSWORD:
            parser.add_argument("password", required=True, location="form")
            args = parser.parse_args()

            password_rex = re.compile("^[0-9a-zA-Z\_\.\!\@\#\$\%\^\&\*]{6,20}$")
            if not password_rex.match(args["password"]):
                return {"message": "密码不合法!"}, 403

            if validate_email_confirm_token(
                token=args["token"],
                operation=AccountOperations.RESET_PASSWORD,
                new_password=args.password,
            ):
                return {"message": "密码已重置!"}

            else:
                return {"message": "错误的 token!"}, 404
        elif type_name == AccountOperations.CHANGE_EMAIL:
            parser.add_argument("newemail", required=True, location="form")
            args = parser.parse_args()
            if not validate_email_confirm_token(
                token=args["token"],
                operation=AccountOperations.CHANGE_EMAIL,
                new_email=args["newemail"],
            ):
                return {"message": "错误的token!"}, 400
            else:
                return {"message": "邮箱已更换, 请确认新的邮箱!"}
        else:
            abort(404)


api.add_resource(account, "/account/<type_name>")


class ResentConfirmEmail(Resource):
    def post(self):
        """重新发送确认邮件
        """
        parser = reqparse.RequestParser()
        parser.add_argument("username", location="form")
        parser.add_argument("password", location="form")
        args = parser.parse_args()
        user = User.objects(username=args["username"]).first()
        if user is None or not user.validate_password(args["password"]):
            return abort(http_status_code=400, message="账户名或密码错误!")

        if user.confirmed_email:
            return {"message": "您的邮箱已经确认,无需再次确认!"}, 403

        flag = send_email_limit(user, AccountOperations.CONFIRM)
        if flag == -2:
            return {"message": "请到 %s 查收邮件!" % user.email}
        else:
            return {"message": "请 %d 秒后重试" % flag, "seconds": flag}, 403


api.add_resource(ResentConfirmEmail, "/auth/resent-confirm")


class ChangePassword(Resource):
    @auth.login_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("oldpassword", required=True, location="form")
        parser.add_argument("newpassword", required=True, location="form")
        parser.add_argument("newpassword2", required=True, location="form")
        args = parser.parse_args()
        user = g.current_user
        if args["newpassword"] != args["newpassword2"]:
            return {"message": "two password not equal"}, 403
        if user.validate_password(args["oldpassword"]):
            user.set_password(args["newpassword"])
            return {"message": "密码修改成功"}
        return {"message": "请输入正确的密码"}, 403


api.add_resource(ChangePassword, "/auth/change-password")


class ResetPassword(Resource):
    """重置密码
    """

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("email", required=True, location="form")
        args = parser.parse_args()

        user = User.objects(email=args["email"], is_deleted=False).first()
        if not user:
            return {"message": "邮箱不存在"}, 404

        flag = send_email_limit(user, AccountOperations.RESET_PASSWORD)

        if flag == -2:
            return {"message": "请到 %s 查收邮件!" % user.email}
        else:
            return {"message": "请 %d 秒后重试" % flag, "seconds": flag}, 403


api.add_resource(ResetPassword, "/auth/reset-password")


class ChangeEmail(Resource):
    """
    更改邮箱
    """

    @auth.login_required
    def post(self):
        user = g.current_user

        flag = send_email_limit(user, AccountOperations.CHANGE_EMAIL)
        if flag == -2:
            return {"message": "请到 %s 查收邮件!" % user.email}
        else:
            return {"message": "请 %d 秒后重试" % flag, "seconds": flag}, 403


api.add_resource(ChangeEmail, "/auth/change-email")
