from flask import Blueprint

oauth_bp=Blueprint('auth',__name__)

from . import views