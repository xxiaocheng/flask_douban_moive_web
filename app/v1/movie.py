import math
import os

from flask import abort, current_app, g, redirect, url_for
from flask_restful import Resource, reqparse
from mongoengine.errors import ValidationError
from mongoengine.queryset.visitor import Q
from werkzeug.datastructures import FileStorage

from app.extensions import api
from app.helpers.redis_utils import *
from app.helpers.utils import query_by_id_list, rename_image
from app.models import Celebrity, Cinema, Follow, Movie, Rating, Tag, User

from .auth import auth, permission_required
from .schemas import (
    items_schema,
    movie_schema,
    movie_summary_schema,
    rating_schema,
    rating_schema_on_user,
)


class CinemaMovie(Resource):
    """正在上映和即将上映的电影
    """

    # @cache.cached(timeout=60*60*24*3,query_string=True)

    def get(self, coming_or_showing):
        parser = reqparse.RequestParser()
        parser.add_argument("page", default=1, type=int, location="args")
        parser.add_argument("per_page", default=20, type=int, location="args")
        args = parser.parse_args()

        if coming_or_showing == "coming":
            pagination = Cinema.objects(cate=1).paginate(
                page=args["page"], per_page=args["per_page"]
            )

        elif coming_or_showing == "showing":
            pagination = Cinema.objects(cate=0).paginate(
                page=args["page"], per_page=args["per_page"]
            )

        items = [movie_summary_schema(cinema.movie) for cinema in pagination.items]

        prev = None
        if pagination.has_prev:
            prev = url_for(
                ".cinemamovie",
                coming_or_showing=coming_or_showing,
                page=args["page"] - 1,
                per_page=args["per_page"],
                _external=True,
            )
        next = None
        if pagination.has_next:
            next = url_for(
                ".cinemamovie",
                coming_or_showing=coming_or_showing,
                page=args["page"] + 1,
                per_page=args["per_page"],
                _external=True,
            )
        first = url_for(
            ".cinemamovie",
            coming_or_showing=coming_or_showing,
            page=1,
            perpage=args["per_page"],
            _external=True,
        )
        last = url_for(
            ".cinemamovie",
            coming_or_showing=coming_or_showing,
            page=pagination.pages,
            perpage=args["per_page"],
            _external=True,
        )
        return items_schema(
            items, prev, next, first, last, pagination.total, pagination.pages
        )


api.add_resource(CinemaMovie, "/movie/cinema/<any(coming,showing):coming_or_showing>")


class Recommend(Resource):
    """
    获取为用户推荐的电影
    暂时未实现
    """

    @auth.login_required
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("page", default=1, type=int, location="args")
        parser.add_argument("per_page", default=20, type=int, location="args")
        args = parser.parse_args()
        pagination = Movie.objects().paginate(page=args.page, per_page=args.per_page)
        items = [movie_summary_schema(movie) for movie in pagination.items]
        prev = None
        if pagination.has_prev:
            prev = url_for(
                ".recommend",
                page=args["page"] - 1,
                per_page=args["per_page"],
                _external=True,
            )
        next = None
        if pagination.has_next:
            next = url_for(
                ".recommend",
                page=args["page"] + 1,
                per_page=args["per_page"],
                _external=True,
            )
        first = url_for(".recommend", page=1, perpage=args["per_page"], _external=True)
        last = url_for(
            ".recommend",
            page=pagination.pages,
            perpage=args["per_page"],
            _external=True,
        )
        return items_schema(
            items, prev, next, first, last, pagination.total, pagination.pages
        )


api.add_resource(Recommend, "/movie/recommend")


