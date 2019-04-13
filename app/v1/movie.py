import datetime
import json
import math

import requests
from flask import abort, g, redirect, url_for
from flask_restful import Resource, reqparse
from mongoengine.errors import ValidationError
from mongoengine.queryset.visitor import Q

from app.extensions import api, cache
from app.helpers.redis_utils import *
from app.helpers.utils import query_by_id_list
from app.models import Movie, Rating, Tag, User,Cinema

from .auth import auth, email_confirm_required, permission_required
from .schemas import (items_schema, movie_schema, movie_summary_schema,
                      rating_schema)


class CinemaMovie(Resource):
    """正在上映和即将上映的电影
    """
    # @cache.cached(timeout=60*60*24*3,query_string=True)
    def get(self, coming_or_showing):
        parser = reqparse.RequestParser()
        parser.add_argument('page', default=1, type=int, location='args')
        parser.add_argument('per_page', default=20, type=int, location='args')
        args = parser.parse_args()

        if coming_or_showing == 'coming':
            pagination=Cinema.objects(cate=1).paginate(page=args['page'], per_page=args['per_page'])

        elif coming_or_showing == 'showing':
            pagination=Cinema.objects(cate=0).paginate(page=args['page'], per_page=args['per_page'])
        
        items = [movie_summary_schema(cinema.movie) for cinema in pagination.items]

        prev = None
        if pagination.has_prev:
            prev = url_for(
                '.cinemamovie', coming_or_showing=coming_or_showing, page=args['page']-1, per_page=args['per_page'], _external=True)
        next = None
        if pagination.has_next:
            next = url_for(
                '.cinemamovie', coming_or_showing=coming_or_showing, page=args['page']+1, per_page=args['per_page'], _external=True)
        first = url_for(
            '.cinemamovie', coming_or_showing=coming_or_showing, page=1, perpage=args['per_page'], _external=True)
        last  = url_for(
            '.cinemamovie', coming_or_showing=coming_or_showing, page=pagination.pages, perpage=args['per_page'], _external=True)
        return items_schema(items, prev, next, first, last, pagination.total, pagination.pages)

api.add_resource(CinemaMovie, '/movie/cinema/<any(coming,showing):coming_or_showing>')


class Recommend(Resource):

    @auth.login_required
    def get(self):
        user = g.current_user
        pass
        # 只返回概述信息


api.add_resource(Recommend, '/movie/Recommend')


class Leaderboard(Resource):

    def get(self, time_range):
        if time_range not in ['week', 'month']:
            abort(404)
        parser = reqparse.RequestParser()
        parser.add_argument('page', default=1, type=int, location='args')
        parser.add_argument('per_page', default=20, type=int, location='args')
        args = parser.parse_args()

        if args['page'] <= 0:
            args['page'] = 1

        if time_range=='week':
            keys=['rating:'+(today-datetime.timedelta(days=days)).strftime('%y%m%d') for days in range(1,8)]
        if time_range=='month':
            keys=['rating:'+(today-datetime.timedelta(days=days)).strftime('%y%m%d') for days in range(1,31)]

        id_items = rank_redis_zset_paginate(
            keys=keys, page=args['page'], per_page=args['per_page'])
        movie_objects_items = query_by_id_list(
            document=Movie, id_list=id_items)

        total = len(movie_objects_items)
        prev = None
        next = None
        if args['page'] == 1:
            prev = None
        else:
            prev = url_for('.leaderboard', time_range=time_range,
                           page=args['page']-1, per_page=args['per_page'], _external=True)
        if args['page']*args['per_page'] > total:
            next = None
        else:
            next = url_for('.leaderboard', time_range=time_range,
                           page=args['page']+1, per_page=args['per_page'], _external=True)
        first = url_for('.leaderboard', time_range=time_range,
                        page=1, per_page=args['per_page'], _external=True)

        pages = math.ceil(total/args['per_page'])
        if pages == 0:
            last = url_for('.leaderboard', time_range=time_range,
                           page=1, per_page=args['per_page'], _external=True)
        else:
            last = url_for('.leaderboard', time_range=time_range,
                           page=pages, per_page=args['per_page'], _external=True)

        return items_schema([movie_summary_schema(movie) for movie in movie_objects_items if movie_objects_items], prev, next, first, last, total, pages)


