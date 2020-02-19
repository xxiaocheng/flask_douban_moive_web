from flask import g
from flask_restful import Resource, inputs, marshal, reqparse
from flask_sqlalchemy import Pagination
from sqlalchemy import desc
from sqlalchemy.sql import func
from werkzeug.datastructures import FileStorage

from app.const import MovieCinemaStatus, RatingType
from app.extensions import cache, sql_db
from app.sql_models import Celebrity, Country, Genre, Image
from app.sql_models import Movie as MovieModel
from app.sql_models import Rating, User, rating_likes
from app.utils.auth_decorator import auth, permission_required
from app.utils.hashid import decode_str_to_id
from app.utils.redis_utils import get_rank_movie_ids_with_range
from app.v2.responses import (
    ErrorCode,
    error,
    get_item_pagination,
    get_pagination_resource_fields,
    movie_resource_fields,
    movie_summary_resource_fields,
    ok,
    rating_resource_fields,
    rating_with_movie_resource_fields,
)


class CinemaMovie(Resource):
    @auth.login_required
    @cache.cached(timeout=60, query_string=True)
    def get(self, coming_or_showing):
        parser = reqparse.RequestParser()
        parser.add_argument("page", default=1, type=inputs.positive, location="args")
        parser.add_argument(
            "per_page", default=20, type=inputs.positive, location="args"
        )
        args = parser.parse_args()
        if coming_or_showing.lower() not in ["coming", "showing"]:
            return error(ErrorCode.INVALID_PARAMS, 400)

        if coming_or_showing.lower() == "coming":
            pagination = (
                MovieModel.query.filter_by(cinema_status=MovieCinemaStatus.COMING)
                .order_by(MovieModel.created_at.desc())
                .paginate(page=args["page"], per_page=args.per_page)
            )
        elif coming_or_showing.lower() == "showing":
            pagination = (
                MovieModel.query.filter_by(cinema_status=MovieCinemaStatus.SHOWING)
                .order_by(MovieModel.created_at.desc())
                .paginate(page=args["page"], per_page=args.per_page)
            )
        p = get_item_pagination(
            pagination, "api.CinemaMovie", coming_or_showing=coming_or_showing
        )
        return ok(
            "ok",
            data=marshal(
                p, get_pagination_resource_fields(movie_summary_resource_fields)
            ),
        )


class MovieRecommend(Resource):
    @auth.login_required
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("page", default=1, type=inputs.positive, location="args")
        parser.add_argument(
            "per_page", default=20, type=inputs.positive, location="args"
        )
        args = parser.parse_args()
        pagination = MovieModel.query.order_by(func.random()).paginate(
            page=args.page, per_page=args.per_page
        )
        p = get_item_pagination(pagination, "api.MovieRecommend")
        return ok(
            "ok",
            data=marshal(
                p, get_pagination_resource_fields(movie_summary_resource_fields)
            ),
        )


class LeaderBoard(Resource):
    @auth.login_required
    @cache.cached(timeout=60, query_string=True)
    def get(self, time_range):
        if time_range not in ["week", "month"]:
            return error(ErrorCode.INVALID_PARAMS, 400)
        parser = reqparse.RequestParser()
        parser.add_argument("page", default=1, type=inputs.positive, location="args")
        parser.add_argument(
            "per_page", default=20, type=inputs.positive, location="args"
        )
        args = parser.parse_args()
        if time_range == "week":
            days = 7
        else:
            days = 30
        movie_ids, total = get_rank_movie_ids_with_range(days, args.page, args.per_page)
        movies = MovieModel.query.filter(MovieModel.id.in_(movie_ids)).all()
        pagination = Pagination("", args.page, args.per_page, total, movies)
        p = get_item_pagination(pagination, "api.LeaderBoard", time_range=time_range)
        return ok(
            "ok",
            data=marshal(
                p, get_pagination_resource_fields(movie_summary_resource_fields)
            ),
        )


