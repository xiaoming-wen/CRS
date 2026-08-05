"""竞赛学历组别（本科/高职）及报名 division 字段迁移。"""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.db_compat import table_columns

logger = logging.getLogger(__name__)


def migrate_competition_division(engine) -> None:
    with engine.connect() as conn:
        cols = table_columns(conn, "competitions")
        if cols:
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
            tcols = table_columns(conn, table)
            if not tcols:
                continue
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
