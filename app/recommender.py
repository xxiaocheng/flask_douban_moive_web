from app.tasks.recommender import get_item_similarity
from app.sql_models import Rating, User
from app.extensions import cache
from app.utils.redis_utils import get_task_id_from_redis


@cache.cached(60, "recommend-movies-for-user", query_string=True)
def item_cf_recommendation(user_id, k):
    w = get_item_similarity.AsyncResult(get_task_id_from_redis("recomm-task")).get()
    res = {}
    if not w:
        return
    user = User.query.get(user_id)
    if not user:
        return
    for rating_i in user.ratings.all():
        if not w.get(str(rating_i.movie_id)):
            continue
        for j, wj in sorted(
            w[str(rating_i.movie_id)].items(), key=lambda item: item[1], reverse=True
        )[0:k]:
            if user.ratings.filter_by(movie_id=j).first():
                continue
            res[j] = res.get(j, 0) + wj * rating_i.score
    return list(res.keys())
