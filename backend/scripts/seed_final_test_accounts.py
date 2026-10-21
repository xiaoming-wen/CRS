#!/usr/bin/env python3
"""
生成决赛测试学生账号：写入账号、决赛队伍、报名，并加入晋级白名单。

登录后可通过决赛门禁，且组队已校审通过，可下载对应赛道试卷
（仍受赛道倒计时约束，本脚本不改倒计时）。

用法（在 backend 目录）:
  python scripts/seed_final_test_accounts.py --count 200 --competition-id 47454000

统一密码 Demo123456；用户名 final_stu0000 … final_stu0199
花名册：scripts/final_test_accounts_roster.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

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
from app.database import UserSessionLocal
from app.datetime_utils import utc_now
from app.eight_digit_id import allocate_eight_digit_id
from app.models.competition import (
    Competition,
    CompetitionEnrollment,
    CompetitionEnrollmentScope,
    CompetitionEnrollmentStatus,
    CompetitionPromotion,
    CompetitionStage,
    Team,
    TeamMember,
    TeamStatus,
)

DEFAULT_PASSWORD = "Demo123456"
USERNAME_FMT = "final_stu{idx:04d}"
TEAM_NAME_FMT = "决赛测试队-{idx:04d}"
ROSTER_PATH = os.path.join(_BACKEND_ROOT, "scripts", "final_test_accounts_roster.json")
SCHOOL = "合肥大学"


def _competition_stage(comp: Competition) -> str:
    return str(getattr(comp, "stage", None) or CompetitionStage.SINGLE).lower()


def _resolve_prelim_id(final: Competition) -> int:
    paired = getattr(final, "paired_competition_id", None)
    if paired is not None:
        return int(paired)
    return int(final.id)


def _promoted_by_id(adb) -> int:
    admin = (
        adb.query(AltAuthUserRecord)
        .filter(AltAuthUserRecord.role == "super_admin")
        .order_by(AltAuthUserRecord.id.asc())
        .first()
    )
    if admin is not None:
        return int(admin.id)
    any_user = adb.query(AltAuthUserRecord).order_by(AltAuthUserRecord.id.asc()).first()
    if any_user is None:
        raise SystemExit("alt_auth 中没有任何账号，无法写入晋级操作人")
    return int(any_user.id)


def main() -> int:
    p = argparse.ArgumentParser(description="生成决赛测试账号并加入晋级白名单")
    p.add_argument("--count", type=int, default=200)
    p.add_argument("--competition-id", type=int, default=47454000, help="决赛竞赛 ID")
    p.add_argument("--work-track", default="software", choices=["software", "hardware", "works"])
    p.add_argument("--division", default="undergraduate", choices=["undergraduate", "vocational"])
    args = p.parse_args()
    if args.count < 1 or args.count > 2000:
        print("count 须在 1～2000")
        return 2

    setup_alt_auth_database()
    adb = SessionAltAuth()
    db = UserSessionLocal()
    try:
        final = db.query(Competition).filter(Competition.id == args.competition_id).first()
        if final is None:
            print(f"竞赛 {args.competition_id} 不存在")
            return 2
        stage = _competition_stage(final)
        if stage != CompetitionStage.FINAL:
            print(f"警告：竞赛 {final.id} 当前 stage={stage}，仍按决赛白名单写入")
        prelim_id = _resolve_prelim_id(final)
        promoted_by = _promoted_by_id(adb)
        pwd_hash = hash_password_plain(DEFAULT_PASSWORD)

        roster = []
        created_users = 0
        created_teams = 0
        created_promos = 0
        for i in range(args.count):
            username = USERNAME_FMT.format(idx=i)
            phone = f"1396{i:07d}"
            user = adb.query(AltAuthUserRecord).filter(AltAuthUserRecord.username == username).first()
            if user is None:
                phone_taken = adb.query(AltAuthUserRecord).filter(AltAuthUserRecord.phone == phone).first()
                if phone_taken:
                    print(f"[SKIP] 手机号 {phone} 已被 {phone_taken.username} 占用")
                    continue
                now = utc_now_naive()
                user = AltAuthUserRecord(
                    id=allocate_eight_digit_id(adb, AltAuthUserRecord),
                    username=username,
                    email=None,
                    phone=phone,
                    full_name=f"决赛测试学生{i:04d}",
                    student_id=f"FT{i:08d}",
                    hashed_password=pwd_hash,
                    role="student",
                    is_active=True,
                    school=SCHOOL,
                    account=phone,
                    account_kind="phone",
                    created_at=now,
                    updated_at=now,
                )
                adb.add(user)
                adb.flush()
                created_users += 1
            else:
                user.is_active = True
                user.role = "student"
                user.hashed_password = pwd_hash
                adb.flush()

            tname = TEAM_NAME_FMT.format(idx=i)
            team = (
                db.query(Team)
                .filter(Team.competition_id == final.id, Team.name == tname)
                .first()
            )
            if team is None:
                team = Team(
                    id=allocate_eight_digit_id(db, Team),
                    competition_id=final.id,
                    name=tname,
                    captain_id=user.id,
                    division=args.division,
                    work_track=args.work_track,
                    status=TeamStatus.ACTIVE,
                    school=SCHOOL,
                    reviewed_at=utc_now(),
                )
                db.add(team)
                db.flush()
                created_teams += 1
            else:
                team.captain_id = user.id
                team.division = args.division
                team.work_track = args.work_track
                team.status = TeamStatus.ACTIVE
                team.school = SCHOOL
                if getattr(team, "reviewed_at", None) is None:
                    team.reviewed_at = utc_now()
                db.flush()

            member = (
                db.query(TeamMember)
                .filter(TeamMember.team_id == team.id, TeamMember.user_id == user.id)
                .first()
            )
            if member is None:
                db.add(TeamMember(team_id=team.id, user_id=user.id, is_captain=True))
            else:
                member.is_captain = True

            enroll = (
                db.query(CompetitionEnrollment)
                .filter(
                    CompetitionEnrollment.competition_id == final.id,
                    CompetitionEnrollment.student_id == user.id,
                    CompetitionEnrollment.work_track == args.work_track,
                )
                .first()
            )
            if enroll is None:
                db.add(
                    CompetitionEnrollment(
                        competition_id=final.id,
                        student_id=user.id,
                        team_id=team.id,
                        enrollment_scope=CompetitionEnrollmentScope.TEAM,
                        division=args.division,
                        work_track=args.work_track,
                        is_captain=True,
                        student_no=user.student_id,
                        real_name=user.full_name,
                        status=CompetitionEnrollmentStatus.ENROLLED,
                    )
                )
            else:
                enroll.team_id = team.id
                enroll.enrollment_scope = CompetitionEnrollmentScope.TEAM
                enroll.division = args.division
                enroll.work_track = args.work_track
                enroll.is_captain = True
                enroll.status = CompetitionEnrollmentStatus.ENROLLED
                enroll.student_no = user.student_id
                enroll.real_name = user.full_name

            promo = (
                db.query(CompetitionPromotion)
                .filter(
                    CompetitionPromotion.to_competition_id == final.id,
                    CompetitionPromotion.source_student_id == user.id,
                )
                .first()
            )
            if promo is None:
                promo = (
                    db.query(CompetitionPromotion)
                    .filter(
                        CompetitionPromotion.to_competition_id == final.id,
                        CompetitionPromotion.final_team_id == team.id,
                    )
                    .first()
                )
            if promo is None:
                promo = CompetitionPromotion(
                    id=allocate_eight_digit_id(db, CompetitionPromotion),
                    from_competition_id=prelim_id,
                    to_competition_id=final.id,
                    source_team_id=None,
                    source_student_id=int(user.id),
                    final_team_id=int(team.id),
                    promoted_by=promoted_by,
                )
                db.add(promo)
                db.flush()
                created_promos += 1
            else:
                promo.final_team_id = int(team.id)
                promo.source_student_id = int(user.id)
                db.flush()

            roster.append(
                {
                    "username": username,
                    "password": DEFAULT_PASSWORD,
                    "user_id": int(user.id),
                    "team_id": int(team.id),
                    "team_name": tname,
                    "phone": phone,
                }
            )
            if (i + 1) % 50 == 0:
                adb.commit()
                db.commit()
                print(f"... {i + 1}/{args.count}")

        adb.commit()
        db.commit()
        payload = {
            "competition_id": int(final.id),
            "competition_name": final.name,
            "stage": stage,
            "password": DEFAULT_PASSWORD,
            "work_track": args.work_track,
            "division": args.division,
            "users": roster,
        }
        with open(ROSTER_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"决赛竞赛 {final.id} ({final.name}) stage={stage}")
        print(f"新建账号 {created_users}，新建队伍 {created_teams}，新建白名单 {created_promos}")
        print(f"花名册 {len(roster)} 条 -> {ROSTER_PATH}")
        print(f"统一密码 {DEFAULT_PASSWORD}")
        print("登录后即可进入决赛；下载试卷仍须赛道倒计时已开始且已上传对应组别试卷。")
        return 0
    except Exception as e:
        adb.rollback()
        db.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        adb.close()
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