class MovieGenresRank(Resource):
    @auth.login_required
    @cache.cached(60, query_string=True)
    def get(self, genre_hash_id):
        parser = reqparse.RequestParser()
        parser.add_argument("page", default=1, type=inputs.positive, location="args")
        parser.add_argument(
            "per_page", default=20, type=inputs.positive, location="args"
        )
        args = parser.parse_args()
        genre_id = decode_str_to_id(genre_hash_id)
        genre = Genre.query.get(genre_id)
        if not genre:
            return error(ErrorCode.GENRES_NOT_FOUND, 404)
        score_stmt = (
            sql_db.session.query(
                Rating.movie_id.label("movie_id"),
                func.avg(Rating.score).label("avg_score"),
            )
            .filter(Rating.category == RatingType.COLLECT)
            .group_by(Rating.movie_id)
            .order_by(desc("avg_score"))
            .subquery()
        )
        movies = MovieModel.query.filter(MovieModel.genres.contains(genre)).subquery()
        pagination = (
            sql_db.session.query(MovieModel)
            .outerjoin(score_stmt, MovieModel.id == score_stmt.c.movie_id)
            .filter(MovieModel.id == movies.c.id)
            .order_by(score_stmt.c.avg_score.desc())
            .paginate(args.page, args.per_page)
        )
        p = get_item_pagination(
            pagination, "api.MovieGenresRank", genre_hash_id=genre_hash_id
        )
        return ok(
            "ok",
            data=marshal(
                p, get_pagination_resource_fields(movie_summary_resource_fields)
            ),
        )


class UserMovie(Resource):
    @auth.login_required
    @cache.cached(10, query_string=True)
    def get(self, username):
        this_user = User.query.filter_by(username=username).first()
        if not this_user:
            return error(ErrorCode.USER_NOT_FOUND, 404)
        parser = reqparse.RequestParser()
        parser.add_argument(
            "type_name", type=str, choices=["wish", "do", "collect"], location="args"
        )
        parser.add_argument("page", default=1, type=inputs.positive, location="args")
        parser.add_argument(
            "per_page", default=20, type=inputs.positive, location="args"
        )
        args = parser.parse_args()
        if args.type_name:
            if args.type_name == "wish":
                rating_paginate = this_user.ratings.filter(
                    Rating.category == RatingType.WISH
                ).paginate(args.page, args.per_page)
            elif args.type_name == "do":
                rating_paginate = this_user.ratings.filter(
                    Rating.category == RatingType.DO
                ).paginate(args.page, args.per_page)
            elif args.type_name == "collect":
                rating_paginate = this_user.ratings.filter(
                    Rating.category == RatingType.COLLECT
                ).paginate(args.page, args.per_page)
            p = get_item_pagination(rating_paginate, "api.UserMovie", username=username)
            return ok(
                "ok",
                data=marshal(
                    p, get_pagination_resource_fields(rating_with_movie_resource_fields)
                ),
            )
        else:
            wish_rating_paginate = this_user.ratings.filter(
                Rating.category == RatingType.WISH
            ).paginate(args.page, args.per_page)
            do_rating_paginate = this_user.ratings.filter(
                Rating.category == RatingType.DO
            ).paginate(args.page, args.per_page)
            collect_rating_paginate = this_user.ratings.filter(
                Rating.category == RatingType.COLLECT
            ).paginate(args.page, args.per_page)
            wish_p = get_item_pagination(
                wish_rating_paginate, "api.UserMovie", username=username
            )
            do_p = get_item_pagination(
                do_rating_paginate, "api.UserMovie", username=username
            )
            collect_p = get_item_pagination(
                collect_rating_paginate, "api.UserMovie", username=username
            )
            data = {
                "wish_movies": marshal(
                    wish_p,
                    get_pagination_resource_fields(rating_with_movie_resource_fields),
                ),
                "do_movies": marshal(
                    do_p,
                    get_pagination_resource_fields(rating_with_movie_resource_fields),
                ),
                "collect_movies": marshal(
                    collect_p,
                    get_pagination_resource_fields(rating_with_movie_resource_fields),
                ),
            }
            return ok("ok", data=data)


