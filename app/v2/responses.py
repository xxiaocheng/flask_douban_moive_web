from flask import url_for
from flask_restful import fields


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
}


def ok(message, data=None, http_status_code=200, **kwargs):
    return {"msg": message, "data": data, **kwargs}, http_status_code


def error(error_code, http_status_code, **kwargs):
    return (
        {"msg": ERROR_MSG_MAP[error_code], "error_code": error_code, **kwargs},
        http_status_code,
    )


class ItemPagination:
    def __init__(self, items, first, last, total, pages, prev=None, next=None):
        self.items = items
        self.prev = prev
        self.next = next
        self.first = first
        self.last = last
        self.total = total
        self.pages = pages


def get_item_pagination(pagination, endpoint, **kwargs):
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
    return ItemPagination(
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

users_pagination_resource_fields = {
    "items": fields.List(fields.Nested(user_resource_fields)),
    "prev": fields.String,
    "next": fields.String,
    "first": fields.String,
    "last": fields.String,
    "total": fields.Integer,
    "pages": fields.Integer,
}
