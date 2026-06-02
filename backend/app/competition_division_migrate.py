"""竞赛学历组别（本科/高职）及报名 division 字段迁移。"""

from __future__ import annotations

import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def migrate_competition_division(engine) -> None:
    with engine.connect() as conn:
        info = conn.execute(text("PRAGMA table_info(competitions)")).fetchall()
        if info:
            cols = {row[1] for row in info}
            for col, ddl in (
                ("division_mode", "VARCHAR(20) NOT NULL DEFAULT 'single'"),
                ("qr_layout", "VARCHAR(20) NOT NULL DEFAULT 'shared'"),
                ("qr_code_path_undergraduate", "VARCHAR(512)"),
                ("qr_code_path_vocational", "VARCHAR(512)"),
            ):
                if col not in cols:
                    try:
                        conn.execute(text(f"ALTER TABLE competitions ADD COLUMN {col} {ddl}"))
                        conn.commit()
                    except Exception:
                        conn.rollback()

        for table in ("competition_enrollments", "teams", "submissions"):
            tinfo = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            if not tinfo:
                continue
            tcols = {row[1] for row in tinfo}
            if "division" not in tcols:
                try:
                    conn.execute(
                        text(
                            f"ALTER TABLE {table} "
                            "ADD COLUMN division VARCHAR(20) NOT NULL DEFAULT 'default'"
                        )
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()

    logger.info("competition division columns migration finished")
