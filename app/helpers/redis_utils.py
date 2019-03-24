from app.extensions import redis_store
import json


def email_task(user, confirm_email_or_reset_password):
    return{
        'to': user.email,
        'cate': confirm_email_or_reset_password,
        'username': user.username
    }


def download_task(subjects_id, cate, priority=0):
    """@param cate: movie or celebrity,image
    @param subjects_id: 需要爬去的唯一标示
    @param priority: 0>low 1>middle 2>high
    """
    assert cate in ['movie', 'celebrity', 'image']
    return{
        "subjects_id": subjects_id,
        "cate": cate,
        "priority": priority
    }


def import_info_from_douban_task(user, douban_id):
    return{
        "user": user.username,
        "douban_id": douban_id
    }


def add_download_task_to_redis(task):
    """以 ``zset`` 存储方便优先级高的在前面
    """
    redis_store.zadd('task:'+task['cate'],
                     {task['subjects_id']: task['priority']})


def add_email_task_to_redis(task):
    """@param task : ``email_task`` instance
    return::``None``
    """
    redis_store.rpush("task:email", json.dumps(task))


def add_import_info_from_douban_task_to_redis(task):
    """以 ``zset`` 存储方便优先级高的在前面
    """
    redis_store.sadd('task:douban', json.dumps(task))


def add_movie_to_rank_redis(movie):
    """@param rating: Rating instance
    在用户评分时,添加所评价电影到redis zset中 ,并设置过期时间 
    """
    redis_store.zadd('rank:week', {str(movie.id): movie.score})
    redis_store.zadd('rank:month', {str(movie.id): movie.score})
    redis_store.expire('rank:week', time=60*60*24*7)
    redis_store.expire('rank:month', time=60*60*24*30)


def redis_zset_paginate(name, page=1, per_page=20, desc=True, withscores=False):
    """@param name :redis``key`` name
    @param page :需要取出第几页,从1开始计数
    @param per_page :每页返回的数量
    @param desc :``True`` 降序排序, ``False`` 升序排序
    @param with_score: ``True`` 带分数返回,``False`` 不带分数返回
    """
    start = per_page*(page-1)
    end = start+per_page-1
    return [value.decode()for value in redis_store.zrange(name, start=start, end=end, desc=desc, withscores=withscores) if redis_store.zrange(name, start=start, end=end, desc=desc, withscores=withscores)]
