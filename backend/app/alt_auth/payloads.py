"""
第二套认证请求/响应：与主站 ``UserCreate`` / ``UserLogin`` / ``Token`` 字段对齐，
注册体在相同字段基础上 **增加必填** ``school``。
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas import UserRole


class AltAuthRegisterPayload(BaseModel):
    """
    对齐 ``UserCreate``，并增加 ``school``。
    密码规则与主站一致：`min_length=6`（无额外强度策略）。
    """

    username: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
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
        if v not in (UserRole.STUDENT, UserRole.ADVISOR, UserRole.TEACHER, UserRole.EXPERT):
            raise ValueError("无效角色")
        return v


class AltAuthLoginPayload(BaseModel):
    """对齐 ``UserLogin``：用户名 + 密码。"""

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
    """对齐 ``UserResponse`` 主要字段 + ``school``。"""

    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool = True
    student_id: Optional[str] = None
    teacher_id: Optional[str] = None
    school: Optional[str] = None
    expert_verified: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class AltAuthLoginResult(BaseModel):
    """
    对齐主站 ``Token``，并 **额外返回** ``school``（可选，历史用户可能无学校）。
    """

    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: str
    full_name: Optional[str] = None
    school: Optional[str] = None


class AltAuthProfileResponse(BaseModel):
    """当前用户 + 权限展开（主站 `/auth/me` 无 permissions 字段）。"""

    id: int
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_active: bool
    student_id: Optional[str] = None
    teacher_id: Optional[str] = None
    school: Optional[str] = None
    created_at: Optional[datetime] = None
    expert_verified: bool = False
    assigned_competition_ids: List[int] = Field(
        default_factory=list,
        description="专家已被指派的竞赛 id；非 expert 或尚未指派时为 []",
    )
    effective_permissions: list[str]
