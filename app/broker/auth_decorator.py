from functools import wraps

from flask import jsonify, g
from flask_httpauth import HTTPTokenAuth
from app.sql_models import User

auth = HTTPTokenAuth(scheme="Bearer")


@auth.verify_token
def verify_token(token):
    if User.verity_auth_token(token):
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
