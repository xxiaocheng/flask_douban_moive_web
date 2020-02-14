from flask_restful import reqparse, Resource, inputs, marshal
from flask_sqlalchemy import Pagination
from app.sql_models import User, Movie, Celebrity
from app.v2.responses import (
    error,
    ok,
    user_resource_fields,
    movie_summary_resource_fields,
    celebrity_summary_resource_fields,
    get_pagination_resource_fields,
    get_item_pagination,
)


class Search(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument(
            "cate",
            required=True,
            choices=["movie", "people", "celebrity"],
            location="args",
        )
        parser.add_argument("q", required=True, type=str, location="args")
        parser.add_argument("page", default=1, type=inputs.positive, location="args")
        parser.add_argument(
            "per_page", default=20, type=inputs.positive, location="args"
        )
        args = parser.parse_args()
        if args.cate == "movie":
            items, total = Movie.search(args.q, args.page, args.per_page)
        elif args.cate == "people":
            items, total = User.search(args.q, args.page, args.per_page)
        else:
            items, total = Celebrity.search(args.q, args.page, args.per_page)
        pagination = Pagination("", args.page, args.per_page, total, items)
        p = get_item_pagination(pagination, "api.Search", cate=args.cate, q=args.q)
        if args.cate == "movie":
            return ok(
                "ok",
                marshal(
                    p, get_pagination_resource_fields(movie_summary_resource_fields)
                ),
            )
        elif args.cate == "people":
            return ok(
                "ok", marshal(p, get_pagination_resource_fields(user_resource_fields))
            )
        else:
            return ok(
                "ok",
                marshal(
                    p, get_pagination_resource_fields(celebrity_summary_resource_fields)
                ),
            )
