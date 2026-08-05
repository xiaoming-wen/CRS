"""
独立数据库连接：默认独立库，与 DATABASE_URL 主业务库互不干扰。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.alt_auth.settings import ALT_AUTH_DATABASE_URL

_is_sqlite = "sqlite" in ALT_AUTH_DATABASE_URL.lower()
_connect_args = {"check_same_thread": False} if _is_sqlite else {}
_engine_kwargs = {"connect_args": _connect_args}
if not _is_sqlite:
    _engine_kwargs["pool_pre_ping"] = True

engine = create_engine(ALT_AUTH_DATABASE_URL, **_engine_kwargs)

SessionAltAuth = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_alt_auth_db():
    """FastAPI Depends 注入用生成器"""
    db = SessionAltAuth()
    try:
        yield db
    finally:
        db.close()
