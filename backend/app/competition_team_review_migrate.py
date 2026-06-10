"""队伍校审字段迁移（school、reviewed_by_id、reviewed_at、review_feedback）。"""

from __future__ import annotations

import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def migrate_competition_team_review(engine) -> None:
    with engine.connect() as conn:
        info = conn.execute(text("PRAGMA table_info(teams)")).fetchall()
        if not info:
            return
        cols = {row[1] for row in info}
        for col, ddl in (
            ("school", "VARCHAR(200)"),
            ("reviewed_by_id", "INTEGER"),
            ("reviewed_at", "DATETIME"),
            ("review_feedback", "TEXT"),
            ("advisor_name", "VARCHAR(100)"),
        ):
            if col not in cols:
                try:
                    conn.execute(text(f"ALTER TABLE teams ADD COLUMN {col} {ddl}"))
                    conn.commit()
                except Exception:
                    conn.rollback()
    logger.info("competition team review columns migration finished")
