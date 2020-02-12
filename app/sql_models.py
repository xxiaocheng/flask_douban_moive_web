import hashlib
from datetime import datetime
import os
import json

from tqdm import tqdm
from flask import current_app, g
from itsdangerous import BadSignature, SignatureExpired
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from sqlalchemy import or_, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import TINYINT
from werkzeug.security import check_password_hash, generate_password_hash

from app.const import (
    ROLES_PERMISSIONS_MAP,
    MovieCinemaStatus,
    MovieType,
    NotificationType,
    RatingType,
    GenderType,
)
from app.extensions import sql_db as db
from app.extensions import cache
from app.es_search import add_to_index, remove_from_index, query_index
from app.utils.redis_utils import add_rating_to_rank_redis


class SearchableMixin:
    @classmethod
    def search(cls, expression, page, per_page):
        """
        :param expression: query expression
        :param page: current page, start from 1
        :param per_page: count/per_page
        :return: flask_sqlalchemy.BaseQuery, total
        """
        ids, total = query_index(cls, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=-1), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return (
            cls.query.filter(cls.id.in_(ids)).order_by(db.case(when, value=cls.id)),
            total,
        )

    @classmethod
    def before_commit(cls, session):
        if not hasattr(session, "_changes") or session._changes is None:
            session._changes = {"add": [], "update": [], "delete": []}
        if session.new:
            session._changes["add"] += [
                obj for obj in session.new if isinstance(obj, cls)
            ]
        if session.dirty:
            session._changes["update"] += [
                obj for obj in session.dirty if isinstance(obj, cls)
            ]
        if session.deleted:
            session._changes["delete"] += [
                obj for obj in session.deleted if isinstance(obj, cls)
            ]

    @classmethod
    def after_commit(cls, session):
        if hasattr(session, "_changes") and session._changes:
            for obj in session._changes["add"]:
                add_to_index(cls.__tablename__, obj)
            for obj in session._changes["update"]:
                add_to_index(cls.__tablename__, obj)
            for obj in session._changes["delete"]:
                remove_from_index(cls.__tablename__, obj)
            session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


class MyBaseModel(db.Model):
    """
    Base Model
    """

    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)


