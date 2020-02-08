import unittest
import time

from faker import Faker
from flask import current_app, g

from app import create_app
from app.const import ROLES_PERMISSIONS_MAP, MovieType, MovieCinemaStatus, GenderType
from app.sql_models import (
    User,
    Movie,
    Celebrity,
    Rating,
    Notification,
    Genre,
    Country,
    Tag,
)
from app.extensions import sql_db as db

fake = Faker()


class UserModelsTestCase(unittest.TestCase):
    def setUp(self):
        app = create_app("testing")
        self.context = app.app_context()
        self.context.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        # db.drop_all()
        self.context.pop()

    def test_password_setter(self):
        """test
        """
        u = User.create_one(
            username=fake.name(), email=fake.email(), password=fake.password()
        )
        self.assertTrue(u.password_hash is not None)

    def test_password_check(self):
        password = fake.password()
        username = fake.name()
        u = User.create_one(username=username, email=fake.email(), password=password)
        db.session.add(u)
        db.session.commit()
        query_user = User.query.filter_by(username=username).first()
        self.assertTrue(query_user.validate_password(password))

    def test_password_salts_are_random(self):
        user_one = User.create_one(
            username=fake.name(), email=fake.email(), password="123456"
        )
        user_two = User.create_one(
            username=fake.name(), email=fake.email(), password="123456"
        )
        self.assertFalse(user_one.password_hash == user_two.password_hash)

    def test_auth_token_check(self):
        user_one = User.create_one(
            username="user_one", email=fake.email(), password="123456"
        )
        db.session.add(user_one)
        db.session.commit()
        token = user_one.generate_token()
        current_user = User.verity_auth_token(token)
        self.assertIsNotNone(current_user)
        self.assertEqual(current_user.username, "user_one")
        self.assertEqual(g.current_user, current_user)
        g.current_user.revoke_auth_token()
        current_user = User.verity_auth_token(token)
        self.assertIsNone(current_user)
        self.assertIsNone(g.current_user)
        user_one = User.create_one(
            username="user_one_two", email=fake.email(), password="123456"
        )
        self.assertNotEqual(g.current_user, user_one)
        token = user_one.generate_token(expiration=2)
        time.sleep(3)
        current_user = User.verity_auth_token(token)
        self.assertIsNone(current_user)

    def test_user_role(self):
        admin_user = User.create_one(
            username="user_two",
            email=current_app.config["ADMIN_EMAIL"],
            password="123456",
        )
        user = User.create_one(
            username="user_one", email=fake.email(), password="123456"
        )
        for permission_name in ROLES_PERMISSIONS_MAP["Administrator"]:
            self.assertTrue(admin_user.check_permission(permission_name))

        for permission_name in ROLES_PERMISSIONS_MAP["User"]:
            self.assertTrue(user.check_permission(permission_name))

        self.assertFalse(user.check_permission("DELETE_MOVIE"))

    def test_change_user_role(self):
        user = User.create_one(
            username="user_one", email=fake.email(), password="123456"
        )
        for permission_name in ROLES_PERMISSIONS_MAP["User"]:
            self.assertTrue(user.check_permission(permission_name))
        self.assertFalse(user.check_permission("DELETE_MOVIE"))
        db.session.add(user)
        db.session.commit()

        query_user = User.query.filter_by(username="user_one").first()
        query_user.change_user_role("Administrator")
        for permission_name in ROLES_PERMISSIONS_MAP["Administrator"]:
            self.assertTrue(query_user.check_permission(permission_name))
        self.assertEqual(
            len(query_user.roles), len(ROLES_PERMISSIONS_MAP["Administrator"])
        )

    def test_lock_user(self):
        user = User.create_one(
            username="user_one", email=fake.email(), password="123456"
        )
        user.lock_this_user()
        for permission_name in ROLES_PERMISSIONS_MAP["User"]:
            self.assertFalse(user.check_permission(permission_name))

    def test_username_and_email_unique(self):
        user = User.create_one(
            username="user_one", email="email@email.com", password="123456"
        )
        self.assertIsNotNone(user)
        user_two = User.create_one(
            username="user_one", email="email@email.com", password="123456"
        )
        self.assertIsNone(user_two)
        db.session.delete(user)
        user = User.create_one(
            username="user_one", email="email@email.com", password="123456"
        )
        self.assertIsNotNone(user)

    def test_follows(self):
        user_one = User.create_one(
            username="user_one", email="email@email.com", password="123456"
        )

        user_two = User.create_one(
            username="user_two", email="email2@email.com", password="123456"
        )
        self.assertFalse(user_one.is_following(user_two))
        self.assertFalse(user_two.is_followed_by(user_one))
        user_one.follow(user_two)
        db.session.commit()
        self.assertTrue(user_one.is_following(user_two))
        self.assertTrue(user_two.is_followed_by(user_one))
        self.assertFalse(user_one.is_followed_by(user_two))
        self.assertTrue(user_two.is_followed_by(user_one))
        self.assertTrue(user_one.followed.count() == 1)
        self.assertTrue(user_two.followers.count() == 1)
        f = user_one.followed.all()[-1]
        self.assertTrue(f == user_two)
        f = user_two.followers.all()[-1]
        self.assertTrue(f == user_one)
        notification = Notification.query.first()
        self.assertEqual(user_one, notification.send_user)
        self.assertEqual(user_two, notification.receiver_user)
        user_one.unfollow(user_two)
        db.session.commit()
        self.assertFalse(user_one.is_following(user_two))
        self.assertFalse(user_two.is_followed_by(user_one))
        notification = Notification.query.first()
        self.assertIsNone(notification)

    def test_create_celebrity(self):
        celebrity_one = Celebrity.create_one(
            name="成龙",
            gender=GenderType.MALE,
            avatar_url_last="backiee-1119391e8a393275e47b82.jpg",
            douban_id="1",
            imdb_id="imdb1",
            born_place="HonKong",
            name_en="ChengLong",
            aka_list=["a", "aa", "aaa"],
            aka_en_list=["A", "AA", "AAA"],
        )

        db.session.add(celebrity_one)
        db.session.commit()
        celebrity_two = Celebrity.create_one(
            name="成龙",
            gender=GenderType.MALE,
            avatar_url_last="backiee-1119391e8a393275e47b82.jpg",
            douban_id="1",
            imdb_id="imdb1",
            born_place="HonKong",
            name_en="ChengLong",
            aka_list=["a", "aa", "aaa"],
            aka_en_list=["A", "AA", "AAA"],
        )
        self.assertIsNone(celebrity_two)
        db.session.delete(celebrity_one)
        db.session.commit()
        celebrity_one = Celebrity.create_one(
            name="成龙",
            gender=GenderType.MALE,
            avatar_url_last="backiee-1119391e8a393275e47b82.jpg",
            douban_id="1",
            imdb_id="imdb1",
            born_place="HonKong",
            name_en="ChengLong",
            aka_list=["a", "aa", "aaa"],
            aka_en_list=["A", "AA", "AAA"],
        )
        self.assertIsNotNone(celebrity_one)
        self.assertEqual(
            celebrity_one.avatar_url,
            current_app.config["CHEVERETO_BASE_URL"] + celebrity_one.avatar_url_last,
        )

    def test_create_and_delete_movie(self):
        celebrity_one = Celebrity.create_one(
            name="成龙",
            gender=GenderType.MALE,
            avatar_url_last="backiee-1119391e8a393275e47b82.jpg",
            douban_id="1",
            imdb_id="imdb1",
            born_place="HonKong",
            name_en="ChengLong",
            aka_list=["a", "aa", "aaa"],
            aka_en_list=["A", "AA", "AAA"],
        )
        celebrity_two = Celebrity.create_one(
            name="成龙",
            gender=GenderType.MALE,
            avatar_url_last="backiee-1119391e8a393275e47b82.jpg",
            douban_id="2",
            imdb_id="imdb2",
            born_place="HonKong",
            name_en="ChengLong",
            aka_list=["a", "aa", "aaa"],
            aka_en_list=["A", "AA", "AAA"],
        )

        movie_one = Movie.create_one(
            title="当幸福来敲门",
            subtype=MovieType.MOVIE,
            image_url_last="backiee-1119391e8a393275e47b82.jpg",
            year=2006,
            douban_id=1,
            imdb_id="imdb2",
            original_title="dang xingfu lai qiaomen",
            seasons_count=1,
            episodes_count=1,
            current_season=1,
            summary="Good",
            cinema_status=MovieCinemaStatus.FINISHED,
            aka_list=["a", "b", "c"],
            genres_name=["励志", "美国"],
            countries_name=["美国", "英国"],
            directors_obj=[celebrity_one],
            celebrities_obj=[celebrity_two],
        )
        db.session.add(movie_one)
        db.session.commit()
        self.assertEqual(
            movie_one.image_url,
            current_app.config["CHEVERETO_BASE_URL"] + movie_one.image_url_last,
        )
        self.assertEqual(len(movie_one.celebrities), 1)
        self.assertEqual(len(movie_one.directors), 1)
        self.assertEqual(len(movie_one.ratings.all()), 0)
        self.assertEqual(Genre.query.count(), 2)
        self.assertEqual(Country.query.count(), 2)
        self.assertEqual(Celebrity.query.count(), 2)
        db.session.delete(celebrity_one)
        db.session.delete(celebrity_two)
        db.session.commit()
        self.assertEqual(len(Movie.query.first().celebrities), 0)
        self.assertEqual(len(Movie.query.first().directors), 0)
        Genre.query.delete()
        Country.query.delete()
        db.session.commit()
        self.assertEqual(Genre.query.count(), 0)
        self.assertEqual(Country.query.count(), 0)
        self.assertEqual(len(Movie.query.first().genres), 0)
        self.assertEqual(len(Movie.query.first().countries), 0)
        Celebrity.query.delete()
        db.session.commit()
        self.assertEqual(len(Movie.query.first().celebrities), 0)
        self.assertEqual(len(Movie.query.first().directors), 0)

    def test_rating(self):
        celebrity_one = Celebrity.create_one(
            name="成龙",
            gender=GenderType.MALE,
            avatar_url_last="backiee-1119391e8a393275e47b82.jpg",
            douban_id="1",
            imdb_id="imdb1",
            born_place="HonKong",
            name_en="ChengLong",
            aka_list=["a", "aa", "aaa"],
            aka_en_list=["A", "AA", "AAA"],
        )
        celebrity_two = Celebrity.create_one(
            name="成龙",
            gender=GenderType.MALE,
            avatar_url_last="backiee-1119391e8a393275e47b82.jpg",
            douban_id="2",
            imdb_id="imdb2",
            born_place="HonKong",
            name_en="ChengLong",
            aka_list=["a", "aa", "aaa"],
            aka_en_list=["A", "AA", "AAA"],
        )

        movie_one = Movie.create_one(
            title="当幸福来敲门",
            subtype=MovieType.TV,
            image_url_last="backiee-1119391e8a393275e47b82.jpg",
            year=2006,
            douban_id=1,
            imdb_id="imdb2",
            original_title="dang xingfu lai qiaomen",
            seasons_count=1,
            episodes_count=1,
            current_season=1,
            summary="Good",
            cinema_status=MovieCinemaStatus.FINISHED,
            aka_list=["a", "b", "c"],
            genres_name=["励志", "美国"],
            countries_name=["美国", "英国"],
            directors_obj=[celebrity_one],
            celebrities_obj=[celebrity_two],
        )
        db.session.add(movie_one)
        db.session.commit()
        self.assertEqual(movie_one.score, 0)
        user_one = User.create_one(
            username="user_one", email=fake.email(), password="123456"
        )
        user_two = User.create_one(
            username="user_two", email=fake.email(), password="123456"
        )
        user_three = User.create_one(
            username="user_three", email=fake.email(), password="123456"
        )
        user_one.wish_movie(movie_one, "Good", tags_name=["G", "O", "D"])
        self.assertEqual(user_one.id, 1)
        self.assertEqual(user_two.id, 2)
        self.assertEqual(user_three.id, 3)
        self.assertEqual(Movie.query.first().score, 0)
        self.assertEqual(Tag.query.count(), 3)
        f = user_two.do_movie(movie_one, 7, "Very Good", tags_name=["V"])
        db.session.commit()
        self.assertTrue(f)
        self.assertEqual(Movie.query.first().score, 0)
        self.assertEqual(Tag.query.count(), 4)
        user_three.collect_movie(movie_one, 6, "Bad", tags_name=["B"])
        db.session.commit()
        self.assertEqual(Movie.query.first().score, 6)
        self.assertEqual(Tag.query.count(), 5)
        self.assertEqual(Rating.query.count(), 3)
        self.assertEqual(user_three.ratings.count(), 1)
        rating_one = movie_one.ratings.first()
        rating_one.like_by(user_two)
        rating_one.report_by(user_three)
        self.assertEqual(user_two.like_ratings.count(), 1)
        self.assertEqual(user_three.report_ratings.count(), 1)
        self.assertEqual(user_one.notifications_received.count(), 1)
        self.assertEqual(user_two.notifications_sent.count(), 1)
        Movie.query.delete()
        db.session.commit()
        self.assertEqual(Rating.query.count(), 0)
        self.assertEqual(user_three.ratings.count(), 0)
        self.assertEqual(Notification.query.count(), 0)
        self.assertEqual(user_one.notifications_received.count(), 0)
        self.assertEqual(user_two.notifications_sent.count(), 0)
        self.assertEqual(user_one.notifications_count, 0)
