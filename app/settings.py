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
    CACHE_REDIS_PASSWORD = os.getenv("CACHE_REDIS_PASSWORD")

    # flask_redis
    if os.getenv("FALSK_REDIS_REDIS_PASSWORD"):
        REDIS_URL = "redis://{password}@{host}:6379/0".format(
            password=os.getenv("FALSK_REDIS_REDIS_PASSWORD"),
            host=os.getenv("FALSK_REDIS_REDIS_HOST", "localhost"),
        )
    else:
        REDIS_URL = "redis://{host}:6379/0".format(
            host=os.getenv("FALSK_REDIS_REDIS_HOST", "localhost")
        )

    AREA_DATA_PATH = os.path.join(basedir, "app")

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

    # CELERY SETTINGS
    if os.getenv("CELERY_BROKER_PASSWORD"):
        CELERY_BROKER_URL = "redis://{password}@{host}:6379/0".format(
            password=os.getenv("CELERY_BROKER_PASSWORD"),
            host=os.getenv("CELERY_BROKER_URL", "localhost"),
        )
    else:
        CELERY_BROKER_URL = "redis://{host}:6379/0".format(
            host=os.getenv("CELERY_BROKER_URL", "localhost")
        )
    if os.getenv("CELERY_RESULT_BACKEND_PASSWORD"):
        CELERY_RESULT_BACKEND = "redis://{password}@{host}:6379/0".format(
            password=os.getenv("CELERY_RESULT_BACKEND_PASSWORD"),
            host=os.getenv("CELERY_RESULT_BACKEND_URL", "localhost"),
        )
    else:
        CELERY_RESULT_BACKEND = "redis://{host}:6379/0".format(
            host=os.getenv("CELERY_RESULT_BACKEND_URL", "localhost")
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
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://{username}:{password}@{host}:{port}/{database}_dev?charset=utf8mb4".format(
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
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://{username}:{password}@{host}:{port}/{database}_test?charset=utf8mb4".format(
        username=os.getenv("MYSQL_USERNAME", "root"),
        password=os.getenv("MYSQL_PASSWORD", "123456"),
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=os.getenv("MYSQL_PORT", "3306"),
        database=os.getenv("MYSQL_DATABASE", "movies_recommend_system"),
    )


class ProductionConfig(BaseConfig):
    ADMIN_EMAIL = "cxxlxx0@gmail.com"

    # SQLALCHEMY DATABASE SETTINGS
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4".format(
        username=os.getenv("MYSQL_USERNAME", "root"),
        password=os.getenv("MYSQL_PASSWORD", "123456"),
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=os.getenv("MYSQL_PORT", "3306"),
        database=os.getenv("MYSQL_DATABASE", "movies_recommend_system"),
    )


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
