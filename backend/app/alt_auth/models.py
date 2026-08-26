"""
第二套认证 ORM（仅存在于 alt_auth 库）。
字段与主站 User 对齐，并增加 school / phone。
保留 account / account_kind 仅兼容历史数据。
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.alt_auth.database import Base
from app.alt_auth.time_util import utc_now_naive


class AltAuthUserRecord(Base):
    __tablename__ = "alt_auth_users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)

    username = Column(String(100), nullable=True, index=True)
    email = Column(String(200), nullable=True, index=True)
    phone = Column(String(20), nullable=True, index=True)
    full_name = Column(String(100), nullable=True)
    student_id = Column(String(50), nullable=True)
    teacher_id = Column(String(50), nullable=True)

    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="student")
    is_active = Column(Boolean, nullable=False, default=True)
    school = Column(String(200), nullable=True)

    # 竞赛专家：须由管理员设为 true 后才可担任评委
    expert_verified = Column(Boolean, nullable=False, default=False)
    expert_review_feedback = Column(String(2000), nullable=True, comment="专家核验未通过原因")

    # 校管理员：注册后可登录；提交资料并经 super_admin 审核通过后方可组队校审
    school_admin_verified = Column(Boolean, nullable=False, default=False)
    school_admin_photo_path = Column(String(512), nullable=True, comment="校管理员申请照片相对路径")
    school_admin_application_status = Column(
        String(30),
        nullable=True,
        comment="校管申请状态：pending / approved / rejected；空表示未提交",
    )
    school_admin_application_contact = Column(String(200), nullable=True, comment="校管申请联系方式")
    school_admin_application_remark = Column(String(1000), nullable=True, comment="校管申请备注")
    school_admin_application_submitted_at = Column(DateTime, nullable=True)
    school_admin_review_feedback = Column(String(2000), nullable=True)
    school_admin_reviewed_at = Column(DateTime, nullable=True)
    school_admin_reviewed_by_id = Column(Integer, nullable=True, index=True)

    # 历史：曾用统一 account + account_kind；可为空
    account = Column(String(256), nullable=True, index=True)
    account_kind = Column(String(16), nullable=True)

    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)


class AltAuthSmsCodeRecord(Base):
    """手机短信验证码（注册等）。"""

    __tablename__ = "alt_auth_sms_codes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    phone = Column(String(20), nullable=False, index=True)
    code = Column(String(16), nullable=False)
    purpose = Column(String(32), nullable=False, default="register", index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=utc_now_naive, nullable=False)
