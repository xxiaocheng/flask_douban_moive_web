from flask import url_for
from flask_restful import fields
from app.utils.hashid import encode_id_to_str


class ErrorCode:
    SUCCESS = 200
    ERROR = 500
    INVALID_PARAMS = 400
    FORBIDDEN = 403

    ACCOUNT_IS_LOCKED = 10001
    EMAIL_NOT_CONFIRMED = 10002
    USER_ALREADY_EXISTS = 10003
    SENDING_EMAIL_FREQUENTLY = 10004
    USERNAME_OR_PASSWORD_ERROR = 10005
    USER_NOT_FOUND = 10404
    FOLLOW_ALREADY_EXISTS = 10007
    FOLLOW_NOT_EXISTS = 10008
    PASSWORD_VALIDATE_ERROR = 10019
    EMAIL_ALREADY_CONFIRMED = 10010
    INVALID_TOKEN = 10011
    EMAIL_ALREADY_EXISTS = 10012

    GENRES_NOT_FOUND = 20404
    MOVIE_NOT_FOUND = 30404
    RATING_ALREADY_EXISTS = 40001
    MOVIE_ALREADY_EXISTS = 30001
    CELEBRITY_NOT_FOUND = 50404
    CELEBRITY_ALREADY_EXISTS = 50001


ERROR_MSG_MAP = {
    ErrorCode.SUCCESS: "OK",
    ErrorCode.ERROR: "Fail",
    ErrorCode.INVALID_PARAMS: "请求参数错误",
    ErrorCode.ACCOUNT_IS_LOCKED: "账号被锁定",
    ErrorCode.EMAIL_NOT_CONFIRMED: "邮箱未验证",
    ErrorCode.USER_ALREADY_EXISTS: "用户已存在",
    ErrorCode.SENDING_EMAIL_FREQUENTLY: "发送邮件频繁",
    ErrorCode.USERNAME_OR_PASSWORD_ERROR: "账户或密码错误",
    ErrorCode.USER_NOT_FOUND: "该用户不存在",
    ErrorCode.FORBIDDEN: "禁止当前操作",
    ErrorCode.FOLLOW_ALREADY_EXISTS: "已关注该用户",
    ErrorCode.FOLLOW_NOT_EXISTS: "未关注该用户",
    ErrorCode.PASSWORD_VALIDATE_ERROR: "密码校验失败",
    ErrorCode.EMAIL_ALREADY_CONFIRMED: "重复的邮箱确认",
    ErrorCode.INVALID_TOKEN: "非法的 TOKEN",
    ErrorCode.EMAIL_ALREADY_EXISTS: "邮箱已存在",
    ErrorCode.GENRES_NOT_FOUND: "该类型不存在",
    ErrorCode.MOVIE_NOT_FOUND: "该电影不存在",
    ErrorCode.RATING_ALREADY_EXISTS: "评价已存在",
    ErrorCode.MOVIE_ALREADY_EXISTS: "电影已存在",
    ErrorCode.CELEBRITY_NOT_FOUND: "艺人不存在",
    ErrorCode.CELEBRITY_ALREADY_EXISTS: "艺人已存在",
}


def ok(message, data=None, http_status_code=200, **kwargs):
    """
    used when no error
    :param message: some message
    :param data: data for return
    :param http_status_code: http status code
    :param kwargs: other data for return
    :return:
    """
    return {"msg": message, "data": data, **kwargs}, http_status_code


def error(error_code, http_status_code, **kwargs):
    """
    used when error
    :param error_code:
    :param http_status_code:
    :param kwargs:
    :return:
    """
    return (
        {"msg": ERROR_MSG_MAP[error_code], "error_code": error_code, **kwargs},
        http_status_code,
    )


class _ItemPagination:
    def __init__(self, items, first, last, total, pages, prev=None, next=None):
        self.items = items
        self.prev = prev
        self.next = next
        self.first = first
        self.last = last
        self.total = total
        self.pages = pages


def get_item_pagination(pagination, endpoint, **kwargs):
    """
    :param pagination: pagination object
    :param endpoint: view endpoint
    :param kwargs: other args for url_for()
    :return:
    """
    prev = next = None
    if pagination.has_prev:
        prev = url_for(
            endpoint,
            page=pagination.page - 1,
            per_page=pagination.per_page,
            _external=True,
            **kwargs
        )
    if pagination.has_next:
        next = url_for(
            endpoint,
            page=pagination.page + 1,
            per_page=pagination.per_page,
            _external=True,
            **kwargs
        )
    first = url_for(
        endpoint, page=1, per_page=pagination.per_page, _external=True, **kwargs
    )
    last = url_for(
        endpoint,
        page=pagination.pages,
        per_page=pagination.per_page,
        _external=True,
        **kwargs
    )
    return _ItemPagination(
        pagination.items,
        first,
        last,
        pagination.total,
        pagination.pages,
        prev=prev,
        next=next,
    )


