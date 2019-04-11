import json
import time

import requests
from fake_useragent import UserAgent
from flask import current_app

from app.extensions import redis_store
from app.helpers.redis_utils import (add_download_task_to_redis, download_task,
                                     had_downloaded)
from app.helpers.user_movies_profile import get_user_profile_movies
from app.helpers.utils import download_image_from_url
from app.models import Celebrity, Movie, Notification, Tag, User,Cinema

ua = UserAgent()

headers = {'user-agent': ua.random}

def sent_sys_message_to_user(user,message=None):
    
    notitication = Notification(
        receiver=user, category=2, system_info=message)
    notitication.save()

def sent_sys_message_to_admin(message=None):
    with redis_store.app.app_context():
        admin_user = User.objects(email=current_app.config['ADMIN_EMAIL']).first()
        sent_sys_message_to_user(admin_user,message)


def _get_cinema_movie(url, cate):
    assert cate in ['showing', 'coming']
    error=False
    r = requests.get(url=url, headers=headers)
    r_json = json.loads(r.text)
    if cate == 'coming':
        subjects=r_json.get('subjects')
        if subjects:
            for movie_obj in subjects:
                try:
                    if not redis_store.sismember('downloaded:movie',movie_obj.get('id')):
                        download_movie(movie_obj.get('id'))
                        time.sleep(5)
                    movie=Movie.objects(douban_id=movie_obj.get('id')).first()

                    Cinema.objects(cate=1,movie=movie).update(upsert=True,cate=1,movie=movie)
                except:
                    error=True

    elif cate == 'showing':
    
        for movie_obj in r_json.get('subjects'):
            try:
                if not redis_store.sismember('downloaded:movie',movie_obj.get('id')):
                    download_movie(movie_obj.get('id'))
                    time.sleep(5)
                movie=Movie.objects(douban_id=movie_obj.get('id')).first()

                Cinema.objects(cate=0,movie=movie).update(upsert=True,cate=0,movie=movie)
            except:
                error=True

    if error or r.status_code!=200:
        # 将失败信息转换成系统通知 ,并且通知管理员
        message = '获取正在热映或即将上映信息失败,请检查!'
        sent_sys_message_to_admin(message)


def get_all_cinema_movie():
    """设置定时任务
    """

    coming_url = 'https://api.douban.com/v2/movie/coming_soon?count=100'
    showing_url = 'https://api.douban.com/v2/movie/in_theaters?count=100'

    _get_cinema_movie(url=coming_url, cate='coming')
    _get_cinema_movie(url=showing_url, cate='showing')


def download_image_from_redis():
    """设置定时任务
    """
    while redis_store.zcard('task:image'):
        image_url = redis_store.zrange(
            'task:image', 1, 1, desc=True)[0].decode()
        if not redis_store.sismember('downloaded:image', image_url):
            time.sleep(10)
            with redis_store.app.app_context():
                if download_image_from_url(image_url) == 200:
                    # 如果下载成功
                    redis_store.zrem('task:image', image_url)
                    # 将已经下载过的资料存储到redis中,避免重复下载
                    had_downloaded(image_url, cate='image')
                else:
                    message = '下载图片失败,请检查!'
                    sent_sys_message_to_admin(message)
        


def download_celebrity_from_redis():
    """添加定时任务
    """
    base_url = 'https://api.douban.com/v2/movie/celebrity/%s'
    while redis_store.zcard('task:celebrity'):
        celebrity_id = redis_store.zrange(
            'task:celebrity', 1, 1, desc=True)[0].decode()
        if not redis_store.sismember('downloaded:celebrity',celebrity_id):
            time.sleep(10)
            r = requests.get(url=base_url % celebrity_id, headers=headers)
            if r.status_code != 200:
                sent_sys_message_to_admin(message='下载celebrity失败,请检查!')
                continue
            r_json = json.loads(r.text)
            avatar_url = r_json.get('avatars').get('large')
            avatar = avatar_url.split('/')[-1]

            image_task = download_task(
                avatar_url, cate='image')  # 将下载头像的任务添加到redis队列中
            add_download_task_to_redis(image_task)
            Celebrity.objects(douban_id=celebrity_id).update(upsert=True,douban_id=celebrity_id, name=r_json.get('name', None), gender=r_json.get('gender', None), avatar=avatar, born_place=r_json.get(
                'born_place'), aka_en=r_json.get('aka_en'), name_en=r_json.get('name_en'), aka=r_json.get('aka'))
            redis_store.zrem('task:celebrity', celebrity_id)
            # 将已经下载过的资料存储到redis中,避免重复下载
            had_downloaded(celebrity_id, cate='celebrity')

