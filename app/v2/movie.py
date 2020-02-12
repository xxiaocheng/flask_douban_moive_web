from flask_restful import Resource
from flask import g
from app.sql_models import Movie
from app.v2.responses import ok, error
from app.extensions import sql_db
