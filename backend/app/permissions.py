from enum import Enum
from typing import List
from fastapi import HTTPException, status


class Permission(Enum):
    VIEW_SYSTEM_METRICS = "view_system_metrics"
    MANAGE_USERS = "manage_users"
    MANAGE_TEACHERS = "manage_teachers"
    MANAGE_STUDENTS = "manage_students"
    ALLOCATE_RESOURCES = "allocate_resources"
    VIEW_STUDENTS = "view_students"
    MANAGE_STUDENTS_TEACHER = "manage_students_teacher"
    SEND_FILES = "send_files"
    RECEIVE_FILES = "receive_files"
    GRADE_REPORTS = "grade_reports"
    SUBMIT_REPORTS = "submit_reports"
    MANAGE_KNOWLEDGE_BASE = "manage_knowledge_base"
    VIEW_KNOWLEDGE_BASE = "view_knowledge_base"

    # ---------- 竞赛报名系统 ----------
    VIEW_COMPETITIONS = "view_competitions"
    ENROLL_COMPETITIONS = "enroll_competitions"
    MANAGE_TEAMS = "manage_teams"
    SUBMIT_SUBMISSIONS = "submit_submissions"
    REVIEW_SUBMISSIONS = "review_submissions"
    MANAGE_COMPETITIONS = "manage_competitions"
    PUBLISH_WINNERS = "publish_winners"
    INVIGILATE_EXAMS = "invigilate_exams"

    # ---------- 考试模块 ----------
    MANAGE_QUESTION_BANK = "manage_question_bank"
    MANAGE_EXAMS = "manage_exams"
    TAKE_EXAMS = "take_exams"
    VIEW_EXAM_RESULTS = "view_exam_results"


def _role_key_for_permissions(user_role: str) -> str:
    """角色键标准化（不做角色互转，仅做空值回退）。"""
    return (user_role or "student").strip()


ROLE_PERMISSIONS = {
    "super_admin": [
        Permission.VIEW_SYSTEM_METRICS,
        Permission.MANAGE_USERS,
        Permission.MANAGE_TEACHERS,
        Permission.MANAGE_STUDENTS,
        Permission.ALLOCATE_RESOURCES,
        Permission.VIEW_STUDENTS,
        Permission.MANAGE_STUDENTS_TEACHER,
        Permission.SEND_FILES,
        Permission.RECEIVE_FILES,
        Permission.GRADE_REPORTS,
        Permission.SUBMIT_REPORTS,
        Permission.MANAGE_KNOWLEDGE_BASE,
        Permission.VIEW_KNOWLEDGE_BASE,

        Permission.VIEW_COMPETITIONS,
        # 管理员：赛制与数据查看，不进行作品评分（无 REVIEW_SUBMISSIONS）
        Permission.MANAGE_COMPETITIONS,
        Permission.PUBLISH_WINNERS,
        Permission.INVIGILATE_EXAMS,
        Permission.MANAGE_QUESTION_BANK,
        Permission.MANAGE_EXAMS,
        Permission.TAKE_EXAMS,
        Permission.VIEW_EXAM_RESULTS,
    ],
    # 指导老师：不可报名 / 提交作品；可代表队务（组队、拉队员）
    "advisor": [
        Permission.VIEW_SYSTEM_METRICS,
        Permission.MANAGE_STUDENTS_TEACHER,
        Permission.VIEW_STUDENTS,
        Permission.SEND_FILES,
        Permission.RECEIVE_FILES,
        Permission.GRADE_REPORTS,
        Permission.SUBMIT_REPORTS,
        Permission.MANAGE_KNOWLEDGE_BASE,
        Permission.VIEW_KNOWLEDGE_BASE,

        Permission.VIEW_COMPETITIONS,
        Permission.MANAGE_TEAMS,
        Permission.INVIGILATE_EXAMS,
        Permission.MANAGE_QUESTION_BANK,
        Permission.MANAGE_EXAMS,
        Permission.VIEW_EXAM_RESULTS,
    ],
    # teacher 与 advisor 并存：权限与 advisor 保持一致（不再自动互转）
    "teacher": [
        Permission.VIEW_SYSTEM_METRICS,
        Permission.MANAGE_STUDENTS_TEACHER,
        Permission.VIEW_STUDENTS,
        Permission.SEND_FILES,
        Permission.RECEIVE_FILES,
        Permission.GRADE_REPORTS,
        Permission.SUBMIT_REPORTS,
        Permission.MANAGE_KNOWLEDGE_BASE,
        Permission.VIEW_KNOWLEDGE_BASE,

        Permission.VIEW_COMPETITIONS,
        Permission.MANAGE_TEAMS,
        Permission.INVIGILATE_EXAMS,
        Permission.MANAGE_QUESTION_BANK,
        Permission.MANAGE_EXAMS,
        Permission.VIEW_EXAM_RESULTS,
    ],
    # 专家：仅能批改被指派的竞赛作品；具体指派由路由校验
    "expert": [
        Permission.VIEW_COMPETITIONS,
        Permission.REVIEW_SUBMISSIONS,
    ],
    "student": [
        Permission.RECEIVE_FILES,
        Permission.SUBMIT_REPORTS,
        Permission.VIEW_KNOWLEDGE_BASE,

        Permission.VIEW_COMPETITIONS,
        Permission.ENROLL_COMPETITIONS,
        Permission.MANAGE_TEAMS,
        Permission.SUBMIT_SUBMISSIONS,
        Permission.TAKE_EXAMS,
        Permission.VIEW_EXAM_RESULTS,
    ],
}


def check_permission(user_role: str, required_permission: Permission) -> bool:
    key = _role_key_for_permissions(user_role)
    if key not in ROLE_PERMISSIONS:
        return False

    user_permissions = ROLE_PERMISSIONS[key]
    return required_permission in user_permissions


def require_permission(user_role: str, required_permission: Permission):
    if not check_permission(user_role, required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {required_permission.value}"
        )
    return True


class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user_role: str):
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {user_role} not allowed to access this resource"
            )
        return True
