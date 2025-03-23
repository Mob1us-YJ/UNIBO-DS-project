import json
import os
import hashlib
import uuid
import sys
from enum import Enum
from datetime import datetime, timedelta, timezone


# Enum for user roles
class Role(Enum):
    ADMIN = "admin"
    USER = "user"


# User class with authentication and scoring
class User:
    def __init__(self, username, email, full_name, role, password, score=0):
        self.username = username
        self.email = email
        self.full_name = full_name
        
        self.role = Role(role) if isinstance(role, str) else role

       
        if len(password) == 64 and all(c in "0123456789abcdef" for c in password):
            self.password = password
        else:
            self.password = self.hash_password(password)

        self.score = score

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password):
        input_hash = hashlib.sha256(password.encode()).hexdigest()
        print(f"DEBUG: Input password hash: {input_hash}")
        print(f"DEBUG: Stored password hash: {self.password}")
        return self.password == input_hash

    def to_dict(self):
        return {
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value,
            "password": self.password,
            "score": self.score
        }

    @staticmethod
    def from_dict(data):
        return User(
            username=data["username"],
            email=data["email"],
            full_name=data["full_name"],
            role=data["role"],
            password=data["password"],
            score=data.get("score", 0)
        )


class Token:
    def __init__(self, user, expiration_minutes=60):
        self.user = user
        self.token = str(uuid.uuid4())
        self.expiration = datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)

    def is_valid(self):
        return datetime.now(timezone.utc) < self.expiration

    def to_dict(self):
        return {
            "token": self.token,
            "username": self.user.username,
            "expiration": self.expiration.isoformat(),
        }


class UserDatabase:
    def __init__(self, filename="users.json"):
        self.filename = filename
        self.users = self.load_users()

    def load_users(self):
        if os.path.exists(self.filename):
            with open(self.filename, "r") as file:
                try:
                    data = json.load(file)
                    return {u["username"]: User.from_dict(u) for u in data}
                except json.JSONDecodeError:
                    return {}
        return {}

    def save_users(self):
        with open(self.filename, "w") as file:
            json.dump([user.to_dict() for user in self.users.values()], file, indent=4)

    def add_user(self, username, password):
        """
        Only need (username, password). We'll fill in the rest:
         - email = "N/A"
         - full_name = username
         - role = "user"
        """
        if username in self.users:
            return "User already exists"


        new_user = User(
            username=username,
            email="N/A",
            full_name=username,
            role="user",
            password=password
        )
        self.users[username] = new_user
        self.save_users()
        return f"User {username} created successfully"

    def get_user(self, username):
        return self.users.get(username)

    def authenticate(self, username, password):
        user = self.get_user(username)
        
        if user:
            print(f"DEBUG: Found user {username}, checking password...")
            print(f"DEBUG: Stored hash: {user.password}")
            print(f"DEBUG: Input hash: {hashlib.sha256(password.encode()).hexdigest()}")

            if user.check_password(password):
                print("✅ Password Matched! Authentication Successful")
                return Token(user)
            else:
                print("❌ Password Mismatch!")
        print("DEBUG: Authentication failed (wrong credentials)")
        return None

    def update_score(self, username, score_change):
        if username in self.users:
            self.users[username].score += score_change
            self.save_users()
            return f"Updated score for {username}: {self.users[username].score}"
        return "User not found"


if __name__ == "__main__":
    user_db = UserDatabase()

    if len(sys.argv) < 2:
        print("Usage: python example0_users.py <command> [options]")
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "add":
            #--user, --password
            username = sys.argv[sys.argv.index("--user") + 1]
            password = sys.argv[sys.argv.index("--password") + 1]
            result = user_db.add_user(username, password)
            print(result)

        elif command == "auth":
            # --user, --password, --save-token
            username = sys.argv[sys.argv.index("--user") + 1]
            password = sys.argv[sys.argv.index("--password") + 1]
            token_file = sys.argv[sys.argv.index("--save-token") + 1]
            token = user_db.authenticate(username, password)
            if token:
                with open(token_file, "w") as f:
                    json.dump(token.to_dict(), f)
                print(f"Authentication successful, token saved to {token_file}")
            else:
                print("Authentication failed")

        elif command == "get":
            #  --user
            username = sys.argv[sys.argv.index("--user") + 1]
            user = user_db.get_user(username)
            if user:
                print(json.dumps(user.to_dict(), indent=4))
            else:
                print("User not found")

        elif command == "update_score":
            #  --user, --score
            username = sys.argv[sys.argv.index("--user") + 1]
            score_change = int(sys.argv[sys.argv.index("--score") + 1])
            print(user_db.update_score(username, score_change))

        else:
            print("Invalid command")

    except (ValueError, IndexError):
        print("Error: Missing or incorrect parameters for command")
