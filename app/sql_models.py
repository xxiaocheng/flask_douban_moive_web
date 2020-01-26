from datetime import datetime

from app.extensions import sql_db as db
from flask_sqlalchemy import BaseQuery
from sqlalchemy import or_
from sqlalchemy.sql import func
from flask import current_app

from werkzeug.security import check_password_hash, generate_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired


class QueryWithSoftDelete(BaseQuery):
    """
    Soft-Delete query class
    """
    _with_deleted = False

    def __new__(cls, *args, **kwargs):
        obj = super(QueryWithSoftDelete, cls).__new__(cls)
        obj._with_deleted = kwargs.pop('_with_deleted', False)
        if len(args) > 0:
            super(QueryWithSoftDelete, obj).__init__(*args, **kwargs)
            return obj.filter_by(deleted=False) if not obj._with_deleted else obj
        return obj

    def __init__(self, *args, **kwargs):
        pass

    def with_deleted(self):
        return self.__class__(db.class_mapper(self._mapper_zero().class_),
                              session=db.session(), _with_deleted=True)

    def _get(self, *args, **kwargs):
        # this calls the original query.get function from the base class
        return super(QueryWithSoftDelete, self).get(*args, **kwargs)

    def get(self, *args, **kwargs):
        # the query.get method does not like it if there is a filter clause
        # pre-loaded, so we need to implement it using a workaround
        obj = self.with_deleted()._get(*args, **kwargs)
        return obj if obj is None or self._with_deleted or not obj.deleted else None


class MyBaseModel(db.Model):
    """
    Base Model
    """
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deleted = db.Column(db.Boolean(), default=False,
                        nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)

    query_class = QueryWithSoftDelete

    def delete_self(self):
        self.deleted = True
        self.deleted_at = datetime.utcnow()


class Like(MyBaseModel):
    """
    Table: user -> rating
    """
    __tablename__ = 'likes'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    rating_id = db.Column(db.Integer, db.ForeignKey('ratings.id'))


class UserRole(db.Model):
    __tablename__ = 'user_role'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

#
# user_role = db.Table('user_role',
#                      db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
#                      db.Column('role_id', db.Integer, db.ForeignKey('roles.id'))
#                      )


class Role(MyBaseModel):
    """
    Table: role permissions
    """
    __tablename__ = 'roles'
    role_name = db.Column(db.String(16))
    permission = db.Column(db.String(32))

    def __repr__(self):
        return '<Role %r>' % self.role_name

    @staticmethod
    def init_role():
        roles_permissions_map = current_app.config['ROLES_PERMISSIONS_MAP']
        for _role_name, _permissions in roles_permissions_map.items():
            for _permission in _permissions:
                if not Role.query.filter(Role.role_name == _role_name).filter(Role.permission == _permission).first():
                    role = Role(role_name=_role_name, permission=_permission)
                    db.session.add(role)
        db.session.commit()


# class Follower(MyBaseModel):
#     __tablename__ = 'followers'
#     follower_id = db.Column(db.Integer, db.ForeignKey('users.id'))
#     followed_id = db.Column(db.Integer, db.ForeignKey('users.id'))

followers = db.Table('followers',
                     db.Column('id', db.Integer, primary_key=True,
                               autoincrement=True),
                     db.Column('follower_id', db.Integer,
                               db.ForeignKey('users.id')),
                     db.Column('followed_id', db.Integer,
                               db.ForeignKey('roles.id')),
                     db.Column('created_at', db.DateTime,
                               default=datetime.utcnow())
                     )


