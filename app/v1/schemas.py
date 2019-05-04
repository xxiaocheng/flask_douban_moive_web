from flask import current_app, g, url_for

from app.models import Movie,Rating,Like


def items_schema(items, prev, next, first, last, total, pages):
    return{
        "items": items,
        "prev": prev,
        "next": next,
        "first": first,
        "last": last,
        "count": total,
        "pages": pages
    }


def user_summary_schema(user):
    return{
        'id':str(user.id),
        "name": user.username,
        "created_time": user.created_time.strftime("%Y-%m-%d %H:%M:%S"),
        "avatar": url_for('api.photo',cate='avatar', filename=user.avatar_l, _external=True),
        "signature": user.signature,
        "role": user.role.name.lower()
    }


def movie_summary_schema(movie):
    return{
        'year': movie.year,
        'id': str(movie.id),
        'title': movie.title,
        'subtype': movie.subtype,
        'image': url_for('api.photo',cate='movie' ,filename=movie.image, _external=True),
        'score': movie.score,
        'alt': current_app.config['WEB_BASE_URL']+'/movie/'+str(movie.id)
    }


def celebrity_summary_schema(celebrity):
    return{
        'id': str(celebrity.id),
        'name': celebrity.name,
        'image': url_for('api.photo', cate='celebrity',filename=celebrity.avatar, _external=True),
        'alt': current_app.config['WEB_BASE_URL']+'/celebrity/'+str(celebrity.id)
    }


def user_schema(user):
    if user.last_login_time:
        last_login = user.last_login_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        last_login = None
    return{
        "name": user.username,
        "email": user.email,
        "loc_name": user.location,
        "created_time": user.created_time.strftime("%Y-%m-%d %H:%M:%S"),
        "is_locked": user.is_locked(),
        "avatar": url_for('api.photo', cate='avatar',filename=user.avatar_l, _external=True),
        "signature": user.signature,
        "role": user.role.name.lower(),
        "do_count": user.do_count,
        "wish_count": user.wish_count,
        "collect_count": user.collect_count,
        "followers_count": user.followers_count,
        "followings_count": user.followings_count,
        "followed": user.is_follow(g.current_user),  # 本人被ta被关注
        "follow": user.is_follow_by(g.current_user),  # 本人关注ta
        "alt": current_app.config['WEB_BASE_URL']+'/people/'+user.username, #个人主页
        "last_login": last_login
    }


def movie_schema(movie):

    try:
        directors=[celebrity_summary_schema(celebrity) for celebrity in movie.directors if movie.directors]
    except:
        directors=[]
    try:
        casts=[celebrity_summary_schema(cast) for cast in movie.casts if movie.casts],
    except:
        casts=[]
    user=g.current_user
    me2movie={
        'cate':-1
    }
    if user:
        rating=Rating.objects(user=user,movie=movie,is_deleted=False).first()
        if rating:
            me2movie={
                'ratingId':str(rating.id),
                'cate':rating.category,
                'score':rating.score,
                'tags':[tag.name for tag in rating.tags if rating.tags],
                'comment':rating.comment,
                'time':rating.rating_time.strftime("%Y-%m-%d %H:%M:%S")
            }
    return{
        'id': str(movie.id),
        'douban_id': movie.douban_id,
        'title': movie.title,
        'subtype': movie.subtype,
        'wish_by_count': movie.wish_by_count,
        'do_by_count': movie.do_by_count,
        'collect_by_count': movie.collect_by_count,
        'year': movie.year,
        'image': url_for('api.photo',cate='movie', filename=movie.image, _external=True),
        'seasons_count': movie.seasons_count,
        'episodes_count': movie.episodes_count,
        'countries': movie.countries,
        'genres': [tag.name for tag in movie.genres if movie.genres],
        'current_season': movie.current_season,
        'original_title': movie.original_title,
        'summary': movie.summary,
        'aka': movie.aka,
        'score': movie.score,
        'rating_count': movie.rating_count,
        'directors': directors,
        'casts': casts,
        'alt': current_app.config['WEB_BASE_URL']+'/movie/'+str(movie.id),
        'me2movie':me2movie
    }


def celebrity_schema(celebrity):
    return{
        'id': str(celebrity.id),
        'name': celebrity.name,
        'image': url_for('api.photo',cate='celebrity', filename=celebrity.avatar, _external=True),
        'alt': current_app.config['WEB_BASE_URL']+'/celebrity/'+str(celebrity.id),
        'gender': celebrity.gender,
        'born_place': celebrity.born_place,
        'aka_en': celebrity.aka_en,
        'name_en': celebrity.name_en,
        'aka': celebrity.aka,
        'douban_id':celebrity.douban_id,
        'direct_movies': [movie_summary_schema(movie) for movie in Movie.objects(directors__in=[celebrity]) if Movie.objects(directors__in=[celebrity])],
        'casts_movies': [movie_summary_schema(movie) for movie in Movie.objects(casts__in=[celebrity]) if Movie.objects(casts__in=[celebrity])]
    }


def rating_schema(rating):
    schema={
        'cate': rating.category,
        'score': rating.score,
        'time': rating.rating_time.strftime("%Y-%m-%d %H:%M:%S"),
        'tags': [tag.name for tag in rating.tags if rating.tags],
        'username': rating.user.username,
        'likecount': rating.like_count,
        'useravatar': url_for('api.photo', cate='avatar',filename=rating.user.avatar_l, _external=True),
        'id': str(rating.id),
        'comment':rating.comment,
        'me2rating':'unlike'
    }

    user=g.current_user
    like=Like.objects(rating=rating,user=user).first()
    if like:
        schema['me2rating']='like'
    else:
        schema['me2rating']='unlike'
    return schema

def rating_schema_on_user(rating):
    
    return{
        'user':user_summary_schema(rating.user),
        'score':rating.score,
        'time': rating.rating_time.strftime("%Y-%m-%d %H:%M:%S"),
        'tags': [tag.name for tag in rating.tags if rating.tags],
        'id':str(rating.id),
        'comment':rating.comment,
        'movie':movie_summary_schema(rating.movie)
    }


def notification_schema(notification):
    if notification.category==0:
        info=_follow_schema(notification.follow_info)
    if notification.category==1:
        info=_like_schema(notification.like_info)
    if notification.category==2:
        info=_sys_notifi_schema(notification.system_info)

    return{
        'info':info,
        'time':notification.created_time.strftime("%Y-%m-%d %H:%M:%S")
    }

def _like_schema(like):
    return{
        'who_name':like.user.username, # 点赞你的人
        'who_avatar':url_for('api.photo',cate='avatar', filename=like.user.avatar_l, _external=True),
        'movie_id':str(like.rating.movie.id),
        'movie_title':like.rating.movie.title
    }

def _follow_schema(follow):
    return{
        'who_name':follow.follower.username, # 点赞你的人
        'who_avatar':url_for('api.photo',cate='avatar', filename=follow.follower.avatar_l, _external=True),
    }

def _sys_notifi_schema(system_info):
    return {
        'info':system_info
    }
