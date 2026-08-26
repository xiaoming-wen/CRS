"""报名唯一约束：同一竞赛同一学生每个 work_track 至多一条（作品/软件/硬件各一次）。"""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.db_compat import is_sqlite, table_columns

logger = logging.getLogger(__name__)

OLD_UQ = "uq_competition_student_scope"
NEW_UQ = "uq_competition_student_work_track"


def migrate_competition_enrollment_multi_work_track(engine) -> None:
    with engine.connect() as conn:
        cols = table_columns(conn, "competition_enrollments")
        if not cols or "work_track" not in cols:
            return

        # 尽量从队伍补全缺失赛道
        try:
            conn.execute(
                text(
                    """
                    UPDATE competition_enrollments e
                    INNER JOIN teams t ON t.id = e.team_id
                    SET e.work_track = t.work_track
                    WHERE (e.work_track IS NULL OR e.work_track = '')
                      AND t.work_track IS NOT NULL
                      AND t.work_track <> ''
                    """
                )
            )
            conn.commit()
        except Exception:
            conn.rollback()
            # SQLite 无 INNER JOIN UPDATE 语法时忽略，下面用 Python 回填
            try:
                rows = conn.execute(
                    text(
                        """
                        SELECT e.id, t.work_track
                        FROM competition_enrollments e
                        JOIN teams t ON t.id = e.team_id
                        WHERE (e.work_track IS NULL OR e.work_track = '')
                          AND t.work_track IS NOT NULL
                          AND TRIM(t.work_track) <> ''
                        """
                    )
                ).fetchall()
                for eid, track in rows:
                    conn.execute(
                        text(
                            "UPDATE competition_enrollments SET work_track = :t WHERE id = :id"
                        ),
                        {"t": str(track).strip().lower(), "id": eid},
                    )
                conn.commit()
            except Exception:
                conn.rollback()

        # 仍为空的组队报名：默认 works（避免唯一索引因 NULL 失效）
        try:
            conn.execute(
                text(
                    """
                    UPDATE competition_enrollments
                    SET work_track = 'works'
                    WHERE (work_track IS NULL OR work_track = '')
                      AND enrollment_scope = 'team'
                    """
                )
            )
            conn.commit()
        except Exception:
            conn.rollback()

        if is_sqlite(conn):
            _migrate_sqlite_unique(conn)
            return

        # MySQL / MariaDB：删旧唯一索引、建新索引
        try:
            idx_rows = conn.execute(text("SHOW INDEX FROM competition_enrollments")).fetchall()
            index_names = {str(r[2]) for r in idx_rows}  # Key_name
        except Exception:
            index_names = set()

        if OLD_UQ in index_names:
            try:
                conn.execute(text(f"ALTER TABLE competition_enrollments DROP INDEX {OLD_UQ}"))
                conn.commit()
                logger.info("Dropped index %s", OLD_UQ)
            except Exception as e:
                conn.rollback()
                logger.warning("Drop index %s failed: %s", OLD_UQ, e)

        # 去重：同竞赛同学同赛道保留 id 最小的 enrolled，其余改 withdrawn 并改 track 后缀避免冲突
        _dedupe_work_tracks_mysql(conn)

        try:
            idx_rows = conn.execute(text("SHOW INDEX FROM competition_enrollments")).fetchall()
            index_names = {str(r[2]) for r in idx_rows}
        except Exception:
            index_names = set()

        if NEW_UQ not in index_names:
            try:
                conn.execute(
                    text(
                        f"""
                        ALTER TABLE competition_enrollments
                        ADD UNIQUE KEY {NEW_UQ} (competition_id, student_id, work_track)
                        """
                    )
                )
                conn.commit()
                logger.info("Added unique index %s", NEW_UQ)
            except Exception as e:
                conn.rollback()
                logger.warning("Add index %s failed: %s", NEW_UQ, e)


def _dedupe_work_tracks_mysql(conn) -> None:
    try:
        dups = conn.execute(
            text(
                """
                SELECT competition_id, student_id, work_track, COUNT(*) AS c
                FROM competition_enrollments
                WHERE work_track IS NOT NULL AND work_track <> ''
                GROUP BY competition_id, student_id, work_track
                HAVING c > 1
                """
            )
        ).fetchall()
        for competition_id, student_id, work_track, _c in dups:
            rows = conn.execute(
                text(
                    """
                    SELECT id, status FROM competition_enrollments
                    WHERE competition_id = :cid AND student_id = :sid AND work_track = :wt
                    ORDER BY CASE WHEN status = 'enrolled' THEN 0 ELSE 1 END, id ASC
                    """
                ),
                {"cid": competition_id, "sid": student_id, "wt": work_track},
            ).fetchall()
            keep_id = rows[0][0] if rows else None
            for i, (rid, _st) in enumerate(rows):
                if rid == keep_id:
                    continue
                # 释放唯一键：改成 withdrawn 且改 work_track 占位
                conn.execute(
                    text(
                        """
                        UPDATE competition_enrollments
                        SET status = 'withdrawn',
                            work_track = CONCAT(:wt, '__dup_', :id)
                        WHERE id = :id
                        """
                    ),
                    {"wt": work_track, "id": rid},
                )
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.warning("Dedupe work_track failed: %s", e)


def _migrate_sqlite_unique(conn) -> None:
    ddl_row = conn.execute(
        text(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='competition_enrollments'"
        )
    ).fetchone()
    ddl = (ddl_row[0] or "") if ddl_row else ""
    if NEW_UQ in ddl:
        return
    if OLD_UQ not in ddl and "UNIQUE" not in ddl.upper():
        # 无旧约束时仅尝试建索引
        try:
            conn.execute(
                text(
                    f"""
                    CREATE UNIQUE INDEX IF NOT EXISTS {NEW_UQ}
                    ON competition_enrollments (competition_id, student_id, work_track)
                    """
                )
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.warning("SQLite create %s failed: %s", NEW_UQ, e)
        return
    logger.info(
        "SQLite competition_enrollments still has old unique; "
        "new installs use model UniqueConstraint. Existing SQLite may need manual rebuild."
    )
