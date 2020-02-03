import os
from dotenv import find_dotenv, load_dotenv


load_dotenv(find_dotenv())

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Operations:
    CONFIRM = 'confirm-email'
    RESET_PASSWORD = 'reset-password'
    CHANGE_EMAIL = 'change-email'


class BaseConfig(object):
    SECRET_KEY = os.getenv('SECRET_KEY', 'secret strings')
    MONGODB_SETTINGS = {
        'db': os.getenv('MONGODB_DB', 'doubanmovie'),
        'host': os.getenv('MONGODB_HOST', 'localhost'),
        'port': 27017,
        'username': os.getenv('MONGODB_USERNAME'),
        'password': os.getenv('MONGODB_PASSWORD')
    }

    # flask_caching
    CACHE_TYPE = 'redis'
    CACHE_REDIS_DB = '0'
    CACHE_REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')

    # flask_redis
    REDIS_URL = "redis://{host}:6379/0".format(
        host=os.getenv('REDIS_HOST', 'localhost'))

    # upload dir
    AREA_DATA_PATH = os.path.join(basedir, 'app')
    UPLOAD_PATH = os.path.join(basedir, 'images')
    AVATAR_UPLOAD_PATH = os.path.join(UPLOAD_PATH, 'avatar')
    MOVIE_IMAGE_UPLOAD_PATH = os.path.join(UPLOAD_PATH, 'movie')
    CELEBRITY_IMAGE_UPLOAD_PATH = os.path.join(UPLOAD_PATH, 'celebrity')

    AVATARS_SAVE_PATH = os.path.join(UPLOAD_PATH, 'avatar')
    AVATARS_SIZE_TUPLE = (30, 100, 200)
    ADMIN_EMAIL = ''
    WEB_BASE_URL = 'http://localhost:8080'  # 前端部署服务器的url

    # sendgrid
    EMAIL_SENDER = 'noreply@todayx.xyz'
    SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')

    EXPIRATION = 60*60*24*7  # token 过期时间为一周

    # image can upload with ext
    UPLOAD_IMAGE_EXT = ['.jpg', '.png', '.jpeg']

    # SQLALCHEMY DATABASE SETTINGS
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CHEVERETO_BASE_URL = "http://119.3.163.246:8080/images/"

    # CELERY SETTINGS
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
    CELERY_TIMEZONE = 'Asia/Shanghai'
    CELERYD_CONCURRENCY = 12
    CELERY_IMPORTS =('app.tasks.email',)

    # ELASTICSEARCH
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')


class DevelopmentConfig(BaseConfig):
    ADMIN_EMAIL = 'cxxlxx0@gmail.com'
    MONGODB_SETTINGS = {
        'db': os.getenv('MONGODB_DB', 'doubanmovie'),
        'host': os.getenv('MONGODB_HOST', 'localhost'),
        'port': 27017,
        'username': os.getenv('MONGODB_USERNAME'),
        'password': os.getenv('MONGODB_PASSWORD')
    }

    # SQLALCHEMY DATABASE SETTINGS
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:4399@127.0.0.1:3306/movies_recommend_system_dev?charset=utf8mb4"


class TestingConfig(BaseConfig):
    TESTING = True

    MONGODB_SETTINGS = {
        'db': os.getenv('MONGODB_DB', 'doubanmovieTest'),
        'host': os.getenv('MONGODB_HOST', 'localhost'),
        'port': 27017,
        'username': os.getenv('MONGODB_USERNAME'),
        'password': os.getenv('MONGODB_PASSWORD')
    }
    ADMIN_EMAIL = 'cxxlxx0@gmail.com'

    # SQLALCHEMY DATABASE SETTINGS
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:4399@127.0.0.1:3306/movies_recommend_system_test"


class ProductionConfig(BaseConfig):
    ADMIN_EMAIL = 'cxxlxx0@gmail.com'

    # SQLALCHEMY DATABASE SETTINGS
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:4399@127.0.0.1:3306/movies_recommend_system"


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}