class User(MyBaseModel):
    __tablename__ = 'users'

    username = db.Column(db.String(80), nullable=False, index=True)  # unique
    email = db.Column(db.String(128), nullable=False, index=True)  # unique
    password_hash = db.Column(db.String(128), nullable=False)
    # location = db.Column(db.Integer, nullable=True)
    last_login_time = db.Column(db.DateTime, default=datetime.utcnow)
    avatar_url = db.Column(db.String(128))
    email_confirmed = db.Column(db.Boolean(), default=False, nullable=False)
    signature = db.Column(db.Text)
    roles = db.relationship('Role', secondary="user_role",
                            backref=db.backref('users', lazy=True))
    followed = db.relationship('User', secondary='followers',
                               primaryjoin='followers.c.follower_id == User.id',
                               secondaryjoin='followers.c.followed_id == User.id',
                               backref=db.backref('followers', lazy='dynamic'),
                               lazy='dynamic')

    ratings = db.relationship('Rating', backref='user', lazy='dynamic')
    notifications = db.relationship(
        'Notification', backref='user', lazy='dynamic')

    def __repr__(self):
        return '<User %r>' % self.username

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        self._set_role()

    def generate_token(self, expiration=3600):
        """
        generate a jwt token and update the field of last_login_time
        :param expiration: a number of seconds
        :return: token
        """
        s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
        token = s.dumps({'uid': str(self.id)}).decode('ascii')
        self.last_login_time = datetime.utcnow()
        db.session.commit()
        return token

    @staticmethod
    def verity_auth_token(token):
        """
        verity the jwt when user login
        :param token: jwt token
        :return: current_user: User
        """
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None
        except BadSignature:
            return None
        current_user = User.query.filter_by(id=data['uid']).first()
        if current_user is None:
            return None
        else:
            return current_user

    @staticmethod
    def create_user(username, email, password):
        """
        create one user from params and commit session
        :param username: username unique
        :param email: email unique
        :param password: password
        :return: user: User if ok else None
        """
        if not username or not email or not password:
            return None
        if User.query.filter(or_(User.username == username, User.email == email)).first():
            return None
        current_user = User(username=username, email=email)
        current_user.password_hash = generate_password_hash(password)
        db.session.add(current_user)
        db.session.commit()
        return current_user

    def change_email(self, new_email):
        """
        change email to `new_email` but not commit session
        :parm new_email: new_email
        :return: True or False
        """
        if User.query.filter_by(email=new_email).first():
            return False
        self.email = new_email
        return True

    def change_password(self, new_password):
        """
        change password but not commit session
        :parm new_password: new password
        :return: True or False
        """
        if not new_password:
            return False
        self.password_hash = generate_password_hash(new_password)
        return True

    def validate_password(self, password):
        """
        validate the password
        :param password: he plaintext password to compare against the hash.
        :return: True or False
        """
        return check_password_hash(self.password_hash, password)

    def _generate_avatar(self):
        pass

    def _set_role(self):
        """
        set role for user when create a user.
        :return: None
        """
        if not Role.query.first():
            Role.init_role()
        if len(self.roles) == 0:
            if self.email == current_app.config['ADMIN_EMAIL']:
                current_roles = Role.query.filter_by(role_name='Administrator')
            else:
                current_roles = Role.query.filter_by(role_name='User')
            self.roles += current_roles

    def change_user_role(self, role_name):
        self.roles.clear()
        if Role.query.count() == 0:
            Role.init_role()
        current_roles = Role.query.filter_by(role_name=role_name)
        self.roles += current_roles

    def follow(self, user):
        """
        follow one user but not commit session
        :param user: User
        :return: True or False
        """
        if self.id != user.id:
            if not self.is_following(user):
                self.followed.append(user)
                return True
        return False

    def unfollow(self, user):
        """
        unfollow one user
        :param user: User
        :return: True or False
        """
        if self.id != user.id:
            if self.is_following(user):
                self.followed.remove(user)
                return True
        return False

    def is_following(self, user):
        """
        :param user: User
        :return: True or False
        """
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def is_following_by(self, user):
        return user.is_following(self)

    def wish_movie(self, movie, comment=None, tags=[]):
        r = Rating.create_rating_with_tags(
            score=0, comment=comment, category=0, tags=tags)
        r.movie_id = movie.id
        r.user_id = self.id
        return True

    def do_movie(self, movie, score=0, comment=None, tags=[]):
        if movie.subtype != 'TV':
            return False
        r = Rating.create_rating_with_tags(
            score=score, comment=comment, category=1, tags=tags)
        r.movie_id = movie.id
        r.user_id = self.id
        return True

    def collect_movie(self, movie, score=0, comment=None, tags=[]):
        r = Rating.create_rating_with_tags(
            score=0, comment=comment, category=2, tags=tags)
        r.movie_id = movie.id
        r.user_id = self.id
        return True

    @property
    def is_locked(self):
        return self.roles[0].role_name == "LOCKED"

    def lock_this_user(self):
        """
        Lock this user
        """
        self.change_user_role('Locked')

    def check_permission(self, permission):
        """Check Permission"""
        return permission.upper() in [role.permission for role in self.roles]

    def delete_self(self):
        """
        delete self and commit
        """
        super(User, self).delete_self()
        self.roles.clear()
        db.session.commit()
        pass
        # TODO