class Leaderboard(Resource):
    def get(self, time_range):
        if time_range not in ["week", "month"]:
            abort(404)
        parser = reqparse.RequestParser()
        parser.add_argument("page", default=1, type=int, location="args")
        parser.add_argument("per_page", default=20, type=int, location="args")
        args = parser.parse_args()

        if args["page"] <= 0:
            args["page"] = 1
        today = datetime.date.today()
        if time_range == "week":
            keys = [
                "rating:" + (today - datetime.timedelta(days=days)).strftime("%y%m%d")
                for days in range(0, 7)
            ]
        if time_range == "month":
            keys = [
                "rating:" + (today - datetime.timedelta(days=days)).strftime("%y%m%d")
                for days in range(0, 30)
            ]

        id_items, id_total = rank_redis_zset_paginate(
            keys=keys,
            time_range=time_range,
            page=args["page"],
            per_page=args["per_page"],
        )
        movie_objects_items = query_by_id_list(document=Movie, id_list=id_items)
        prev = None
        next = None
        if args["page"] == 1:
            prev = None
        else:
            prev = url_for(
                ".leaderboard",
                time_range=time_range,
                page=args["page"] - 1,
                per_page=args["per_page"],
                _external=True,
            )
        if args["page"] * args["per_page"] >= id_total:
            next = None
        else:
            next = url_for(
                ".leaderboard",
                time_range=time_range,
                page=args["page"] + 1,
                per_page=args["per_page"],
                _external=True,
            )
        first = url_for(
            ".leaderboard",
            time_range=time_range,
            page=1,
            per_page=args["per_page"],
            _external=True,
        )

        pages = math.ceil(id_total / args["per_page"])
        if pages == 0:
            last = url_for(
                ".leaderboard",
                time_range=time_range,
                page=1,
                per_page=args["per_page"],
                _external=True,
            )
        else:
            last = url_for(
                ".leaderboard",
                time_range=time_range,
                page=pages,
                per_page=args["per_page"],
                _external=True,
            )

        return items_schema(
            [
                movie_summary_schema(movie)
                for movie in movie_objects_items
                if movie_objects_items and movie
            ],
            prev,
            next,
            first,
            last,
            id_total,
            pages,
        )


api.add_resource(Leaderboard, "/movie/leaderboard/<time_range>")


class TypeRank(Resource):
    """根据标签对电影进行排序
    """

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("type_name", type=str, location="args")
        parser.add_argument("page", default=1, type=int, location="args")
        parser.add_argument("per_page", default=20, type=int, location="args")
        args = parser.parse_args()
        # 仅查询系统内提供的标签
        tag_obj = Tag.objects(name=args["type_name"], cate=1).first()
        if not tag_obj:
            return {"message": "type not found"}, 404

        # 按照评分降序查询
        pagination = (
            Movie.objects(genres__in=[tag_obj], is_deleted=False)
            .order_by("-score")
            .paginate(page=args["page"], per_page=args["per_page"])
        )

        items = [movie_summary_schema(movie) for movie in pagination.items]

        prev = None
        if pagination.has_prev:
            prev = url_for(
                ".typerank",
                type_name=args["type_name"],
                page=args["page"] - 1,
                per_page=args["per_page"],
                _external=True,
            )

        next = None
        if pagination.has_next:
            next = url_for(
                ".typerank",
                type_name=args["type_name"],
                page=args["page"] + 1,
                per_page=args["per_page"],
                _external=True,
            )

        first = url_for(
            ".typerank",
            type_name=args["type_name"],
            page=1,
            perpage=args["per_page"],
            _external=True,
        )
        last = url_for(
            ".typerank",
            type_name=args["type_name"],
            page=pagination.pages,
            perpage=args["per_page"],
            _external=True,
        )
        return items_schema(
            items, prev, next, first, last, pagination.total, pagination.pages
        )


api.add_resource(TypeRank, "/movie/typerank")


