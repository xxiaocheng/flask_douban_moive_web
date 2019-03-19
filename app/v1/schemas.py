from flask import url_for, current_app, g


def user_schema(user):
    return{
        "uid": str(user.id),
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
        "alt": current_app.config['WEB_BASE_URL']+'/people/'+user.username
    }


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
