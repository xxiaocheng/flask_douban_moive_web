import os
import sys


basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class BaseConfig(object):
    SECRET_KEY = os.getenv('SECRET_KEY', 'secret stringos')
    MONGODB_SETTINGS={
        'db':os.getenv('MONGODB_DB','doubanmovie'),
        'host':os.getenv('MONGODB_HOST','127.0.0.1'),
        'port':27017,
        'username':os.getenv('MONGODB_USERNAME'),
        'password':os.getenv('MONGODB_PASSWORD')
    }

    # flask_caching
    CACHE_TYPE='redis'
    CACHE_REDIS_DB='0'
    CACHE_REDIS_HOST=os.getenv('REDIS_HOST','127.0.0.1')

    # flask_redis 
    REDIS_URL = "redis://localhost:6379/0"

    UPLOAD_PATH = os.path.join(basedir, 'uploads')

    AVATARS_SAVE_PATH = os.path.join(UPLOAD_PATH, 'avatar')
    AVATARS_SIZE_TUPLE = (30, 100, 200)
    ADMIN_EMAIL=''
    WEB_BASE_URL='' # 前端部署服务器的url

class DevelopmentConfig(BaseConfig):
    ADMIN_EMAIL='cxxlxx0@gmail.com'
    MONGODB_SETTINGS={
        'db':os.getenv('MONGODB_DB','doubanmovie'),
        'host':os.getenv('MONGODB_HOST','127.0.0.1'),
        'port':27017,
        'username':os.getenv('MONGODB_USERNAME'),
        'password':os.getenv('MONGODB_PASSWORD')
    }

class TestingConfig(BaseConfig):
    MONGODB_SETTINGS={
        'db':os.getenv('MONGODB_DB','doubanmovieTest'),
        'host':os.getenv('MONGODB_HOST','127.0.0.1'),
        'port':27017,
        'username':os.getenv('MONGODB_USERNAME'),
        'password':os.getenv('MONGODB_PASSWORD')
    }
    ADMIN_EMAIL='cxxlxx0@gmail.com'

class ProductionCofig(BaseConfig):
    pass


config={
    'development':DevelopmentConfig,
    'testing':TestingConfig,
    'production':ProductionCofig
}