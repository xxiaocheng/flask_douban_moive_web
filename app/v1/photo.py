from flask import send_from_directory,current_app
from flask import Blueprint

photo_bp=Blueprint('photo',__name__)

@photo_bp.route('/<path:filename>')
def send_file(filename):
    return send_from_directory(current_app.config['UPLOAD_PATH'],filename)