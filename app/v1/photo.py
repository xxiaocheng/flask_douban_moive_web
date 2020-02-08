from flask import send_from_directory, current_app
from flask import Blueprint
from app.extensions import api
from flask_restful import Resource


class Photo(Resource):
    def get(self, cate, filename):
        if cate == "avatar":
            base_path = current_app.config["AVATAR_UPLOAD_PATH"]
        elif cate == "celebrity":
            base_path = current_app.config["CELEBRITY_IMAGE_UPLOAD_PATH"]
        elif cate == "movie":
            base_path = current_app.config["MOVIE_IMAGE_UPLOAD_PATH"]

        return send_from_directory(base_path, filename)


api.add_resource(Photo, "/photo/<any(avatar,celebrity,movie):cate>/<path:filename>")
