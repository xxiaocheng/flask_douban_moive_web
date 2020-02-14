import os
from dotenv import find_dotenv, load_dotenv


load_dotenv(find_dotenv())

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class BaseConfig(object):
    SECRET_KEY = os.getenv("SECRET_KEY", "secret strings")

    # flask_caching
    CACHE_TYPE = "redis"
    CACHE_REDIS_DB = "0"
    CACHE_REDIS_HOST = os.getenv("CACHE_REDIS_HOST", "localhost")

    # flask_redis
    REDIS_URL = "redis://{host}:6379/0".format(
        host=os.getenv("FALSK_REDIS_REDIS_HOST", "localhost")
    )

    # upload dir

    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "cxxlxx0@gmail.com")
    WEB_BASE_URL = os.getenv(
        "FRONT_WEB_BASE_URL", "http://localhost:8080"
    )  # 前端部署服务器的url

    # sendgrid
    EMAIL_SENDER = os.getenv("SENDERGRID_EMAIL_SENDER", "noreply@todayx.xyz")
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

    EXPIRATION = 60 * 60 * 24 * 7  # token 过期时间为一周

    # SQLALCHEMY DATABASE SETTINGS
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CHEVERETO_BASE_URL = os.getenv(
        "CHEVERETO_BASE_URL", "http://119.3.163.246:8080/images/"
    )

    # CELERY SETTINGS
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
    )
    CELERY_TIMEZONE = "Asia/Shanghai"
    CELERYD_CONCURRENCY = os.getenv("CELERYD_CONCURRENCY", 12)
    CELERY_IMPORTS = ("app.tasks.email",)

    # ELASTICSEARCH
    ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")

    # hashids
    HASHIDS_SALT = os.getenv("HASHIDS_SALT", "this is my salt")

    # flask-restful
    BUNDLE_ERRORS = True


class DevelopmentConfig(BaseConfig):
    ADMIN_EMAIL = "cxxlxx0@gmail.com"

    # SQLALCHEMY DATABASE SETTINGS
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4".format(
        username=os.getenv("MYSQL_USERNAME", "root"),
        password=os.getenv("MYSQL_PASSWORD", "123456"),
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=os.getenv("MYSQL_PORT", "3306"),
        database=os.getenv("MYSQL_DATABASE", "movies_recommend_system_dev"),
    )


class TestingConfig(BaseConfig):
    TESTING = True

    ADMIN_EMAIL = "cxxlxx0@gmail.com"

    # SQLALCHEMY DATABASE SETTINGS
    SQLALCHEMY_DATABASE_URI = (
        "mysql+pymysql://root:4399@127.0.0.1:3306/movies_recommend_system_test"
    )


class ProductionConfig(BaseConfig):
    ADMIN_EMAIL = "cxxlxx0@gmail.com"

    # SQLALCHEMY DATABASE SETTINGS
    SQLALCHEMY_DATABASE_URI = (
        "mysql+pymysql://root:4399@127.0.0.1:3306/movies_recommend_system"
    )


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
