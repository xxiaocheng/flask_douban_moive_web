from app.extensions import redis_store
import json


def email_task(user,confirm_email_or_reset_password):
    return{
        'to':user.email,
        'cate':confirm_email_or_reset_password,
        'username':user.username
    }

def download_task(subjects_id,cate,priority=0):
    """@param cate: movie or celebrity,image
    @param subjects_id: 需要爬去的唯一标示
    @param priority: 0>low 1>middle 2>high
    """
    assert cate in ['movie','celebrity','image']
    return{
        "subjects_id":subjects_id,
        "cate":cate,
        "priority":priority
    }

def import_info_from_douban_task(user,douban_id):
    return{
        "user":user.username,
        "douban_id":douban_id
    }

def add_download_task_to_redis(task):
    """以 ``zset`` 存储方便优先级高的在前面
    """
    redis_store.zadd('task:'+task['cate'],{task['subjects_id']:task['priority']})

def add_email_task_to_redis(task):
    """@param task : ``email_task`` instance
    return::``None``
    """
    redis_store.rpush("task:email",json.dumps(task))

def add_import_info_from_douban_task_to_redis(task):
    """以 ``zset`` 存储方便优先级高的在前面
    """
    redis_store.sadd('task:douban',json.dumps(task))


def add_rating_to_redis(rating):
    """@param rating: Rating instance
    在用户评分时,添加所评价电影到redis zset中 ,并设置过期时间 
    """
    redis_store.zadd('rating:week',{rating.movie.movie_id:rating.movie.score})
    redis_store.zadd('rating:month',{rating.movie.movie_id:rating.movie.score})
    redis_store.expire('rating:week',time=60*60*24*7)
    redis_store.expire('rating:month',time=60*60*24*30)