# rating_tags = db.Table('rating_tags',
#                        db.Column('id', db.Integer, primary_key=True, autoincrement=True),
#                        db.Column('rating_id'), db.Integer, db.ForeignKey('ratings.id'))
#
# movie_genres = db.Table('movie_genres',
#                         db.Column('id', db.Integer, primary_key=True, autoincrement=True),
#                         db.Column('movie_id'), db.Integer, db.ForeignKey('movies.id'))


class Celebrity(MyBaseModel):
    __tablename__ = 'celebrities'
    douban_id = db.Column(db.Integer)
    imdb_id = db.Column(db.String(16))
    name = db.Column(db.String(128), nullable=False)
    gender = db.Column(db.String(4))
    avatar_url = db.Column(db.String(128))
    born_place = db.Column(db.String(32))
    name_en = db.Column(db.String(32))
    aka_text = db.Column(db.Text)
    aka_en_text = db.Column(db.Text)


class Country(MyBaseModel):
    __tablename__ = 'countries'
    country_name = db.Column(db.String(16), nullable=False)
    movies = db.relationship('Movie', secondary="movie_country",
                             backref=db.backref('countries', lazy=True))


class Genre(MyBaseModel):
    __tablename__ = 'genres'
    genre_name = db.Column(db.String(8), nullable=False)


movie_genre = db.Table('movie_genres',
                       db.Column('id', db.Integer, primary_key=True,
                                 autoincrement=True),
                       db.Column('movie_id', db.Integer,
                                 db.ForeignKey('movies.id')),
                       db.Column('genre_id', db.Integer, db.ForeignKey('genres.id')))

movie_celebrity = db.Table('movie_celebrities',
                           db.Column('id', db.Integer, primary_key=True,
                                     autoincrement=True),
                           db.Column('movie_id', db.Integer,
                                     db.ForeignKey('movies.id')),
                           db.Column('celebrity_id', db.Integer,
                                     db.ForeignKey('celebrities.id')))

movie_director = db.Table('movie_directors',
                          db.Column('id', db.Integer, primary_key=True,
                                    autoincrement=True),
                          db.Column('movie_id', db.Integer,
                                    db.ForeignKey('movies.id')),
                          db.Column('celebrity_id', db.Integer,
                                    db.ForeignKey('celebrities.id')))


movie_country = db.Table('movie_countries',
                         db.Column('id', db.Integer, primary_key=True,
                                   autoincrement=True),
                         db.Column('movie_id', db.Integer, db.ForeignKey(
                             'movies.id')),
                         db.Column('country_id', db.Integer, db.ForeignKey('countries.id')))


class Movie(MyBaseModel):
    __tablename__ = 'movies'

    douban_id = db.Column(db.Integer)
    imdb_id = db.Column(db.String(16))
    title = db.Column(db.String(64), nullable=False)
    original_title = db.Column(db.String(64))
    subtype = db.Column(db.String(10), nullable=False)
    year = db.Column(db.Integer)
    image_url = db.Column(db.String(128))
    seasons_count = db.Column(db.Integer)  # 季数
    episodes_count = db.Column(db.Integer)  # 集数
    current_season = db.Column(db.Integer)  # 当前第几季
    summary = db.Column(db.String(64))
    # 0=finshed, 1=showing, 2=coming
    cinema_status = db.Column(db.Integer, default=0)
    aka_text = db.Column(db.Text)
    ratings = db.relationship('Rating', backref='movie', lazy='dynamic')
    genres = db.relationship('Genre', secondary="movie_genre",
                             backref=db.backref('movies', lazy='dynamic'), lazy=True)
    directors = db.relationship('Celebrity', secondary="movie_director",
                                backref=db.backref('director_movies', lazy='dynamic'), lazy=True)
    celebrities = db.relationship('Celebrity', secondary="movie_celebrity",
                                  backref=db.backref('celebrity_movies', lazy='dynamic'), lazy=True)

    @property
    def score(self):
        # query = self.ratings.filter_by(category=2).with_entities(func.avg(Rating.score)).all()
        # return query
        pass

    @property
    def user_do(self):
        pass

    @property
    def user_wish(self):
        pass

    @property
    def user_collect(self):
        pass

    def __repr__(self):
        return '<Movie %r>' % self.title

    def delete_self(self):
        super(Movie, self).delete_self()
        pass


