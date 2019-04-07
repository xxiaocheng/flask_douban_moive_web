from flask import Blueprint

api_bp = Blueprint('api', __name__)

from .user import *
from .auth import *
from .movie import *
from .search import *
from .tag import *
from .rating import *
from .notification import *
from .celebrity import *
from .photo import *