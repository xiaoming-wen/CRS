"""
将本地 SQLite（user_management.db / alt_auth.db）数据导入当前 .env 配置的 MySQL。
用法（在 backend 目录）:
  python scripts/migrate_sqlite_to_mysql.py
"""
from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


def _sqlite_engine(path: str) -> Engine | None:
    if not os.path.isfile(path):
        print(f"skip missing sqlite: {path}")
        return None
    return create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})


def _copy_database(src: Engine, dst: Engine, label: str) -> None:
    src_insp = inspect(src)
    dst_insp = inspect(dst)
    tables = src_insp.get_table_names()
    print(f"[{label}] tables: {tables}")

    with dst.begin() as conn:
        if dst.dialect.name == "mysql":
            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))

    for table in tables:
        if not dst_insp.has_table(table):
            print(f"  skip {table}: not in destination schema (run app once to create_all)")
            continue
        src_cols = [c["name"] for c in src_insp.get_columns(table)]
        dst_cols = {c["name"] for c in dst_insp.get_columns(table)}
        cols = [c for c in src_cols if c in dst_cols]
        if not cols:
            continue
        col_list = ", ".join(f"`{c}`" if dst.dialect.name == "mysql" else c for c in cols)
        placeholders = ", ".join(f":{c}" for c in cols)

        with src.connect() as sconn:
            rows = sconn.execute(text(f"SELECT {', '.join(cols)} FROM {table}")).mappings().all()

        if not rows:
            print(f"  {table}: 0 rows")
            continue

        with dst.begin() as dconn:
            if dst.dialect.name == "mysql":
                dconn.execute(text(f"DELETE FROM `{table}`"))
            else:
                dconn.execute(text(f"DELETE FROM {table}"))
            for row in rows:
                payload = {c: row[c] for c in cols}
                dconn.execute(
                    text(f"INSERT INTO `{table}` ({col_list}) VALUES ({placeholders})"),
                    payload,
                )
        print(f"  {table}: {len(rows)} rows")

    with dst.begin() as conn:
        if dst.dialect.name == "mysql":
            conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))


def main() -> None:
    from app.config import get_settings
    from app.alt_auth.settings import ALT_AUTH_DATABASE_URL
    from app.database import UserBase, user_engine
    from app.alt_auth.database import Base as AltBase, engine as alt_engine

    import app.models.user  # noqa: F401
    import app.models.competition  # noqa: F401
    import app.alt_auth.models  # noqa: F401

    settings = get_settings()
    print("MySQL main:", settings.DATABASE_URL)
    print("MySQL alt :", ALT_AUTH_DATABASE_URL)

    UserBase.metadata.create_all(bind=user_engine)
    AltBase.metadata.create_all(bind=alt_engine)

    main_sqlite = _sqlite_engine(os.path.join(PROJECT_ROOT, "user_management.db"))
    alt_sqlite = _sqlite_engine(os.path.join(PROJECT_ROOT, "alt_auth.db"))

    if main_sqlite is not None:
        _copy_database(main_sqlite, user_engine, "competition_user")
    if alt_sqlite is not None:
        _copy_database(alt_sqlite, alt_engine, "competition_alt_auth")

    print("done")


if __name__ == "__main__":
    main()
