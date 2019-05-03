from flask import g,url_for
from flask_restful import Resource, reqparse

from app.extensions import api
from app.models import Notification
from .schemas import notification_schema, items_schema
from .auth import auth


class NotificationCount(Resource):

    """获取未读取通知数量
    """
    @auth.login_required
    def get(self):
        user = g.current_user
        count = Notification.objects(receiver=user, is_read=False).count()
        return {
            'count': count,
            'message': 'sum of notification not read'
        }


api.add_resource(NotificationCount, '/notification/new_count')


class NotificationInfo(Resource):

    @auth.login_required
    def get(self, type_name):
        """ 根据``type_name`` 查询所有通知"""
        parser = reqparse.RequestParser()
        parser.add_argument('page', default=1, type=int, location='args')
        parser.add_argument('per_page', default=20, type=int, location='args')
        args = parser.parse_args()
        user = g.current_user
        if type_name=='friendship':
            pagination=Notification.objects(receiver=user,category=0).paginate(
                page=args['page'], per_page=args['per_page'])

        if type_name=='like':
            pagination=Notification.objects(receiver=user,category=1).paginate(
                page=args['page'], per_page=args['per_page'])

        if type_name=='sys':
            pagination=Notification.objects(receiver=user,category=2).paginate(
                page=args['page'], per_page=args['per_page'])

        items = [notification_schema(notification) for notification in pagination.items]

        #将未读通知更改为已读
        _=[notification.update(is_read=True) for notification in pagination.items]
        
        prev = None
        if pagination.has_prev:
            prev = url_for(
                '.notificationinfo', type_name=type_name,  page=args['page']-1, per_page=args['per_page'], _external=True)

        next = None
        if pagination.has_next:
            prev = url_for(
                '.notificationinfo', type_name=type_name,  page=args['page']+1, per_page=args['per_page'], _external=True)

        first = url_for(
            '.notificationinfo', type_name=type_name, page=1, perpage=args['per_page'], _external=True)
        last = prev = url_for(
            '.notificationinfo', type_name=type_name, page=pagination.pages, perpage=args['per_page'], _external=True)
        return items_schema(items, prev, next, first, last, pagination.total, pagination.pages)



api.add_resource(NotificationInfo,
                 '/notification/<any(friendship,like,sys):type_name>')
