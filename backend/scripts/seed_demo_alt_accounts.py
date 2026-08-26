#!/usr/bin/env python3
"""
种子账号：安徽师范大学 / 合肥大学 学生、指导老师、专家、校管理员。

用法（在 backend 目录）:
  python scripts/seed_demo_alt_accounts.py

幂等：同用户名已存在则跳过（不覆盖密码）。
统一初始密码见 DEFAULT_PASSWORD。
"""
from __future__ import annotations

import os
import sys

# 保证可从 backend/ 或 scripts/ 启动时找到 app 包
_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

os.chdir(_BACKEND_ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(_BACKEND_ROOT, ".env"))

from app.alt_auth.bootstrap import setup_alt_auth_database
from app.alt_auth.database import SessionAltAuth
from app.alt_auth.models import AltAuthUserRecord
from app.alt_auth.password_codec import hash_password_plain
from app.alt_auth.time_util import utc_now_naive
from app.eight_digit_id import allocate_eight_digit_id

DEFAULT_PASSWORD = "Demo123456"

SCHOOL_AHNU = "安徽师范大学"
SCHOOL_HFU = "合肥大学"

# (username, role, school, full_name, phone, student_id, teacher_id,
#  expert_verified, school_admin_verified)
ACCOUNTS = [
    ("ahnu_stu1", "student", SCHOOL_AHNU, "安师大学生一", "13810001001", "AHNU2026001", None, False, False),
    ("ahnu_stu2", "student", SCHOOL_AHNU, "安师大学生二", "13810001002", "AHNU2026002", None, False, False),
    ("ahnu_stu3", "student", SCHOOL_AHNU, "安师大学生三", "13810001003", "AHNU2026003", None, False, False),
    ("hfu_stu1", "student", SCHOOL_HFU, "合大学生一", "13820002001", "HFU2026001", None, False, False),
    ("hfu_stu2", "student", SCHOOL_HFU, "合大学生二", "13820002002", "HFU2026002", None, False, False),
    ("hfu_stu3", "student", SCHOOL_HFU, "合大学生三", "13820002003", "HFU2026003", None, False, False),
    ("ahnu_advisor1", "advisor", SCHOOL_AHNU, "安师大指导老师", "13810003001", None, "AHNUT2026001", False, False),
    ("hfu_advisor1", "advisor", SCHOOL_HFU, "合大指导老师", "13820003001", None, "HFUT2026001", False, False),
    ("ahnu_expert1", "expert", SCHOOL_AHNU, "安师大专家", "13810004001", None, None, True, False),
    ("hfu_expert1", "expert", SCHOOL_HFU, "合大专家", "13820004001", None, None, True, False),
    ("ahnu_school_admin", "school_admin", SCHOOL_AHNU, "安师大校管理员", "13810005001", None, None, False, True),
    ("hfu_school_admin", "school_admin", SCHOOL_HFU, "合大校管理员", "13820005001", None, None, False, True),
]


def main() -> int:
    setup_alt_auth_database()
    db = SessionAltAuth()
    created = []
    skipped = []
    try:
        pwd_hash = hash_password_plain(DEFAULT_PASSWORD)
        for (
            username,
            role,
            school,
            full_name,
            phone,
            student_id,
            teacher_id,
            expert_verified,
            school_admin_verified,
        ) in ACCOUNTS:
            exists = (
                db.query(AltAuthUserRecord)
                .filter(AltAuthUserRecord.username == username)
                .first()
            )
            if exists:
                skipped.append((username, exists.id, exists.role, exists.school))
                continue

            phone_taken = (
                db.query(AltAuthUserRecord)
                .filter(AltAuthUserRecord.phone == phone)
                .first()
            )
            if phone_taken:
                print(f"[SKIP] 手机号 {phone} 已被用户 {phone_taken.username} 占用，无法创建 {username}")
                skipped.append((username, None, role, school))
                continue

            now = utc_now_naive()
            row = AltAuthUserRecord(
                id=allocate_eight_digit_id(db, AltAuthUserRecord),
                username=username,
                email=None,
                phone=phone,
                full_name=full_name,
                student_id=student_id,
                teacher_id=teacher_id,
                hashed_password=pwd_hash,
                role=role,
                is_active=True,
                school=school,
                expert_verified=bool(expert_verified),
                school_admin_verified=bool(school_admin_verified),
                school_admin_application_status="approved" if school_admin_verified else None,
                school_admin_application_submitted_at=now if school_admin_verified else None,
                school_admin_reviewed_at=now if school_admin_verified else None,
                account=phone,
                account_kind="phone",
            )
            db.add(row)
            db.flush()
            created.append((username, row.id, role, school, full_name, phone))

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
        return 1
    finally:
        db.close()

    print("=" * 72)
    print(f"统一初始密码: {DEFAULT_PASSWORD}")
    print("=" * 72)
    print(f"{'用户名':<20} {'ID':<10} {'角色':<14} {'学校':<12} {'姓名':<12} {'手机号'}")
    print("-" * 72)
    for username, uid, role, school, full_name, phone in created:
        print(f"{username:<20} {uid:<10} {role:<14} {school:<12} {full_name:<12} {phone}")
    if not created:
        print("(本次无新建)")
    if skipped:
        print("-" * 72)
        print("已存在/跳过:")
        for item in skipped:
            print(f"  {item}")
    print("=" * 72)
    print(f"新建 {len(created)} 个，跳过 {len(skipped)} 个。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
