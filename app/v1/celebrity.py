from flask_restful import Resource, reqparse
from flask import current_app
import os
from app.extensions import api
from .schemas import celebrity_schema, celebrity_summary_schema
from app.models import Celebrity
from .auth import permission_required, auth
from mongoengine.errors import ValidationError
from werkzeug.datastructures import FileStorage
from app.helpers.utils import rename_image


class CelebrityInfo(Resource):
    def get(self, id):
        """返回单个影人详细信息
        """
        parser = reqparse.RequestParser()
        parser.add_argument(
            "cate", default="detail", choices=["summary", "detail"], location="args"
        )
        args = parser.parse_args()
        try:
            celebrity = Celebrity.objects(id=id, is_deleted=False).first()
        except ValidationError:
            return {"message": "celebrity not found."}, 404

        if not celebrity:

            return {"message": "celebrity not found."}, 404
        if args.cate == "summary":
            return celebrity_summary_schema(celebrity)
        return celebrity_schema(celebrity)

    @auth.login_required
    @permission_required("DELETE_CELEBRITY")
    def delete(self, id):
        # 删除一个艺人信息  ,需要验证具备权限的用户操作
        try:
            celebrity = Celebrity.objects(id=id, is_deleted=False).first()
        except ValidationError:
            return {"message": "celebrity not found."}, 404

        if not celebrity:
            return {"message": "celebrity not found."}, 404

        celebrity.update(is_deleted=True)
        return {"message": "celebrity deleted."}


api.add_resource(CelebrityInfo, "/celebrity/<id>")


class AddCelebrity(Resource):
    @auth.login_required
    @permission_required("UPLOAD")
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("douban_id", default="", type=str, location="form")
        parser.add_argument("avatar", required=True, type=FileStorage, location="files")
        parser.add_argument("name", required=True, location="form")
        parser.add_argument(
            "gender", required=True, choices=["男", "女"], location="form"
        )
        parser.add_argument("name_en", default="", type=str, location="form")
        parser.add_argument("born_place", default="", type=str, location="form")
        parser.add_argument("aka", location="form")
        parser.add_argument("aka_en", location="form")
        args = parser.parse_args()

        # parse cebrity avatar
        avatar_ext = os.path.splitext(args["avatar"].filename)[1]
        if avatar_ext not in current_app.config["UPLOAD_IMAGE_EXT"]:
            return {"message": "file type error", "type": avatar_ext}, 403
        avatar_filename = rename_image(args["avatar"].filename)

        with open(
            os.path.join(
                current_app.config["CELEBRITY_IMAGE_UPLOAD_PATH"], avatar_filename
            ),
            "wb",
        ) as f:
            args["avatar"].save(f)

        if args.aka:
            aka = args.aka.split(" ")
        else:
            aka = []
        if args.aka_en:
            aka_en = args.aka_en.split(" ")
        else:
            aka_en = []

        Celebrity(
            douban_id=args.douban_id,
            avatar=avatar_filename,
            name=args.name,
            gender=args.gender,
            name_en=args.name_en,
            born_place=args.born_place,
            aka=aka,
            aka_en=aka_en,
        ).save()
        return {"message": "艺人信息添加成功"}


api.add_resource(AddCelebrity, "/celebrity")
