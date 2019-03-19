from datetime import datetime

from flask import current_app, g
from flask_avatars import Identicon
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired


class Role(db.Document):
    name = db.StringField()
    permissions = db.ListField()

    def __repr__(self):
        super().__repr__()
        return '<%s: Role object>' % self.name

    @staticmethod
    def init_role():
        roles_permissions_map = {
            'Locked': ['FOLLOW', 'COLLECT'],
            'User': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD'],
            'Moderator': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD', 'MODERATE'],
            'Administrator': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD', 'MODERATE', 'ADMINISTER']
        }

        for role_name in roles_permissions_map:
            if len(Role.objects(name=role_name)) == 0:
                role = Role(name=role_name,
                            permissions=roles_permissions_map[role_name])
                role.save()
            Role.objects(name=role_name).update(
                permissions=roles_permissions_map[role_name])


class User(db.Document):
    username = db.StringField(required=True)  # weiyi
    email = db.EmailField(required=True)
    password_hash = db.StringField()
    name = db.StringField()
    location = db.StringField()
    created_time = db.DateTimeField(default=datetime.now)
    last_login_time = db.DateTimeField()
    followers_count = db.IntField(default=0)
    followings_count = db.IntField(default=0)
    do_count = db.IntField(default=0)
    wish_count = db.IntField(default=0)
    collect_count = db.IntField(default=0)
    avatar_s = db.StringField()
    avatar_m = db.StringField()
    avatar_l = db.StringField()
    avatar_raw = db.StringField()
    confirmed_email = db.BooleanField(default=False)
    is_deleted = db.BooleanField(default=False)
    is_locked = db.BooleanField(default=False)
    notification_count = db.IntField(default=0)
    role = db.ReferenceField(Role)
    signature=db.StringField()  # 个性签名


    def __repr__(self):
        super().__repr__()
        return '<%s: User object>' % self.username

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generate_avatar()
        self.set_role()
        self.save()

    def generate_token(self, expiration=3600):
        """根据用户id生成带有过期时间的token,默认过期时间为3600秒
        """
        s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
        token = s.dumps({'username': self.username}).decode('ascii')
        return token

    @staticmethod
    def verify_auth_token(token):
        """验证认证token是否正确 ,返回 ``User``
        """
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None  # valid token, but expired
        except BadSignature:
            return None  # invalid token
        user = User.objects(username=data['username'],is_deleted=False).first()
        if user is None:
            return None
        g.current_user=user
        return user

    @staticmethod
    def create_user(username, email, password):
        """ 根据用户名,邮箱,密码创建新用户,返回创建结果 ``True`` or ``False``
        """
        if User.objects(username=username, is_deleted=False).first() or User.objects(email=email, is_deleted=False).first():
            return False
        try:
            user = User(username=username, email=email)
            user.set_password(password)
            user.save()
            return True
        except:
            return False

    def set_role(self):
        # 为新添加的用户设置默认角色
        if self.role == None:
            if self.email == current_app.config['ADMIN_EMAIL']:
                self.role = Role.objects.get(name='Administrator')
            else:
                self.role = Role.objects.get(name='User')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def validate_password(self, password):
        return check_password_hash(self.password_hash, password)

    def follow(self, user):
        """ 关注``user``
        :param user :the instance of ``User``
        """
        if self.username != user.username:
            if not self.is_follow(user):
                follow = Follow(followed=user, follower=self)
                follow.save()
                self.update(inc__followings_count=1)
                user.update(inc__followers_count=1)

    def unfollow(self, user):
        # 取消对 ``user`` 关注
        if self.username != user.username:
            if user.is_follow_by(self):
                follow_ob = Follow.objects(
                    followed=user, follower=self).first()
                follow_ob.update(is_deleted=True)
                Notification.objects(follow_info=follow_ob).delete()
                self.update(dec__followings_count=1)
                user.update(dec__followers_count=1)

    def _update_rating(self, movie):
        # 在用户对电影进行评价后或者更改评价后 更新电影评分,0 分计入评分
        score_sum = Rating.objects(movie=movie).sum('score')

        if movie.rating_count > 0:
            new_score = score_sum/movie.rating_count
            movie.update(set__score=new_score)
        if movie.rating_count == 0:
            movie.update(set__score=0)

    def _rating_on_movie(self, movie, category, score=0, comment=None, tags=None):
        assert score in [x for x in range(0, 11)]
        assert category in [0, 1, 2]
        # 好恶心的代码,自己也不想看,反正测试通过了...
        if not movie.is_deleted:
            last_rating = Rating.objects(
                user=self, movie=movie, is_deleted=False).first()
            if last_rating:
                last_category = last_rating.category
                last_score = last_rating.score
                if last_score > 0:
                    movie.update(dec__rating_count=1)
                    movie.reload()
                if score > 0:
                    last_rating.update(
                        category=category, score=score, comment=comment, tags=tags, rating_time=datetime.now())
                    movie.update(inc__rating_count=1)
                    movie.reload()
                else:
                    last_rating.update(
                        category=category, score=score, comment=comment, tags=tags, rating_time=datetime.now())
                    movie.reload()
                if last_category != category:
                    if last_category == 0:
                        self.update(dec__wish_count=1)
                        movie.update(dec__wish_by_count=1)
                    if last_category == 1:
                        self.update(dec__do_count=1)
                        movie.update(dec__do_by_count=1)
                    if last_category == 2:
                        self.update(dec__collect_count=1)
                        movie.update(dec__collect_by_count=1)
                    if category == 0:
                        self.update(inc__wish_count=1)
                        movie.update(inc__wish_by_count=1)
                    if category == 1:
                        self.update(inc__do_count=1)
                        movie.update(inc__do_by_count=1)
                    if category == 2:
                        self.update(inc__collect_count=1)
                        movie.update(inc__collect_by_count=1)
            else:
                if score:
                    rating = Rating(user=self, movie=movie, category=category,
                                    score=score, comment=comment, tags=tags)
                    movie.update(inc__rating_count=1)
                else:
                    rating = Rating(user=self, movie=movie,
                                    category=category, comment=comment, tags=tags)
                rating.save()
                if category == 0:
                    self.update(inc__wish_count=1)
                    movie.update(inc__wish_by_count=1)
                if category == 1:
                    self.update(inc__do_count=1)
                    movie.update(inc__do_by_count=1)
                if category == 2:
                    self.update(inc__collect_count=1)
                    movie.update(inc__collect_by_count=1)
            movie.reload()
            self._update_rating(movie)

    def wish_movie(self, movie, score=0, comment=None, tags=None):
        self._rating_on_movie(movie, category=0, score=score,
                              comment=comment, tags=tags)

    def do_movie(self, movie, score=0, comment=None, tags=None):
        self._rating_on_movie(movie, category=1, score=score,
                              comment=comment, tags=tags)

    def collect_movie(self, movie, score=0, comment=None, tags=None):
        self._rating_on_movie(movie, category=2, score=score,
                              comment=comment, tags=tags)

    def interest_on_movie(self, movie):
        pass

    def is_follow(self, user):
        if Follow.objects(followed=user, follower=self, is_deleted=False):
            return True
        else:
            return False

    def is_follow_by(self, user):
        if Follow.objects(followed=self, follower=user, is_deleted=False):
            return True
        else:
            return False

    def lock(self):
        self.lock = True
        self.save()

    def unlock(self):
        self.lock = False
        self.save()

    def check_permission(self, permission_name):
        if permission_name in self.role.permissions:
            return True
        return False

    def generate_avatar(self):
        avatar = Identicon()
        filenames = avatar.generate(text=self.username)
        self.avatar_s = filenames[0]
        self.avatar_m = filenames[1]
        self.avatar_l = filenames[2]

    def delete_rating(self, movie):
        rating = Rating.objects(user=self, movie=movie,
                                is_deleted=False).first()
        if rating:
            category = rating.category
            score = rating.score
            rating.update(is_deleted=True)
            if score > 0:
                movie.update(dec__rating_count=1)
            if category == 0:
                self.update(dec__wish_count=1)
                movie.update(dec__wish_by_count=1)
            if category == 1:
                self.update(dec__do_count=1)
                movie.update(dec__do_by_count=1)
            if category == 2:
                self.update(dec__collect_count=1)
                movie.update(dec__collect_by_count=1)
            self.reload()
            movie.reload()
            self._update_rating(movie)


