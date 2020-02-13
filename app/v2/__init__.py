from flask import Blueprint
from flask_restful import Api

from app.v2.movie import (
    ChoiceMovie,
    CinemaMovie,
    LeaderBoard,
    Movie,
    MovieGenresRank,
    MovieRecommend,
    MovieUserRating,
    UserMovie,
    FollowFeed,
    Movies,
)
from app.v2.user import (
    AuthToken,
    EmailToken,
    ExistTest,
    Follow,
    Roles,
    User,
    UserEmail,
    UserPassword,
    UserRole,
    Users,
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
api.add_resource(UserEmail, "/user/email", endpoint="UserEmail")
api.add_resource(UserPassword, "/user/password", endpoint="UserPassword")
api.add_resource(EmailToken, "/user/email/token/<operation>", endpoint="EmailToken")

api.add_resource(
    CinemaMovie, "/movie/cinema/<coming_or_showing>", endpoint="CinemaMovie"
)
api.add_resource(MovieRecommend, "/movie/recommend", endpoint="MovieRecommend")
api.add_resource(
    LeaderBoard, "/movie/leader-board/<time_range>", endpoint="LeaderBoard"
)
api.add_resource(
    MovieGenresRank, "/movie/genre/<genre_hash_id>", endpoint="MovieGenresRank"
)
api.add_resource(UserMovie, "/users/<username>/movie", endpoint="UserMovie")
api.add_resource(ChoiceMovie, "/movie/choice", endpoint="ChoiceMovie")
api.add_resource(Movie, "/movie/<movie_hash_id>", endpoint="Movie")
api.add_resource(
    MovieUserRating, "/movie/<movie_hash_id>/rating", endpoint="MovieUserRating"
)
api.add_resource(FollowFeed, "/movie/feed", endpoint="FollowFeed")
api.add_resource(Movies, "/movie", endpoint="Movies")
