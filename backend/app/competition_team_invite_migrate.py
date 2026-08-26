"""队长/指导老师入队邀请表 team_invites。"""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.db_compat import is_sqlite

logger = logging.getLogger(__name__)


def migrate_competition_team_invites(engine) -> None:
    if not is_sqlite(engine):
        logger.info("team_invites: skip SQLite-only DDL on %s", engine.dialect.name)
        return

    with engine.connect() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS team_invites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id INTEGER NOT NULL,
                    competition_id INTEGER NOT NULL,
                    invitee_id INTEGER NOT NULL,
                    inviter_id INTEGER NOT NULL,
                    as_captain BOOLEAN NOT NULL DEFAULT 0,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    created_at DATETIME,
                    responded_at DATETIME,
                    FOREIGN KEY(team_id) REFERENCES teams(id)
                )
                """
            )
        )
        for sql in (
            "CREATE INDEX IF NOT EXISTS ix_team_invites_team_id ON team_invites (team_id)",
            "CREATE INDEX IF NOT EXISTS ix_team_invites_competition_id ON team_invites (competition_id)",
            "CREATE INDEX IF NOT EXISTS ix_team_invites_invitee_id ON team_invites (invitee_id)",
            "CREATE INDEX IF NOT EXISTS ix_team_invites_inviter_id ON team_invites (inviter_id)",
            "CREATE INDEX IF NOT EXISTS ix_team_invites_status ON team_invites (status)",
        ):
            conn.execute(text(sql))
        conn.commit()
    logger.info("team_invites migration finished")
