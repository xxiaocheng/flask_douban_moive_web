from flask_caching import Cache
from flask_cors import CORS
from flask_restful import Api
from flask_redis import FlaskRedis
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_avatars import Avatars

cache = Cache()
cors = CORS()
api = Api()
redis_store = FlaskRedis()
sql_db = SQLAlchemy()
migrate = Migrate()
avatars = Avatars()
