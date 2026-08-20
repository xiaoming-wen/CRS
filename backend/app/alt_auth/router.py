"""
第二套 REST 登录/注册路由：路径、模型、校验、Token 均独立于 /api/v1/auth。
注册使用手机号 + 短信验证码（不再要求邮箱）。
"""
from __future__ import annotations

import logging
import random
import string
from datetime import timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.alt_auth import settings as alt_settings
from app.alt_auth.context import get_current_alt_identity
from app.alt_auth.database import get_alt_auth_db
from app.alt_auth.models import AltAuthSmsCodeRecord, AltAuthUserRecord
from app.alt_auth.password_codec import hash_password_plain, verify_password_plain
from app.alt_auth.payloads import (
    AltAuthLoginPayload,
    AltAuthLoginResult,
    AltAuthProfileResponse,
    AltAuthRegisterPayload,
    AltAuthRegisterResult,
    AltAuthResetPasswordPayload,
    AltAuthResetPasswordResult,
    AltAuthSendSmsCodePayload,
    AltAuthSendSmsCodeResult,
)
from app.alt_auth.permission_view import list_effective_permissions_for_role
from app.alt_auth.sms_service import send_verification_sms
from app.alt_auth.time_util import utc_now_naive
from app.alt_auth.token_codec import issue_access_token
from app.database import get_db
from app.eight_digit_id import allocate_eight_digit_id
from app.schemas import UserRole

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Alt Identity — independent auth"])


def _persist_alt_register_role(role) -> str:
    v = role.value if hasattr(role, "value") else str(role)
    return v.strip()


def _normalize_stored_role(value: Optional[str]) -> str:
    return (value or UserRole.STUDENT.value).strip()


def _assigned_competition_ids_for_expert(main_db: Session, expert_user_id: int) -> List[int]:
    from app.models.competition import CompetitionExpertAssignment

    rows = (
        main_db.query(CompetitionExpertAssignment.competition_id)
        .filter(CompetitionExpertAssignment.expert_id == expert_user_id)
        .all()
    )
    return sorted({int(r[0]) for r in rows})


def _assigned_teams_for_expert(main_db: Session, expert_user_id: int):
    from app.models.competition import CompetitionExpertTeamAssignment, Team
    from app.alt_auth.payloads import AltAuthAssignedTeam

    rows = (
        main_db.query(
            CompetitionExpertTeamAssignment.competition_id,
            CompetitionExpertTeamAssignment.team_id,
            Team.name,
        )
        .outerjoin(Team, Team.id == CompetitionExpertTeamAssignment.team_id)
        .filter(CompetitionExpertTeamAssignment.expert_id == expert_user_id)
        .all()
    )
    items = [
        AltAuthAssignedTeam(
            competition_id=int(comp_id),
            team_id=int(team_id),
            team_name=team_name,
        )
        for comp_id, team_id, team_name in rows
    ]
    return sorted(items, key=lambda t: (t.competition_id, t.team_id))


def _generate_sms_code(length: int = 6) -> str:
    return "".join(random.choice(string.digits) for _ in range(length))


def _consume_sms_code(db: Session, phone: str, purpose: str, code: str) -> None:
    now = utc_now_naive()
    row = (
        db.query(AltAuthSmsCodeRecord)
        .filter(
            AltAuthSmsCodeRecord.phone == phone,
            AltAuthSmsCodeRecord.purpose == purpose,
            AltAuthSmsCodeRecord.used.is_(False),
            AltAuthSmsCodeRecord.expires_at >= now,
        )
        .order_by(AltAuthSmsCodeRecord.id.desc())
        .first()
    )
    if row is None or str(row.code) != str(code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码无效或已过期",
        )
    row.used = True
    db.flush()


