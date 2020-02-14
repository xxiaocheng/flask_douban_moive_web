from flask_restful import Resource, reqparse, marshal, inputs
from app.v2.responses import (
    celebrity_resource_fields,
    ErrorCode,
    ok,
    error,
    get_pagination_resource_fields,
    get_item_pagination,
    movie_summary_resource_fields,
)
from app.sql_models import Celebrity as CelebrityModel, Movie
from app.utils.auth_decorator import auth, permission_required
from app.utils.hashid import decode_str_to_id
from app.extensions import sql_db
from app.const import GenderType


class Celebrity(Resource):
    @auth.login_required
    def get(self, celebrity_hash_id):
        celebrity = CelebrityModel.query.get(decode_str_to_id(celebrity_hash_id))
        if not celebrity:
            return error(ErrorCode.CELEBRITY_NOT_FOUND, 404)
        return ok("ok", data=marshal(celebrity, celebrity_resource_fields))

    @auth.login_required
    @permission_required("DELETE_CELEBRITY")
    def delete(self, celebrity_hash_id):
        celebrity = CelebrityModel.query.get(decode_str_to_id(celebrity_hash_id))
        if not celebrity:
            return error(ErrorCode.CELEBRITY_NOT_FOUND, 404)
        sql_db.session.delete(celebrity)
        sql_db.session.commit()
        return ok("已删除该艺人")


class Celebrities(Resource):
    @auth.login_required
    @permission_required("UPLOAD")
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("douban_id", type=int, location="form")
        parser.add_argument("avatar_url_last", required=True, type=str, location="form")
        parser.add_argument("name", required=True, location="form")
        parser.add_argument(
            "gender", required=True, choices=["male", "female"], location="form"
        )
        parser.add_argument("name_en", default="", type=str, location="form")
        parser.add_argument("born_place", default="", type=str, location="form")
        parser.add_argument("aka", location="form")
        parser.add_argument("aka_en", location="form")
        args = parser.parse_args()
        if args.aka:
            args.aka = args.aka.split("/")
        if args.aka_en:
            args.aka_en = args.aka_en.split("/")
        if args.gender == "male":
            args.gender = GenderType.MALE
        else:
            args.gender = GenderType.FEMALE
        celebrity = CelebrityModel.create_one(
            args.name,
            args.gender,
            avatar_url_last=args.avatar_url_last,
            douban_id=args.douban_id,
            born_place=args.born_place,
            name_en=args.name_en,
            aka_list=args.aka,
            aka_en_list=args.aka_en,
        )
        if not celebrity:
            return error(ErrorCode.CELEBRITY_ALREADY_EXISTS, 401)
        else:
            sql_db.session.add(celebrity)
            sql_db.session.commit()
            return ok("ok", http_status_code=201)


class CelebrityMovie(Resource):
    @auth.login_required
    def get(self, celebrity_hash_id):
        this_celebrity = CelebrityModel.query.get(decode_str_to_id(celebrity_hash_id))
        if not this_celebrity:
            return error(ErrorCode.CELEBRITY_NOT_FOUND, 404)
        parser = reqparse.RequestParser()
        parser.add_argument(
            "cate", type=str, choices=["director", "celebrity"], location="args"
        )
        parser.add_argument("page", default=1, type=inputs.positive, location="args")
        parser.add_argument(
            "per_page", default=20, type=inputs.positive, location="args"
        )
        args = parser.parse_args()
        director_pagination = this_celebrity.director_movies.order_by(
            Movie.year.desc()
        ).paginate(args.page, args.per_page)
        director_p = get_item_pagination(
            director_pagination,
            "api.CelebrityMovie",
            celebrity_hash_id=celebrity_hash_id,
            cate=args.cate,
        )

        celebrity_pagination = this_celebrity.celebrity_movies.order_by(
            Movie.year.desc()
        ).paginate(args.page, args.per_page)
        celebrity_p = get_item_pagination(
            celebrity_pagination,
            "api.CelebrityMovie",
            celebrity_hash_id=celebrity_hash_id,
            cate=args.cate,
        )
        if args.cate:
            if args.cate == "director":
                return ok(
                    "ok",
                    data=marshal(
                        director_p,
                        get_pagination_resource_fields(movie_summary_resource_fields),
                    ),
                )
            else:
                return ok(
                    "ok",
                    data=marshal(
                        celebrity_p,
                        get_pagination_resource_fields(movie_summary_resource_fields),
                    ),
                )
        else:
            return ok(
                "ok",
                data={
                    "directed": marshal(
                        director_p,
                        get_pagination_resource_fields(movie_summary_resource_fields),
                    ),
                    "celebrity": marshal(
                        celebrity_p,
                        get_pagination_resource_fields(movie_summary_resource_fields),
                    ),
                },
            )
