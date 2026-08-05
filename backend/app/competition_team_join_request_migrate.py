"""学生入队申请表 team_join_requests。"""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.db_compat import is_sqlite

logger = logging.getLogger(__name__)


def migrate_competition_team_join_requests(engine) -> None:
    # MySQL 等新库由 metadata.create_all 建表；此脚本仅兼容旧 SQLite
    if not is_sqlite(engine):
        logger.info("team_join_requests: skip SQLite-only DDL on %s", engine.dialect.name)
        return

    with engine.connect() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS team_join_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    created_at DATETIME,
                    reviewed_at DATETIME,
                    reviewed_by_id INTEGER,
                    FOREIGN KEY(team_id) REFERENCES teams(id)
                )
                """
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_team_join_requests_team_id "
                "ON team_join_requests (team_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_team_join_requests_user_id "
                "ON team_join_requests (user_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_team_join_requests_status "
                "ON team_join_requests (status)"
            )
        )
        conn.commit()
    logger.info("team_join_requests migration finished")