class ChoiceMovie(Resource):
    @auth.login_required
    @cache.cached(60, query_string=True)
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument(
            "subtype",
            default=None,
            type=str,
            choices=["tv", "movie", ""],
            location="args",
        )
        parser.add_argument("genre_name", default=None, type=str, location="args")
        parser.add_argument("country_name", default=None, type=str, location="args")
        parser.add_argument("year", default=None, type=str, location="args")
        parser.add_argument("page", default=1, type=inputs.positive, location="args")
        parser.add_argument(
            "per_page", default=20, type=inputs.positive, location="args"
        )
        args = parser.parse_args()
        query = MovieModel.query
        if args.genre_name:
            genre = Genre.query.filter_by(genre_name=args.genre_name).first()
            if genre:
                query = query.filter(MovieModel.genres.contains(genre))
        if args.country_name:
            country = Country.query.filter_by(country_name=args.country_name).first()
            if country:
                query = query.filter(MovieModel.countries.contains(country))
        if args.subtype:
            query = query.filter_by(subtype=args.subtype)
        if args.year:
            query = query.filter_by(year=args.year)
        score_stmt = (
            sql_db.session.query(
                Rating.movie_id.label("movie_id"),
                func.avg(Rating.score).label("avg_score"),
            )
            .filter(Rating.category == RatingType.COLLECT)
            .group_by(Rating.movie_id)
            .order_by(desc("avg_score"))
            .subquery()
        )
        movies = query.subquery()
        pagination = (
            sql_db.session.query(MovieModel)
            .outerjoin(score_stmt, MovieModel.id == score_stmt.c.movie_id)
            .filter(MovieModel.id == movies.c.id)
            .order_by(score_stmt.c.avg_score.desc())
            .paginate(args.page, args.per_page)
        )
        p = get_item_pagination(
            pagination,
            "api.ChoiceMovie",
            subtype=args.subtype,
            genre_hash_id=args.genre_name,
            country_hash_id=args.country_name,
            year=args.year,
        )
        return ok(
            "ok",
            data=marshal(
                p, get_pagination_resource_fields(movie_summary_resource_fields)
            ),
        )


class Movie(Resource):
    @auth.login_required
    def get(self, movie_hash_id):
        movie = MovieModel.query.get(decode_str_to_id(movie_hash_id))
        if not movie:
            return error(ErrorCode.MOVIE_NOT_FOUND, 404)
        return ok("ok", data=marshal(movie, movie_resource_fields))

    @auth.login_required
    @permission_required("DELETE_MOVIE")
    def delete(self, movie_hash_id):
        movie = MovieModel.query.get(decode_str_to_id(movie_hash_id))
        if not movie:
            return error(ErrorCode.MOVIE_NOT_FOUND, 404)
        sql_db.session.delete(movie)
        sql_db.session.commit()
        return ok("Deleted This Movie Successfully!")


