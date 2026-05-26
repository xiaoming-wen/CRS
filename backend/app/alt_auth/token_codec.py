"""
JWT：独立密钥与声明，不复用主系统 token 逻辑。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.alt_auth.settings import (
    ALT_AUTH_JWT_ALGORITHM,
    ALT_AUTH_JWT_ISSUER,
    ALT_AUTH_JWT_SECRET,
    ALT_AUTH_TOKEN_EXPIRE_MINUTES,
)


def issue_access_token(*, user_id: int, username: str, role: str) -> tuple[str, int]:
    """
    签发访问令牌。

    Returns:
        (token_str, expires_in_seconds)
    """
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=ALT_AUTH_TOKEN_EXPIRE_MINUTES)
    payload = {
        "iss": ALT_AUTH_JWT_ISSUER,
        "sub": str(user_id),
        "acct": username,
        "role": role,
        "kind": "alt_auth_v1",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(
        payload,
        ALT_AUTH_JWT_SECRET,
        algorithm=ALT_AUTH_JWT_ALGORITHM,
    )
    return token, int((exp - now).total_seconds())


def decode_access_token_optional(token: str | None) -> dict | None:
    """兼容旧名：宽松解析。"""
    if not token:
        return None
    try:
        return jwt.decode(
            token,
            ALT_AUTH_JWT_SECRET,
            algorithms=[ALT_AUTH_JWT_ALGORITHM],
            options={"verify_aud": False},
        )
    except JWTError:
        return None


def decode_alt_access_token_strict(token: str | None) -> dict | None:
    """
    校验签名、过期时间、签发方、令牌类型；
    role 须在 payload 中存在（新版本签发）；旧 token 可无 role 视作无效。
    """
    if not token or not str(token).strip():
        return None
    try:
        data = jwt.decode(
            token,
            ALT_AUTH_JWT_SECRET,
            algorithms=[ALT_AUTH_JWT_ALGORITHM],
            issuer=ALT_AUTH_JWT_ISSUER,
            options={"verify_aud": False},
        )
    except JWTError:
        return None

    if data.get("kind") != "alt_auth_v1":
        return None

    rid = data.get("sub")
    role = data.get("role")

    try:
        int(rid)
    except (TypeError, ValueError):
        return None

    # 仅接受签发时写入 role 的令牌，避免误判主站 JWT
    if role is None or role not in ("super_admin", "teacher", "student"):
        return None

    return data