user_resource_fields = {
    "username": fields.String,
    "email": fields.String,
    "city_name": fields.String(attribute=lambda x: x.city.name if x.city else None),
    "avatar_thumb": fields.String,
    "avatar_image": fields.String,
    "signature": fields.String,
    "role_name": fields.String,
    "last_login_time": fields.DateTime(dt_format="iso8601"),
    "followers_count": fields.Integer,
    "followings_count": fields.Integer,
}


def get_pagination_resource_fields(resource_fields):
    return {
        "items": fields.List(fields.Nested(resource_fields)),
        "prev": fields.String,
        "next": fields.String,
        "first": fields.String,
        "last": fields.String,
        "total": fields.Integer,
        "pages": fields.Integer,
    }


movie_summary_resource_fields = {
    "id": fields.String(attribute=lambda x: encode_id_to_str(x.id)),
    "year": fields.Integer,
    "title": fields.String,
    "subtype": fields.String,
    "image_url": fields.String,
    "score": fields.Float,
}

celebrity_summary_resource_fields = {
    "id": fields.String(attribute=lambda x: encode_id_to_str(x.id)),
    "name": fields.String,
    "avatar_url": fields.String,
}

country_resource_fields = {
    "id": fields.String(attribute=lambda x: encode_id_to_str(x.id)),
    "country_name": fields.String,
}
genre_resource_fields = {
    "id": fields.String(attribute=lambda x: encode_id_to_str(x.id)),
    "genre_name": fields.String,
}


class SplitToList(fields.Raw):
    def format(self, value):
        return value.split(" ")


movie_resource_fields = {
    "id": fields.String(attribute=lambda x: encode_id_to_str(x.id)),
    "year": fields.Integer,
    "title": fields.String,
    "subtype": fields.String,
    "image_url": fields.String,
    "score": fields.Float,
    "douban_id": fields.String,
    "wish_by_count": fields.Integer(
        attribute=lambda x: x.user_wish_rating_query.count()
    ),
    "do_by_count": fields.Integer(attribute=lambda x: x.user_do_rating_query.count()),
    "collect_by_count": fields.Integer(
        attribute=lambda x: x.user_collect_query.count()
    ),
    "seasons_count": fields.Integer,
    "episodes_count": fields.Integer,
    "current_season": fields.Integer,
    "original_title": fields.String,
    "summary": fields.String,
    "aka_list": SplitToList,
    "countries": fields.List(fields.Nested(country_resource_fields)),
    "genres": fields.List(fields.Nested(genre_resource_fields)),
    "directors": fields.List(fields.Nested(celebrity_summary_resource_fields)),
    "celebrities": fields.List(fields.Nested(celebrity_summary_resource_fields)),
}

celebrity_resource_fields = {
    "id": fields.String(attribute=lambda x: encode_id_to_str(x.id)),
    "douban_id": fields.String,
    "name": fields.String,
    "avatar_url": fields.String,
    "gender": fields.Integer,
    "born_place": fields.String,
    "name_en": fields.String,
    "aka_list": SplitToList,
    "aka_en_list": SplitToList,
}

rating_resource_fields = {
    "id": fields.String(attribute=lambda x: encode_id_to_str(x.id)),
    "category": fields.Integer,
    "comment": fields.String,
    "score": fields.Integer,
    "when": fields.DateTime(dt_format="iso8601", attribute="created_at"),
    "username": fields.String(attribute=lambda x: x.user.username),
    "user_avatar": fields.String(attribute=lambda x: x.user.avatar_thumb),
    "like_count": fields.Integer,
}

rating_with_movie_resource_fields = {
    "id": fields.String(attribute=lambda x: encode_id_to_str(x.id)),
    "category": fields.Integer,
    "comment": fields.String,
    "score": fields.Integer,
    "when": fields.DateTime(dt_format="iso8601", attribute="created_at"),
    "username": fields.String(attribute=lambda x: x.user.username),
    "user_avatar": fields.String(attribute=lambda x: x.user.avatar_thumb),
    "like_count": fields.Integer,
    "movie": fields.Nested(movie_resource_fields),
}
