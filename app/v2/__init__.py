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
from app.v2.celebrity import Celebrity, Celebrities, CelebrityMovie
from app.v2.search import Search
from app.v2.tag import Genre, Country, Year
from app.v2.rating import Rating, ReportedRating
from app.v2.notification import NotificationCount, Notification


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


api.add_resource(Celebrity, "/celebrity/<celebrity_hash_id>", endpoint="Celebrity")
api.add_resource(Celebrities, "/celebrity", endpoint="Celebrities")
api.add_resource(
    CelebrityMovie, "/celebrity/<celebrity_hash_id>/movie", endpoint="CelebrityMovie"
)


api.add_resource(Search, "/search", endpoint="Search")


api.add_resource(Genre, "/genre", endpoint="Genre")
api.add_resource(Country, "/country", endpoint="Country")
api.add_resource(Year, "/year", endpoint="Year")


api.add_resource(Rating, "/rating/<rating_hash_id>", endpoint="Rating")
api.add_resource(ReportedRating, "/rating/reported", endpoint="ReportedRating")


api.add_resource(
    NotificationCount, "/notification/new_count", endpoint="NotificationCount"
)
api.add_resource(
    Notification,
    "/notification/<any(friendship,like):type_name>",
    endpoint="Notification",
)