class MovieUserRating(Resource):
    @auth.login_required
    def post(self, movie_hash_id):
        parser = reqparse.RequestParser()
        parser.add_argument(
            "interest",
            type=int,
            choices=[RatingType.COLLECT, RatingType.WISH, RatingType.DO],
            required=True,
            location="form",
        )
        parser.add_argument(
            "score",
            type=inputs.positive,
            choices=[i for i in range(0, 11)],
            default=0,
            location="form",
        )
        parser.add_argument("tags", type=inputs.regex("^.{0,512}$"), location="form")
        parser.add_argument("comment", type=inputs.regex("^.{0,128}$"), location="form")
        args = parser.parse_args()
        this_movie = MovieModel.query.get(decode_str_to_id(movie_hash_id))
        this_user = g.current_user
        if not this_movie:
            return error(ErrorCode.MOVIE_NOT_FOUND, 404)
        f = False
        if args.interest == RatingType.WISH:
            f = this_user.wish_movie(
                this_movie, comment=args.comment, tags_name=args.tags.split(" ")
            )
        if args.interest == RatingType.DO:
            f = this_user.do_movie(
                this_movie,
                score=args.score,
                comment=args.comment,
                tags_name=args.tags.split(" "),
            )
        if args.interest == RatingType.COLLECT:
            f = this_user.collect_movie(
                this_movie,
                score=args.score,
                comment=args.comment,
                tags_name=args.tags.split(" "),
            )
        if f:
            print(1)
            sql_db.session.commit()
            return ok("Rating This Movie Successfully")
        return error(ErrorCode.RATING_ALREADY_EXISTS, 403)

    @auth.login_required
    def delete(self, movie_hash_id):
        this_movie = MovieModel.query.get(decode_str_to_id(movie_hash_id))
        this_user = g.current_user
        if not this_movie:
            return error(ErrorCode.MOVIE_NOT_FOUND, 404)
        this_user.delete_rating_on(this_movie)
        sql_db.session.commit()
        return ok("Deleted This Rating Successfully!")

    @auth.login_required
    def get(self, movie_hash_id):
        this_movie = MovieModel.query.get(decode_str_to_id(movie_hash_id))
        if not this_movie:
            return error(ErrorCode.MOVIE_NOT_FOUND, 404)
        parser = reqparse.RequestParser()
        parser.add_argument("category", choices=["wish", "do", "collect"])
        parser.add_argument(
            "sort", default="new", choices=["hot", "new"], type=str, location="args"
        )
        parser.add_argument("page", default=1, type=inputs.positive, location="args")
        parser.add_argument(
            "per_page", default=20, type=inputs.positive, location="args"
        )
        args = parser.parse_args()
        if not args.category:
            if args.sort == "new":
                pagination = this_movie.ratings.order_by(
                    Rating.created_at.desc()
                ).paginate(args.page, args.per_page)
            else:
                s = (
                    sql_db.session.query(
                        rating_likes.c.rating_id, func.count("*").label("like_count")
                    )
                    .group_by(rating_likes.c.rating_id)
                    .subquery()
                )
                m = this_movie.ratings.subquery()
                pagination = (
                    sql_db.session.query(Rating)
                    .outerjoin(s, Rating.id == s.c.rating_id)
                    .filter(Rating.id == m.c.id)
                    .order_by(s.c.like_count.desc())
                    .paginate(args.page, args.per_page)
                )
            p = get_item_pagination(
                pagination, "api.MovieUserRating", movie_hash_id=movie_hash_id
            )
            return ok(
                "ok",
                data=marshal(p, get_pagination_resource_fields(rating_resource_fields)),
            )
        cate = None
        if args.category == "wish":
            cate = RatingType.WISH
        elif args.category == "do":
            cate = RatingType.DO
        elif args.category == "collect":
            cate = RatingType.COLLECT
        if args.sort == "new":
            pagination = (
                this_movie.ratings.filter(Rating.category == cate)
                .order_by(Rating.created_at.desc())
                .paginate(args.page, args.per_page)
            )
        else:
            s = (
                sql_db.session.query(
                    rating_likes.c.rating_id, func.count("*").label("like_count")
                )
                .group_by(rating_likes.c.rating_id)
                .subquery()
            )
            m = this_movie.ratings.subquery()
            pagination = (
                sql_db.session.query(Rating)
                .outerjoin(s, Rating.id == s.c.rating_id)
                .filter(Rating.id == m.c.id)
                .filter(Rating.category == cate)
                .order_by(s.c.like_count.desc())
                .paginate(args.page, args.per_page)
            )
        p = get_item_pagination(
            pagination, "api.MovieUserRating", movie_hash_id=movie_hash_id
        )
        return ok(
            "ok",
            data=marshal(p, get_pagination_resource_fields(rating_resource_fields)),
        )