@router.post(
    "/send-sms-code",
    response_model=AltAuthSendSmsCodeResult,
    summary="发送短信验证码（注册 / 忘记密码）",
    responses={
        400: {"description": "手机号无效、用途不匹配或发送过于频繁"},
        500: {"description": "短信发送失败"},
    },
)
async def alt_identity_send_sms_code(
    body: AltAuthSendSmsCodePayload,
    db: Session = Depends(get_alt_auth_db),
):
    phone = body.phone
    purpose = body.purpose
    cooldown = int(alt_settings.SMS_CODE_RESEND_INTERVAL_SECONDS or 60)
    ttl = int(alt_settings.SMS_CODE_TTL_SECONDS or 300)

    existing_user = (
        db.query(AltAuthUserRecord)
        .filter(AltAuthUserRecord.phone == phone)
        .first()
    )
    if purpose == "register":
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该手机号已被注册",
            )
    elif purpose == "reset_password":
        if existing_user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该手机号未注册",
            )
        if not bool(getattr(existing_user, "is_active", True)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="账号已停用，请联系管理员",
            )

    now = utc_now_naive()
    latest = (
        db.query(AltAuthSmsCodeRecord)
        .filter(
            AltAuthSmsCodeRecord.phone == phone,
            AltAuthSmsCodeRecord.purpose == purpose,
        )
        .order_by(AltAuthSmsCodeRecord.id.desc())
        .first()
    )
    if latest is not None and latest.created_at is not None:
        elapsed = (now - latest.created_at).total_seconds()
        if elapsed < cooldown:
            remain = max(1, int(cooldown - elapsed))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"发送过于频繁，请 {remain} 秒后再试",
            )

    code = _generate_sms_code(6)
    ok, msg = send_verification_sms(phone, code)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"短信发送失败：{msg}",
        )

    db.add(
        AltAuthSmsCodeRecord(
            phone=phone,
            code=code,
            purpose=purpose,
            expires_at=now + timedelta(seconds=ttl),
            used=False,
            created_at=now,
        )
    )
    db.commit()

    result = AltAuthSendSmsCodeResult(
        ok=True,
        message="验证码已发送",
        cooldown_seconds=cooldown,
    )
    if alt_settings.ALIYUN_SMS_DEBUG:
        result.debug_code = code
        result.message = "验证码已发送（调试模式）"
    return result


@router.post(
    "/reset-password",
    response_model=AltAuthResetPasswordResult,
    summary="忘记密码：手机号验证码重置密码",
    responses={
        400: {"description": "手机号未注册或验证码无效"},
    },
)
async def alt_identity_reset_password(
    body: AltAuthResetPasswordPayload,
    db: Session = Depends(get_alt_auth_db),
):
    phone = body.phone
    user = (
        db.query(AltAuthUserRecord)
        .filter(AltAuthUserRecord.phone == phone)
        .first()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该手机号未注册",
        )
    if not bool(getattr(user, "is_active", True)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="账号已停用，请联系管理员",
        )

    try:
        _consume_sms_code(db, phone, "reset_password", body.sms_code)
        user.hashed_password = hash_password_plain(body.new_password)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("reset password failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重置密码失败，请稍后重试",
        ) from e

    return AltAuthResetPasswordResult(
        ok=True,
        message="密码已重置，请使用新密码登录",
        username=user.username,
    )


@router.post(
    "/register",
    response_model=AltAuthRegisterResult,
    status_code=status.HTTP_201_CREATED,
    summary="第二套注册（手机号+短信验证码）",
    responses={
        400: {"description": "校验失败或用户名/手机号已存在"},
        500: {"description": "服务器内部错误"},
    },
)
async def alt_identity_register(
    body: AltAuthRegisterPayload,
    db: Session = Depends(get_alt_auth_db),
):
    username = body.username
    phone = body.phone

    try:
        existing = (
            db.query(AltAuthUserRecord)
            .filter(
                or_(
                    AltAuthUserRecord.username == username,
                    AltAuthUserRecord.phone == phone,
                )
            )
            .first()
        )
        if existing:
            if (existing.username or "") == username:
                detail = "该用户名已被注册"
            else:
                detail = "该手机号已被注册"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail,
            )

        _consume_sms_code(db, phone, "register", body.sms_code)

        role_str = _persist_alt_register_role(body.role)
        hashed = hash_password_plain(body.password)

        row = AltAuthUserRecord(
            id=allocate_eight_digit_id(db, AltAuthUserRecord),
            username=username,
            email=None,
            phone=phone,
            full_name=body.full_name,
            student_id=body.student_id,
            teacher_id=body.teacher_id,
            hashed_password=hashed,
            role=role_str,
            expert_verified=False,
            school_admin_verified=False,
            is_active=True,
            school=body.school,
            account=phone,
            account_kind="phone",
        )

        db.add(row)
        db.commit()
        db.refresh(row)
        return AltAuthRegisterResult.model_validate(row)
    except HTTPException:
        raise
    except IntegrityError:
        db.rollback()
        logger.warning(
            "alt_identity register integrity (username/phone): %s / %s",
            username,
            phone,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该用户名或手机号已被注册",
        ) from None
    except Exception as e:
        db.rollback()
        logger.exception("alt_identity register failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Register failed: {type(e).__name__}: {str(e)}",
        ) from e


