"""

第二套 REST 登录/注册路由：路径、模型、校验、Token 均独立于 /api/v1/auth。

请求体字段与主站 ``UserCreate`` / ``UserLogin`` 对齐；注册多必填 ``school``。

"""

from __future__ import annotations



import logging

from typing import Optional



from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import or_

from sqlalchemy.exc import IntegrityError

from sqlalchemy.orm import Session



from app.alt_auth.database import get_alt_auth_db

from app.alt_auth.models import AltAuthUserRecord

from app.alt_auth.context import get_current_alt_identity

from app.alt_auth.payloads import (

    AltAuthLoginPayload,

    AltAuthLoginResult,

    AltAuthProfileResponse,

    AltAuthRegisterPayload,

    AltAuthRegisterResult,

)

from app.alt_auth.permission_view import list_effective_permissions_for_role

from app.alt_auth.password_codec import hash_password_plain, verify_password_plain

from app.alt_auth.token_codec import issue_access_token

from app.schemas import UserRole



logger = logging.getLogger(__name__)



_ALLOWED_ROLE_VALUES = frozenset(

    {

        UserRole.SUPER_ADMIN.value,

        UserRole.TEACHER.value,

        UserRole.STUDENT.value,

    }

)





def _normalize_stored_role(value: Optional[str]) -> str:

    r = (value or UserRole.STUDENT.value).strip()

    if r not in _ALLOWED_ROLE_VALUES:

        return UserRole.STUDENT.value

    return r





# 挂载到主应用时建议使用 prefix="/api/alt-identity"，全路径形如：

#   POST /api/alt-identity/register

#   POST /api/alt-identity/session   （登录，避免与主系统 /login 混淆）

router = APIRouter(tags=["Alt Identity — independent auth"])





@router.post(

    "/register",

    response_model=AltAuthRegisterResult,

    status_code=status.HTTP_201_CREATED,

    summary="第二套注册",

    responses={

        400: {"description": "校验失败或用户名/邮箱已存在"},

        500: {"description": "服务器内部错误"},

    },

)

async def alt_identity_register(

    body: AltAuthRegisterPayload,

    db: Session = Depends(get_alt_auth_db),

):

    """

    使用独立表 ``alt_auth_users``；密码 BCrypt；字段与 ``POST /api/v1/auth/register`` 一致，

    并 **多** 必填 ``school``。



    **权限**：无需认证（与主站注册一致）。



    **角色**：``role`` 与主站相同，决定 ``app.permissions.ROLE_PERMISSIONS``。

    """

    username = body.username

    email_norm = str(body.email).strip().lower()



    try:

        existing = (

            db.query(AltAuthUserRecord)

            .filter(

                or_(

                    AltAuthUserRecord.username == username,

                    AltAuthUserRecord.email == email_norm,

                )

            )

            .first()

        )

        if existing:

            raise HTTPException(

                status_code=status.HTTP_400_BAD_REQUEST,

                detail="Username or email already registered",

            )



        role_str = body.role.value if hasattr(body.role, "value") else str(body.role)

        role_str = _normalize_stored_role(role_str)

        hashed = hash_password_plain(body.password)



        row = AltAuthUserRecord(

            username=username,

            email=email_norm,

            full_name=body.full_name,

            student_id=body.student_id,

            teacher_id=body.teacher_id,

            hashed_password=hashed,

            role=role_str,

            is_active=True,

            school=body.school,

            account=email_norm,

            account_kind="email",

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

            "alt_identity register integrity (username/email): %s / %s",

            username,

            email_norm,

        )

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail="Username or email already registered",

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

    """

    使用 **用户名** + 密码（与 ``UserLogin`` 一致）；成功后签发独立 JWT。



    **权限**：无需认证（与主站登录语义一致）。



    **停用**：``is_active=false`` 时返回 403。

    """

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

        login_name = (row.username or "").strip() or (row.account or "").strip()

        token_str, _ttl = issue_access_token(

            user_id=row.id, username=login_name, role=role_out

        )



        return AltAuthLoginResult(

            access_token=token_str,

            token_type="bearer",

            user_id=row.id,

            role=role_out,

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

):

    """

    需请求头：``Authorization: Bearer <第二套 access_token>``。



    返回 ``effective_permissions``：与主站 ``ROLE_PERMISSIONS[role]`` 一致。

    """

    role_out = _normalize_stored_role(principal.role)

    return AltAuthProfileResponse(

        id=principal.id,

        username=principal.username,

        email=principal.email,

        full_name=principal.full_name,

        role=role_out,

        is_active=bool(principal.is_active),

        student_id=principal.student_id,

        teacher_id=principal.teacher_id,

        school=principal.school,

        created_at=principal.created_at,

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
    """
    与主站 ``POST /api/v1/auth/refresh-token`` 语义一致：凭有效第二套 JWT 换取新 ``access_token``。
    请求头须为 ``Authorization: Bearer <第二套 access_token>``；**不可**使用主站 Token。
    """
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
        full_name=principal.full_name,
        school=principal.school,
    )