api.add_resource(Leaderboard, '/movie/leaderboard/<time_range>')


class TypeRank(Resource):

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('type_name', type=str, location='args')
        parser.add_argument('page', default=1, type=int, location='args')
        parser.add_argument('per_page', default=20, type=int, location='args')
        args = parser.parse_args()
        # 仅查询系统内提供的标签
        tag_obj = Tag.objects(name=args['type_name'], cate=1).first()
        if not tag_obj:
            return{
                "message": 'no type found'
            }, 404

        # 按照评分降序查询
        pagination = Movie.objects(genres__in=[tag_obj], is_deleted=False).order_by('-score').paginate(
            page=args['page'], per_page=args['per_page'])

        items = [movie_summary_schema(movie) for movie in pagination.items]

        prev = None
        if pagination.has_prev:
            prev = url_for(
                '.typerank', type_name=args['type_name'], page=args['page']-1, per_page=args['per_page'], _external=True)

        next = None
        if pagination.has_next:
            next = url_for(
                '.typerank', type_name=args['type_name'], page=args['page']+1, per_page=args['per_page'], _external=True)

        first = url_for(
            '.typerank', type_name=args['type_name'], page=1, perpage=args['per_page'], _external=True)
        last  = url_for(
            '.typerank', type_name=args['type_name'], page=pagination.pages, perpage=args['per_page'], _external=True)
        return items_schema(items, prev, next, first, last, pagination.total, pagination.pages)


api.add_resource(TypeRank, '/movie/typerank')


class UserMovie(Resource):
    def get(self, username):
        user = User.objects(username=username, is_deleted=False).first()
        if not user:
            return{
                'message': 'user not found'
            }, 404

        parser = reqparse.RequestParser()
        parser.add_argument('type_name', type=str, choices=[
                            'wish', 'do', 'collect'], location='args')
        parser.add_argument('page', default=1, type=int, location='args')
        parser.add_argument('per_page', default=20, type=int, location='args')
        args = parser.parse_args()

        if not args['type_name']:
            wish_movies_items = [movie_summary_schema(rating.movie) for rating in Rating.objects(
                user=user, is_deleted=False, category=0)[0:20]]
            do_movies_items = [movie_summary_schema(rating.movie) for rating in Rating.objects(
                user=user, is_deleted=False, category=1)[0:20]]
            collect_movies_items = [movie_summary_schema(rating.movie) for rating in Rating.objects(
                user=user, is_deleted=False, category=2)[0:20]]

            return{
                'username': user.username,
                'wish_count': user.wish_count,
                'do_count': user.do_count,
                'collect_count': user.collect_count,
                'wish_movies_items': wish_movies_items,
                'do_movies_items': do_movies_items,
                'collect_movies_items': collect_movies_items
            }
        if args['type_name'] == 'wish':
            pagination = Rating.objects(user=user, category=0, is_deleted=False).paginate(
                page=args['page'], per_page=args['per_page'])

        if args['type_name'] == 'do':
            pagination = Rating.objects(user=user, category=1, is_deleted=False).paginate(
                page=args['page'], per_page=args['per_page'])

        if args['type_name'] == 'collect':
            pagination = Rating.objects(user=user, category=2, is_deleted=False).paginate(
                page=args['page'], per_page=args['per_page'])

        items = [movie_summary_schema(rating.movie)
                 for rating in pagination.items]

        prev = None
        if pagination.has_prev:
            prev = url_for(
                '.usermovie', username=username, type_name=args['type_name'], page=args['page']-1, per_page=args['per_page'], _external=True)

        next = None
        if pagination.has_next:
            next = url_for(
                '.usermovie', username=username, type_name=args['type_name'], page=args['page']+1, per_page=args['per_page'], _external=True)

        first = url_for(
            '.usermovie', username=username, type_name=args['type_name'], page=1, perpage=args['per_page'], _external=True)
        last  = url_for(
            '.usermovie', username=username, type_name=args['type_name'], page=pagination.pages, perpage=args['per_page'], _external=True)
        return items_schema(items, prev, next, first, last, pagination.total, pagination.pages)