user_roles = db.Table(
    "user_roles",
    db.Column("id", db.Integer, primary_key=True, autoincrement=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id", ondelete="CASCADE")),
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE")),
    UniqueConstraint("user_id", "role_id", name="unique_user_id_and_role_id"),
)


class Role(MyBaseModel):
    """
    Table: role permissions
    """

    __tablename__ = "roles"
    role_name = db.Column(db.String(16))
    permission = db.Column(db.String(32))

    def __repr__(self):
        return "<Role %r>" % self.role_name

    @staticmethod
    def init_role():
        for _role_name, _permissions in ROLES_PERMISSIONS_MAP.items():
            for _permission in _permissions:
                if (
                    not Role.query.filter(Role.role_name == _role_name)
                    .filter(Role.permission == _permission)
                    .first()
                ):
                    role = Role(role_name=_role_name, permission=_permission)
                    db.session.add(role)
        db.session.commit()


followers = db.Table(
    "followers",
    db.Column("id", db.Integer, primary_key=True, autoincrement=True),
    db.Column("follower_id", db.Integer, db.ForeignKey("users.id")),
    db.Column("followed_id", db.Integer, db.ForeignKey("users.id")),
    db.Column("created_at", db.DateTime, default=datetime.utcnow()),
    UniqueConstraint(
        "follower_id", "followed_id", name="unique_follower_id_and_followed_id"
    ),
)


class Notification(MyBaseModel):
    receiver_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sender_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_read = db.Column(db.Boolean(), default=False)
    category = db.Column(TINYINT(1))  # must be in `NotificationType`
    information_text = db.Column(db.Text)  # not used
    rating_id = db.Column(
        db.Integer, db.ForeignKey("ratings.id", ondelete="CASCADE"), nullable=True
    )

    @staticmethod
    def create_one(receiver_user_id, sender_user_id, category, rating_id=None):
        """
        add action to Notification
        :param receiver_user_id: User.id
        :param sender_user_id: user send this notification
        :param category: NotificationType.FOLLOW or .RATING_ACTION
        :param follower_id: Followers.id
        :param rating_id: rating_id
        :return: Notification or None
        """
        if category not in [NotificationType.FOLLOW, NotificationType.RATING_ACTION]:
            return None
        notification = Notification.query.filter_by(
            receiver_user_id=receiver_user_id,
            sender_user_id=sender_user_id,
            category=category,
            rating_id=rating_id,
        ).first()
        if not notification:
            notification = Notification(
                receiver_user_id=receiver_user_id,
                sender_user_id=sender_user_id,
                category=category,
                rating_id=rating_id,
            )
            return notification
        return None


class ChinaArea(db.Model):
    __tablename__ = "china_area_code"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.BIGINT, nullable=False)
    name = db.Column(db.String(128), default="", nullable=False)
    level = db.Column(TINYINT(1), nullable=False)
    pcode = db.Column(db.BIGINT)
    """
    select `a`.`code` AS `CODE`,`c`.`name` AS `province`,`b`.`name` AS `city`,`a`.`name` AS `country` from ((`china_area_code` `a` join `china_area_code` `b` on(((`a`.`level` = 3) and (`b`.`level` = 2) and (`a`.`pcode` = `b`.`code`)))) join `china_area_code` `c` on((`b`.`pcode` = `c`.`code`))) order by `a`.`code`
    """

    @staticmethod
    def load_data_from_json():
        with open(
            os.path.join(current_app.config["AREA_DATA_PATH"], "area_code_2019.json"),
            "r",
        ) as f:
            area_data_json = json.load(f)
        for record in tqdm(area_data_json["RECORDS"]):
            china_area = ChinaArea(
                code=record["code"],
                name=record["name"],
                level=record["level"],
                pcode=record["pcode"],
            )
            db.session.add(china_area)
        db.session.commit()

    @staticmethod
    @cache.cached(timeout=99 ^ 99, key_prefix="get_all_data_area")
    def get_all_area_date():
        res = list(
            db.session.execute(
                "select a.id, code, name from china_area_code as a where a.level=1"
            )
        )
        parent = []
        for p in res:
            t = {"id": p[0], "code": p[1], "name": p[2]}
            two_level_children = []
            level_two_res = list(
                db.session.execute(
                    "select a.id, code, name from china_area_code as a where a.pcode="
                    + str(p[1])
                )
            )
            for level_two in level_two_res:
                tt = {"id": level_two[0], "code": level_two[1], "name": level_two[2]}
                three_leve_children = []
                level_three_res = list(
                    db.session.execute(
                        "select a.id, code, name from china_area_code as a where a.pcode="
                        + str(level_two[1])
                    )
                )
                for level_three in level_three_res:
                    ttt = {
                        "id": level_three[0],
                        "code": level_three[1],
                        "name": level_three[2],
                    }
                    three_leve_children.append(ttt)
                tt["children"] = three_leve_children
                two_level_children.append(tt)
            t["children"] = two_level_children
            parent.append(t)
        return parent


