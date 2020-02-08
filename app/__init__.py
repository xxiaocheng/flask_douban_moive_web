import os

from flask import Flask, jsonify, request
import click
import logging
from logging.handlers import RotatingFileHandler
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from celery import Celery
from elasticsearch import Elasticsearch

from app.extensions import avatars, cache, cors, db, api, redis_store, sql_db, migrate
from app.sql_models import ChinaArea, User
from app.v1 import api_bp
from app.settings import config, BaseConfig

# migrate the databases
from app.sql_models import User

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[
        FlaskIntegration(),
        CeleryIntegration(),
        RedisIntegration(),
        SqlalchemyIntegration(),
    ],
)


celery = Celery(__name__, broker=BaseConfig.CELERY_BROKER_URL)

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv("FLASK_CONFIG", "development")

    app = Flask(__name__)

    app.config.from_object(config[config_name])

    register_extensions(app)
    # register_blueprints(app) # not work when test
    register_error_handlers(app)
    register_commands(app)
    register_logger(app)
    celery.conf.update(app.config)

    app.elasticsearch = (
        Elasticsearch([app.config["ELASTICSEARCH_URL"]])
        if app.config["ELASTICSEARCH_URL"]
        else None
    )
    return app


def register_extensions(app):
    cors.init_app(app)
    db.init_app(app)
    cache.init_app(app)
    avatars.init_app(app)
    redis_store.init_app(app)
    sql_db.init_app(app)
    migrate.init_app(app, db=sql_db)

    api.init_app(api_bp)  # flask_restful 文档关于蓝本的用法


def register_blueprints(app):
    """Register the blueprints to the app.
    :param app: the instance of ``Flask``
    """
    app.register_blueprint(api_bp, url_prefix="/api/v1")


def register_error_handlers(app):
    """
    返回json形式的error信息
    :param app:
    :return:
    """

    @app.errorhandler(400)
    def bad_request(e):
        response = jsonify(message="Bad Request")
        response.status_code = 400
        return response

    @app.errorhandler(403)
    def forbidden(e):
        response = jsonify(message="Forbidden")
        response.status_code = 403
        return response

    @app.errorhandler(404)
    def page_not_found(e):
        response = jsonify(message="Not Found")
        response.status_code = 404
        return response

    @app.errorhandler(500)
    def internal_server_error(e):
        response = jsonify(message="Internal Server Error")
        response.status_code = 500
        return response


def register_logger(app):
    class RequestFormatter(logging.Formatter):
        def format(self, record):
            record.url = request.url
            record.remote_addr = request.remote_addr
            return super(RequestFormatter, self).format(record)

    request_formatter = RequestFormatter(
        "[%(asctime)s] %(remote_addr)s requested %(url)s\n"
        "%(levelname)s in %(module)s: %(message)s"
    )

    file_handler = RotatingFileHandler(
        os.path.join(basedir, "logs/douban-movie.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=100,
    )
    file_handler.setFormatter(request_formatter)
    file_handler.setLevel(logging.INFO)

    # if not app.debug:
    #     app.logger.addHandler(file_handler)
    app.logger.addHandler(file_handler)


def register_commands(app):
    @app.cli.command("init")
    @click.option("--drop", is_flag=True, help="Create after drop.")
    def init_db(drop):
        """Initialize the database."""
        if drop:
            click.confirm(
                "This operation will delete the database, do you want to continue?",
                abort=True,
            )
            sql_db.drop_all()
            click.echo("Drop tables.")
        sql_db.create_all()
        click.echo("Initialized database.")
        click.echo("Load China area data.")
        ChinaArea.load_data_from_json()
        click.echo("Finished.")
