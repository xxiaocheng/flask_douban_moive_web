import os
import sys


basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Operations:
    CONFIRM = 'confirm-email'
    RESET_PASSWORD = 'reset-password'
    CHANGE_EMAIL = 'change-email'


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

    #upload dir
    AREA_DATA_PATH=os.path.join(basedir,'app');
    UPLOAD_PATH = os.path.join(basedir, 'uploads')
    AVATAR_UPLOAD_PATH=os.path.join(UPLOAD_PATH,'avatar')
    MOVIE_IMAGE_UPLOAD_PATH=os.path.join(UPLOAD_PATH,'movie')
    CELEBRITY_IMAGE_UPLOAD_PATH=os.path.join(UPLOAD_PATH,'celebrity')

    AVATARS_SAVE_PATH = os.path.join(UPLOAD_PATH, 'avatar')
    AVATARS_SIZE_TUPLE = (30, 100, 200)
    ADMIN_EMAIL=''
    WEB_BASE_URL='http://localhost:8080' # 前端部署服务器的url

    # sendgrid
    EMAIL_SENDER='noreply@miaomovie.com'

    EXPIRATION=60*60*24

    #APScheduler
    # SCHEDULER_API_ENABLED = True
    JOBS=[
        # 
        # {导入豆瓣用户信息 
        #     'id': 'download_douban_user_info',
        #     'func': 'app.tasks.download_tasks:get_douban_user_import_from_redis',
        #     'trigger': 'interval',
        #     'seconds': 60*60*24 # 一天执行一次
        # },
        {
            'id': 'download_celebrity',
            'func': 'app.tasks.download_tasks:download_celebrity_from_redis',
            'trigger': 'interval',
            'seconds': 60*60*24 # 一天执行一次
        },
        {
            'id': 'download_images',
            'func': 'app.tasks.download_tasks:download_image_from_redis',
            'trigger': 'interval',
            'seconds': 10 # 一天执行一次
        },
        {
            'id': 'download_cinema_movie',
            'func': 'app.tasks.download_tasks:get_all_cinema_movie',
            'trigger': 'interval',
            'seconds': 60*60*24 # 一天执行一次
        },
        {
            'id': 'send_email_job',
            'func': 'app.tasks.email_tasks:handle_email',
            'trigger': 'interval',
            'seconds': 10
        }
        
    ]
    SCHEDULER_EXECUTORS = {
        'default': {'type': 'threadpool', 'max_workers': 100}
    }

    # image can upload with ext
    UPLOAD_IMAGE_EXT=['.jpg','.png','.jpeg']

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

class ProductionConfig(BaseConfig):
    pass


config={
    'development':DevelopmentConfig,
    'testing':TestingConfig,
    'production':ProductionConfig
}