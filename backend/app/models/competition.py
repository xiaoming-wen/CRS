from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Float, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import UserBase as Base
from app.datetime_utils import utc_now


class CompetitionStatus(str):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class CompetitionDivisionMode(str):
    """是否分本科/高职组别。"""
    SINGLE = "single"
    DUAL = "dual"


class CompetitionQrLayout(str):
    """双组别时的二维码策略。"""
    SHARED = "shared"
    SEPARATE = "separate"


class CompetitionDivision(str):
    """学历组别（报名/组队归属）。"""
    DEFAULT = "default"
    UNDERGRADUATE = "undergraduate"
    VOCATIONAL = "vocational"


class Competition(Base):
    __tablename__ = "competitions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    rules_text = Column(Text)

    status = Column(String(30), default=CompetitionStatus.DRAFT, nullable=False)
    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)

    allow_individual = Column(Boolean, default=True, nullable=False)
    allow_team = Column(Boolean, default=True, nullable=False)

    division_mode = Column(
        String(20),
        default=CompetitionDivisionMode.SINGLE,
        nullable=False,
    )
    qr_layout = Column(
        String(20),
        default=CompetitionQrLayout.SHARED,
        nullable=False,
    )

    qr_code_path = Column(String(512), nullable=True)
    qr_code_path_undergraduate = Column(String(512), nullable=True)
    qr_code_path_vocational = Column(String(512), nullable=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    teams = relationship("Team", back_populates="competition")
    enrollments = relationship("CompetitionEnrollment", back_populates="competition")


class CompetitionEnrollmentStatus(str):
    ENROLLED = "enrolled"
    WITHDRAWN = "withdrawn"


class CompetitionEnrollmentScope(str):
    """同一学生可在同一竞赛同时持有个人与组队两条有效报名（各一条）。"""
    INDIVIDUAL = "individual"
    TEAM = "team"


class CompetitionEnrollment(Base):
    """
    学生在某竞赛的报名记录。
    ``student_id`` 存 **第二套主体** ``alt_auth_users.id``（无外键、不引用主库 ``users``）。
    每人每赛每种赛道（``enrollment_scope``）至多一条记录。
    """

    __tablename__ = "competition_enrollments"
    __table_args__ = (
        UniqueConstraint(
            "competition_id",
            "student_id",
            "enrollment_scope",
            name="uq_competition_student_scope",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False)
    student_id = Column(Integer, nullable=False, index=True)

    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    enrollment_scope = Column(
        String(20),
        default=CompetitionEnrollmentScope.INDIVIDUAL,
        nullable=False,
    )
    division = Column(
        String(20),
        default=CompetitionDivision.DEFAULT,
        nullable=False,
        comment="学历组别：default / undergraduate / vocational",
    )

    is_captain = Column(Boolean, default=False, nullable=False)

    student_no = Column(String(50), nullable=True, comment="学号")
    real_name = Column(String(100), nullable=True, comment="姓名")
    college = Column(String(200), nullable=True, comment="学院")
    grade = Column(String(50), nullable=True, comment="年级，如 2023级")
    contact = Column(String(100), nullable=True, comment="联系方式（手机/邮箱）")

    status = Column(String(30), default=CompetitionEnrollmentStatus.ENROLLED, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    competition = relationship("Competition", back_populates="enrollments")
    team = relationship("Team", foreign_keys=[team_id], uselist=False)


class TeamStatus(str):
    PENDING_SCHOOL_REVIEW = "pending_school_review"
    ACTIVE = "active"
    REJECTED = "rejected"
    DISBANDED = "disbanded"


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False)

    # 展示用队名（队长或指导老师创建者可修改）
    name = Column(String(200), nullable=True)

    # alt_auth_users.id（队长，须为学生）
    captain_id = Column(Integer, nullable=False, index=True)

    # 指导老师代为建队时记录其 alt_auth_users.id（普通学生自建队则为空）
    created_by_advisor_id = Column(Integer, nullable=True, index=True)
    # 学生自建队时填写的指导老师姓名（展示用；可与 created_by_advisor_id 并存）
    advisor_name = Column(String(100), nullable=True)

    division = Column(
        String(20),
        default=CompetitionDivision.DEFAULT,
        nullable=False,
        comment="队伍所属学历组别",
    )

    status = Column(String(30), default=TeamStatus.PENDING_SCHOOL_REVIEW, nullable=False)

    school = Column(String(200), nullable=True, comment="队伍所属学校（队长学校快照）")
    reviewed_by_id = Column(Integer, nullable=True, index=True, comment="校管理员 alt_auth_users.id")
    reviewed_at = Column(DateTime, nullable=True)
    review_feedback = Column(Text, nullable=True, comment="校审备注/驳回原因")

    created_at = Column(DateTime, default=utc_now)

    competition = relationship("Competition", back_populates="teams")
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")


class TeamJoinRequestStatus(str):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TeamJoinRequest(Base):
    """学生申请加入队伍，须队长（或建队指导老师）审核。"""

    __tablename__ = "team_join_requests"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    status = Column(String(20), default=TeamJoinRequestStatus.PENDING, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_id = Column(Integer, nullable=True, index=True)

    team = relationship("Team", backref="join_requests")


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_member"),
    )

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    # alt_auth_users.id
    user_id = Column(Integer, nullable=False, index=True)

    is_captain = Column(Boolean, default=False, nullable=False)
    joined_at = Column(DateTime, default=utc_now)

    team = relationship("Team", back_populates="members")


class SubmissionStatus(str):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("competition_id", "team_id", "student_id", name="uq_submission_competition_target"),
    )

    id = Column(Integer, primary_key=True, index=True)

    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False)

    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    # 个人赛道归属：alt_auth_users.id
    student_id = Column(Integer, nullable=False, index=True)
    # 实际点击提交的主体：alt_auth_users.id
    submitter_id = Column(Integer, nullable=False, index=True)

    title = Column(String(200), nullable=False)
    description = Column(Text)

    file_id = Column(Integer, ForeignKey("files.id"), nullable=True)
    content_text = Column(Text, nullable=True)

    division = Column(
        String(20),
        default=CompetitionDivision.DEFAULT,
        nullable=False,
        comment="作品所属学历组别，与报名 division 一致",
    )

    status = Column(String(30), default=SubmissionStatus.SUBMITTED, nullable=False)
    submitted_at = Column(DateTime, default=utc_now)

    competition = relationship("Competition")
    team = relationship("Team")
    review = relationship("Review", back_populates="submission", uselist=False, cascade="all, delete-orphan")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, unique=True)
    # 评委：alt_auth_users.id
    reviewer_id = Column(Integer, nullable=False, index=True)

    status = Column(String(30), default=SubmissionStatus.UNDER_REVIEW, nullable=False)
    score = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    submission = relationship("Submission", back_populates="review")


class CompetitionExpertAssignment(Base):
    """
    管理员为某竞赛指派的评委专家（仅被指派的 expert_verified 专家可批改该赛作品）。
    """

    __tablename__ = "competition_expert_assignments"
    __table_args__ = (UniqueConstraint("competition_id", "expert_id", name="uq_competition_expert"),)

    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False, index=True)
    expert_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)
