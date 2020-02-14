from flask import g
from flask_restful import Resource, inputs, marshal, reqparse
from sqlalchemy import func

from app.extensions import sql_db
from app.sql_models import Rating as RatingModel
from app.sql_models import rating_reports
from app.utils.auth_decorator import auth, permission_required
from app.utils.hashid import decode_str_to_id
from app.v2.responses import (
    ErrorCode,
    error,
    get_item_pagination,
    get_pagination_resource_fields,
    ok,
    rating_with_movie_resource_fields,
)


class Rating(Resource):
    @auth.login_required
    def post(self, rating_hash_id):
        this_rating = RatingModel.query.get(decode_str_to_id(rating_hash_id))
        if not this_rating:
            return error(ErrorCode.RATING_NOT_FOUND, 404)
        parser = reqparse.RequestParser()
        parser.add_argument(
            "cate",
            choices=["like", "unlike", "report"],
            required=True,
            location="form",
            type=str,
        )
        args = parser.parse_args()
        if args.cate == "like":
            f = this_rating.like_by(g.current_user)
            if f:
                sql_db.session.commit()
                return ok("点赞成功", http_status_code=201)
            else:
                return error(ErrorCode.RATING_LIKE_ALREADY_EXISTS, 403)
        if args.cate == "unlike":
            f = this_rating.unlike_by(g.current_user)
            if f:
                sql_db.session.commit()
                return ok("取消点赞成功", http_status_code=201)
            else:
                return error(ErrorCode.RATING_LIKE_NOT_FOUND, 403)
        if args.cate == "report":
            f = this_rating.report_by(g.current_user)
            if f:
                sql_db.session.commit()
                return ok("举报评论成功", http_status_code=201)
            else:
                return error(ErrorCode.RATING_REPORT_FORBIDDEN, 403)

    @auth.login_required
    def delete(self, rating_hash_id):
        this_rating = RatingModel.query.get(decode_str_to_id(rating_hash_id))
        if not this_rating:
            return error(ErrorCode.RATING_NOT_FOUND, 404)
        this_user = g.current_user
        if this_rating == this_rating.user or this_user.check_permission(
            "HANDLE_REPORT"
        ):
            sql_db.session.delete(this_rating)
            sql_db.session.commit()
            return ok("删除成功")
        else:
            return error(ErrorCode.RATING_DELETE_FORBIDDEN, 403)


class ReportedRating(Resource):
    @auth.login_required
    @permission_required("HANDLE_REPORT")
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("page", default=1, type=inputs.positive, location="args")
        parser.add_argument(
            "per_page", default=20, type=inputs.positive, location="args"
        )
        args = parser.parse_args()

        s = (
            sql_db.session.query(
                rating_reports.c.rating_id, func.count("*").label("report_count")
            )
            .group_by(rating_reports.c.rating_id)
            .subquery()
        )
        pagination = (
            sql_db.session.query(RatingModel)
            .outerjoin(s, RatingModel.id == s.c.rating_id)
            .order_by(s.c.report_count.desc())
            .paginate(args.page, args.per_page)
        )
        p = get_item_pagination(pagination, "api.ReportedRating")
        return ok(
            "ok",
            data=marshal(
                p, get_pagination_resource_fields(rating_with_movie_resource_fields)
            ),
        )
