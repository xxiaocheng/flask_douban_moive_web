from flask import send_from_directory,current_app
from flask import Blueprint

photo_bp=Blueprint('photo',__name__)


@photo_bp.route('/avatar/<path:filename>')
def send_avatar_file(filename):
    return send_from_directory(current_app.config['UPLOAD_PATH'],'avatar/'+filename)

@photo_bp.route('/celebrity/<path:filename>')
def send_celebrity_file(filename):
    return send_from_directory(current_app.config['UPLOAD_PATH'],'celebrity/'+filename)

@photo_bp.route('/movie/<path:filename>')
def send_movie_file(filename):
    return send_from_directory(current_app.config['UPLOAD_PATH'],'movie/'+filename)