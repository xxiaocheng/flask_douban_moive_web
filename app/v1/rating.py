from flask import g, url_for
from flask_restful import Resource, reqparse

from app.extensions import api
from app.models import Rating

from .auth import auth, permission_required
from .schemas import items_schema, rating_schema_on_user
from mongoengine.errors import ValidationError


class RatingAction(Resource):
    @auth.login_required
    def post(self, ratingid):
        parser = reqparse.RequestParser()
        parser.add_argument(
            "typename",
            choices=["like", "unlike", "report"],
            required=True,
            location="form",
            type=str,
        )
        args = parser.parse_args()
        try:
            rating = Rating.objects(id=ratingid, is_deleted=False).first()
        except ValidationError:
            return {"message": "评论未找到!"}, 404
        if not rating:
            return {"message": "评论未找到!"}, 404
        user = g.current_user
        if args["typename"] == "like":
            if user.is_like_rating(rating):
                return {"message": "你已经点赞过!"}, 403
            else:
                rating.like_by(user)
                return {"message": "点赞成功!"}
        if args["typename"] == "unlike":
            if not user.is_like_rating(rating):
                return {"message": "取消点赞失败!"}, 403
            else:
                rating.unlike_by(user)
                return {"message": "取消点赞成功!"}
        if args["typename"] == "report":
            if rating.user == user:
                return {"message": "不能举报自己的评论!"}, 403
            f = rating.report_by(user)
            if f:
                return {"message": "举报成功!"}
            else:
                return {"message": "你已经举报过该评论!"}

    @auth.login_required
    def delete(self, ratingid):
        # 删除评分信息 ,只有本人或者具有管理评分权限的管理员可以删除
        user = g.current_user
        try:
            rating = Rating.objects(id=ratingid, is_deleted=False).first()
        except ValidationError:
            return ({"message": "rating not found"},)
        if not rating:
            return {"message": "rating not found"}, 404
        if user == rating.user or user.check_permission("HANDLE_REPORT"):
            rating.delete_self()
            return {"message": "评价已删除!"}
        else:
            return {"message": "permission required"}, 403


api.add_resource(RatingAction, "/rating/<ratingid>")


class ReportRating(Resource):
    @auth.login_required
    @permission_required("HANDLE_REPORT")
    def get(self):
        # 查看所有被举报的评分
        parser = reqparse.RequestParser()
        parser.add_argument("page", default=1, type=int, location="args")
        parser.add_argument("per_page", default=20, type=int, location="args")
        args = parser.parse_args()
        pagination = (
            Rating.objects(report_count__gt=0, is_deleted=False)
            .order_by("-report_count")
            .paginate(page=args.page, per_page=args.per_page)
        )

        items = [rating_schema_on_user(rating) for rating in pagination.items]

        prev = None
        if pagination.has_prev:
            prev = url_for(
                ".reportrating",
                page=args["page"] - 1,
                per_page=args["per_page"],
                _external=True,
            )

        next = None
        if pagination.has_next:
            prev = url_for(
                ".reportrating",
                page=args["page"] + 1,
                per_page=args["per_page"],
                _external=True,
            )

        first = url_for(
            ".reportrating", page=1, perpage=args["per_page"], _external=True
        )
        last = prev = url_for(
            ".reportrating",
            page=pagination.pages,
            perpage=args["per_page"],
            _external=True,
        )
        return items_schema(
            items, prev, next, first, last, pagination.total, pagination.pages
        )


api.add_resource(ReportRating, "/rating/report")
