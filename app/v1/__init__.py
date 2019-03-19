from flask import Blueprint

api_bp = Blueprint('api', __name__)

from .user import *
from .auth import *
from .movie import *