class UserMovie(Resource):
    @auth.login_required
    def get(self, username):
        user = User.objects(username=username, is_deleted=False).first()
        if not user:
            return {"message": "user not found"}, 404

        parser = reqparse.RequestParser()
        parser.add_argument(
            "type_name", type=str, choices=["wish", "do", "collect"], location="args"
        )
        parser.add_argument("page", default=1, type=int, location="args")
        parser.add_argument("per_page", default=20, type=int, location="args")
        args = parser.parse_args()

        if not args["type_name"]:
            wish_movies_items = [
                movie_summary_schema(rating.movie)
                for rating in Rating.objects(user=user, is_deleted=False, category=0)[
                    0:20
                ]
            ]
            do_movies_items = [
                movie_summary_schema(rating.movie)
                for rating in Rating.objects(user=user, is_deleted=False, category=1)[
                    0:20
                ]
            ]
            collect_movies_items = [
                movie_summary_schema(rating.movie)
                for rating in Rating.objects(user=user, is_deleted=False, category=2)[
                    0:20
                ]
            ]

            return {
                "username": user.username,
                "wish_count": user.wish_count,
                "do_count": user.do_count,
                "collect_count": user.collect_count,
                "wish_movies_items": wish_movies_items,
                "do_movies_items": do_movies_items,
                "collect_movies_items": collect_movies_items,
            }
        if args["type_name"] == "wish":
            pagination = (
                Rating.objects(user=user, category=0, is_deleted=False)
                .order_by("-rating_time")
                .paginate(page=args["page"], per_page=args["per_page"])
            )

        if args["type_name"] == "do":
            pagination = (
                Rating.objects(user=user, category=1, is_deleted=False)
                .order_by("-rating_time")
                .paginate(page=args["page"], per_page=args["per_page"])
            )

        if args["type_name"] == "collect":
            pagination = (
                Rating.objects(user=user, category=2, is_deleted=False)
                .order_by("-rating_time")
                .paginate(page=args["page"], per_page=args["per_page"])
            )

        items = [rating_schema_on_user(rating) for rating in pagination.items]

        prev = None
        if pagination.has_prev:
            prev = url_for(
                ".usermovie",
                username=username,
                type_name=args["type_name"],
                page=args["page"] - 1,
                per_page=args["per_page"],
                _external=True,
            )

        next = None
        if pagination.has_next:
            next = url_for(
                ".usermovie",
                username=username,
                type_name=args["type_name"],
                page=args["page"] + 1,
                per_page=args["per_page"],
                _external=True,
            )

        first = url_for(
            ".usermovie",
            username=username,
            type_name=args["type_name"],
            page=1,
            perpage=args["per_page"],
            _external=True,
        )
        last = url_for(
            ".usermovie",
            username=username,
            type_name=args["type_name"],
            page=pagination.pages,
            perpage=args["per_page"],
            _external=True,
        )
        return items_schema(
            items, prev, next, first, last, pagination.total, pagination.pages
        )


api.add_resource(UserMovie, "/user/<username>/movie")


class MineMovie(Resource):
    @auth.login_required
    def get(self):
        user = g.current_user
        parser = reqparse.RequestParser()
        parser.add_argument(
            "type_name", type=str, choices=["wish", "do", "collect"], location="args"
        )
        parser.add_argument("page", default=1, type=int, location="args")
        parser.add_argument("per_page", default=20, type=int, location="args")
        args = parser.parse_args()
        return redirect(
            url_for(
                ".usermovie",
                username=user.username,
                type_name=args["type_name"],
                page=args["page"],
                perpage=args["per_page"],
            )
        )


api.add_resource(MineMovie, "/movie/mine")


