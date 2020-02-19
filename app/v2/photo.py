import base64

from flask import Response
from flask_restful import Resource, abort
from app.utils.hashid import decode_str_to_id
from app.sql_models import Image
from app.extensions import cache


class Photo(Resource):
    @cache.cached(timeout=60 * 60 * 24 * 7)
    def get(self, image_hash_id):
        image = Image.query.get(decode_str_to_id(image_hash_id))
        if not image:
            abort(404)
        image_file = base64.b64decode(image.image)
        return Response(image_file, mimetype="image/jpeg")
