import os

from flask import Flask,jsonify

from app.extensions import avatars, cache, cors, db,api,redis_store,scheduler
from app.v1.photo import photo_bp
from app.v1 import api_bp
from app.settings import config

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'development')

    app = Flask(__name__)

    app.config.from_object(config[config_name])
    
    register_extensions(app)
    register_blueprints(app)
    register_errorhandlers(app)
    return app

def register_extensions(app):
    cors.init_app(app)
    db.init_app(app)
    cache.init_app(app)
    avatars.init_app(app)
    redis_store.init_app(app)
    api.init_app(api_bp)   # flask_restful 文档关于蓝本的用法
    # flask_apscheduler
    scheduler.init_app(app)
    scheduler.start()
    redis_store.app=app #为了发送邮件部分能够在程序上下文中运行


    

def register_blueprints(app):
    """Register the blueprints to the app.
    :param app: the instance of ``Flask``
    """
    app.register_blueprint(photo_bp,url_prefix='/photo')
    app.register_blueprint(api_bp,url_prefix='/api/v1')

def register_errorhandlers(app):
    '''返回json形式的error信息
    '''
    @app.errorhandler(400)
    def bad_request(e):
        response=jsonify(message='Bad Request')
        response.status_code=400
        return response

    @app.errorhandler(403)
    def forbidden(e):
        response=jsonify(message='Forbidden')
        response.status_code=403
        return response

    @app.errorhandler(404)
    def page_not_found(e):
        response=jsonify(message='Not Found')
        response.status_code=404
        return response

    @app.errorhandler(500)
    def internal_server_error(e):
        response=jsonify(message='Internal Server Error')
        response.status_code=500
        return response
