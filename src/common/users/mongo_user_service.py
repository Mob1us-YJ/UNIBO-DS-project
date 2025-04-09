# src/common/users/mongo_user_service.py

from pymongo import MongoClient
from src.common.users import User, Role
import bcrypt

def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def check_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


class MongoUserService:
    def __init__(self, uri="mongodb://localhost:27017", db_name="mindroll"):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.users = self.db["users"]
        self.users.create_index("username", unique=True)

    def add_user(self, user: User):
        doc = {
            "username": user.username,
            "name": user.name,
            "password": hash_password(user.password),
            "role": user.role.name,
        }
        self.users.insert_one(doc)

    def get_user_by_username(self, username: str) -> User | None:
        doc = self.users.find_one({"username": username})
        if not doc:
            return None
        return User(
            username=doc["username"],
            name=doc.get("name"),
            role=Role[doc.get("role", "USER")],
            password=doc.get("password")
        )

    def validate_credentials(self, username: str, password: str) -> bool:
        user = self.users.find_one({"username": username})
        if not user:
            return False
        hashed = user.get("password")
        return check_password(password, hashed)

    def delete_all_users(self):
        self.users.delete_many({})
