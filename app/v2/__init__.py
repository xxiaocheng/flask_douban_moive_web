from flask import Blueprint
from flask_restful import Api
from app.v2.user import (
    AuthToken,
    Users,
    User,
    Follow,
    UserRole,
    Roles,
    ExistTest,
    UserEmail,
    UserPassword,
    EmailToken,
)

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

api = Api(api_bp)

api.add_resource(AuthToken, "/token", endpoint="AuthToken")
api.add_resource(Users, "/users", endpoint="Users")
api.add_resource(User, "/users/<username>", endpoint="User")
api.add_resource(Follow, "/users/<username>/<follower_or_following>", endpoint="Follow")
api.add_resource(UserRole, "/users/<username>/role", endpoint="UserRole")
api.add_resource(Roles, "/roles", endpoint="Roles")
api.add_resource(ExistTest, "/user/test/<username_or_email>", endpoint="ExistTest")
api.add_resource(UserEmail, "/user/email")
api.add_resource(UserPassword, "/user/password")
api.add_resource(EmailToken, "/user/email/token/<operation>")
