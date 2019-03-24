from flask import url_for, current_app, g
from app.models import Movie


def items_schema(items, prev, next, first, last, pagination):
    return{
        "items": items,
        "prev": prev,
        "next": next,
        "first": first,
        "last": last,
        "count": pagination.total,
        "pages": pagination.pages
    }

def user_summary_schema(user):
    pass


def movie_summary_schema(movie):
    return{
        'id':str(movie.id),
        'title':movie.title,
        'subtype':movie.subtype,
        'image':url_for('photo.send_movie_file', filename=movie.image, _external=True),
        'score':movie.score,
        'alt': current_app.config['WEB_BASE_URL']+'/movie/'+str(movie.id)
    }

def celebrity_summary_schema(celebrity):
    return{
        'id':str(celebrity.id),
        'name':celebrity.name,
        'image':url_for('photo.send_celebrity_file', filename=celebrity.avatar, _external=True),
        'alt': current_app.config['WEB_BASE_URL']+'/celebrity/'+str(celebrity.id)
    }

def user_schema(user):
    return{
        "name": user.username,
        "email": user.email,
        "loc_name": user.location,
        "created_time": user.created_time.strftime("%Y-%m-%d %H:%M:%S"),
        "is_locked": user.is_locked,
        "avatar": url_for('photo.send_avatar_file', filename=user.avatar_l, _external=True),
        "signature": user.signature,
        "type": user.role.name.lower(),
        "do_count": user.do_count,
        "wish_count": user.wish_count,
        "collect_count": user.collect_count,
        "followers_count": user.followers_count,
        "followings_count": user.followings_count,
        "followed": user.is_follow(g.current_user),  # 本人被ta被关注
        "follow": user.is_follow(g.current_user),  # 本人关注ta
        "alt": current_app.config['WEB_BASE_URL']+'/people/'+user.username,
        "last_login":user.last_login_time.strftime("%Y-%m-%d %H:%M:%S")
    }

def movie_schema(movie):
    return{
        'id':str(movie.id),
        'douban_id':movie.douban_id,
        'title':movie.title,
        'subtype':movie.subtype,
        'wish_by_count':movie.wish_by_count,
        'do_by_count':movie.do_by_count,
        'collect_by_count':movie.collect_by_count,
        'year':movie.year,
        'image':url_for('photo.send_movie_file', filename=movie.image, _external=True),
        'seasons_count':movie.seasons_count,
        'episodes_count':movie.episodes_count,
        'countries':movie.countries,
        'genres':[tag.name for tag in movie.genres if movie.genres],
        'current_season':movie.current_season,
        'original_title':movie.original_title,
        'summary':movie.summary,
        'aka':movie.aka,
        'score':movie.score,
        'rating_count':movie.rating_count,
        'directors':[celebrity_summary_schema(celebrity) for celebrity in movie.directors if movie.directors],
        'casts':[celebrity_summary_schema(cast) for cast in movie.casts if movie.casts],
        'alt': current_app.config['WEB_BASE_URL']+'/movie/'+str(movie.id)
    }


def celebrity_schema(celebrity):
    return{
        'id':str(celebrity.id),
        'name':celebrity.name,
        'image':url_for('photo.send_celebrity_file', filename=celebrity.avatar, _external=True),
        'alt': current_app.config['WEB_BASE_URL']+'/celebrity/'+str(celebrity._id),
        'gender':celebrity.gender,
        'born_place':celebrity.born_place,
        'aka_en':celebrity.aka_en,
        'name_en':celebrity.name_en,
        'aka':celebrity.aka,
        'direct_movies':[movie_summary_schema(movie) for movie in Movie.objects(directors__in=[celebrity]) if Movie.objects(directors__in=[celebrity]) ],
        'casts_movies':[movie_summary_schema(movie) for movie in Movie.objects(casts__in=[celebrity]) if Movie.objects(casts__in=[celebrity])]
    }
    

