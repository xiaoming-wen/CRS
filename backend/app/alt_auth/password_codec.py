"""
密码散列（BCrypt），与 app.security.get_password_hash 实现隔离。
不使用 MD5。
"""
from passlib.context import CryptContext

_alt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password_plain(plain_password: str) -> str:
    """生成可入库的 bcrypt 哈希。"""
    return _alt_context.hash(plain_password)


def verify_password_plain(plain_password: str, password_hash: str) -> bool:
    """校验明文与哈希。"""
    try:
        return bool(_alt_context.verify(plain_password, password_hash))
    except Exception:
        return False
