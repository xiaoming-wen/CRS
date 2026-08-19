"""
第二套认证请求/响应：注册以手机号 + 短信验证码为主（不再要求邮箱）。
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas import UserRole

_CN_MOBILE_RE = re.compile(r"^1[3-9]\d{9}$")


def normalize_cn_mobile(raw: str) -> str:
    s = str(raw or "").strip().replace(" ", "").replace("-", "")
    if s.startswith("+86"):
        s = s[3:]
    if s.startswith("86") and len(s) == 13:
        s = s[2:]
    return s


class AltAuthSendSmsCodePayload(BaseModel):
    phone: str = Field(..., min_length=11, max_length=20, description="中国大陆手机号")
    purpose: str = Field("register", description="用途：目前支持 register")

    @field_validator("phone")
    @classmethod
    def phone_cn_mobile(cls, v: str) -> str:
        s = normalize_cn_mobile(v)
        if not _CN_MOBILE_RE.match(s):
            raise ValueError("请输入正确的11位手机号")
        return s

    @field_validator("purpose")
    @classmethod
    def purpose_allowed(cls, v: str) -> str:
        s = (v or "register").strip().lower() or "register"
        if s != "register":
            raise ValueError("purpose 仅支持 register")
        return s


class AltAuthSendSmsCodeResult(BaseModel):
    ok: bool = True
    message: str = "验证码已发送"
    cooldown_seconds: int = 60
    # 仅 ALIYUN_SMS_DEBUG=true 时可能返回，便于联调
    debug_code: Optional[str] = None


class AltAuthRegisterPayload(BaseModel):
    """
    手机号注册：须先调用 send-sms-code。
    """

    username: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=11, max_length=20)
    sms_code: str = Field(..., min_length=4, max_length=8, description="短信验证码")
    full_name: Optional[str] = None
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole
    student_id: Optional[str] = None
    teacher_id: Optional[str] = None
    school: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="学校名称（第二套相对主站多出的字段）",
    )

    @field_validator("username")
    @classmethod
    def username_strip(cls, v: str) -> str:
        s = str(v).strip()
        if not s:
            raise ValueError("用户名不能为空")
        return s

    @field_validator("phone")
    @classmethod
    def phone_cn_mobile(cls, v: str) -> str:
        s = normalize_cn_mobile(v)
        if not _CN_MOBILE_RE.match(s):
            raise ValueError("请输入正确的11位手机号")
        return s

    @field_validator("sms_code")
    @classmethod
    def sms_code_digits(cls, v: str) -> str:
        s = str(v or "").strip()
        if not s or not s.isdigit():
            raise ValueError("验证码格式不正确")
        return s

    @field_validator("password")
    @classmethod
    def password_non_empty(cls, v: str) -> str:
        if v is None or not str(v).strip():
            raise ValueError("密码不能为空")
        return str(v)

    @field_validator("full_name", "student_id", "teacher_id")
    @classmethod
    def strip_optional_blank_to_none(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    @field_validator("school")
    @classmethod
    def school_not_blank(cls, v: str) -> str:
        s = str(v).strip()
        if not s:
            raise ValueError("学校名称不能为空")
        return s

    @field_validator("role")
    @classmethod
    def registerable_role_only(cls, v: UserRole) -> UserRole:
        if v == UserRole.SUPER_ADMIN:
            raise ValueError("该角色不可自助注册，请联系管理员")
        if v not in (
            UserRole.STUDENT,
            UserRole.ADVISOR,
            UserRole.TEACHER,
            UserRole.EXPERT,
            UserRole.SCHOOL_ADMIN,
        ):
            raise ValueError("无效角色")
        return v


class AltAuthLoginPayload(BaseModel):
    """对齐 UserLogin：用户名 + 密码。"""

    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("username", "password")
    @classmethod
    def strip_non_empty(cls, v: str) -> str:
        s = str(v).strip()
        if not s:
            raise ValueError("用户名与密码均不能为空")
        return s


class AltAuthRegisterResult(BaseModel):
    id: int
    username: str
    phone: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_active: bool = True
    student_id: Optional[str] = None
    teacher_id: Optional[str] = None
    school: Optional[str] = None
    expert_verified: bool = False
    school_admin_verified: bool = False
    school_admin_application_status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AltAuthLoginResult(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    school: Optional[str] = None


class AltAuthAssignedTeam(BaseModel):
    competition_id: int
    team_id: int
    team_name: Optional[str] = None


class AltAuthProfileResponse(BaseModel):
    id: int
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_active: bool
    student_id: Optional[str] = None
    teacher_id: Optional[str] = None
    school: Optional[str] = None
    created_at: Optional[datetime] = None
    expert_verified: bool = False
    school_admin_verified: bool = False
    school_admin_application_status: Optional[str] = Field(
        None,
        description="校管申请状态：null/空=未提交；pending=待审；approved=已通过；rejected=已驳回",
    )
    school_admin_application_submitted_at: Optional[datetime] = None
    school_admin_review_feedback: Optional[str] = None
    school_admin_photo_url: Optional[str] = Field(
        None,
        description="校管申请照片访问路径（仅本人或 super_admin 可见时有值）",
    )
    assigned_competition_ids: List[int] = Field(
        default_factory=list,
        description="专家已被指派的竞赛 id；非 expert 或尚未指派时为 []",
    )
    assigned_teams: List[AltAuthAssignedTeam] = Field(
        default_factory=list,
        description="专家可评阅的队伍列表",
    )
    effective_permissions: list[str]