class ChoiceMovie(Resource):
    """
    根据时间, 国家,类型, 电影或电视剧 进行选择
    """

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument(
            "subtype",
            default=None,
            type=str,
            choices=["tv", "movie", ""],
            location="args",
        )
        parser.add_argument("type_name", default=None, type=str, location="args")
        parser.add_argument("country", default=None, type=str, location="args")
        parser.add_argument("year", default=None, type=str, location="args")

        parser.add_argument("page", default=1, type=int, location="args")
        parser.add_argument("per_page", default=20, type=int, location="args")
        parser.add_argument(
            "oredr", default="score", choices=["score", "collect_count"]
        )
        args = parser.parse_args()

        tag_obj = None
        if args["type_name"]:
            tag_obj = Tag.objects(name=args["type_name"], cate=1).first()
            if not tag_obj:
                return {"message": "no movie found"}, 404
        condition_list = []
        if tag_obj:
            condition_list.append(Q(genres__in=[tag_obj]))
        if args["subtype"]:
            condition_list.append(Q(subtype=args["subtype"]))
        if args["country"]:
            condition_list.append(Q(countries__in=[args["country"]]))
        if args["year"]:
            condition_list.append(Q(year=args["year"]))
        # 组合查询条件,将查询条件不为空的放在查询条件列表中以供组合查询
        condition = None
        for i in range(len(condition_list)):
            if condition:
                condition = condition & condition_list[i]
            else:
                condition = condition_list[i]
        if condition:
            pagination = (
                Movie.objects(condition & Q(is_deleted=False))
                .order_by("-score")
                .paginate(page=args["page"], per_page=args["per_page"])
            )
        else:
            pagination = (
                Movie.objects(is_deleted=False)
                .order_by("-score")
                .paginate(page=args["page"], per_page=args["per_page"])
            )

        items = [movie_summary_schema(movie) for movie in pagination.items]

        prev = None
        if pagination.has_prev:
            prev = url_for(
                ".choicemovie",
                type_name=args["type_name"],
                page=args["page"] - 1,
                per_page=args["per_page"],
                _external=True,
            )

        next = None
        if pagination.has_next:
            next = url_for(
                ".choicemovie",
                type_name=args["type_name"],
                page=args["page"] + 1,
                per_page=args["per_page"],
                _external=True,
            )

        first = url_for(
            ".choicemovie",
            type_name=args["type_name"],
            page=1,
            perpage=args["per_page"],
            _external=True,
        )
        last = url_for(
            ".choicemovie",
            type_name=args["type_name"],
            page=pagination.pages,
            perpage=args["per_page"],
            _external=True,
        )
        return items_schema(
            items, prev, next, first, last, pagination.total, pagination.pages
        )


api.add_resource(ChoiceMovie, "/movie/choices")


class MovieInfo(Resource):

    # @cache.cached(timeout=60,query_string=True)

    @auth.login_required
    def get(self, movieid):
        # 返回此电影详细信息
        try:
            movie = Movie.objects(id=movieid, is_deleted=False).first()
        except ValidationError:
            return {"message": "movie not found"}, 404
        if movie:
            return movie_schema(movie)
        else:
            return {"message": "movie not found"}, 404

    @auth.login_required
    @permission_required("DELETE_MOVIE")
    def delete(self, movieid):
        try:
            movie = Movie.objects(id=movieid, is_deleted=False).first()
        except ValidationError:
            return {"message": "illegal movieid"}, 402
        if movie:
            movie.delete_self()
            return {"message": "delete this movie successfuly "}
        return {"message": "movie not exist"}


api.add_resource(MovieInfo, "/movie/<movieid>")


class UserInterestMovie(Resource):
    # 用户对电影评价
    @auth.login_required
    def post(self, movieid):
        user = g.current_user
        parser = reqparse.RequestParser()
        parser.add_argument(
            "interest",
            type=str,
            choices=["wish", "do", "collect"],
            required=True,
            location="form",
        )
        parser.add_argument("score", type=int, default=0, location="form")
        parser.add_argument("tags", type=str, location="form")
        parser.add_argument("comment", type=str, location="form")
        args = parser.parse_args()
        try:
            movie = Movie.objects(id=movieid, is_deleted=False).first()
        except ValidationError:
            return {"message": "movie not found"}, 404

        if not movie:
            return {"message": "movie not found"}, 404

        if len(args.comment) > 100:
            return {"message": "评论长度不能超过100个字符!"}, 403
        if args.score > 10 or args.score < 0:
            return {"message": "评分必须在 1-10 之间!"}, 403
        if len(args.tags.split(" ")) > 10:
            return {"message": "最多可以添加10个标签!"}, 403

        if args["interest"] == "wish":
            user.wish_movie(
                movie, score=args["score"], comment=args["comment"], tags=args["tags"]
            )
        if args["interest"] == "do":
            user.do_movie(
                movie, score=args["score"], comment=args["comment"], tags=args["tags"]
            )
        if args["interest"] == "collect":
            user.collect_movie(
                movie, score=args["score"], comment=args["comment"], tags=args["tags"]
            )

        # 无论是否评论成功,都返回成功,不作区分
        return {"message": "succeed"}


