from flask import current_app
from itsdangerous import BadSignature, SignatureExpired
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from app.const import AccountOperations
from app.extensions import sql_db
from app.sql_models import User
from app.tasks.email import send_confirm_email


def generate_email_confirm_token(username, operation, expire_in=None, **kwargs):
    s = Serializer(current_app.config["SECRET_KEY"], expire_in)

    data = {"username": username, "operation": operation}
    data.update(**kwargs)
    return s.dumps(data).decode("ascii")


def validate_email_confirm_token(token, operation, new_password=None, new_email=None):
    s = Serializer(current_app.config["SECRET_KEY"])

    try:
        data = s.loads(token)
    except (SignatureExpired, BadSignature):
        return False

    if operation != data.get("operation"):
        return False
    username = data.get("username")
    if operation == AccountOperations.CONFIRM:
        email = data.get("email")
        user = User.query.filter_by(email=email).first()
        if not user:
            return False
        user.email_confirmed = True
        sql_db.session.commit()

    elif operation == AccountOperations.RESET_PASSWORD:
        user = User.query.filter_by(username=username).first()
        if not user:
            return False
        user.change_password(new_password)
        sql_db.session.commit()

    elif operation == AccountOperations.CHANGE_EMAIL:
        if new_email is None:
            return False
        user = User.query.filter_by(username=username).first()
        if not user:
            return False
        else:
            if user.change_email(new_email):
                sql_db.session.commit()
                token = generate_email_confirm_token(
                    username, AccountOperations.CONFIRM, email=new_email
                )
                send_confirm_email.delay(token, new_email, username)
            else:
                return False
    else:
        return False
    return True
