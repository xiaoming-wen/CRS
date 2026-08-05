"""专家队伍指派表 competition_expert_team_assignments（旧 SQLite 兼容建表）。"""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.db_compat import is_sqlite

logger = logging.getLogger(__name__)


def migrate_competition_expert_team_assignments(engine) -> None:
    # MySQL 等新库由 metadata.create_all 建表；此脚本仅兼容旧 SQLite
    if not is_sqlite(engine):
        logger.info(
            "competition_expert_team_assignments: skip SQLite-only DDL on %s",
            engine.dialect.name,
        )
        return

    with engine.connect() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS competition_expert_team_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    competition_id INTEGER NOT NULL,
                    expert_id INTEGER NOT NULL,
                    team_id INTEGER NOT NULL,
                    created_at DATETIME,
                    FOREIGN KEY(competition_id) REFERENCES competitions(id),
                    FOREIGN KEY(team_id) REFERENCES teams(id),
                    UNIQUE (competition_id, expert_id, team_id)
                )
                """
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_competition_expert_team_assignments_competition_id "
                "ON competition_expert_team_assignments (competition_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_competition_expert_team_assignments_expert_id "
                "ON competition_expert_team_assignments (expert_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_competition_expert_team_assignments_team_id "
                "ON competition_expert_team_assignments (team_id)"
            )
        )
        conn.commit()
    logger.info("competition_expert_team_assignments migration finished")
