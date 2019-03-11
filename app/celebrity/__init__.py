from flask import Blueprint

celebrity_bp=Blueprint('celebrity',__name__)

from . import views