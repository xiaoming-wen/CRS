"""专家按题评分表 competition_team_question_grades。"""
from __future__ import annotations

import logging

from sqlalchemy import text

from app.db_compat import is_sqlite, table_columns

logger = logging.getLogger(__name__)


def migrate_competition_team_question_grades(engine) -> None:
    with engine.connect() as conn:
        cols = table_columns(conn, "competition_team_question_grades")
        if cols:
            logger.info("competition_team_question_grades already exists")
            return
        if is_sqlite(engine):
            ddl = """
                CREATE TABLE IF NOT EXISTS competition_team_question_grades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    competition_id INTEGER NOT NULL,
                    team_id INTEGER NOT NULL,
                    reviewer_id INTEGER NOT NULL,
                    score_q1 FLOAT NOT NULL,
                    score_q2 FLOAT NOT NULL,
                    score_q3 FLOAT NOT NULL,
                    score_q4 FLOAT NOT NULL,
                    score_q5 FLOAT NOT NULL,
                    total_score FLOAT NOT NULL,
                    feedback TEXT,
                    reviewed_at DATETIME,
                    created_at DATETIME,
                    FOREIGN KEY(competition_id) REFERENCES competitions(id),
                    FOREIGN KEY(team_id) REFERENCES teams(id),
                    UNIQUE (competition_id, team_id)
                )
            """
        else:
            ddl = """
                CREATE TABLE IF NOT EXISTS competition_team_question_grades (
                    id INT NOT NULL AUTO_INCREMENT,
                    competition_id INT NOT NULL,
                    team_id INT NOT NULL,
                    reviewer_id INT NOT NULL,
                    score_q1 FLOAT NOT NULL,
                    score_q2 FLOAT NOT NULL,
                    score_q3 FLOAT NOT NULL,
                    score_q4 FLOAT NOT NULL,
                    score_q5 FLOAT NOT NULL,
                    total_score FLOAT NOT NULL,
                    feedback TEXT,
                    reviewed_at DATETIME NULL,
                    created_at DATETIME NULL,
                    PRIMARY KEY (id),
                    UNIQUE KEY uq_competition_team_question_grade (competition_id, team_id),
                    KEY ix_ctqg_competition_id (competition_id),
                    KEY ix_ctqg_team_id (team_id),
                    KEY ix_ctqg_reviewer_id (reviewer_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        try:
            conn.execute(text(ddl))
            conn.commit()
            logger.info("competition_team_question_grades created")
        except Exception:
            conn.rollback()
            logger.exception("competition_team_question_grades migration failed")
