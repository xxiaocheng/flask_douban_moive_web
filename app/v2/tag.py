from flask_restful import Resource, reqparse, marshal
from app.sql_models import (
    Genre as GenreModel,
    Country as CountryModel,
    Movie as MovieModel,
)
from app.extensions import cache
from app.utils.auth_decorator import auth
from app.v2.responses import error, ok, country_resource_fields, genre_resource_fields


class Genre(Resource):
    @auth.login_required
    @cache.cached(timeout=60, query_string=True)
    def get(self):
        genres = GenreModel.query.all()
        return ok("ok", data=marshal(genres, genre_resource_fields))


class Country(Resource):
    @auth.login_required
    @cache.cached(timeout=60, query_string=True)
    def get(self):
        countries = CountryModel.query.all()
        return ok("ok", data=marshal(countries, country_resource_fields))


class Year(Resource):
    @auth.login_required
    @cache.cached(timeout=60, query_string=True)
    def get(self):
        years = (
            MovieModel.query.with_entities(MovieModel.year)
            .distinct(MovieModel.year)
            .order_by(MovieModel.year.desc())
            .all()
        )
        return ok("ok", data=[y[0] for y in years if years])
