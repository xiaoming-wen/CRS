"""将 competition_enrollments 迁移为支持个人+组队双赛道报名。"""

from __future__ import annotations

import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def migrate_competition_enrollment_dual_track(engine) -> None:
    with engine.connect() as conn:
        info = conn.execute(text("PRAGMA table_info(competition_enrollments)")).fetchall()
        if not info:
            return
        cols = {row[1] for row in info}
        ddl_row = conn.execute(
            text(
                "SELECT sql FROM sqlite_master WHERE type='table' "
                "AND name='competition_enrollments'"
            )
        ).fetchone()
        ddl = (ddl_row[0] or "") if ddl_row else ""

        needs_rebuild = "uq_competition_student_scope" not in ddl and (
            "uq_competition_student" in ddl or "enrollment_scope" not in cols
        )

        if needs_rebuild:
            _rebuild_enrollments_table(conn)
            conn.commit()
            logger.info("competition_enrollments migrated to dual-track (individual + team)")
            return

        if "enrollment_scope" not in cols:
            try:
                conn.execute(
                    text(
                        "ALTER TABLE competition_enrollments "
                        "ADD COLUMN enrollment_scope VARCHAR(20) NOT NULL DEFAULT 'individual'"
                    )
                )
                conn.commit()
            except Exception:
                conn.rollback()

        conn.execute(
            text(
                "UPDATE competition_enrollments SET enrollment_scope = 'team' "
                "WHERE team_id IS NOT NULL"
            )
        )
        conn.commit()


def _rebuild_enrollments_table(conn) -> None:
    info = conn.execute(text("PRAGMA table_info(competition_enrollments)")).fetchall()
    col_names = [row[1] for row in info]
    optional = {
        "student_no": "VARCHAR(50)",
        "real_name": "VARCHAR(100)",
        "college": "VARCHAR(200)",
        "grade": "VARCHAR(50)",
        "contact": "VARCHAR(100)",
    }
    opt_select = []
    opt_insert = []
    for name, sql_type in optional.items():
        if name in col_names:
            opt_select.append(name)
            opt_insert.append(name)
        else:
            opt_select.append(f"NULL AS {name}")
            opt_insert.append(name)

    opt_cols_sql = ", ".join(f"{n} {optional[n]}" for n in opt_insert)
    opt_cols_part = f", {opt_cols_sql}" if opt_cols_sql else ""
    opt_select_sql = ", ".join(opt_select)
    opt_insert_sql = ", ".join(opt_insert)
    opt_part = f", {opt_select_sql}" if opt_select_sql else ""
    opt_insert_part = f", {opt_insert_sql}" if opt_insert_sql else ""

    conn.execute(text("DROP TABLE IF EXISTS competition_enrollments_new"))
    conn.execute(
        text(
            f"""
            CREATE TABLE competition_enrollments_new (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                competition_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                team_id INTEGER,
                enrollment_scope VARCHAR(20) NOT NULL DEFAULT 'individual',
                is_captain BOOLEAN NOT NULL DEFAULT 0,
                {opt_cols_sql + "," if opt_cols_sql else ""}
                status VARCHAR(30) NOT NULL DEFAULT 'enrolled',
                created_at DATETIME,
                FOREIGN KEY(competition_id) REFERENCES competitions(id),
                FOREIGN KEY(team_id) REFERENCES teams(id),
                CONSTRAINT uq_competition_student_scope UNIQUE (
                    competition_id, student_id, enrollment_scope
                )
            )
            """
        )
    )
    conn.execute(
        text(
            f"""
            INSERT INTO competition_enrollments_new (
                id, competition_id, student_id, team_id, enrollment_scope,
                is_captain{opt_insert_part}, status, created_at
            )
            SELECT
                id, competition_id, student_id, team_id,
                CASE WHEN team_id IS NOT NULL THEN 'team' ELSE 'individual' END,
                is_captain{opt_part}, status, created_at
            FROM competition_enrollments
            """
        )
    )
    conn.execute(text("DROP TABLE competition_enrollments"))
    conn.execute(text("ALTER TABLE competition_enrollments_new RENAME TO competition_enrollments"))
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_competition_enrollments_student_id "
            "ON competition_enrollments (student_id)"
        )
    )
