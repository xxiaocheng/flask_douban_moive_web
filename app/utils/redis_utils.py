import datetime

from app.const import AccountOperations
from app.extensions import redis_store


def add_rating_to_rank_redis(movie, dec=False):
    """
    在用户评分时,添加所评价电影到redis zset中 ,并设置过期时间
    :param movie: Movie
    :param dec: set True when delete rating
    """
    key = "rating:" + datetime.date.today().strftime("%y%m%d")
    # 设置过期时间为三十天
    if dec:
        redis_store.zincrby(key, -1, str(movie.id))
    else:
        redis_store.zincrby(key, 1, str(movie.id))
    redis_store.expire(key, time=60 * 60 * 24 * 31)


def _movie_rank_redis_zset_paginate(
    keys, time_range="week", page=1, per_page=20, desc=True, with_scores=False
):
    """
    :param keys :redis``key``list
    :param time_range: such as 'week' or 'month'
    :param page :需要取出第几页,从1开始计数
    :param per_page :每页返回的数量
    :param desc :``True`` 降序排序, ``False`` 升序排序
    :param with_scores: ``True`` 带分数返回,``False`` 不带分数返回
    """
    today_rank_key = (
        "rating:rank:" + time_range + ":" + datetime.date.today().strftime("%y%m%d")
    )
    if not redis_store.exists(today_rank_key):
        redis_store.zunionstore(today_rank_key, keys=keys)
        redis_store.expire(today_rank_key, time=60 * 5)  # 排行榜临时键过期时间为五分钟

    start = per_page * (page - 1)
    end = start + per_page - 1
    total_count = redis_store.zcard(today_rank_key)

    return (
        [
            value.decode()
            for value in redis_store.zrange(
                today_rank_key, start=start, end=end, desc=desc, withscores=with_scores
            )
            if redis_store.zrange(
                today_rank_key, start=start, end=end, desc=desc, withscores=with_scores
            )
        ],
        total_count,
    )


def get_rank_movie_ids_with_range(days, page=1, per_page=20):
    """
    :param days: count of days
    :param page: current page
    :param per_page: items count of one page
    :return:
    """
    today = datetime.datetime.today()
    keys = [
        "rating:" + (today - datetime.timedelta(days=days)).strftime("%y%m%d")
        for days in range(0, days)
    ]
    return _movie_rank_redis_zset_paginate(
        keys=keys, time_range=str(days), page=page, per_page=per_page
    )


def test_limit_of_send_email(user, operation):
    """
    发送邮件前检测用户是否发送频繁
    :param user : Object of `User`
    :param operation : Operations
    :return :-2  发送成功 ,>0 限制 多少秒后才可发送 , 默认限制5分钟发送一次
    """
    key = ""
    if operation == AccountOperations.CONFIRM:
        key = "confirmEmail:limit:" + user.email
    elif operation == AccountOperations.RESET_PASSWORD:
        key = "resetPasswordEmail:limit:" + user.email
    elif operation == AccountOperations.CHANGE_EMAIL:
        key = "changeEmail:limit:" + user.email

    ttl_time = redis_store.ttl(key)
    if ttl_time > 0:
        return ttl_time
    redis_store.set(key, 1, 60)  # 限制60s 发送一次
    return -2


def push_task_id_to_redis(key, task_id):
    redis_store.rpush(key, task_id)


def get_task_id_from_redis(key):
    key_len = redis_store.llen(key)
    if key_len > 0:
        return redis_store.lrange(key, key_len - 1, key_len)[-1]
    return None
