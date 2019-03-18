import os

from flask import Flask

from app.oauth import oauth_bp
from app.celebrity import celebrity_bp
from app.extensions import avatars, cache, cors, db,api
from app.main import main_bp
from app.movie import movie_bp
from app.settings import config
from app.user import user_bp
from app.photo import photo_bp

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
    api.init_app(app)

def register_blueprints(app):
    """Register the blueprints to the app.
    :param app: the instance of ``Flask``
    """
    app.register_blueprint(photo_bp,url_prefix='/photo')
    app.register_blueprint(main_bp,url_prefix='/api/v1')
    app.register_blueprint(oauth_bp, url_prefix='/oauth')
    app.register_blueprint(celebrity_bp, url_prefix='/celebrity')
    app.register_blueprint(movie_bp, url_prefix='/movie')
    app.register_blueprint(user_bp, url_prefix='/user')