api.add_resource(UserInterestMovie, "/movie/<movieid>/interest")


class MovieRating(Resource):
    """评价过这部电影的人.
    """

    @auth.login_required
    def get(self, movieid, category):
        parser = reqparse.RequestParser()
        parser.add_argument("sort", choices=["hot", "new"], type=str, location="args")
        parser.add_argument("page", default=1, type=int, location="args")
        parser.add_argument("per_page", default=20, type=int, location="args")
        args = parser.parse_args()
        try:
            # 当查询的movie ID 不符合规范触发
            movie = Movie.objects(id=movieid, is_deleted=False).first()
        except ValidationError:
            return {"message": "movie not found"}, 404

        if not movie or category not in ["wish", "do", "collect", "all"]:
            return {"message": "rating not found"}, 404
        if category == "all":
            pagination = (
                Rating.objects(movie=movie, is_deleted=False)
                .order_by("-like_count" if args["sort"] == "hot" else "-rating_time")
                .paginate(page=args["page"], per_page=args["per_page"])
            )
        else:
            if category == "wish":
                cate = 0
            if category == "do":
                cate = 1
            if category == "collect":
                cate = 2

            pagination = (
                Rating.objects(movie=movie, is_deleted=False, category=cate)
                .order_by("-like_count" if args["sort"] == "hot" else "-rating_time")
                .paginate(page=args["page"], per_page=args["per_page"])
            )
        # fenye  tiquhanshu chonggou
        items = [rating_schema(rating) for rating in pagination.items]

        prev = None
        if pagination.has_prev:
            prev = url_for(
                ".movierating",
                movieid=movieid,
                category=category,
                sort=args["sort"],
                page=args["page"] - 1,
                per_page=args["per_page"],
                _external=True,
            )

        next = None
        if pagination.has_next:
            next = url_for(
                ".movierating",
                movieid=movieid,
                category=category,
                sort=args["sort"],
                page=args["page"] + 1,
                per_page=args["per_page"],
                _external=True,
            )

        first = url_for(
            ".movierating",
            movieid=movieid,
            category=category,
            sort=args["sort"],
            page=1,
            perpage=args["per_page"],
            _external=True,
        )
        last = url_for(
            ".movierating",
            movieid=movieid,
            category=category,
            sort=args["sort"],
            page=pagination.pages,
            perpage=args["per_page"],
            _external=True,
        )
        return items_schema(
            items, prev, next, first, last, pagination.total, pagination.pages
        )


api.add_resource(MovieRating, "/movie/<movieid>/rating/<category>")


class FollowFeed(Resource):
    """首页显示用户关注的用户的信息
    """

    @auth.login_required
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("page", default=1, type=int, location="args")
        parser.add_argument("per_page", default=20, type=int, location="args")
        args = parser.parse_args()

        current_user = g.current_user

        following = Follow.objects(follower=current_user, is_deleted=False)

        following_user = [follow.followed for follow in following]

        pagination = (
            Rating.objects(user__in=following_user, is_deleted=False)
            .order_by("-rating_time")
            .paginate(page=args.page, per_page=args.per_page)
        )

        items = [rating_schema_on_user(rating) for rating in pagination.items]

        prev = None
        if pagination.has_prev:
            prev = url_for(
                ".followfeed",
                page=args["page"] - 1,
                per_page=args["per_page"],
                _external=True,
            )

        next = None
        if pagination.has_next:
            next = url_for(
                ".followfeed",
                page=args["page"] + 1,
                per_page=args["per_page"],
                _external=True,
            )

        first = url_for(
            ".followfeed", page=1, per_page=args["per_page"], _external=True
        )
        last = url_for(
            ".followfeed",
            page=pagination.pages,
            per_page=args["per_page"],
            _external=True,
        )
        return items_schema(
            items, prev, next, first, last, pagination.total, pagination.pages
        )


