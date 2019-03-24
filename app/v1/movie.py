from flask import redirect
import json
import math

import requests
from flask import abort, g, url_for
from flask_restful import Resource, reqparse

from app.extensions import api, cache
from app.helpers.redis_utils import *
from app.helpers.utils import query_by_id_list
from app.models import Movie, Rating, Tag, User

from .auth import auth, email_confirm_required, permission_required
from .schemas import items_schema, movie_summary_schema, movie_pagination_to_json


class Cinema(Resource):

    def _parse_task(self, r_json):
        [add_download_task_to_redis(download_task(
            subject['id'], 'movie', 2)) for subject in r_json['subjects']]

    @cache.cached(timeout=60*60*24*3)
    def get(self, coming_or_showing):
        if coming_or_showing not in ['coming', 'showing']:
            return{
                "message": "parameter error"
            }, 400

        if coming_or_showing == 'coming':
            try:
                r = requests.get(
                    url='https://api.douban.com/v2/movie/coming_soon?count=100')
                r_json = json.loads(r.text)
                self._parse_task(r_json)
                return r_json
            except:
                return{
                    'message': 'internal error'
                }, 500

            # 添加log

        if coming_or_showing == 'showing':
            try:
                r = requests.get(
                    url='https://api.douban.com/v2/movie/in_theaters?count=100')
                r_json = json.loads(r.text)
                self._parse_task(r_json)
                return r_json
            except:
                return{
                    'message': 'internal error'
                }, 500
            # 添加log


api.add_resource(Cinema, '/movie/cinema/<coming_or_showing>')


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

        id_items = redis_zset_paginate(
            name='rank:'+time_range, page=args['page'], per_page=args['per_page'])
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
        tag_obj = Tag.objects(name=args['type_name']).first()
        if not tag_obj:
            return{
                "message": 'no type found'
            }, 404

        pagination = Movie.objects(genres__in=[tag_obj], is_deleted=False).paginate(
            page=args['page'], per_page=args['per_page'])

        items = [movie_summary_schema(movie) for movie in pagination.items]

        prev = None
        if pagination.has_prev:
            prev = url_for(
                '.typerank', type_name=args['type_name'], page=args['page']-1, per_page=args['per_page'], _external=True)

        next = None
        if pagination.has_next:
            prev = url_for(
                '.typerank', type_name=args['type_name'], page=args['page']+1, per_page=args['per_page'], _external=True)

        first = url_for(
            '.typerank', type_name=args['type_name'], page=1, perpage=args['per_page'], _external=True)
        last = prev = url_for(
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
            prev = url_for(
                '.usermovie', username=username, type_name=args['type_name'], page=args['page']+1, per_page=args['per_page'], _external=True)

        first = url_for(
            '.usermovie', username=username, type_name=args['type_name'], page=1, perpage=args['per_page'], _external=True)
        last = prev = url_for(
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
        return redirect(url_for( '.usermovie', username=user.username, type_name=args['type_name'], page=args['page'], perpage=args['per_page']))


api.add_resource(MineMovie, '/movie/mine')


class ChoiceMovie(Resource):

    def get(self):
        pass

api.add_resource(MineMovie, '/movie/choices ')