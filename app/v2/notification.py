from flask import g
from flask_restful import Resource, inputs, marshal, reqparse

from app import sql_db
from app.const import NotificationType
from app.sql_models import Notification as NotificationModel
from app.utils.auth_decorator import auth
from app.v2.responses import (
    ErrorCode,
    error,
    get_item_pagination,
    get_pagination_resource_fields,
    notification_resource_fields,
    ok,
)


class NotificationCount(Resource):
    @auth.login_required
    def get(self):
        return ok(
            "ok",
            data={
                "count": g.current_user.notifications_received.filter_by(
                    is_read=False
                ).count()
            },
        )


class Notification(Resource):
    @auth.login_required
    def get(self, type_name):
        parser = reqparse.RequestParser()
        parser.add_argument("page", default=1, type=inputs.positive, location="args")
        parser.add_argument(
            "per_page", default=20, type=inputs.positive, location="args"
        )
        args = parser.parse_args()
        if type_name == "friendship":
            pagination = (
                g.current_user.notifications_received.filter_by(
                    category=NotificationType.FOLLOW
                )
                .order_by(NotificationModel.created_at.desc())
                .paginate(args.page, args.per_page)
            )
        elif type_name == "like":
            pagination = (
                g.current_user.notifications_received.filter_by(
                    category=NotificationType.RATING_ACTION
                )
                .order_by(NotificationModel.created_at.desc())
                .paginate(args.page, args.per_page)
            )
        else:
            return error(ErrorCode.INVALID_PARAMS, 403)
        for notification in pagination.items:
            notification.is_read = True
        sql_db.session.commit()
        p = get_item_pagination(pagination, "api.Notification", type_name=type_name)
        return ok(
            "ok",
            data=marshal(
                p, get_pagination_resource_fields(notification_resource_fields)
            ),
        )