api.add_resource(FollowFeed, "/feed")


class UploadMovie(Resource):
    @auth.login_required
    @permission_required("UPLOAD")
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("douban_id", default="", type=str, location="form")
        parser.add_argument("title", type=str, required=True, location="form")
        parser.add_argument(
            "subtype", choices=["movie", "tv"], required=True, location="form"
        )
        parser.add_argument("year", type=int, required=True, location="form")
        parser.add_argument("image", required=True, type=FileStorage, location="files")
        parser.add_argument("countries", required=True, type=str, location="form")
        parser.add_argument("genres", required=True, type=str, location="form")
        parser.add_argument("original_title", default="", type=str, location="form")
        parser.add_argument("summary", required=True, type=str, location="form")
        parser.add_argument("aka", default="", type=str, location="form")
        parser.add_argument("directors", required=True, type=str, location="form")
        parser.add_argument("casts", required=True, type=str, location="form")
        parser.add_argument("seasons_count", type=int, location="form")
        parser.add_argument("episodes_count", type=int, location="form")
        parser.add_argument("current_season", type=int, location="form")
        args = parser.parse_args()

        # parse image
        image_ext = os.path.splitext(args["image"].filename)[1]
        if image_ext not in current_app.config["UPLOAD_IMAGE_EXT"]:
            return {"message": "file type error", "type": image_ext}, 403
        image_filename = rename_image(args["image"].filename)

        with open(
            os.path.join(current_app.config["MOVIE_IMAGE_UPLOAD_PATH"], image_filename),
            "wb",
        ) as f:
            args["image"].save(f)
        # parse country
        countries = args.countries.split(" ")

        # parse tags
        genres_text = args.genres.split(" ")
        genres = []
        for tag_name in genres_text:
            if tag_name != "":
                tag = Tag.objects(name=tag_name, cate=1).first()
                if tag:
                    genres.append(tag)
                else:
                    Tag(name=tag_name, cate=1).save()
                    tag = Tag.objects(name=tag_name, cate=1).first()
                    genres.append(tag)

        # parse aka
        if args.aka:
            aka = args.aka.split(" ")
        else:
            aka = []

        # parse directors
        try:
            directors = [
                Celebrity.objects(id=id, is_deleted=False).first()
                for id in args.directors.split(" ")
                if args.genres and id != ""
            ]
        except ValidationError:
            directors = []
            return {"message": "导演信息不正确"}, 400

        # parse casts:
        try:
            casts = [
                Celebrity.objects(id=id, is_deleted=False).first()
                for id in args.casts.split(" ")
                if args.casts and id != ""
            ]
        except ValidationError:
            casts = []
            return {"message": "演员信息不正确"}, 400

        if args.subtype == "tv":
            Movie(
                douban_id=args.douban_id,
                title=args.title,
                subtype=args.subtype,
                year=args.year,
                image=image_filename,
                countries=countries,
                genres=genres,
                original_title=args.original_title,
                summary=args.summary,
                aka=aka,
                directors=directors,
                casts=casts,
                seasons_count=args.seasons_count,
                episodes_count=args.episodes_count,
                current_season=args.current_season,
            ).save()
        else:
            Movie(
                douban_id=args.douban_id,
                title=args.title,
                subtype=args.subtype,
                year=args.year,
                image=image_filename,
                countries=countries,
                genres=genres,
                original_title=args.original_title,
                summary=args.summary,
                aka=aka,
                directors=directors,
                casts=casts,
            ).save()

        return {"message": "添加影视信息成功"}


api.add_resource(UploadMovie, "/movie")
