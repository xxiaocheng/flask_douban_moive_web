import os

from flask import Flask

from app.auth import auth_bp
from app.celebrity import celebrity_bp
from app.main import main_bp
from app.movie import movie_bp
from app.user import user_bp

from app.extensions import db
from app.extensions import toolbar
from app.extensions import cache
from app.extensions import login_manager
from app.extensions import avatars

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
    db.init_app(app)
    toolbar.init_app(app)
    cache.init_app(app)
    login_manager.init_app(app)
    avatars.init_app(app)

def register_blueprints(app):
    """Register the blueprints to the app.
    :param app: the instance of ``Flask``
    """
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/user')
    app.register_blueprint(celebrity_bp, url_prefix='/celebrity')
    app.register_blueprint(movie_bp, url_prefix='/movie')
    app.register_blueprint(user_bp, url_prefix='/user')


