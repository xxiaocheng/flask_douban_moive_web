import math

from celery import Task

from app import celery
from app.sql_models import User, Rating
from app.utils.redis_utils import push_task_id_to_redis


class MyTask(Task):
    def on_success(self, retval, task_id, args, kwargs):
        push_task_id_to_redis("recomm-task", task_id)
        return super(MyTask, self).on_success(retval, task_id, args, kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        return super(MyTask, self).on_failure(exc, task_id, args, kwargs, einfo)


@celery.task(base=MyTask)
def get_item_similarity():
    if User.query.count() < 5 or Rating.query.count() < 25:
        return None
    count = {}
    N = {}
    for user in User.query.all():
        for rating_i in user.ratings.all():
            N[rating_i.movie_id] = N.get(rating_i.movie_id, 0) + 1
            for rating_j in user.ratings.all():
                if rating_i.movie_id == rating_j.movie_id:
                    continue
                if not count.get(rating_i.movie_id):
                    count[rating_i.movie_id] = {}
                if not count[rating_i.movie_id].get(rating_j.movie_id):
                    count[rating_i.movie_id][rating_j.movie_id] = 0
                count[rating_i.movie_id][rating_j.movie_id] += 1
    res = {}
    for u, related_items in count.items():
        for v, cij in related_items.items():
            if not res.get(u):
                res[u] = {}
            res[u][v] = cij / math.sqrt(N[u] * N[v])

    return res