@router.post(
    "/session",
    response_model=AltAuthLoginResult,
    summary="第二套登录（创建会话令牌）",
    responses={
        400: {"description": "用户名或格式错误"},
        401: {"description": "凭据不正确"},
        403: {"description": "账号已停用"},
        500: {"description": "服务器内部错误"},
    },
)
async def alt_identity_login(
    body: AltAuthLoginPayload,
    db: Session = Depends(get_alt_auth_db),
):
    try:
        uname = body.username
        row: Optional[AltAuthUserRecord] = (
            db.query(AltAuthUserRecord)
            .filter(AltAuthUserRecord.username == uname)
            .first()
        )

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not row.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        if not verify_password_plain(body.password, row.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        role_out = _normalize_stored_role(row.role)
        if role_out == UserRole.EXPERT.value and not bool(getattr(row, "expert_verified", False)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Expert account pending verification; please wait for administrator approval",
            )

        login_name = (row.username or "").strip() or (row.account or "").strip()
        token_str, _ttl = issue_access_token(
            user_id=row.id, username=login_name, role=role_out
        )

        return AltAuthLoginResult(
            access_token=token_str,
            token_type="bearer",
            user_id=row.id,
            role=role_out,
            username=login_name or None,
            full_name=row.full_name,
            school=row.school,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("alt_identity login failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {type(e).__name__}: {str(e)}",
        ) from e


@router.get(
    "/me",
    response_model=AltAuthProfileResponse,
    summary="第二套当前主体与有效权限",
    responses={401: {"description": "未提供或无效的第二套 JWT"}},
)
async def alt_identity_me(
    principal: AltAuthUserRecord = Depends(get_current_alt_identity),
    main_db: Session = Depends(get_db),
):
    role_out = _normalize_stored_role(principal.role)
    assigned_ids: List[int] = []
    assigned_teams = []
    if role_out == UserRole.EXPERT.value:
        assigned_ids = _assigned_competition_ids_for_expert(main_db, principal.id)
        assigned_teams = _assigned_teams_for_expert(main_db, principal.id)

    school_admin_photo_url = None
    if (
        role_out == UserRole.SCHOOL_ADMIN.value
        and getattr(principal, "school_admin_photo_path", None)
    ):
        school_admin_photo_url = "/api/v1/competitions/school-admin/application/photo"

    return AltAuthProfileResponse(
        id=principal.id,
        username=principal.username,
        email=principal.email,
        phone=getattr(principal, "phone", None),
        full_name=principal.full_name,
        role=role_out,
        is_active=bool(principal.is_active),
        student_id=principal.student_id,
        teacher_id=principal.teacher_id,
        school=principal.school,
        created_at=principal.created_at,
        expert_verified=bool(getattr(principal, "expert_verified", False)),
        school_admin_verified=bool(getattr(principal, "school_admin_verified", False)),
        school_admin_application_status=getattr(principal, "school_admin_application_status", None),
        school_admin_application_submitted_at=getattr(
            principal, "school_admin_application_submitted_at", None
        ),
        school_admin_review_feedback=getattr(principal, "school_admin_review_feedback", None),
        school_admin_photo_url=school_admin_photo_url,
        assigned_competition_ids=assigned_ids,
        assigned_teams=assigned_teams,
        effective_permissions=list_effective_permissions_for_role(role_out),
    )


@router.post(
    "/refresh-token",
    response_model=AltAuthLoginResult,
    summary="第二套刷新访问令牌",
    responses={401: {"description": "未提供或无效的第二套 JWT"}},
)
async def alt_identity_refresh_token(
    principal: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    role_out = _normalize_stored_role(principal.role)
    login_name = (principal.username or "").strip() or (principal.account or "").strip()
    token_str, _ttl = issue_access_token(
        user_id=principal.id, username=login_name, role=role_out
    )
    return AltAuthLoginResult(
        access_token=token_str,
        token_type="bearer",
        user_id=principal.id,
        role=role_out,
        username=login_name or None,
        full_name=principal.full_name,
        school=principal.school,
    )
