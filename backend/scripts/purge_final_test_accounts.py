#!/usr/bin/env python3
"""
删除决赛测试账号及其队伍、报名、晋级白名单、答案。

识别规则：
  用户名 final_stu*
  队名   决赛测试队-*

用法（在 backend 目录）:
  # 先预览
  python scripts/purge_final_test_accounts.py --competition-id 47454000
  # 确认后真正删除
  python scripts/purge_final_test_accounts.py --competition-id 47454000 --yes
"""
from __future__ import annotations

import argparse
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
from app.database import UserSessionLocal
from app.models.competition import (
    CompetitionEnrollment,
    CompetitionExpertTeamAssignment,
    CompetitionPromotion,
    CompetitionQuestionAnswer,
    CompetitionTeamQuestionGrade,
    Review,
    Submission,
    Team,
    TeamInvite,
    TeamJoinRequest,
    TeamMember,
)


USERNAME_PREFIX = "final_stu"
TEAM_NAME_PREFIX = "决赛测试队-"


def main() -> int:
    p = argparse.ArgumentParser(description="删除决赛测试账号及关联数据")
    p.add_argument("--competition-id", type=int, default=47454000)
    p.add_argument("--yes", action="store_true", help="真正写入删除；不加则只预览")
    args = p.parse_args()

    setup_alt_auth_database()
    adb = SessionAltAuth()
    db = UserSessionLocal()
    try:
        users = (
            adb.query(AltAuthUserRecord)
            .filter(AltAuthUserRecord.username.like(f"{USERNAME_PREFIX}%"))
            .all()
        )
        user_ids = [int(u.id) for u in users]
        teams = (
            db.query(Team)
            .filter(
                Team.competition_id == args.competition_id,
                Team.name.like(f"{TEAM_NAME_PREFIX}%"),
            )
            .all()
        )
        team_ids = [int(t.id) for t in teams]

        extra_teams = []
        if user_ids:
            extra_q = db.query(Team).filter(
                Team.competition_id == args.competition_id,
                Team.captain_id.in_(user_ids),
            )
            if team_ids:
                extra_q = extra_q.filter(~Team.id.in_(team_ids))
            extra_teams = extra_q.all()
            for t in extra_teams:
                teams.append(t)
                team_ids.append(int(t.id))

        print(f"竞赛 {args.competition_id}")
        print(f"账号 {len(users)} 个（{USERNAME_PREFIX}*）")
        print(f"队伍 {len(teams)} 个（{TEAM_NAME_PREFIX}* 或队长为测试账号）")
        if extra_teams:
            print(f"  其中按队长补到 {len(extra_teams)} 个")
        if users:
            print(f"  示例账号 {users[0].username} … {users[-1].username}")
        if teams:
            print(f"  示例队伍 {teams[0].name} … {teams[-1].name}")

        def _count(q):
            return q.count()

        n_answers = (
            _count(db.query(CompetitionQuestionAnswer).filter(CompetitionQuestionAnswer.team_id.in_(team_ids)))
            if team_ids
            else 0
        )
        n_grades = (
            _count(db.query(CompetitionTeamQuestionGrade).filter(CompetitionTeamQuestionGrade.team_id.in_(team_ids)))
            if team_ids
            else 0
        )
        n_expert_teams = (
            _count(
                db.query(CompetitionExpertTeamAssignment).filter(
                    CompetitionExpertTeamAssignment.team_id.in_(team_ids)
                )
            )
            if team_ids
            else 0
        )
        n_join = (
            _count(db.query(TeamJoinRequest).filter(TeamJoinRequest.team_id.in_(team_ids))) if team_ids else 0
        )
        n_invite = _count(db.query(TeamInvite).filter(TeamInvite.team_id.in_(team_ids))) if team_ids else 0
        n_member = _count(db.query(TeamMember).filter(TeamMember.team_id.in_(team_ids))) if team_ids else 0
        n_enroll_team = (
            _count(db.query(CompetitionEnrollment).filter(CompetitionEnrollment.team_id.in_(team_ids)))
            if team_ids
            else 0
        )
        n_enroll_user = (
            _count(
                db.query(CompetitionEnrollment).filter(
                    CompetitionEnrollment.competition_id == args.competition_id,
                    CompetitionEnrollment.student_id.in_(user_ids),
                )
            )
            if user_ids
            else 0
        )
        n_promo = 0
        if team_ids or user_ids:
            q = db.query(CompetitionPromotion).filter(
                CompetitionPromotion.to_competition_id == args.competition_id
            )
            if team_ids and user_ids:
                from sqlalchemy import or_

                q = q.filter(
                    or_(
                        CompetitionPromotion.final_team_id.in_(team_ids),
                        CompetitionPromotion.source_student_id.in_(user_ids),
                    )
                )
            elif team_ids:
                q = q.filter(CompetitionPromotion.final_team_id.in_(team_ids))
            else:
                q = q.filter(CompetitionPromotion.source_student_id.in_(user_ids))
            n_promo = q.count()
        n_sub = 0
        n_rev = 0
        if team_ids or user_ids:
            from sqlalchemy import or_

            sub_q = db.query(Submission).filter(Submission.competition_id == args.competition_id)
            conds = []
            if team_ids:
                conds.append(Submission.team_id.in_(team_ids))
            if user_ids:
                conds.append(Submission.student_id.in_(user_ids))
            subs = sub_q.filter(or_(*conds)).all() if conds else []
            n_sub = len(subs)
            sub_ids = [int(s.id) for s in subs]
            n_rev = (
                db.query(Review).filter(Review.submission_id.in_(sub_ids)).count() if sub_ids else 0
            )

        print(
            "关联："
            f"答案 {n_answers}，评分 {n_grades}，专家指派 {n_expert_teams}，"
            f"入队申请 {n_join}，邀请 {n_invite}，队员 {n_member}，"
            f"报名(队) {n_enroll_team}，报名(人) {n_enroll_user}，"
            f"白名单 {n_promo}，作品 {n_sub}，评审 {n_rev}"
        )

        if not args.yes:
            print("预览结束。确认无误后加上 --yes 再执行。")
            return 0
        if not users and not teams:
            print("没有可删数据。")
            return 0

        from sqlalchemy import or_

        if team_ids:
            db.query(CompetitionQuestionAnswer).filter(
                CompetitionQuestionAnswer.team_id.in_(team_ids)
            ).delete(synchronize_session=False)
            db.query(CompetitionTeamQuestionGrade).filter(
                CompetitionTeamQuestionGrade.team_id.in_(team_ids)
            ).delete(synchronize_session=False)
            db.query(CompetitionExpertTeamAssignment).filter(
                CompetitionExpertTeamAssignment.team_id.in_(team_ids)
            ).delete(synchronize_session=False)
            db.query(TeamJoinRequest).filter(TeamJoinRequest.team_id.in_(team_ids)).delete(
                synchronize_session=False
            )
            db.query(TeamInvite).filter(TeamInvite.team_id.in_(team_ids)).delete(
                synchronize_session=False
            )
            db.query(TeamMember).filter(TeamMember.team_id.in_(team_ids)).delete(
                synchronize_session=False
            )

        sub_q = db.query(Submission).filter(Submission.competition_id == args.competition_id)
        conds = []
        if team_ids:
            conds.append(Submission.team_id.in_(team_ids))
        if user_ids:
            conds.append(Submission.student_id.in_(user_ids))
        if conds:
            subs = sub_q.filter(or_(*conds)).all()
            sub_ids = [int(s.id) for s in subs]
            if sub_ids:
                db.query(Review).filter(Review.submission_id.in_(sub_ids)).delete(
                    synchronize_session=False
                )
                db.query(Submission).filter(Submission.id.in_(sub_ids)).delete(
                    synchronize_session=False
                )

        if team_ids:
            db.query(CompetitionEnrollment).filter(
                CompetitionEnrollment.team_id.in_(team_ids)
            ).delete(synchronize_session=False)
        if user_ids:
            db.query(CompetitionEnrollment).filter(
                CompetitionEnrollment.competition_id == args.competition_id,
                CompetitionEnrollment.student_id.in_(user_ids),
            ).delete(synchronize_session=False)

        promo_q = db.query(CompetitionPromotion).filter(
            CompetitionPromotion.to_competition_id == args.competition_id
        )
        promo_conds = []
        if team_ids:
            promo_conds.append(CompetitionPromotion.final_team_id.in_(team_ids))
        if user_ids:
            promo_conds.append(CompetitionPromotion.source_student_id.in_(user_ids))
        if promo_conds:
            promo_q.filter(or_(*promo_conds)).delete(synchronize_session=False)

        if team_ids:
            db.query(Team).filter(Team.id.in_(team_ids)).delete(synchronize_session=False)

        if user_ids:
            adb.query(AltAuthUserRecord).filter(AltAuthUserRecord.id.in_(user_ids)).delete(
                synchronize_session=False
            )

        db.commit()
        adb.commit()
        print("已删除测试账号及相关队伍/报名/白名单/答案。")
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