class FollowFeed(Resource):
    @auth.login_required
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("page", default=1, type=inputs.positive, location="args")
        parser.add_argument(
            "per_page", default=20, type=inputs.positive, location="args"
        )
        args = parser.parse_args()
        s = g.current_user.followed.subquery()
        pagination = (
            sql_db.session.query(Rating)
            .join(s, Rating.user_id == s.c.id)
            .order_by(Rating.created_at.desc())
            .paginate(args.page, args.per_page)
        )

        p = get_item_pagination(pagination, "api.FollowFeed")
        return ok(
            "ok",
            data=marshal(
                p, get_pagination_resource_fields(rating_with_movie_resource_fields)
            ),
        )


class Movies(Resource):
    @auth.login_required
    @permission_required("UPLOAD")
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument(
            "douban_id", type=inputs.regex("^[0-9]{0,10}$"), location="form"
        )
        parser.add_argument("title", type=str, required=True, location="form")
        parser.add_argument(
            "subtype", choices=["movie", "tv"], required=True, location="form"
        )
        parser.add_argument("year", type=int, required=True, location="form")
        parser.add_argument("image", required=True, type=FileStorage, location="files")
        parser.add_argument("countries", required=True, type=str, location="form")
        parser.add_argument("genres_name", required=True, type=str, location="form")
        parser.add_argument("original_title", type=str, location="form")
        parser.add_argument("summary", required=True, type=str, location="form")
        parser.add_argument("aka", type=str, location="form")
        parser.add_argument(
            "cinema_status",
            default=MovieCinemaStatus.FINISHED,
            type=int,
            choices=[
                MovieCinemaStatus.FINISHED,
                MovieCinemaStatus.COMING,
                MovieCinemaStatus.SHOWING,
            ],
        )
        parser.add_argument("director_ids", required=True, type=str, location="form")
        parser.add_argument("celebrities_ids", required=True, type=str, location="form")
        parser.add_argument("seasons_count", type=int, location="form")
        parser.add_argument("episodes_count", type=int, location="form")
        parser.add_argument("current_season", type=int, location="form")
        args = parser.parse_args()
        if args.subtype == "movie":
            args.seasons_count = args.episodes_count = args.current_season = None
        if args.aka:
            args.aka = args.aka.split("/")
        if args.genres_name:
            args.genres_name = args.genres_name.split(" ")
        if args.countries:
            args.countries = args.countries.split(" ")
        directors_obj = Celebrity.query.filter(
            Celebrity.id.in_(
                [
                    decode_str_to_id(hash_id)
                    for hash_id in args.director_ids.split(" ")
                    if args.director_ids
                ]
            )
        )
        celebrities_obj = Celebrity.query.filter(
            Celebrity.id.in_(
                [
                    decode_str_to_id(hash_id)
                    for hash_id in args.celebrities_ids.split(" ")
                    if args.celebrities_ids
                ]
            )
        )
        image = Image.create_one(args.image)
        movie = MovieModel.create_one(
            title=args.title,
            subtype=args.subtype,
            image=image,
            year=args.year,
            douban_id=args.douban_id,
            original_title=args.original_title,
            seasons_count=args.seasons_count,
            episodes_count=args.episodes_count,
            current_season=args.current_season,
            summary=args.summary,
            cinema_status=args.cinema_status,
            aka_list=args.aka,
            genres_name=args.genres_name,
            countries_name=args.countries,
            directors_obj=directors_obj,
            celebrities_obj=celebrities_obj,
        )
        if movie:
            sql_db.session.add(movie)
            sql_db.session.commit()
            return ok("Movie Created!", http_status_code=201)
        else:
            return error(ErrorCode.MOVIE_ALREADY_EXISTS, 403)
