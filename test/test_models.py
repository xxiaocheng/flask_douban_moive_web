import unittest

from faker import Faker
from flask import current_app

from app import create_app
from app.models import (Follow, Like, Movie, Notification, Rating, Report,
                        Role, User)
from app.extensions import db

fake = Faker()


class ModelsTestCase(unittest.TestCase):

    def setUp(self):
        super().setUp()
        app = create_app('testing')

        self.context = app.test_request_context()
        self.context.push()
        self.client = app.test_client()
        self.runner = app.test_cli_runner()

        Role.objects.delete()
        User.objects.delete()
        Movie.objects.delete()
        Rating.objects.delete()
        Follow.objects.delete()
        Notification.objects.delete()
        Report.objects.delete()
        Like.objects.delete()

        Role.init_role()

        for i in range(10):
            user = User(username=fake.word(), email=fake.email())
            user.set_password(fake.password())
            user.save()
            movie = Movie(movie_id=fake.md5(),
                          title=fake.word(), subtype=fake.word())
            movie.save()

    def test_follow(self):
        user_list = User.objects()
        user_a = user_list[0]
        user_b = user_list[1]
        user_c = user_list[3]
        user_a.follow(user_b)
        user_a.follow(user_c)
        user_a.follow(user_a)
        user_b.follow(user_a)
        user_b.follow(user_b)
        user_b.follow(user_c)
        user_c.follow(user_a)
        user_c.follow(user_b)
        user_c.follow(user_c)

        user_a.reload()
        user_b.reload()
        user_c.reload()

        self.assertEqual(len(Follow.objects(is_deleted=False)), 6)
        self.assertEqual(user_a.followers_count, 2)
        self.assertEqual(user_b.followers_count, 2)
        self.assertEqual(user_c.followers_count, 2)
        self.assertEqual(user_a.followings_count, 2)
        self.assertEqual(user_b.followings_count, 2)
        self.assertEqual(user_c.followings_count, 2)

        self.assertTrue(user_a.is_follow(user_b))
        self.assertTrue(user_a.is_follow(user_c))
        self.assertTrue(user_b.is_follow(user_c))
        self.assertFalse(user_a.is_follow(user_a))

        user_a.unfollow(user_b)
        user_a.unfollow(user_c)
        user_a.unfollow(user_a)
        user_b.unfollow(user_a)
        user_b.unfollow(user_b)
        user_b.unfollow(user_c)
        user_c.unfollow(user_a)
        user_c.unfollow(user_b)
        user_c.unfollow(user_c)

        user_a.reload()
        user_b.reload()
        user_c.reload()

        self.assertEqual(len(Follow.objects(is_deleted=False)), 0)

        self.assertEqual(user_a.followers_count, 0)
        self.assertEqual(user_b.followers_count, 0)
        self.assertEqual(user_c.followers_count, 0)
        self.assertEqual(user_a.followings_count, 0)
        self.assertEqual(user_b.followings_count, 0)
        self.assertEqual(user_c.followings_count, 0)

    def test_rating(self):
        user_list = User.objects()
        user_a = user_list[0]
        user_b = user_list[1]
        movie_list = Movie.objects()
        movie_a = movie_list[0]
        movie_b = movie_list[1]
        user_a.wish_movie(movie_a)
        user_a.reload()
        movie_a.reload()
        user_a.do_movie(movie_a)
        user_a.reload()
        movie_a.reload()
        user_a.collect_movie(movie_a)
        user_a.reload()
        movie_a.reload()
        self.assertEqual(user_a.collect_count, 1)
        self.assertEqual(user_a.wish_count, 0)
        self.assertEqual(user_a.do_count, 0)
        self.assertEqual(movie_a.collect_by_count, 1)
        self.assertEqual(movie_a.wish_by_count, 0)
        self.assertEqual(movie_a.do_by_count, 0)

        user_b.wish_movie(movie_a, score=5)
        user_b.reload()
        movie_a.reload()
        user_b.do_movie(movie_a, score=8)
        user_b.reload()
        movie_a.reload()
        user_b.collect_movie(movie_a, score=10)
        user_b.reload()
        movie_a.reload()
        self.assertEqual(user_a.collect_count, 1)
        self.assertEqual(user_b.collect_count, 1)
        self.assertEqual(user_a.wish_count, 0)
        self.assertEqual(user_a.do_count, 0)
        self.assertEqual(movie_a.collect_by_count, 2)
        self.assertEqual(movie_a.wish_by_count, 0)
        self.assertEqual(movie_a.do_by_count, 0)
        self.assertEqual(movie_a.rating_count, 1)
        self.assertEqual(movie_a.score, 10)

        user_a.collect_movie(movie_a, score=5)
        user_a.reload()
        movie_a.reload()
        self.assertEqual(movie_a.rating_count, 2)
        self.assertEqual(movie_a.score, 7.5)
        self.assertEqual(movie_a.collect_by_count, 2)

        user_a.wish_movie(movie_a)
        user_a.reload()
        movie_a.reload()
        user_a.do_movie(movie_a)
        user_a.reload()
        movie_a.reload()
        user_a.collect_movie(movie_a)
        user_a.reload()
        movie_a.reload()

        self.assertEqual(movie_a.rating_count, 1)
        self.assertEqual(movie_a.score, 10)

        user_a.wish_movie(movie_a, score=5)
        user_a.reload()
        movie_a.reload()
        user_a.do_movie(movie_a, score=8)
        user_a.reload()
        movie_a.reload()
        user_a.collect_movie(movie_a, score=5)
        user_a.reload()
        movie_a.reload()
        self.assertEqual(movie_a.wish_by_count, 0)
        self.assertEqual(movie_a.do_by_count, 0)
        self.assertEqual(movie_a.collect_by_count, 2)
        self.assertEqual(movie_a.rating_count, 2)
        self.assertEqual(movie_a.score, 7.5)
        user_a.wish_movie(movie_b, score=5)
        user_a.reload()
        movie_b.reload()
        user_a.do_movie(movie_b, score=8)
        user_a.reload()
        movie_b.reload()
        user_a.collect_movie(movie_b, score=5)
        user_a.reload()
        movie_b.reload()
        self.assertEqual(user_a.collect_count, 2)
        self.assertEqual(movie_b.rating_count, 1)
        self.assertEqual(movie_b.score, 5)

    def test_delete_rating(self):
        user_list = User.objects()
        user_a = user_list[0]
        user_b = user_list[1]
        movie_list = Movie.objects()
        movie_a = movie_list[0]
        movie_b = movie_list[1]
        user_a.wish_movie(movie_a)
        user_a.delete_rating(movie_a)
        user_a.reload()
        movie_a.reload()
        self.assertEqual(user_a.wish_count, 0)
        self.assertEqual(movie_a.wish_by_count, 0)
        user_b.wish_movie(movie_b, score=5)
        user_b.reload()
        movie_b.reload()
        self.assertEqual(movie_b.wish_by_count, 1)
        self.assertEqual(user_b.wish_count, 1)
        self.assertEqual(movie_b.rating_count, 1)
        self.assertEqual(movie_b.score, 5)

        user_b.delete_rating(movie_b)
        user_b.reload()
        movie_b.reload()
        self.assertEqual(movie_b.wish_by_count, 0)
        self.assertEqual(user_b.wish_count, 0)
        self.assertEqual(movie_b.rating_count, 0)
        self.assertEqual(movie_b.score, 0)

    def test_delete_movie(self):
        user_list = User.objects()
        user_a = user_list[0]
        user_b = user_list[1]
        movie_list = Movie.objects()
        movie_a = movie_list[0]
        user_a.wish_movie(movie_a)
        movie_a.reload()
        user_b.wish_movie(movie_a)
        user_a.reload()
        movie_a.reload()
        user_b.reload()
        self.assertEqual(movie_a.wish_by_count, 2)
        movie_a.delete_this()
        movie_a.reload()
        user_a.reload()
        user_b.reload()
        self.assertEqual(user_a.wish_count, 0)
        self.assertEqual(user_b.wish_count, 0)

        user_a.wish_movie(movie_a)
        movie_a.reload()
        user_b.wish_movie(movie_a)
        user_a.reload()
        movie_a.reload()
        user_b.reload()
        self.assertEqual(movie_a.wish_by_count, 0)
        self.assertEqual(user_a.wish_count, 0)
        self.assertEqual(user_b.wish_count, 0)

    def test_password_check(self):
        user = User(username=fake.word(), email=fake.email())
        user.set_password('666')
        user.save()
        user.reload()
        self.assertEqual(user.validate_password('666'), True)

    def test_check_permission(self):
        user = User(username=fake.word(), email=fake.email())
        user.set_password('666')
        user.save()
        admin = User(username=fake.word(),
                     email=current_app.config['ADMIN_EMAIL'])
        admin.save()
        self.assertFalse(user.check_permission('ADMINISTER'))
        self.assertTrue(user.check_permission('COLLECT'))
        self.assertTrue(admin.check_permission('ADMINISTER'))

    def test_add_like_to_notification(self):
        user_list = User.objects()
        user_a = user_list[0]
        user_b = user_list[1]
        movie_list = Movie.objects()
        movie_a = movie_list[0]
        movie_b = movie_list[1]
        user_a.wish_movie(movie_a)
        user_b.collect_movie(movie_b)
        user_a.reload()
        user_b.reload()
        movie_a.reload()
        movie_b.reload()
        rating_a2a = Rating.objects(user=user_a, movie=movie_a).first()
        rating_a2a.save()
        rating_a2a.like_by(user_b)
        rating_a2a.reload()
        self.assertEqual(rating_a2a.like_count, 1)
        like_a2_a2a = Like.objects(user=user_b, rating=rating_a2a)
        self.assertEqual(len(like_a2_a2a), 1)
        self.assertEqual(len(Notification.objects(
            like_info=like_a2_a2a.first())), 1)
        rating_a2a.unlike_by(user_b)
        rating_a2a.reload()
        user_b.reload()
        like_a2_a2a = Like.objects(user=user_b, rating=rating_a2a)
        self.assertEqual(rating_a2a.like_count, 0)
        self.assertEqual(len(like_a2_a2a), 0)
        self.assertEqual(len(Notification.objects(
            like_info=like_a2_a2a.first())), 0)
        
    def test_add_follow_to_nofication(self):
        user_list = User.objects()
        user_a = user_list[0]
        user_b = user_list[1]
        user_a.follow(user_b)
        notification=Notification.objects(receiver=user_b,category=0).first()
        self.assertEqual(len(Notification.objects(receiver=user_b)),1)
        self.assertEqual(notification.follow_info.follower,user_a)
        user_a.reload()
        user_b.reload()
        user_a.unfollow(user_b)
        self.assertEqual(len(Notification.objects(receiver=user_a,category=0)),0)

    def test_report(self):
        user_list = User.objects()
        user_a = user_list[0]
        user_b = user_list[1]
        movie_list = Movie.objects()
        movie_a = movie_list[0]
        user_a.wish_movie(movie_a)
        rating=Rating.objects(user=user_a,movie=movie_a,is_deleted=False)
        rating.first().report_by(user_a)
        self.assertEqual(len(Report.objects()),0)
        rating.first().report_by(user_b)
        report=Report.objects(rating=rating.first()).first()
        self.assertEqual(report.user,user_b)
        

        

    def tearDown(self):
        self.context.pop()
        Role.objects.delete()
        User.objects.delete()
        Movie.objects.delete()
        Rating.objects.delete()
        Follow.objects.delete()
        Notification.objects.delete()
        Report.objects.delete()
        Like.objects.delete()