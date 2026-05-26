"""

第二套认证 ORM（仅存在于 alt_auth.db）。

字段与主站 ``User`` 对齐（username / email / …），并增加 ``school``。

保留 ``account`` / ``account_kind`` 仅兼容历史数据，新业务以 username+email 为准。

"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String



from app.alt_auth.database import Base

from app.alt_auth.time_util import utc_now_naive





class AltAuthUserRecord(Base):

    __tablename__ = "alt_auth_users"



    id = Column(Integer, primary_key=True, index=True, autoincrement=True)



    username = Column(String(100), nullable=True, index=True)

    email = Column(String(200), nullable=True, index=True)

    full_name = Column(String(100), nullable=True)

    student_id = Column(String(50), nullable=True)

    teacher_id = Column(String(50), nullable=True)



    hashed_password = Column(String(255), nullable=False)

    role = Column(String(32), nullable=False, default="student")

    is_active = Column(Boolean, nullable=False, default=True)

    school = Column(String(200), nullable=True)

    # 历史：曾用统一 account + account_kind；可为空

    account = Column(String(256), nullable=True, index=True)

    account_kind = Column(String(16), nullable=True)



    created_at = Column(DateTime, default=utc_now_naive)

    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)
