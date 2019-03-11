from app.main import main_bp 
from app.extensions import cache

@main_bp.route('/')
@cache.cached(timeout=10*60)
def login():
    return """
    <body>It's Work!</body>
    """