class RatingTag(MyBaseModel):
    __tablename__ = 'rating_tags'
    rating_id = db.Column(db.Integer, db.ForeignKey(
        'ratings.id'), nullable=False)
    tag = db.Column(db.String(16), nullable=False)

    def __repr__(self):
        return '<RatingTag %r>' % self.tag


class RatingLike(MyBaseModel):
    __tablename__ = 'rating_likes'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating_id = db.Column(db.Integer, db.ForeignKey(
        'ratings.id'), nullable=False)
    user = db.relationship('User', backref='rating_likes', lazy='dynamic')


class RatingReport(MyBaseModel):
    __tablename__ = 'rating_reports'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    rating_id = db.Column(db.Integer, db.ForeignKey('ratings.id'))
    user = db.relationship('User', backref='rating_reports', lazy='dynamic')


class Rating(MyBaseModel):
    __tablename__ = 'ratings'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey(
        'movies.id'), nullable=False)
    score = db.Column(db.Integer, default=0)
    comment = db.Column(db.Text, default='')
    category = db.Column(db.Integer, default=2)  # 0=wish, 1=do, 2=collect
    tags = db.relationship('RatingTag', backref='rating', lazy=True)
    likes = db.relationship('RatingLike', backref='rating', lazy='dynamic')
    reports = db.relationship('RatingReport', backref='rating', lazy='dunamic')

    def __repr__(self):
        return '<Rating %r>' % self.comment

    @staticmethod
    def create_rating_with_tags(score=0, comment='', category=2, tags=[]):
        """
        create one rating with tags but not commit
        :param score: score
        :param comment: comment
        :parm category: category in (0, 1, 2), 0=wish, 1=do, 2=collect
        :return: r Rating
        """
        r = Rating(score=score, comment=comment, category=category)
        for tag in tags:
            rating_tag = RatingTag(tag=tag)
            r.tags.append(rating_tag)
        return r

    def like_by(self, user):
        """

        :param user:  User
        :return: RatingLike or None
        """
        rating_like = RatingLike.query.filter_by(
            user_id=user.id).filter_by(rating_id=self.id).first()
        if rating_like:
            return None
        rating_like = RatingLike(user_id=user.id, arting_id=self.id)
        return rating_like

    def unlike_by(self, user):
        """

        :param user: User
        :return: True or False
        """
        rating_like = RatingLike.query.filter_by(
            user_id=user.id).filter_by(rating_id=self.id).first()
        if not rating_like:
            return False
        rating_like.delete_self()
        return True

    def report_by(self, user):
        """

        :param user:
        :return: RatingReport or None
        """
        rating_report = RatingReport.query.filter_by(
            user_id=user.id).filter_by(rating_id=self.id).first()
        if not rating_report:
            rating_report = RatingReport(user_id=user.id, rating_id=self.id)
            return rating_report
        return None

    def delete_self(self):
        super(Rating, self).delete_self()
        # TODO


class Notification(MyBaseModel):
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    is_read = db.Column(db.Boolean(), default=False)
    information = db.Column(db.Integer)
    category = db.Column(db.Integer)  # 0=follow, 1=rating

    @staticmethod
    def add_to_notification(receiver_id, information, category):
        """
        add action to Notification
        :param receiver_id: User.id
        :param information: Follow.id or RatingLike.id
        :param category: 0 or 1 0=follow, 1=rating
        :return: Notification or None
        """
        if category not in [0, 1]:
            return None
        notification = Notification.query.filter_by(
            receiver_id=receiver_id, information=information, category=category).first()
        if not notification:
            notification = Notification(
                receiver_id=receiver_id, information=information, category=category)
            return notification
        return None

    @staticmethod
    def cancel_notification(receiver_id, information, category):
        if category not in [0, 1]:
            return None
        notification = Notification.query.filter_by(
            receiver_id=receiver_id, information=information, category=category).first()
        if not notification:
            return False
        else:
            notification.delete_self()
            return True
