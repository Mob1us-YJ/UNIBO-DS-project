import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from src.common.users import UserDatabase, Token

class TestAuthentication(unittest.TestCase):
    def test_register_user(self):
        db = UserDatabase()
        result = db.add_user("test_user", "password123")
        self.assertEqual(result, "User test_user created successfully")

    def test_login_valid(self):
        db = UserDatabase()
        db.add_user("test_user", "password123")
        token = db.authenticate("test_user", "password123")
        self.assertIsNotNone(token)

    def test_login_invalid(self):
        db = UserDatabase()
        db.add_user("test_user", "password123")
        token = db.authenticate("test_user", "wrong_password")
        self.assertIsNone(token)