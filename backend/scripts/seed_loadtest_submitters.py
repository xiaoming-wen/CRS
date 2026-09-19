#!/usr/bin/env python3
"""
为本机压测准备可正式提交的假数据：学生账号 + 已校审队伍 + 草稿答案。

用法（在 backend 目录）:
  python scripts/seed_loadtest_submitters.py --count 1000 --competition-id 58582342
  python scripts/seed_loadtest_submitters.py --reset-answers

统一密码 Demo123456；用户名 load_stu0000 … ；花名册写入 scripts/loadtest_submit_roster.json
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
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
from app.competition_exam_config import dumps_track_time_windows
from app.database import UserSessionLocal
from app.datetime_utils import utc_now
from app.eight_digit_id import EIGHT_DIGIT_ID_MAX, EIGHT_DIGIT_ID_MIN
from app.models.competition import (
    Competition,
    CompetitionEnrollment,
    CompetitionEnrollmentScope,
    CompetitionEnrollmentStatus,
    CompetitionQuestionAnswer,
    CompetitionQuestionAnswerStatus,
    CompetitionStatus,
    Team,
    TeamMember,
    TeamStatus,
)
from app.models.user import File as FileModel

DEFAULT_PASSWORD = "Demo123456"
USERNAME_FMT = "load_stu{idx:04d}"
TEAM_NAME_FMT = "loadteam-{idx:04d}"
ROSTER_PATH = os.path.join(_BACKEND_ROOT, "scripts", "loadtest_submit_roster.json")
DUMMY_ANSWER_PATH = os.path.join(_BACKEND_ROOT, "loadtest_dummy_answer.txt")
SCHOOL = "合肥大学"


def _take_ids(used: set[int], n: int) -> list[int]:
    out: list[int] = []
    span = EIGHT_DIGIT_ID_MAX - EIGHT_DIGIT_ID_MIN + 1
    while len(out) < n:
        cand = secrets.randbelow(span) + EIGHT_DIGIT_ID_MIN
        if cand in used:
            continue
        used.add(cand)
        out.append(cand)
    return out


def _ensure_competition(db, competition_id: int) -> Competition:
    row = db.query(Competition).filter(Competition.id == competition_id).first()
    if row is None:
        raise SystemExit(f"竞赛 {competition_id} 不存在，无法灌数")
    row.status = CompetitionStatus.PUBLISHED
    # 关闭赛道倒计时，避免「不在竞赛时间段 / 比赛结束」挡住压测提交
    row.track_time_windows = dumps_track_time_windows(
        {
            "works": {"enabled": False},
            "software": {"enabled": False},
            "hardware": {"enabled": False},
        }
    )
    db.add(row)
    db.flush()
    return row


def _dummy_file(db, owner_id: int) -> FileModel:
    if not os.path.isfile(DUMMY_ANSWER_PATH):
        with open(DUMMY_ANSWER_PATH, "w", encoding="utf-8") as f:
            f.write("loadtest dummy answer\n")
    existing = (
        db.query(FileModel)
        .filter(FileModel.file_path == DUMMY_ANSWER_PATH, FileModel.filename == "loadtest_dummy_answer.txt")
        .first()
    )
    if existing:
        return existing
    rec = FileModel(
        filename="loadtest_dummy_answer.txt",
        file_type="submission",
        file_path=DUMMY_ANSWER_PATH,
        file_size=os.path.getsize(DUMMY_ANSWER_PATH),
        mime_type="text/plain",
        sender_id=owner_id,
        description="loadtest",
    )
    db.add(rec)
    db.flush()
    return rec


def reset_answers(db, competition_id: int, count: int) -> int:
    names = [TEAM_NAME_FMT.format(idx=i) for i in range(count)]
    teams = (
        db.query(Team)
        .filter(Team.competition_id == competition_id, Team.name.in_(names))
        .all()
    )
    ids = [t.id for t in teams]
    if not ids:
        return 0
    n = (
        db.query(CompetitionQuestionAnswer)
        .filter(
            CompetitionQuestionAnswer.competition_id == competition_id,
            CompetitionQuestionAnswer.team_id.in_(ids),
        )
        .update(
            {
                CompetitionQuestionAnswer.status: CompetitionQuestionAnswerStatus.DRAFT,
                CompetitionQuestionAnswer.submitted_at: None,
            },
            synchronize_session=False,
        )
    )
    return int(n or 0)


def main() -> int:
    p = argparse.ArgumentParser(description="灌入压测提交用假账号/队伍/草稿答案")
    p.add_argument("--count", type=int, default=1000)
    p.add_argument("--competition-id", type=int, default=58582342)
    p.add_argument("--reset-answers", action="store_true", help="只把灌数队伍的答案打回 draft")
    args = p.parse_args()
    if args.count < 1 or args.count > 5000:
        print("count 须在 1～5000")
        return 2

    setup_alt_auth_database()
    adb = SessionAltAuth()
    db = UserSessionLocal()
    try:
        comp = _ensure_competition(db, args.competition_id)
        if args.reset_answers:
            n = reset_answers(db, comp.id, args.count)
            db.commit()
            print(f"已将 {n} 条答案重置为 draft")
            return 0

        pwd_hash = hash_password_plain(DEFAULT_PASSWORD)
        used_user_ids = {r[0] for r in adb.query(AltAuthUserRecord.id).all() if r[0] is not None}
        used_team_ids = {r[0] for r in db.query(Team.id).all() if r[0] is not None}

        roster = []
        created_users = 0
        for i in range(args.count):
            username = USERNAME_FMT.format(idx=i)
            phone = f"1395{i:07d}"
            user = adb.query(AltAuthUserRecord).filter(AltAuthUserRecord.username == username).first()
            if user is None:
                phone_taken = adb.query(AltAuthUserRecord).filter(AltAuthUserRecord.phone == phone).first()
                if phone_taken:
                    print(f"[SKIP] 手机号 {phone} 已被 {phone_taken.username} 占用")
                    continue
                uid = _take_ids(used_user_ids, 1)[0]
                now = utc_now_naive()
                user = AltAuthUserRecord(
                    id=uid,
                    username=username,
                    email=None,
                    phone=phone,
                    full_name=f"压测学生{i:04d}",
                    student_id=f"LD{i:08d}",
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

            tname = TEAM_NAME_FMT.format(idx=i)
            team = (
                db.query(Team)
                .filter(Team.competition_id == comp.id, Team.name == tname)
                .first()
            )
            if team is None:
                tid = _take_ids(used_team_ids, 1)[0]
                team = Team(
                    id=tid,
                    competition_id=comp.id,
                    name=tname,
                    captain_id=user.id,
                    division="undergraduate",
                    work_track="software",
                    status=TeamStatus.ACTIVE,
                    school=SCHOOL,
                )
                db.add(team)
                db.flush()
                db.add(
                    TeamMember(
                        team_id=team.id,
                        user_id=user.id,
                        is_captain=True,
                    )
                )
                db.add(
                    CompetitionEnrollment(
                        competition_id=comp.id,
                        student_id=user.id,
                        team_id=team.id,
                        enrollment_scope=CompetitionEnrollmentScope.TEAM,
                        division="undergraduate",
                        work_track="software",
                        is_captain=True,
                        student_no=user.student_id,
                        real_name=user.full_name,
                        status=CompetitionEnrollmentStatus.ENROLLED,
                    )
                )

            frow = _dummy_file(db, user.id)
            qa = (
                db.query(CompetitionQuestionAnswer)
                .filter(
                    CompetitionQuestionAnswer.competition_id == comp.id,
                    CompetitionQuestionAnswer.team_id == team.id,
                    CompetitionQuestionAnswer.question_no == 1,
                )
                .first()
            )
            if qa is None:
                db.add(
                    CompetitionQuestionAnswer(
                        competition_id=comp.id,
                        team_id=team.id,
                        question_no=1,
                        submitter_id=user.id,
                        file_id=frow.id,
                        status=CompetitionQuestionAnswerStatus.DRAFT,
                    )
                )
            else:
                qa.status = CompetitionQuestionAnswerStatus.DRAFT
                qa.submitted_at = None
                qa.file_id = frow.id
                qa.submitter_id = user.id

            roster.append(
                {
                    "username": username,
                    "team_id": int(team.id),
                    "user_id": int(user.id),
                }
            )
            if (i + 1) % 100 == 0:
                adb.commit()
                db.commit()
                print(f"... {i + 1}/{args.count}")

        adb.commit()
        db.commit()
        payload = {
            "competition_id": int(comp.id),
            "password": DEFAULT_PASSWORD,
            "work_track": "software",
            "division": "undergraduate",
            "users": roster,
        }
        with open(ROSTER_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        print(f"竞赛 {comp.id} status={comp.status}")
        print(f"新建账号 {created_users}，花名册 {len(roster)} 条 -> {ROSTER_PATH}")
        print(f"统一密码 {DEFAULT_PASSWORD}")
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
