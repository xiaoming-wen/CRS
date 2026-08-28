"""队伍校审字段迁移（school、reviewed_by_id、reviewed_at、review_feedback）。"""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.db_compat import table_columns

logger = logging.getLogger(__name__)


def migrate_competition_team_review(engine) -> None:
    with engine.connect() as conn:
        cols = table_columns(conn, "teams")
        if not cols:
            return
        for col, ddl in (
            ("school", "VARCHAR(200)"),
            ("reviewed_by_id", "INTEGER"),
            ("reviewed_at", "DATETIME"),
            ("review_feedback", "TEXT"),
            ("advisor_name", "VARCHAR(100)"),
            ("second_advisor_id", "INTEGER"),
            ("second_advisor_name", "VARCHAR(100)"),
        ):
            if col not in cols:
                try:
                    conn.execute(text(f"ALTER TABLE teams ADD COLUMN {col} {ddl}"))
                    conn.commit()
                except Exception:
                    conn.rollback()
    logger.info("competition team review columns migration finished")
