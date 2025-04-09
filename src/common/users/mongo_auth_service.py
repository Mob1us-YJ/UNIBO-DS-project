# src/common/users/mongo_auth_service.py

from datetime import datetime, timedelta
from pymongo import MongoClient
import hashlib
from src.common.users import User, Credentials, Token, Role
from src.common.users.mongo_user_service import MongoUserService


def _compute_sha256_hash(input: str) -> str:
    sha256 = hashlib.sha256()
    sha256.update(input.encode("utf-8"))
    return sha256.hexdigest()


class MongoAuthenticationService:
    def __init__(self, user_db: MongoUserService, secret=None, debug: bool = True):
        self._db = user_db
        self._debug = debug
        self._secret = secret or "mindroll-secret"

        self._token_store = self._db.db["tokens"]  # Mongo 中保存 token
        self._token_store.create_index("signature", unique=True)

        if self._debug:
            print(f"[AuthService] Initialized with secret: {self._secret}")

    def authenticate(self, credentials: Credentials, duration: timedelta = None) -> Token:
        if duration is None:
            duration = timedelta(hours=1)

        if not self._db.validate_credentials(credentials.id, credentials.password):
            raise ValueError("Invalid credentials")

        user = self._db.get_user_by_username(credentials.id)
        expiration = datetime.now() + duration
        signature = _compute_sha256_hash(f"{user.username}{expiration}{self._secret}")

        token_obj = Token(user=user, expiration=expiration, signature=signature)

        self._token_store.insert_one({
            "signature": token_obj.signature,
            "username": user.username,
            "expiration": token_obj.expiration
        })

        if self._debug:
            print(f"[AuthService] Issued token for {user.username}: {signature}")

        return token_obj

    def validate_token(self, token: Token) -> bool:
        return token.expiration > datetime.now() and self.__validate_signature(token)

    def validate_token_by_str(self, token_str: str) -> Token | None:
        token_doc = self._token_store.find_one({"signature": token_str})
        if not token_doc:
            return None

        if token_doc["expiration"] <= datetime.now():
            return None

        user = self._db.get_user_by_username(token_doc["username"])
        token_obj = Token(user=user, expiration=token_doc["expiration"], signature=token_doc["signature"])

        if not self.__validate_signature(token_obj):
            return None
        return token_obj

    def __validate_signature(self, token: Token) -> bool:
        expected = _compute_sha256_hash(f"{token.user.username}{token.expiration}{self._secret}")
        return token.signature == expected
