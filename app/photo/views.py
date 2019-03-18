from flask import send_from_directory,current_app
from app.photo import photo_bp

@photo_bp.route('/<path:filename>')
def send_file(filename):
    return send_from_directory(current_app.config['UPLOAD_PATH'],filename)