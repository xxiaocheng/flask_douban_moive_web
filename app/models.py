from datetime import datetime
from app.extensions import db
from flask_avatars import Identicon
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app


class Role(db.Document):
    name=db.StringField()
    permissions=db.ListField()

    @staticmethod
    def init_role():
        roles_permissions_map = {
            'Locked': ['FOLLOW', 'COLLECT'],
            'User': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD'],
            'Moderator': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD', 'MODERATE'],
            'Administrator': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD', 'MODERATE', 'ADMINISTER']
        }
        
        for role_name in roles_permissions_map:
            if len(Role.objects(name=role_name))==0:
                role=Role(name=role_name,permissions=roles_permissions_map[role_name])
                role.save()
            Role.objects(name=role_name).update(permissions=roles_permissions_map[role_name])


class User(db.Document, UserMixin):
    username = db.StringField(required=True)
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
    role=db.ReferenceField(Role)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generate_avatar()
        self.set_role()
        self.save()

    def set_role(self):
        if self.role==None:
            if self.email == current_app.config['ADMIN_EMAIL']:
                self.role = Role.objects.get(name='Administrator')
            else:
                self.role = Role.objects.get(name='User')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def validate_password(self, password):
        return check_password_hash(self.password_hash, password)

    def follow(self, user):
        """
        :param user :the instance of ``User``
        """
        if not self.is_follow(user):
            follow=Follow(followed=user,follower=self)
            follow.save()
            self.followings_count=self.followings_count+1
            self.save()
            user.followers_count=self.followers_count+1
            user.save()

    def unfollow(self, user):
        if Follow.objects(followed=user,follower=self,is_deleted=False).first():
            Follow.objects(followed=user,follower=self).update(is_deleted=True)
            self.followings_count=self.followings_count-1
            self.save()
            user.followers_count=self.followers_count-1
            user.save()
            
    def _update_rating(self,movie,rating,delete_rating=False):
        """
        :param rating :``Int``
        """
        rating_obj=Rating.objects(user=self,movie=movie,is_deleted=False).first()
        rating_pepple=movie.wish_by_count+movie.do_by_count+movie.collect_by_count
        if not delete_rating:     
            # 当添加新的评分记录时更新电影评分
            
            new_rating=(movie.rating*rating_pepple+rating)/(rating_pepple+1)
            print('onr')
        if delete_rating:
            # 当删除评分记录时更新电影评分
            new_rating=(movie.rating*rating_pepple-rating)/(rating_pepple-1)
            print('tewo')
        Movie.objects(movie_id=movie.movie_id).update(rating=new_rating)
            

    def _rating_on_movie(self,movie,category,rating=None,comment=None,tags=None):
        assert rating in [x for x in range(0,11)] or rating is None
        assert category in [0,1,2]

        # 当评分记录中有当前用户对当前电影评分时候更新此评分记录,并且更新该电影评分
        if Rating.objects(user=self,movie=movie,is_deleted=False):
            last_rating_obj=Rating.objects(user=self,movie=movie,is_deleted=False).first()
            last_category= last_rating_obj.category
            last_rating= last_rating_obj.rating
            if last_category==0:
                self.wish_count-=1
                movie.wish_by_count-=1
                # self.save()
                # movie.save()
            if last_category==1:
                self.do_count-=1
                movie.do_by_count-=1
                # self.save()
                # movie.save()
            if last_category==2:
                self.collect_count-=1
                movie.collect_by_count-=1
                # self.save()
                # movie.save()
            if last_rating:
                self._update_rating(movie,last_rating,delete_rating=True)
            Rating.objects(user=self,movie=movie,is_deleted=False).delete()
            
        rating_obj=Rating(user=self,movie=movie,category=category,rating=rating,comment=comment,tags=tags)
        rating_obj.save()

        if rating:
            self._update_rating(movie,rating,delete_rating=False)
        if category==0:
            self.wish_count+=1
            movie.wish_by_count+=1
            # self.save()
            # movie.save()
        if category==1:
            self.do_count+=1
            movie.do_by_count+=1
            # self.save()
            # movie.save()
        if category==2:
            self.collect_count+=1
            movie.collect_by_count+=1
            # self.save()
            # movie.save()
            
        self.save()
        movie.save()

    def wish_movie(self,movie,rating=None,comment=None,tags=None):
        self._rating_on_movie(movie,category=0,rating=rating,comment=comment,tags=tags)
        

    def do_movie(self,movie,rating=None,comment=None,tags=None):
        self._rating_on_movie(movie,category=1,rating=rating,comment=comment,tags=tags)


    def collect_movie(self, movie,rating=None,comment=None,tags=None):
        self._rating_on_movie(movie,category=2,rating=rating,comment=comment,tags=tags)

    def is_wish(self,movie):
        pass
    
    def is_do(self,movie):
        pass

    def is_collect(self,movie):
        pass

    def is_follow(self, user):
        pass

    def is_follow_by(self, user):
        pass

    def lock(self):
        pass

    def unlock(self):
        pass

    def delete_this(self):
        pass

    def check_permission(self, permission_name):
        pass

    def generate_avatar(self):
        avatar = Identicon()
        filenames = avatar.generate(text=self.username)
        self.avatar_s = filenames[0]
        self.avatar_m = filenames[1]
        self.avatar_l = filenames[2]


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
    rating = db.FloatField(default=0)
    directors = db.ListField()
    casts = db.ListField()
    is_deleted = db.BooleanField()
    created_time = db.DateTimeField(default=datetime.now)

    def delete_this(self):
        pass


class Follow(db.Document):
    followed = db.ReferenceField(User)
    follower = db.ReferenceField(User)
    follow_time = db.DateTimeField(default=datetime.now)
    is_deleted = db.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    # add it to notifations

    
    def delete_this(self):
        pass


class Rating(db.Document):
    user = db.ReferenceField(User)
    movie = db.ReferenceField(Movie)
    rating_time = db.DateTimeField(default=datetime.now)
    is_deleted = db.BooleanField(default=False)
    rating = db.IntField(default=0)
    comment = db.StringField()
    tags = db.ListField()
    like_count = db.IntField(default=0)
    report_count = db.IntField(default=0)
    category=db.IntField() # 0>wish 1>do 2>collect 


    def like_by(self, user):
        pass

    def unlike_by(self, user):
        pass

    def report_by(self, by):
        pass

    def delete_this(self):
        pass


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
        pass


class Like(db.Document):
    user = db.ReferenceField(User)
    rating = db.ReferenceField(Rating)
    created_time = db.DateTimeField(default=datetime.now)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pass


class Report(db.Document):
    user = db.ReferenceField(User)
    rating = db.ReferenceField(Rating)
    created_time = db.DateTimeField(default=datetime.now)


class Notification(db.Document):
    receiver_id = db.ReferenceField(User)
    is_read = db.BooleanField()
    category = db.IntField()  # 0>follow 1>like
    like_info = db.ReferenceField(Like)
    follow = db.ReferenceField(Follow)

