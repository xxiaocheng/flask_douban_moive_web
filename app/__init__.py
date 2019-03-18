import os

from flask import Flask

from app.extensions import avatars, cache, cors, db,api
from app.v1.photo import photo_bp
from app.v1.resources import api_bp
from app.settings import config

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'development')

    app = Flask(__name__)

    app.config.from_object(config[config_name])
    
    register_extensions(app)
    register_blueprints(app)
    

    return app

def register_extensions(app):
    cors.init_app(app)
    db.init_app(app)
    cache.init_app(app)
    avatars.init_app(app)
    api.init_app(api_bp)

def register_blueprints(app):
    """Register the blueprints to the app.
    :param app: the instance of ``Flask``
    """
    app.register_blueprint(photo_bp,url_prefix='/photo')
    app.register_blueprint(api_bp,url_prefix='/api/v1')