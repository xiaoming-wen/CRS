"""独立的时间工具（不引用 app.datetime_utils）。"""
from datetime import datetime, timezone


def utc_now_naive() -> datetime:
    """UTC naive datetime，适配 SQLite DATETIME。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