api.add_resource(UserMovie, '/movie/by/<username>')


class MineMovie(Resource):

    @auth.login_required
    def get(self):
        user = g.current_user
        parser = reqparse.RequestParser()
        parser.add_argument('type_name', type=str, choices=[
                            'wish', 'do', 'collect'], location='args')
        parser.add_argument('page', default=1, type=int, location='args')
        parser.add_argument('per_page', default=20, type=int, location='args')
        args = parser.parse_args()
        return redirect(url_for('.usermovie', username=user.username, type_name=args['type_name'], page=args['page'], perpage=args['per_page']))


api.add_resource(MineMovie, '/movie/mine')


class ChoiceMovie(Resource):

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('subtype', default=None, type=str, choices=[
                            'tv', 'movie'], location='args')
        parser.add_argument('type_name', default=None,
                            type=str, location='args')
        parser.add_argument('country', default=None, type=str, location='args')
        parser.add_argument('year', default=None, type=str, location='args')

        parser.add_argument('page', default=1, type=int, location='args')
        parser.add_argument('per_page', default=20, type=int, location='args')
        args = parser.parse_args()

        tag_obj = None
        if args['type_name']:
            tag_obj = Tag.objects(name=args['type_name'], cate=1).first()
            if not tag_obj:
                return{
                    "message": 'no movie found'
                }, 404
        condition_list = []
        if tag_obj:
            condition_list.append(Q(genres__in=[tag_obj]))
        if args['subtype']:
            condition_list.append(Q(subtype=args['subtype']))
        if args['country']:
            condition_list.append(Q(countries__in=[args['country']]))
        if args['year']:
            condition_list.append(Q(year=args['year']))
        # 组合查询条件,将查询条件不为空的放在查询条件列表中以供组合查询
        condition = None
        for i in range(len(condition_list)):
            if condition:
                condition = condition & condition_list[i]
            else:
                condition = condition_list[i]
        if condition:
            pagination = Movie.objects(condition & Q(is_deleted=False)).order_by('-score').paginate(
                page=args['page'], per_page=args['per_page'])
        else:
            pagination = Movie.objects(is_deleted=False).order_by('-score').paginate(
                page=args['page'], per_page=args['per_page'])

        items = [movie_summary_schema(movie) for movie in pagination.items]

        prev = None
        if pagination.has_prev:
            prev = url_for(
                '.typerank', type_name=args['type_name'], page=args['page']-1, per_page=args['per_page'], _external=True)

        next = None
        if pagination.has_next:
            next = url_for(
                '.typerank', type_name=args['type_name'], page=args['page']+1, per_page=args['per_page'], _external=True)

        first = url_for(
            '.typerank', type_name=args['type_name'], page=1, perpage=args['per_page'], _external=True)
        last  = url_for(
            '.typerank', type_name=args['type_name'], page=pagination.pages, perpage=args['per_page'], _external=True)
        return items_schema(items, prev, next, first, last, pagination.total, pagination.pages)


api.add_resource(ChoiceMovie, '/movie/choices')


class MovieInfo(Resource):

    @auth.login_required
    def get(self, movieid):
        # 返回此电影详细信息
        try:
            movie = Movie.objects(id=movieid, is_deleted=False).first()
        except  ValidationError:
            return{
                'message':'movie not found'
            },404
        if movie:
            return movie_schema(movie)
        else:
            return {
                'message':'movie not found'
            },404


    # @auth.login_required
    # @permission_required('DELETED_MOVIE')
    def delete(self,movieid):
        try:
            n=Movie.objects(id=movieid,is_deleted=False).update(is_deleted=True)
        except ValidationError:
            return{
                'message':'illegal movieid'
            },402
        if n==1:
            return {
                'message':'delete this movie successfuly '
            }
        return{
            'message':'movie not exist'
        }

