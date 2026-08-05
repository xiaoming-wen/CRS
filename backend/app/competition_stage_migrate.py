"""竞赛初赛/决赛字段与晋级表迁移。"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text

from app.db_compat import is_mysql, is_sqlite, table_columns

logger = logging.getLogger(__name__)


def migrate_competition_stage(engine) -> None:
    with engine.connect() as conn:
        cols = table_columns(conn, "competitions")
        if cols:
            for col, ddl in (
                ("series_id", "INTEGER"),
                ("stage", "VARCHAR(20) NOT NULL DEFAULT 'single'"),
                ("paired_competition_id", "INTEGER"),
            ):
                if col not in cols:
                    try:
                        conn.execute(text(f"ALTER TABLE competitions ADD COLUMN {col} {ddl}"))
                        conn.commit()
                    except Exception:
                        conn.rollback()

        insp = inspect(conn)
        if insp.has_table("competition_promotions"):
            logger.info("competition stage / promotions migration finished")
            return

        if is_sqlite(conn):
            ddl = """
                CREATE TABLE competition_promotions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_competition_id INTEGER NOT NULL,
                    to_competition_id INTEGER NOT NULL,
                    source_team_id INTEGER,
                    source_student_id INTEGER,
                    final_team_id INTEGER,
                    promoted_by INTEGER NOT NULL,
                    created_at DATETIME,
                    CONSTRAINT uq_promo_final_source_team UNIQUE (to_competition_id, source_team_id),
                    CONSTRAINT uq_promo_final_source_student UNIQUE (to_competition_id, source_student_id)
                )
            """
        elif is_mysql(conn):
            ddl = """
                CREATE TABLE competition_promotions (
                    id INTEGER NOT NULL AUTO_INCREMENT,
                    from_competition_id INTEGER NOT NULL,
                    to_competition_id INTEGER NOT NULL,
                    source_team_id INTEGER NULL,
                    source_student_id INTEGER NULL,
                    final_team_id INTEGER NULL,
                    promoted_by INTEGER NOT NULL,
                    created_at DATETIME NULL,
                    PRIMARY KEY (id),
                    UNIQUE KEY uq_promo_final_source_team (to_competition_id, source_team_id),
                    UNIQUE KEY uq_promo_final_source_student (to_competition_id, source_student_id),
                    KEY ix_competition_promotions_from (from_competition_id),
                    KEY ix_competition_promotions_to (to_competition_id)
                )
            """
        else:
            logger.info("competition_promotions: rely on create_all for dialect %s", conn.dialect.name)
            return

        try:
            conn.execute(text(ddl))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.warning("competition_promotions create skipped: %s", e)

    logger.info("competition stage / promotions migration finished")
