"""数据库方言兼容工具（SQLite / MySQL）。"""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, Engine


def is_sqlite(bind: Engine | Connection) -> bool:
    return bind.dialect.name == "sqlite"


def is_mysql(bind: Engine | Connection) -> bool:
    return bind.dialect.name == "mysql"


def table_columns(conn: Connection, table: str) -> set[str]:
    """返回表字段名集合；表不存在时返回空集。"""
    insp = inspect(conn)
    if not insp.has_table(table):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def disable_foreign_keys(conn: Connection) -> None:
    if is_sqlite(conn):
        conn.execute(text("PRAGMA foreign_keys=OFF"))
    elif is_mysql(conn):
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))


def enable_foreign_keys(conn: Connection) -> None:
    if is_sqlite(conn):
        conn.execute(text("PRAGMA foreign_keys=ON"))
    elif is_mysql(conn):
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