class User(SearchableMixin, MyBaseModel):
    __tablename__ = "users"
    __searchable__ = [
        {"key": "username", "weight": 3},
        {"key": "signature", "weight": 1},
    ]

    username = db.Column(db.String(80), nullable=False, index=True, unique=True)
    email = db.Column(db.String(128), nullable=False, index=True, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    token_salt = db.Column(db.Integer, default=0, nullable=False)
    last_login_time = db.Column(db.DateTime, default=datetime.utcnow)
    avatar_url_last = db.Column(db.String(128))
    email_confirmed = db.Column(db.Boolean(), default=False, nullable=False)
    signature = db.Column(db.Text)
    city_id = db.Column(db.Integer, db.ForeignKey("china_area_code.id"))
    city = db.relationship("ChinaArea", backref="users", lazy=True)
    roles = db.relationship(
        "Role",
        secondary="user_roles",
        backref=db.backref("users", lazy="dynamic"),
        lazy=True,
    )
    followed = db.relationship(
        "User",
        secondary="followers",
        primaryjoin="followers.c.follower_id == User.id",
        secondaryjoin="followers.c.followed_id == User.id",
        backref=db.backref("followers", lazy="dynamic"),
        lazy="dynamic",
    )

    # Danger: with soft deleted
    ratings = db.relationship(
        "Rating", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    notifications_received = db.relationship(
        "Notification",
        foreign_keys=[Notification.receiver_user_id],
        backref="receiver_user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    notifications_sent = db.relationship(
        "Notification",
        foreign_keys=[Notification.sender_user_id],
        backref="send_user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return "<User %r>" % self.username

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        self._set_role()

    def generate_token(self, expiration=3600):
        """
        generate a jwt token and update the field of last_login_time
        :param expiration: a number of seconds
        :return: token
        """
        s = Serializer(current_app.config["SECRET_KEY"], expires_in=expiration)
        token = s.dumps({"uid": str(self.id), "token_salt": self.token_salt}).decode(
            "ascii"
        )
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
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None
        except BadSignature:
            return None
        current_user = User.query.filter_by(id=data["uid"]).first()
        if current_user is None:
            return None
        else:
            token_salt = data.get("token_salt")
            if token_salt == current_user.token_salt:
                g.current_user = current_user
                return current_user
            else:
                return None

    def revoke_auth_token(self):
        self.token_salt += 1
        g.current_user = None
        db.session.commit()

    @staticmethod
    def create_one(username, email, password):
        """
        create one user from params but not commit session
        :param username: username unique
        :param email: email unique
        :param password: password
        :return: user: User if ok else None
        """
        if not username or not email or not password:
            return None
        if User.query.filter(
            or_(User.username == username, User.email == email)
        ).first():
            return None
        current_user = User(username=username, email=email)
        current_user.password_hash = generate_password_hash(password)
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
        self.email_confirmed = False
        return True

    def change_username(self, new_username):
        if User.query.filter_by(username=new_username).first():
            return False
        self.username = new_username
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
        self.token_salt += 1
        return True

    def validate_password(self, password):
        """
        validate the password
        :param password: he plaintext password to compare against the hash.
        :return: True or False
        """
        return check_password_hash(self.password_hash, password)

    def _set_role(self):
        """
        set role for user when create a user.
        :return: None
        """
        if Role.query.count() == 0:
            Role.init_role()
        if len(self.roles) == 0:
            if self.email == current_app.config["ADMIN_EMAIL"]:
                current_roles = Role.query.filter_by(role_name="Administrator")
            else:
                current_roles = Role.query.filter_by(role_name="User")
            self.roles += current_roles

    def change_role(self, role_name):
        """
        change user`s role
        :param role_name: ROLES_PERMISSIONS_MAP.keys()
        """
        self.roles.clear()
        if Role.query.count() == 0:
            Role.init_role()
        current_roles = Role.query.filter_by(role_name=role_name.title())
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
                notification = Notification.create_one(
                    user.id, self.id, NotificationType.FOLLOW
                )
                if notification:
                    user.notifications_received.append(notification)
                    self.notifications_sent.append(notification)
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
                notification = Notification.query.filter_by(
                    receiver_user_id=user.id,
                    sender_user_id=self.id,
                    category=NotificationType.FOLLOW,
                ).first()
                if notification:
                    user.notifications_received.remove(notification)
                    self.notifications_sent.remove(notification)
                return True
        return False

    def is_following(self, user):
        """
        current user is follow `user`
        :param user: User
        :return: True or False
        """
        if self == user:
            return True
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def is_followed_by(self, user):
        """
        current user is follow by `user`
        :param user: User
        :return: True or False
        """
        if self == user:
            return True
        return user.is_following(self)

    def wish_movie(self, movie, comment=None, tags_name=[]):
        """
        wish movie by rating
        :param movie: Movie
        :param comment: comment for rating
        :param tags_name: list of tags
        :return: Rating or None
        """
        if Rating.query.filter_by(movie_id=movie.id, user_id=self.id).first():
            return None
        r = Rating.create_rating_with_tags(
            score=0, comment=comment, category=RatingType.WISH, tags_name=tags_name
        )
        r.movie_id = movie.id
        self.ratings.append(r)
        add_rating_to_rank_redis(movie)
        return r

    def do_movie(self, movie, score=0, comment=None, tags_name=[]):
        """
        do movie by rating
        :param movie: Movie
        :param score: score for rating
        :param comment: comment for rating
        :param tags_name: list of tags
        :return: Rating or None
        """
        if Rating.query.filter_by(movie_id=movie.id, user_id=self.id).first():
            return None
        if movie.subtype != MovieType.TV:
            return None
        r = Rating.create_rating_with_tags(
            score=score, comment=comment, category=RatingType.DO, tags_name=tags_name
        )
        r.movie_id = movie.id
        self.ratings.append(r)
        add_rating_to_rank_redis(movie)
        return r

    def collect_movie(self, movie, score=0, comment=None, tags_name=[]):
        """
        collect movie by rating
        :param movie: Movie
        :param score: score for rating
        :param comment: comment for rating
        :param tags_name: list of tags
        :return: Rating or None
        """
        if Rating.query.filter_by(movie_id=movie.id, user_id=self.id).first():
            return None
        r = Rating.create_rating_with_tags(
            score=score,
            comment=comment,
            category=RatingType.COLLECT,
            tags_name=tags_name,
        )
        r.movie_id = movie.id
        self.ratings.append(r)
        add_rating_to_rank_redis(movie)
        return r

    def delete_rating_on(self, movie):
        """
        delete one rating on this movie
        :param movie:
        :return:
        """
        rating = Rating.query.filter_by(movie_id=movie.id, user_id=self.id).first()
        if not rating:
            return False
        self.ratings.remove(rating)
        add_rating_to_rank_redis(movie, True)
        return True

    @property
    def role_name(self):
        if not self.roles:
            return
        return self.roles[0].role_name

    @property
    def is_locked(self):
        """
        test this user is locked or not
        :return: True or False
        """
        return self.role_name == "LOCKED"

    @property
    def notifications_count(self):
        return self.notifications_received.count()

    def lock_this_user(self):
        """
        lock this user
        """
        self.change_role("Locked")

    def check_permission(self, permission):
        """Check Permission"""
        return permission.upper() in [role.permission for role in self.roles]

    def _gen_email_hashgravatar(self, size=500):
        """
        generate avatar image url for user
        :param size: size
        :return: avatar url
        """
        email_hash = hashlib.md5(self.email.lower().encode("utf-8")).hexdigest()
        url = "https://secure.gravatar.com/avatar"
        return "{url}/{hash}?s={size}&d=identicon&r=g".format(
            url=url, hash=email_hash, size=size
        )

    @property
    def avatar_thumb(self):
        """
        thumb avatar
        """
        if not self.avatar_url_last:
            return self._gen_email_hashgravatar(100)
        else:
            url = current_app.config["CHEVERETO_BASE_URL"]
            file_name = self.avatar_url_last.split(".")[0]
            file_ext = self.avatar_url_last.split(".")[1]
            return url + file_name + ".th." + file_ext

    @property
    def avatar_image(self):
        """
        avatar image
        """
        if not self.avatar_url_last:
            return self._gen_email_hashgravatar(1000)
        else:
            url = current_app.config["CHEVERETO_BASE_URL"]
            return url + self.avatar_url_last

    @property
    def followers_count(self):
        return self.followers.count()

    @property
    def followings_count(self):
        return self.followed.count()


class Celebrity(SearchableMixin, MyBaseModel):
    __tablename__ = "celebrities"
    __searchable__ = [
        {"key": "name", "weight": 3},
        {"key": "name_en", "weight": 2},
        {"key": "born_place", "weight": 1},
    ]

    douban_id = db.Column(db.Integer, nullable=True, unique=True)
    imdb_id = db.Column(db.String(16), nullable=True, unique=True)
    name = db.Column(db.String(128), nullable=False)
    gender = db.Column(TINYINT(1), default=GenderType.MALE, nullable=False)
    avatar_url_last = db.Column(db.String(128), nullable=False)
    born_place = db.Column(db.String(32))
    name_en = db.Column(db.String(32))
    aka_list = db.Column(db.Text)
    aka_en_list = db.Column(db.Text)

    @staticmethod
    def create_one(
        name,
        gender,
        avatar_url_last,
        douban_id=None,
        imdb_id=None,
        born_place=None,
        name_en=None,
        aka_list=[],
        aka_en_list=[],
    ):
        """"""
        if Celebrity.query.filter(
            or_(Celebrity.douban_id == douban_id, Celebrity.imdb_id == imdb_id)
        ).first():
            return None
        else:
            celebrity = Celebrity(
                name=name,
                gender=gender,
                avatar_url_last=avatar_url_last,
                douban_id=douban_id,
                imdb_id=imdb_id,
                born_place=born_place,
                name_en=name_en,
                aka_list=" ".join(aka_list),
                aka_en_list=" ".join(aka_en_list),
            )
            return celebrity

    @property
    def avatar_url(self):
        """
        :return: avatar image url
        """
        url = current_app.config["CHEVERETO_BASE_URL"]
        return url + self.avatar_url_last


class Genre(MyBaseModel):
    """
    movie genre
    """

    __tablename__ = "genres"
    genre_name = db.Column(db.String(8), nullable=False)

    @staticmethod
    def create_one(genre_name):
        """
        create a Genre object, not commit session
        :param genre_name: genre name
        :return: Genre object
        """
        genre = Genre.query.filter_by(genre_name=genre_name).first()
        if genre:
            return genre
        else:
            genre = Genre(genre_name=genre_name)
            return genre


class Country(MyBaseModel):
    __tablename__ = "countries"
    country_name = db.Column(db.String(16), unique=True, nullable=False)

    @staticmethod
    def create_one(country_name):
        """
        create a Country object, not commit session
        :param country_name: country name
        :return: Country object
        """
        c = Country.query.filter_by(country_name=country_name).first()
        if c:
            return c
        else:
            c = Country(country_name=country_name)
            return c


movie_genres = db.Table(
    "movie_genres",
    db.Column("id", db.Integer, primary_key=True, autoincrement=True),
    db.Column("movie_id", db.Integer, db.ForeignKey("movies.id", ondelete="CASCADE")),
    db.Column("genre_id", db.Integer, db.ForeignKey("genres.id", ondelete="CASCADE")),
    UniqueConstraint("movie_id", "genre_id", name="unique_movie_id_and_genre_id"),
)

movie_celebrities = db.Table(
    "movie_celebrities",
    db.Column("id", db.Integer, primary_key=True, autoincrement=True),
    db.Column("movie_id", db.Integer, db.ForeignKey("movies.id", ondelete="CASCADE")),
    db.Column(
        "celebrity_id", db.Integer, db.ForeignKey("celebrities.id", ondelete="CASCADE")
    ),
    UniqueConstraint(
        "movie_id", "celebrity_id", name="unique_movie_id_and_celebrity_id"
    ),
)

movie_directors = db.Table(
    "movie_directors",
    db.Column("id", db.Integer, primary_key=True, autoincrement=True),
    db.Column("movie_id", db.Integer, db.ForeignKey("movies.id", ondelete="CASCADE")),
    db.Column(
        "celebrity_id", db.Integer, db.ForeignKey("celebrities.id", ondelete="CASCADE")
    ),
    UniqueConstraint(
        "movie_id", "celebrity_id", name="unique_movie_id_and_celebrity_id"
    ),
)

movie_countries = db.Table(
    "movie_countries",
    db.Column("id", db.Integer, primary_key=True, autoincrement=True),
    db.Column("movie_id", db.Integer, db.ForeignKey("movies.id", ondelete="CASCADE")),
    db.Column(
        "country_id", db.Integer, db.ForeignKey("countries.id", ondelete="CASCADE")
    ),
    UniqueConstraint("movie_id", "country_id", name="unique_movie_id_and_country_id"),
)


class Movie(SearchableMixin, MyBaseModel):
    __tablename__ = "movies"
    __searchable__ = [
        {"key": "title", "weight": 4},
        {"key": "original_title", "weight": 3},
        {"key": "summary", "weight": 1},
    ]

    douban_id = db.Column(db.Integer, unique=True, nullable=True)
    imdb_id = db.Column(db.String(16), unique=True, nullable=True)
    title = db.Column(db.String(64), nullable=False)
    original_title = db.Column(db.String(64))
    subtype = db.Column(db.String(10), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    image_url_last = db.Column(db.String(128), nullable=False)
    seasons_count = db.Column(db.Integer)  # 季数
    episodes_count = db.Column(db.Integer)  # 集数
    current_season = db.Column(db.Integer)  # 当前第几季
    summary = db.Column(db.Text)
    # must be in MovieCinemaStatus
    cinema_status = db.Column(
        db.Integer, default=MovieCinemaStatus.FINISHED, nullable=False
    )
    aka_list = db.Column(db.Text)
    ratings = db.relationship(
        "Rating", backref="movie", lazy="dynamic", cascade="all, delete-orphan"
    )
    genres = db.relationship(
        "Genre",
        secondary="movie_genres",
        backref=db.backref("movies", lazy="dynamic"),
        lazy=True,
    )
    countries = db.relationship(
        "Country",
        secondary="movie_countries",
        backref=db.backref("movies", lazy="dynamic"),
        lazy=True,
    )
    directors = db.relationship(
        "Celebrity",
        secondary="movie_directors",
        backref=db.backref("director_movies", lazy="dynamic"),
        lazy=True,
    )
    celebrities = db.relationship(
        "Celebrity",
        secondary="movie_celebrities",
        backref=db.backref("celebrity_movies", lazy="dynamic"),
        lazy=True,
    )

    @staticmethod
    def create_one(
        title,
        subtype,
        image_url_last,
        year,
        douban_id=None,
        imdb_id=None,
        original_title=None,
        seasons_count=None,
        episodes_count=None,
        current_season=None,
        summary=None,
        cinema_status=MovieCinemaStatus.FINISHED,
        aka_list=[],
        genres_name=[],
        countries_name=[],
        directors_obj=[],
        celebrities_obj=[],
    ):
        if Movie.query.filter(
            or_(Movie.douban_id == douban_id, Movie.imdb_id == imdb_id)
        ).first():
            return None
        else:
            movie = Movie(
                title=title,
                subtype=subtype,
                image_url_last=image_url_last,
                summary=summary,
                douban_id=douban_id,
                imdb_id=imdb_id,
                original_title=original_title,
                year=year,
                seasons_count=seasons_count,
                episodes_count=episodes_count,
                current_season=current_season,
                cinema_status=cinema_status,
                aka_list=" ".join(aka_list),
            )
            for genre_name in genres_name:
                genre_obj = Genre.create_one(genre_name)
                movie.genres.append(genre_obj)
            for country_name in countries_name:
                country_obj = Country.create_one(country_name)
                movie.countries.append(country_obj)
            movie.directors += directors_obj
            movie.celebrities += celebrities_obj
            return movie

    @property
    def score(self):
        score = (
            self.ratings.filter_by(category=RatingType.COLLECT)
            .with_entities(func.avg(Rating.score))
            .all()[0][0]
        )
        try:
            return float(score)
        except TypeError:
            return 0

    @property
    def user_do_rating_query(self):
        return self.ratings.filter_by(category=RatingType.DO)

    @property
    def user_wish_rating_query(self):
        return self.ratings.filter_by(category=RatingType.WISH)

    @property
    def user_collect_query(self):
        return self.ratings.filter_by(category=RatingType.COLLECT)

    @property
    def image_url(self):
        url = current_app.config["CHEVERETO_BASE_URL"]
        return url + self.image_url_last

    def __repr__(self):
        return "<Movie %r>" % self.title


class Tag(MyBaseModel):
    __tablename__ = "tags"
    tag_name = db.Column(db.String(8), unique=True, nullable=False, index=True)

    @staticmethod
    def create_one(tag_name):
        """
        create a tag by tag name and return
        :param tag_name: tag name
        :return: Tag object
        """
        tag = Tag.query.filter_by(tag_name=tag_name).first()
        if tag:
            return tag
        tag = Tag(tag_name=tag_name)
        return tag


rating_tags = db.Table(
    "rating_tags",
    db.Column("id", db.Integer, primary_key=True, autoincrement=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), nullable=False),
    db.Column(
        "rating_id",
        db.Integer,
        db.ForeignKey("ratings.id", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("tag_id", "rating_id", name="unique_tag_id_and_rating_id"),
)

rating_likes = db.Table(
    "rating_likes",
    db.Column("id", db.Integer, primary_key=True, autoincrement=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), nullable=False),
    db.Column(
        "rating_id",
        db.Integer,
        db.ForeignKey("ratings.id", ondelete="CASCADE"),
        nullable=False,
    ),
    db.Column("created_at", db.DateTime, default=datetime.utcnow()),
    UniqueConstraint("user_id", "rating_id", name="unique_user_id_and_rating_id"),
)

rating_reports = db.Table(
    "rating_reports",
    db.Column("id", db.Integer, primary_key=True, autoincrement=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), nullable=False),
    db.Column(
        "rating_id",
        db.Integer,
        db.ForeignKey("ratings.id", ondelete="CASCADE"),
        nullable=False,
    ),
    db.Column("created_at", db.DateTime, default=datetime.utcnow()),
    UniqueConstraint("user_id", "rating_id", name="unique_user_id_and_rating_id"),
)


class Rating(MyBaseModel):
    __tablename__ = "ratings"
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    movie_id = db.Column(
        db.Integer, db.ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    score = db.Column(db.Integer, default=0)
    comment = db.Column(db.Text, default="")
    category = db.Column(TINYINT(1), default=2)  # 0=wish, 1=do, 2=collect
    tags = db.relationship(
        "Tag",
        secondary="rating_tags",
        backref=db.backref("ratings", lazy="dynamic"),
        lazy=True,
    )
    like_by_users = db.relationship(
        "User",
        secondary="rating_likes",
        backref=db.backref("like_ratings", lazy="dynamic"),
        lazy="dynamic",
    )
    report_by_users = db.relationship(
        "User",
        secondary="rating_reports",
        backref=db.backref("report_ratings", lazy="dynamic"),
        lazy="dynamic",
    )

    __table_args__ = (UniqueConstraint("user_id", "movie_id", "category"),)

    def __repr__(self):
        return "<Rating %r>" % self.comment

    @staticmethod
    def create_rating_with_tags(
        score=0, comment="", category=RatingType.COLLECT, tags_name=[]
    ):
        """
        create one rating with tags but not commit
        :param score: score
        :param comment: comment
        :param category: category must be in RatingType
        :return: Rating object
        """
        r = Rating(score=score, comment=comment, category=category)
        for tag_name in tags_name:
            rating_tag = Tag.create_one(tag_name=tag_name)
            r.tags.append(rating_tag)
        return r

    def like_by(self, user):
        """
        :param user:  User
        :return: False or True
        """
        if self.like_by_users.filter_by(id=user.id).first():
            return False
        self.like_by_users.append(user)
        notification = Notification.create_one(
            self.user_id, user.id, NotificationType.RATING_ACTION, rating_id=self.id
        )
        if notification:
            self.user.notifications_received.append(notification)
            user.notifications_sent.append(notification)
        return True

    def unlike_by(self, user):
        """
        :param user: User
        :return: True or False
        """
        if not self.like_by_users.filter_by(id=user.id).first():
            return False
        self.like_by_users.remove(user)
        notification = Notification.query.filter_by(
            receiver_user_id=self.user.id,
            sent_user_id=user.id,
            category=NotificationType.RATING_ACTION,
        ).first()
        if notification:
            self.user.notifications_received.remove(notification)
            user.notifications_sent.remove(notification)
        return True

    def report_by(self, user):
        """
        :param user:
        :return: True or False
        """
        if self.report_by_users.filter_by(id=user.id).first():
            return False
        self.report_by_users.append(user)
        return True


db.event.listen(db.session, "before_commit", User.before_commit)
db.event.listen(db.session, "after_commit", User.after_commit)

db.event.listen(db.session, "before_commit", Movie.before_commit)
db.event.listen(db.session, "after_commit", Movie.after_commit)

db.event.listen(db.session, "before_commit", Celebrity.before_commit)
db.event.listen(db.session, "after_commit", Celebrity.after_commit)
