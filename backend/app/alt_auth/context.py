"""
第二套 JWT 解析与 FastAPI Depends（不导入 app.security.get_current_user）。
"""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.alt_auth.database import get_alt_auth_db
from app.alt_auth.models import AltAuthUserRecord
from app.alt_auth.token_codec import decode_alt_access_token_strict

_alt_bearer = HTTPBearer(auto_error=False)


async def get_current_alt_identity(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(_alt_bearer)
    ],
    db: Annotated[Session, Depends(get_alt_auth_db)],
) -> AltAuthUserRecord:
    """
    要求请求头：`Authorization: Bearer <第二套 JWT>`。
    与主网关 Token 互不兼容。
    """
    if credentials is None or (credentials.scheme or "").lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header (Bearer alt-identity token required)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_alt_access_token_strict(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired alt-identity token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    uid_s = payload.get("sub")
    try:
        uid = int(uid_s)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token subject")

    row = db.query(AltAuthUserRecord).filter(AltAuthUserRecord.id == uid).first()
    if row is None:
        raise HTTPException(status_code=401, detail="Principal not found")

    if not row.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Alt-identity account is inactive",
        )
    return row


async def get_optional_alt_identity(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(_alt_bearer)
    ],
    db: Annotated[Session, Depends(get_alt_auth_db)],
) -> Optional[AltAuthUserRecord]:
    """
    可选的第二套 JWT：无 Authorization 或令牌无效时返回 None（不抛 401）。
    用于分享链接等匿名可读接口。
    """
    if credentials is None or (credentials.scheme or "").lower() != "bearer":
        return None
    payload = decode_alt_access_token_strict(credentials.credentials)
    if payload is None:
        return None
    uid_s = payload.get("sub")
    try:
        uid = int(uid_s)
    except (TypeError, ValueError):
        return None

    row = db.query(AltAuthUserRecord).filter(AltAuthUserRecord.id == uid).first()
    if row is None or not row.is_active:
        return None
    return row