api.add_resource(MovieInfo, '/movie/<movieid>')


# class MovieAction(Resource):

#     # # @auth.login_required
#     # # @permission_required('UPLOAD_MOVIE')
#     # def post(self):
#     #     # 添加一个新的电影
#     #     return{
#     #         'message': 'add  movie here'
#     #     }
    



# api.add_resource(MovieAction, '/movie')


class UserInterestMovie(Resource):
    # 用户对电影评价
    @auth.login_required
    def post(self, movieid):
        user = g.current_user
        parser = reqparse.RequestParser()
        parser.add_argument('interest', type=str,choices=['wish','do','collect'],
                            required=True, location='form')
        parser.add_argument('score', type=int, default=0, location='form')
        parser.add_argument('tags', type=str, location='form')
        parser.add_argument('comment', type=str, location='form')
        args = parser.parse_args()
        try:
            movie = Movie.objects(id=movieid, is_deleted=False).first()
        except ValidationError :
            return{
                'message':'movie not found'
            },404

        if not movie:
            return{
                'message': 'movie not found'
            },404

        if args['interest'] == 'wish':
            user.wish_movie(
                movie, score=args['score'], comment=args["comment"], tags=args['tags'])
        if args['interest'] == 'do':
            user.do_movie(
                movie, score=args['score'], comment=args["comment"], tags=args['tags'])
        if args['interest'] == 'collect':
            user.collect_movie(
                movie, score=args['score'], comment=args["comment"], tags=args['tags'])

        # 无论是否评论成功,都返回成功,不作区分
        return{
            'message': 'succeed'
        }


api.add_resource(UserInterestMovie, '/movie/<movieid>/interest')


class MovieRating(Resource):

    def get(self, movieid, category):
        parser = reqparse.RequestParser()
        parser.add_argument(
            'sort', choices=['hot', 'new'], type=str, location='args')
        parser.add_argument('page', default=1, type=int, location='args')
        parser.add_argument('per_page', default=20, type=int, location='args')
        args = parser.parse_args()
        try:
            #当查询的movie ID 不符合规范触发
            movie = Movie.objects(id=movieid, is_deleted=False).first()
        except ValidationError:
            return{
                'message':'movie not found'
            },404

        if not movie or category not in ['wish', 'do', 'collect', 'all']:
            return{
                'message': 'rating not found'
            }, 404
        if category == 'all':
            pagination = Rating.objects(movie=movie, is_deleted=False).order_by(
                '-like_count' if args['sort'] == 'hot' else '-rating_time').paginate(
                page=args['page'], per_page=args['per_page'])
        else:
            if category == 'wish':
                cate = 0
            if category == 'do':
                cate = 1
            if category == 'collect':
                cate = 2

            pagination = Rating.objects(movie=movie, is_deleted=False, category=cate).order_by(
                '-like_count' if args['sort'] == 'hot' else '-rating_time').paginate(
                page=args['page'], per_page=args['per_page'])
        # fenye  tiquhanshu chonggou
        items = [rating_schema(rating)
                 for rating in pagination.items]

        prev = None
        if pagination.has_prev:
            prev = url_for(
                '.movierating', movieid=movieid, category=category, sort=args['sort'], page=args['page']-1, per_page=args['per_page'], _external=True)

        next = None
        if pagination.has_next:
            next = url_for(
                '.movierating', movieid=movieid, category=category, sort=args['sort'],  page=args['page']+1, per_page=args['per_page'], _external=True)

        first = url_for(
            '.movierating', movieid=movieid, category=category, sort=args['sort'], page=1, perpage=args['per_page'], _external=True)
        last  = url_for(
            '.movierating', movieid=movieid, category=category, sort=args['sort'], page=pagination.pages, perpage=args['per_page'], _external=True)
        return items_schema(items, prev, next, first, last, pagination.total, pagination.pages)


api.add_resource(MovieRating, '/movie/<movieid>/<category>')
