from flask_mongoengine import MongoEngine
from flask_debugtoolbar import DebugToolbarExtension
from flask_caching import Cache
from flask_login import LoginManager,AnonymousUserMixin
from flask_avatars import Avatars

db=MongoEngine()
toolbar=DebugToolbarExtension()
cache=Cache()
login_manager=LoginManager()
avatars=Avatars()


login_manager.login_view = 'auth.login'
# login_manager.login_message = 'Your custom message'
login_manager.login_message_category = '请先登录'

#login_manager.refresh_view = 'auth.re_authenticate'
#login_manager.needs_refresh_message = 'Your custom message'
#login_manager.needs_refresh_message_category = 'warning'


class Guest(AnonymousUserMixin):

    def can(self, permission_name):
        return False

    @property
    def is_admin(self):
        return False