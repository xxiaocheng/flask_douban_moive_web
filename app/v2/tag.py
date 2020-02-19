from flask_restful import Resource, marshal, reqparse

from app.extensions import cache
from app.sql_models import Country as CountryModel
from app.sql_models import Genre as GenreModel
from app.sql_models import Movie as MovieModel
from app.utils.auth_decorator import auth
from app.v2.responses import country_resource_fields, error, genre_resource_fields, ok


class Genre(Resource):
    @auth.login_required
    @cache.cached(timeout=60 * 3, query_string=True)
    def get(self):
        genres = GenreModel.query.all()
        return ok("ok", data=marshal(genres, genre_resource_fields))


class Country(Resource):
    @auth.login_required
    @cache.cached(timeout=60 * 3, query_string=True)
    def get(self):
        countries = CountryModel.query.all()
        return ok("ok", data=marshal(countries, country_resource_fields))


class Year(Resource):
    @auth.login_required
    @cache.cached(timeout=60 * 3, query_string=True)
    def get(self):
        years = (
            MovieModel.query.with_entities(MovieModel.year)
            .distinct(MovieModel.year)
            .order_by(MovieModel.year.desc())
            .all()
        )
        return ok("ok", data=[y[0] for y in years if years])
