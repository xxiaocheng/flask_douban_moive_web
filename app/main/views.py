from flask import jsonify

from app.main import main_bp 
from app.extensions import cache

@main_bp.route('/')
def login():
    return jsonify(message='hello,world!')
