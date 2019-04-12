from flask import g
from flask_restful import Resource, reqparse

from app.extensions import api
from app.models import Rating

from .auth import auth, permission_required
from .schemas import items_schema, rating_schema


class RatingAction(Resource):

    @auth.login_required
    def post(self, ratingid):
        parser = reqparse.RequestParser()
        parser.add_argument('typename', choices=[
                            'like', 'unlike', 'report'], required=True, location='form', type=str)
        args = parser.parse_args()
        rating = Rating.objects(id=ratingid, is_deleted=False).first()
        if not rating:
            return{
                'message': 'rating not found'
            }, 404
        user = g.current_user
        if args['typename'] == 'like':
            if user.is_like_rating(rating):
                return{
                    'message': 'you already like this rating'
                }, 403
            else:
                rating.like_by(user)
                return{
                    'message': 'like successfuly'
                }
        if args['typename'] == 'unlike':
            if not user.is_like_rating(rating):
                return{
                    'message': 'you not like this rating before'
                }, 403
            else:
                rating.unlike_by(user)
                return{
                    'message': 'unlike'
                }
        if args['typename'] == 'report':
            rating.report_by(user)
            return{
                'message': 'succeed'
            }

    @auth.login_required
    def delete(self, ratingid):
        # 删除评分信息 ,只有本人或者具有管理评分权限的管理员可以删除
        user = g.current_user
        rating = Rating.objects(id=ratingid, is_deleted=False).first()
        if not rating:
            return{
                'message': 'rating not found'
            }, 404

        if rating.user == user or user.check_permission("HANDLE_REPORT"):
            rating.delete_self()
            return{
                'message': 'rating has deleted'
            }
        else:
            return {
                'message': 'permission required.'
            }, 400


api.add_resource(RatingAction, '/rating/<ratingid>')


class ReportRating(Resource):

    # @auth.login_required
    # @permission_required('HANDLE_REPORT')
    def get(self):
        # 查看所有被举报的评分
        parser = reqparse.RequestParser()
        parser.add_argument('page', default=1, type=int, location='args')
        parser.add_argument('per_page', default=20, type=int, location='args')
        args = parser.parse_args()
        pagination = Rating.objects(report_count__gt=0).order_by(
            '-report_count').paginate()

        items = [rating_schema(rating)
                 for rating in pagination.items]

        prev = None
        if pagination.has_prev:
            prev = url_for(
                '.reportrating', movieid=movieid, category=category, sort=args['sort'], page=args['page']-1, per_page=args['per_page'], _external=True)

        next = None
        if pagination.has_next:
            prev = url_for(
                '.reportrating', movieid=movieid, category=category, sort=args['sort'],  page=args['page']+1, per_page=args['per_page'], _external=True)

        first = url_for(
            '.reportrating', movieid=movieid, category=category, sort=args['sort'], page=1, perpage=args['per_page'], _external=True)
        last = prev = url_for(
            '.reportrating', movieid=movieid, category=category, sort=args['sort'], page=pagination.pages, perpage=args['per_page'], _external=True)
        return items_schema(items, prev, next, first, last, pagination.total, pagination.pages)


api.add_resource(
    ReportRating, '/rating/report')