class Movie(db.Document):
    movie_id = db.StringField(required=True)
    title = db.StringField(required=True)
    subtype = db.StringField(required=True)
    wish_by_count = db.IntField(default=0)
    do_by_count = db.IntField(default=0)
    collect_by_count = db.IntField(default=0)
    year = db.IntField()
    image = db.StringField()
    seasons_count = db.IntField()
    episodes_count = db.IntField()
    countrues = db.ListField()
    genres = db.ListField()
    current_season = db.IntField()
    original_title = db.StringField()
    summary = db.StringField()
    aka = db.ListField()
    score = db.FloatField(default=0)
    rating_count = db.IntField(default=0)
    # directors = db.ListField(db.ReferenceField(Celebrity))
    # casts = db.ListField(db.ReferenceField(Celebrity))
    directors = db.ListField()
    casts = db.ListField()
    is_deleted = db.BooleanField()
    created_time = db.DateTimeField(default=datetime.now)

    def __repr__(self):
        super().__repr__()
        return '<%s: Movie object>' % self.movie_id

    def delete_this(self):
        ratings = Rating.objects(movie=self, is_deleted=False)
        for rating in ratings:
            rating.update(is_deleted=True)
            category = rating.category
            if category == 0:
                rating.user.update(dec__wish_count=1)
            if category == 1:
                rating.user.update(dec__do_count=1)
            if category == 2:
                rating.user.update(dec__collect_count=1)
        self.update(is_deleted=True, wish_by_count=0, do_by_count=0,
                    collect_by_count=0, score=0, rating_count=0)


