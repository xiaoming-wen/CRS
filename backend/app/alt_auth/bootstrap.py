"""
第二套认证库：`alt_auth.db` 表结构幂等补丁与默认管理员种子。
默认帐号与主站 ``init_db`` / API 文档「默认管理员账户」一致。
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import text

_LOGGER = logging.getLogger(__name__)

# 与主站 init_db 及 API 文档一致
ALT_DEFAULT_ADMIN_USERNAME = "admin"
ALT_DEFAULT_ADMIN_PASSWORD = "admin123"
ALT_DEFAULT_ADMIN_EMAIL = "admin@system.edu"
ALT_DEFAULT_ADMIN_SCHOOL = "系统内置"


def ensure_default_alt_auth_admin(log: Optional[logging.Logger] = None) -> None:
    """
    若不存在用户名为 ``admin`` 的记录，则创建默认超级管理员。
    已存在则不覆盖密码（避免重置运维改过的口令）。
    """
    lg = log or _LOGGER
    from app.alt_auth.database import SessionAltAuth
    from app.alt_auth.models import AltAuthUserRecord
    from app.alt_auth.password_codec import hash_password_plain
    from app.eight_digit_id import allocate_eight_digit_id

    db = SessionAltAuth()
    try:
        if (
            db.query(AltAuthUserRecord)
            .filter(AltAuthUserRecord.username == ALT_DEFAULT_ADMIN_USERNAME)
            .first()
        ):
            return

        row = AltAuthUserRecord(
            id=allocate_eight_digit_id(db, AltAuthUserRecord),
            username=ALT_DEFAULT_ADMIN_USERNAME,
            email=ALT_DEFAULT_ADMIN_EMAIL,
            full_name="System Administrator",
            student_id=None,
            teacher_id=None,
            hashed_password=hash_password_plain(ALT_DEFAULT_ADMIN_PASSWORD),
            role="super_admin",
            is_active=True,
            school=ALT_DEFAULT_ADMIN_SCHOOL,
            account=ALT_DEFAULT_ADMIN_EMAIL,
            account_kind="email",
        )
        db.add(row)
        db.commit()
        lg.info(
            "Alt-auth: created default super_admin user %r",
            ALT_DEFAULT_ADMIN_USERNAME,
        )
    except Exception as e:
        db.rollback()
        lg.warning("Alt-auth default admin seed failed: %s", e)
    finally:
        db.close()


def setup_alt_auth_database(log: Optional[logging.Logger] = None) -> None:
    """建表、补列、回填历史列、种子默认管理员。"""
    lg = log or _LOGGER
    from app.alt_auth.database import Base as AltAuthBase, engine as alt_auth_engine

    import app.alt_auth.models as _alt_auth_models  # noqa: F401

    AltAuthBase.metadata.create_all(bind=alt_auth_engine)

    for alt_sql in (
        "ALTER TABLE alt_auth_users ADD COLUMN role VARCHAR(32) DEFAULT 'student'",
        "ALTER TABLE alt_auth_users ADD COLUMN is_active BOOLEAN DEFAULT 1",
        "ALTER TABLE alt_auth_users ADD COLUMN school VARCHAR(200)",
        "ALTER TABLE alt_auth_users ADD COLUMN username VARCHAR(100)",
        "ALTER TABLE alt_auth_users ADD COLUMN email VARCHAR(200)",
        "ALTER TABLE alt_auth_users ADD COLUMN full_name VARCHAR(100)",
        "ALTER TABLE alt_auth_users ADD COLUMN student_id VARCHAR(50)",
        "ALTER TABLE alt_auth_users ADD COLUMN teacher_id VARCHAR(50)",
        "ALTER TABLE alt_auth_users ADD COLUMN expert_verified BOOLEAN DEFAULT 0",
        "ALTER TABLE alt_auth_users ADD COLUMN school_admin_verified BOOLEAN DEFAULT 0",
        "ALTER TABLE alt_auth_users ADD COLUMN school_admin_photo_path VARCHAR(512)",
        "ALTER TABLE alt_auth_users ADD COLUMN school_admin_application_status VARCHAR(30)",
        "ALTER TABLE alt_auth_users ADD COLUMN school_admin_application_contact VARCHAR(200)",
        "ALTER TABLE alt_auth_users ADD COLUMN school_admin_application_remark VARCHAR(1000)",
        "ALTER TABLE alt_auth_users ADD COLUMN school_admin_application_submitted_at DATETIME",
        "ALTER TABLE alt_auth_users ADD COLUMN school_admin_review_feedback VARCHAR(2000)",
        "ALTER TABLE alt_auth_users ADD COLUMN school_admin_reviewed_at DATETIME",
        "ALTER TABLE alt_auth_users ADD COLUMN school_admin_reviewed_by_id INTEGER",
        "ALTER TABLE alt_auth_users ADD COLUMN phone VARCHAR(20)",
    ):
        try:
            with alt_auth_engine.connect() as conn:
                conn.execute(text(alt_sql))
                conn.commit()
        except Exception:
            pass

    try:
        with alt_auth_engine.connect() as conn:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_alt_auth_users_phone ON alt_auth_users (phone)"
                )
            )
            conn.commit()
    except Exception:
        pass

    try:
        with alt_auth_engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE alt_auth_users SET role = 'student' "
                    "WHERE role IS NULL OR TRIM(COALESCE(role,'')) = ''"
                )
            )
            conn.execute(
                text(
                    "UPDATE alt_auth_users SET is_active = 1 WHERE is_active IS NULL"
                )
            )
            conn.execute(
                text(
                    "UPDATE alt_auth_users SET username = TRIM(account) "
                    "WHERE account IS NOT NULL AND TRIM(account) <> '' "
                    "AND (username IS NULL OR TRIM(COALESCE(username,'')) = '')"
                )
            )
            conn.execute(
                text(
                    "UPDATE alt_auth_users SET email = LOWER(TRIM(account)) "
                    "WHERE account IS NOT NULL AND TRIM(account) <> '' "
                    "AND LOWER(TRIM(COALESCE(account_kind,''))) = 'email' "
                    "AND (email IS NULL OR TRIM(COALESCE(email,'')) = '')"
                )
            )
            # 角色保持原样：teacher 与 advisor 并存，不做自动互转
            conn.commit()
    except Exception:
        pass

    ensure_default_alt_auth_admin(log=lg)
