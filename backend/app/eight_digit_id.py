"""
竞赛用户 ID、竞赛 ID、队伍 ID：8 位十进制整数（10_000_000–99_999_999），各自表内唯一。
"""
from __future__ import annotations

import secrets
from typing import Iterable, Set, Type

from fastapi import HTTPException
from sqlalchemy.orm import Session

EIGHT_DIGIT_ID_MIN = 10_000_000
EIGHT_DIGIT_ID_MAX = 99_999_999
_MAX_ALLOCATE_ATTEMPTS = 256


def is_eight_digit_id(value: int | None) -> bool:
    if value is None:
        return False
    try:
        n = int(value)
    except (TypeError, ValueError):
        return False
    return EIGHT_DIGIT_ID_MIN <= n <= EIGHT_DIGIT_ID_MAX


def needs_eight_digit_id_migration(value: int | None) -> bool:
    if value is None:
        return False
    return not is_eight_digit_id(value)


def validate_eight_digit_id(value: int, *, label: str = "ID") -> int:
    if not is_eight_digit_id(value):
        raise HTTPException(
            status_code=400,
            detail=f"{label} must be a unique 8-digit number ({EIGHT_DIGIT_ID_MIN}–{EIGHT_DIGIT_ID_MAX})",
        )
    return int(value)


def draw_unused_eight_digit_id(used: Set[int]) -> int:
    for _ in range(_MAX_ALLOCATE_ATTEMPTS):
        candidate = secrets.randbelow(EIGHT_DIGIT_ID_MAX - EIGHT_DIGIT_ID_MIN + 1) + EIGHT_DIGIT_ID_MIN
        if candidate not in used:
            return candidate
    raise RuntimeError("Failed to allocate unique 8-digit id")


def allocate_eight_digit_id(db: Session, model: Type, *, used_extra: Iterable[int] | None = None) -> int:
    """在 model 表内分配未占用的 8 位主键 ID。"""
    used: Set[int] = {row[0] for row in db.query(model.id).all() if row[0] is not None}
    if used_extra:
        used.update(int(x) for x in used_extra if x is not None)
    candidate = draw_unused_eight_digit_id(used)
    return candidate