def download_movie(movie_id):
    base_url = 'https://api.douban.com/v2/movie/subject/%s'
    if not redis_store.sismember('downloaded:movie',movie_id):
        r = requests.get(url=base_url % movie_id, headers=headers)
        if r.status_code != 200:
            sent_sys_message_to_admin(message='下载电影失败,请检查!')
            return False
        else:
            r_json = json.loads(r.text)
            parse_movie_json(r_json)
            return True
    else:
        return True

def parse_movie_json(r_json):
    genres = r_json.get('genres')  # 标签
    for genre in genres:
        Tag.objects(name=genre, cate=1).update(
            upsert=True, name=genre, cate=1)

    casts = r_json.get('casts')
    directors = r_json.get('directors')
    for cast in casts+directors:
        try:
            avatar_url = cast['avatars']['large']
            avatar = avatar_url.split('/')[-1]
            image_task = download_task(
                avatar_url, cate='image')  # 将下载头像的任务添加到redis队列中
            add_download_task_to_redis(image_task)

            celebrity_task=download_task(cast.get('id'),'celebrity')# 将下载演员的任务添加到redis中
            add_download_task_to_redis(celebrity_task)
            Celebrity.objects(douban_id=cast['id']).update(
                upsert=True, douban_id=cast['id'], name=cast['name'], avatar=avatar)
        except TypeError :
            pass


    casts_obj=[]
    directors_obj=[]
    genres_obj=[]
    for cast in casts:
        casts_obj.append(Celebrity.objects(douban_id=cast.get('id')).first())
    for director in directors:
        directors_obj.append(Celebrity.objects(douban_id=director.get('id')).first())
    for genre in genres:
        genres_obj.append(Tag.objects(name=genre).first())

    image_url=r_json.get('images').get('large')
    image=image_url.split('/')[-1]
    image_task=download_task(image_url,'image')
    add_download_task_to_redis(image_task)

    # 持久化
    Movie(douban_id=r_json['id'], title=r_json['title'], subtype=r_json['subtype'], year=int(r_json['year']), image=image, seasons_count=r_json.get('seasons_count',None), episodes_count=r_json.get('episodes_count',None),
        countries=r_json.get('countries',None), genres=genres_obj, current_season=r_json.get('current_season',None), original_title=r_json['original_title'], summary=r_json['summary'], aka=r_json['aka'], directors=directors_obj, casts=casts_obj).save()
    had_downloaded(r_json.get('id'),cate='movie')


def get_douban_user_import_from_redis():
    """将redis列队中用户请求导入的任务下载到本地并完成数据添加   
    定时任务
    """
    while redis_store.exists('task:douban'):
        with redis_store.app.app_context():
            task_json=json.loads(redis_store.spop('task:douban').decode())
            user=User.objects(username=task_json['user']).first()
        
        print(1)
        collect_list,wish_list,do_list= get_user_profile_movies(task_json['douban_id'])
        print(2)
        for collect_movie_id in collect_list:
            time.sleep(10)    # 睡眠五秒,避免爬取速度过快爬虫被ban
            download_movie(collect_list)
            movie=Movie.objects(douban_id=collect_movie_id).first()
            user.wish_movie(movie)
        for wish_movie_id in wish_list:
            time.sleep(10)    # 睡眠五秒,避免爬取速度过快爬虫被ban
            download_movie(wish_movie_id)
            movie=Movie.objects(douban_id=wish_movie_id).first()
            user.wish_movie(movie)

        for do_movie_id in do_list:
            time.sleep(10)    # 睡眠五秒,避免爬取速度过快爬虫被ban
            download_movie(do_movie_id)
            movie=Movie.objects(douban_id=do_movie_id).first()
            user.wish_movie(movie)

        sent_sys_message_to_user(user,message='您豆瓣电影的个人数据已经导入完成啦~')
            
        # except:
        #     redis_store.sadd('task:douban', json.dumps(task_json))
        #     sent_sys_message_to_admin(message='用户导入豆瓣数据失败啦')
