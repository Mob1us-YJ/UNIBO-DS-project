from ..users import *
import hashlib
from datetime import datetime, timedelta

def _compute_sha256_hash(input: str) -> str:
    sha256_hash = hashlib.sha256()
    sha256_hash.update(input.encode('utf-8'))
    return sha256_hash.hexdigest()

class _Debuggable:
    def __init__(self, debug: bool = True):
        self.__debug = debug
    
    def _log(self, *args, **kwargs):
        if self.__debug:
            print(*args, **kwargs)

class InMemoryUserDatabase(UserDatabase, _Debuggable):
    def __init__(self, debug: bool = True):
        _Debuggable.__init__(self, debug)
        self.__users: dict[str, User] = {}
        self._log("User database initialized with empty users")
    
    def add_user(self, user: User):
        # 1) 检查用户名是否已经存在
        if user.username in self.__users:
            raise ValueError(f"User with ID {user.username} already exists")
        
        # 2) 检查密码是否为空
        if user.password is None:
            raise ValueError("Password digest is required")

        # 3) 若密码还没哈希，则哈希
        user = user.copy(password=_compute_sha256_hash(user.password))

        # 4) 只用 user.username 作为key，存到 self.__users
        self.__users[user.username] = user

        # 5) 记录日志
        self._log(f"Add: {user}")


    def __get_user(self, id: str) -> User:
        if id not in self.__users:
            raise KeyError(f"User with ID {id} not found")
        return self.__users[id]
    
    def get_user(self, id: str) -> User:
        result = self.__get_user(id).copy(password=None)
        self._log(f"Get user with ID {id}: {result}")
        return result

    def check_password(self, credentials: Credentials) -> bool:
        try:
            user = self.__get_user(credentials.id)
            result = user.password == _compute_sha256_hash(credentials.password)
        except KeyError:
            result = False
        self._log(f"Checking {credentials}: {'correct' if result else 'incorrect'}")
        return result
    

class InMemoryAuthenticationService(AuthenticationService, _Debuggable):
    """
    增加了 self.__tokens，用 signature 作为字典key，并提供 validate_token_by_str(token_str) 以支持服务器鉴权
    """
    def __init__(self, database: UserDatabase, secret: str = None, debug: bool = True):
        _Debuggable.__init__(self, debug)
        self.__database = database
        if not secret:
            import uuid
            secret = str(uuid.uuid4())
        self.__secret = secret
        self._log(f"Authentication service initialized with secret {secret}")

        # ★ 新增一个字典用于存储发放的 Token：key=token.signature, value=Token
        self.__tokens = {}

    def authenticate(self, credentials: Credentials, duration: timedelta = None) -> Token:
        if duration is None:
            duration = timedelta(days=1)
        if self.__database.check_password(credentials):
            expiration = datetime.now() + duration
            user = self.__database.get_user(credentials.id)
            # signature 等于对 (user + expiration + secret) 做 sha256
            signature = _compute_sha256_hash(f"{user}{expiration}{self.__secret}")
            result = Token(user, expiration, signature)
            self._log(f"Generate token for user {credentials.id}: {result}")

            # ★ 将生成的 Token 存储起来，key=signature
            self.__tokens[result.signature] = result
            return result
        raise ValueError("Invalid credentials")
    
    def __validate_token_signature(self, token: Token) -> bool:
        expected = _compute_sha256_hash(f"{token.user}{token.expiration}{self.__secret}")
        return token.signature == expected

    def validate_token(self, token: Token) -> bool:
        """
        旧方法：如果 token 在过期时间内，且签名校验通过，就认为 valid
        """
        result = token.expiration > datetime.now() and self.__validate_token_signature(token)
        self._log(f"{token} is " + ('valid' if result else 'invalid'))
        return result

    def validate_token_by_str(self, token_str: str) -> Token | None:
        """
        新方法：服务器端 (__check_authorization) 会传入 token_str=signature。
        我们在 self.__tokens 中找对应 Token 对象，并检查是否过期、签名是否一致
        """
        token_obj = self.__tokens.get(token_str)
        if not token_obj:
            return None
        # 检查过期
        if token_obj.expiration <= datetime.now():
            return None
        # 检查签名
        if not self.__validate_token_signature(token_obj):
            return None
        return token_obj