class Follow(db.Document):
    followed = db.ReferenceField(User)
    follower = db.ReferenceField(User)
    follow_time = db.DateTimeField(default=datetime.now)
    is_deleted = db.BooleanField(default=False)

    def __repr__(self):
        super().__repr__()
        return '<%s following %s: Follow object>' % self.follower, self.followed

    def save(self, force_insert=False, validate=True, clean=True, write_concern=None, cascade=None, cascade_kwargs=None, _refs=None, save_condition=None, signal_kwargs=None, **kwargs):
        super().save(force_insert=force_insert, validate=validate, clean=clean, write_concern=write_concern, cascade=cascade,
                     cascade_kwargs=cascade_kwargs, _refs=_refs, save_condition=save_condition, signal_kwargs=signal_kwargs, **kwargs)
        self.add_to_notification()

    def add_to_notification(self):
        follow_notification = Notification(
            receiver=self.followed, category=0, follow_info=self)
        follow_notification.save()


class Rating(db.Document):
    user = db.ReferenceField(User)
    movie = db.ReferenceField(Movie)
    rating_time = db.DateTimeField(default=datetime.now)
    is_deleted = db.BooleanField(default=False)
    score = db.IntField(default=0)
    comment = db.StringField()
    tags = db.ListField()
    like_count = db.IntField(default=0)
    report_count = db.IntField(default=0)
    category = db.IntField()  # 0>wish 1>do 2>collect

    def like_by(self, user):
        if not Like.objects(user=user, rating=self).first():
            like = Like(user=user, rating=self)
            like.save()
            self.update(inc__like_count=1)
            self.save()

    def unlike_by(self, user):
        like = Like.objects(user=user, rating=self)
        if like:
            Notification.objects(like_info=like.first()).delete()
            like.delete()
            self.update(dec__like_count=1)

    def report_by(self, user):
        if not Report.objects(user=user, rating=self) and self.user != user:
            report = Report(user=user, rating=self)
            report.save()
            self.update(inc__report_count=1)


class Celebrity(db.Document):
    celebrity_id = db.StringField(required=True)
    name = db.StringField(required=True)
    genger = db.StringField(required=True)
    avatar = db.StringField()
    created_time = db.DateTimeField(default=datetime.now)
    born_place = db.StringField()
    aka_en = db.ListField()
    name_en = db.StringField()
    aka = db.ListField()
    is_deleted = db.BooleanField()

    def delete_this(self):
        self.is_deleted = True
        self.save()


class Like(db.Document):
    user = db.ReferenceField(User)
    rating = db.ReferenceField(Rating)
    created_time = db.DateTimeField(default=datetime.now)

    def save(self, force_insert=False, validate=True, clean=True, write_concern=None, cascade=None, cascade_kwargs=None, _refs=None, save_condition=None, signal_kwargs=None, **kwargs):
        super().save(force_insert=force_insert, validate=validate, clean=clean, write_concern=write_concern, cascade=cascade,
                     cascade_kwargs=cascade_kwargs, _refs=_refs, save_condition=save_condition, signal_kwargs=signal_kwargs, **kwargs)
        self._add_to_notification()

    def _add_to_notification(self):
        like_notificatrion = Notification(
            receiver=self.rating.user, category=1, like_info=self)
        like_notificatrion.save()


class Report(db.Document):
    user = db.ReferenceField(User)
    rating = db.ReferenceField(Rating)
    created_time = db.DateTimeField(default=datetime.now)


class Notification(db.Document):
    receiver = db.ReferenceField(User)
    is_read = db.BooleanField(default=False)
    category = db.IntField()  # 0>follow 1>like
    like_info = db.ReferenceField(Like)
    follow_info = db.ReferenceField(Follow)
    created_time = db.DateTimeField(default=datetime.now)