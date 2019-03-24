import requests
from flask_restful import Resource, reqparse
import json
from flask import g

from app.extensions import api, cache
from app.models import Movie
from app.helpers.redis_utils import *
from .auth import auth, email_confirm_required, permission_required

class Cinema(Resource):

    def _parse_task(self,r_json):
        [add_download_task_to_redis(download_task(subject['id'],'movie',2)) for subject in r_json['subjects']]

    @cache.cached(timeout=60*60*24*3)
    def get(self,coming_or_showing):
        if coming_or_showing not in ['coming','showing']:
            return{
                "message":"parameter error"
            },400
        
        if coming_or_showing=='coming':
            try:
                r=requests.get(url='https://api.douban.com/v2/movie/coming_soon?count=100')
                r_json=json.loads(r.text)
                self._parse_task(r_json)
                return r_json
            except:
                return{
                    'message':'internal error'
                },500

            #添加log

        if coming_or_showing=='showing':
            try:
                r=requests.get(url='https://api.douban.com/v2/movie/in_theaters?count=100')
                r_json=json.loads(r.text)
                self._parse_task(r_json)
                return r_json
            except:
                return{
                    'message':'internal error'
                },500
            #添加log

api.add_resource(Cinema,'/movies/cinema/<coming_or_showing>')


class Recommend(Resourced):

    @auth.login_required
    def get(self):
        user=g.current_user
        pass
        # 只返回概述信息


api.add_resource(Recommend,'/movies/Recommend')


class Leaderboard(Resource):

    def get(self,time_range):
        pass

        # tag or timerange or 
        # tag database class


api.add_resource(Leaderboard,'/movies/leaderboard/<time_range>')