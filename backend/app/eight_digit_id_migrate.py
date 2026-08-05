"""
将既有竞赛 ID、alt_auth 用户 ID 迁移为 8 位数字（仅处理不在合法区间的旧自增 ID）。
"""
from __future__ import annotations

import logging
from typing import Dict, Set

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_compat import disable_foreign_keys, enable_foreign_keys
from app.eight_digit_id import (
    EIGHT_DIGIT_ID_MAX,
    EIGHT_DIGIT_ID_MIN,
    draw_unused_eight_digit_id,
    needs_eight_digit_id_migration,
)

logger = logging.getLogger(__name__)

_COMPETITION_FK_COLUMNS = (
    ("teams", "competition_id"),
    ("competition_enrollments", "competition_id"),
    ("submissions", "competition_id"),
    ("competition_expert_assignments", "competition_id"),
    ("exams", "competition_id"),
)

_ALT_USER_FK_COLUMNS_MAIN = (
    ("competition_enrollments", "student_id"),
    ("teams", "captain_id"),
    ("teams", "created_by_advisor_id"),
    ("teams", "reviewed_by_id"),
    ("team_members", "user_id"),
    ("team_join_requests", "user_id"),
    ("team_join_requests", "reviewed_by_id"),
    ("submissions", "student_id"),
    ("submissions", "submitter_id"),
    ("reviews", "reviewer_id"),
    ("competition_expert_assignments", "expert_id"),
)


def _build_id_mapping(existing_ids: Set[int]) -> Dict[int, int]:
    mapping: Dict[int, int] = {}
    used = set(existing_ids)
    for old_id in sorted(existing_ids):
        if not needs_eight_digit_id_migration(old_id):
            continue
        new_id = draw_unused_eight_digit_id(used)
        mapping[old_id] = new_id
        used.add(new_id)
    return mapping


def migrate_competition_ids_to_eight_digit(engine: Engine) -> None:
    with engine.connect() as conn:
        if not conn.dialect.has_table(conn, "competitions"):
            return
        rows = conn.execute(text("SELECT id FROM competitions")).fetchall()
        existing = {int(r[0]) for r in rows if r[0] is not None}
        mapping = _build_id_mapping(existing)
        if not mapping:
            return
        logger.info("Migrating %s competition id(s) to 8-digit format", len(mapping))
        disable_foreign_keys(conn)
        for old_id, new_id in mapping.items():
            for table, col in _COMPETITION_FK_COLUMNS:
                if not conn.dialect.has_table(conn, table):
                    continue
                conn.execute(
                    text(f"UPDATE {table} SET {col} = :new WHERE {col} = :old"),
                    {"new": new_id, "old": old_id},
                )
            conn.execute(
                text("UPDATE competitions SET id = :new WHERE id = :old"),
                {"new": new_id, "old": old_id},
            )
        enable_foreign_keys(conn)
        conn.commit()


def migrate_alt_user_ids_to_eight_digit(alt_engine: Engine, main_engine: Engine) -> None:
    with alt_engine.connect() as alt_conn:
        if not alt_conn.dialect.has_table(alt_conn, "alt_auth_users"):
            return
        rows = alt_conn.execute(text("SELECT id FROM alt_auth_users")).fetchall()
        existing = {int(r[0]) for r in rows if r[0] is not None}
        mapping = _build_id_mapping(existing)
        if not mapping:
            return
        logger.info("Migrating %s alt_auth user id(s) to 8-digit format", len(mapping))

        disable_foreign_keys(alt_conn)
        for old_id, new_id in mapping.items():
            alt_conn.execute(
                text(
                    "UPDATE alt_auth_users SET school_admin_reviewed_by_id = :new "
                    "WHERE school_admin_reviewed_by_id = :old"
                ),
                {"new": new_id, "old": old_id},
            )
        for old_id, new_id in mapping.items():
            alt_conn.execute(
                text("UPDATE alt_auth_users SET id = :new WHERE id = :old"),
                {"new": new_id, "old": old_id},
            )
        enable_foreign_keys(alt_conn)
        alt_conn.commit()

    with main_engine.connect() as conn:
        disable_foreign_keys(conn)
        for old_id, new_id in mapping.items():
            for table, col in _ALT_USER_FK_COLUMNS_MAIN:
                if not conn.dialect.has_table(conn, table):
                    continue
                conn.execute(
                    text(f"UPDATE {table} SET {col} = :new WHERE {col} = :old"),
                    {"new": new_id, "old": old_id},
                )
        enable_foreign_keys(conn)
        conn.commit()


def run_eight_digit_id_migrations(main_engine: Engine, alt_engine: Engine) -> None:
    try:
        migrate_competition_ids_to_eight_digit(main_engine)
    except Exception as e:
        logger.warning("Competition 8-digit id migration skipped: %s", e)
    try:
        migrate_alt_user_ids_to_eight_digit(alt_engine, main_engine)
    except Exception as e:
        logger.warning("Alt user 8-digit id migration skipped: %s", e)
