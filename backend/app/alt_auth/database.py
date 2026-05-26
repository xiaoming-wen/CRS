"""
独立数据库连接：默认独立 SQLite，与 DATABASE_URL/user_management.db 互不干扰。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.alt_auth.settings import ALT_AUTH_DATABASE_URL

_connect_args = (
    {"check_same_thread": False} if "sqlite" in ALT_AUTH_DATABASE_URL.lower() else {}
)

engine = create_engine(ALT_AUTH_DATABASE_URL, connect_args=_connect_args)

SessionAltAuth = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_alt_auth_db():
    """FastAPI Depends 注入用生成器"""
    db = SessionAltAuth()
    try:
        yield db
    finally:
        db.close()
