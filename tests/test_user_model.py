import unittest
import time

from faker import Faker
from flask import current_app

from app import create_app
from app.sql_models import (User)
from app.extensions import sql_db as db

fake = Faker()


class UserModelsTestCase(unittest.TestCase):

    def setUp(self):
        app = create_app('testing')
        self.context = app.app_context()
        self.context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_password_setter(self):
        """test
        """
        u = User.create_user(username=fake.name(),
                             email=fake.email(), password=fake.password())
        self.assertTrue(u.password_hash is not None)

    def test_password_check(self):
        password = fake.password()
        username = fake.name()
        u = User.create_user(
            username=username, email=fake.email(), password=password)
        db.session.add(u)
        db.session.commit()
        query_user = User.query.filter_by(username=username).first()
        self.assertTrue(query_user.validate_password(password))

    def test_password_salts_are_random(self):
        user_one = User.create_user(username=fake.name(),
                                    email=fake.email(), password='123456')
        user_two = User.create_user(username=fake.name(),
                                    email=fake.email(), password='123456')
        self.assertFalse(user_one.password_hash == user_two.password_hash)

    def test_auth_token_check(self):
        user_one = User.create_user(username="user_one",
                                    email=fake.email(), password='123456')
        token = user_one.generate_token()
        current_user = User.verity_auth_token(token)
        self.assertIsNotNone(current_user)
        self.assertEqual(current_user.username, 'user_one')

        user_one = User.create_user(username="user_one_two",
                                    email=fake.email(), password='123456')
        token = user_one.generate_token(expiration=2)
        time.sleep(3)
        current_user = User.verity_auth_token(token)
        self.assertIsNone(current_user)

    def test_user_role(self):
        admin_user = User.create_user(username="user_two",
                                      email=current_app.config['ADMIN_EMAIL'], password='123456')
        user = User.create_user(username="user_one",
                                email=fake.email(), password='123456')
        for permission_name in current_app.config['ROLES_PERMISSIONS_MAP']['Administrator']:
            self.assertTrue(admin_user.check_permission(permission_name))

        for permission_name in current_app.config['ROLES_PERMISSIONS_MAP']['User']:
            self.assertTrue(user.check_permission(permission_name))

        self.assertFalse(user.check_permission('DELETE_MOVIE'))

    def test_change_user_role(self):
        user = User.create_user(username="user_one",
                                email=fake.email(), password='123456')
        for permission_name in current_app.config['ROLES_PERMISSIONS_MAP']['User']:
            self.assertTrue(user.check_permission(permission_name))
        self.assertFalse(user.check_permission('DELETE_MOVIE'))
        db.session.add(user)
        db.session.commit()

        query_user = User.query.filter_by(username='user_one').first()
        query_user.change_user_role('Administrator')
        for permission_name in current_app.config['ROLES_PERMISSIONS_MAP']['Administrator']:
            self.assertTrue(query_user.check_permission(permission_name))
        self.assertEqual(len(query_user.roles), len(
            current_app.config['ROLES_PERMISSIONS_MAP']['Administrator']))

    def test_lock_user(self):
        user = User.create_user(username="user_one",
                                email=fake.email(), password='123456')
        user.lock_this_user()
        for permission_name in current_app.config['ROLES_PERMISSIONS_MAP']['User']:
            self.assertFalse(user.check_permission(permission_name))

    def test_username_and_email_unique(self):
        user = User.create_user(username="user_one",
                                email='email@email.com', password='123456')
        self.assertIsNotNone(user)
        user_two = User.create_user(username="user_one",
                                    email='email@email.com', password='123456')
        self.assertIsNone(user_two)
        user.delete_self()
        user = User.create_user(username="user_one",
                                email='email@email.com', password='123456')
        self.assertIsNotNone(user)

    def test_follows(self):
        user_one = User.create_user(username="user_one",
                                    email='email@email.com', password='123456')

        user_two = User.create_user(username="user_two",
                                    email='email2@email.com', password='123456')
        self.assertFalse(user_one.is_following(user_two))
        self.assertFalse(user_two.is_following_by(user_one))
        user_one.follow(user_two)
        db.session.commit()
        self.assertTrue(user_one.is_following(user_two))
        self.assertTrue(user_two.is_following_by(user_one))
        self.assertFalse(user_one.is_following_by(user_two))
        self.assertTrue(user_two.is_following_by(user_one))
        self.assertTrue(user_one.followed.count() == 1)
        self.assertTrue(user_two.followers.count() == 1)
        f = user_one.followed.all()[-1]
        self.assertTrue(f == user_two)
        f = user_two.followers.all()[-1]
        self.assertTrue(f == user_one)
        user_one.unfollow(user_two)
        db.session.commit()
        self.assertFalse(user_one.is_following(user_two))
        self.assertFalse(user_two.is_following_by(user_one))
