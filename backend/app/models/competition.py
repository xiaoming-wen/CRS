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


class CompetitionWorkTrack(str):
    """报名赛道（作品类型）。"""
    WORKS = "works"
    SOFTWARE = "software"
    HARDWARE = "hardware"


class CompetitionStage(str):
    """赛程阶段：单阶段 / 初赛 / 决赛。"""
    SINGLE = "single"
    PRELIMINARY = "preliminary"
    FINAL = "final"


class Competition(Base):
    __tablename__ = "competitions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    rules_text = Column(Text)

    # 参赛对象、联系人、地点与环境（详情 briefing 展示）
    target_audience = Column(Text, nullable=True, comment="参赛对象")
    contact_name = Column(String(100), nullable=True, comment="竞赛联系人")
    contact_phone = Column(String(100), nullable=True, comment="联系方式")
    location = Column(String(500), nullable=True, comment="竞赛地点")
    environment = Column(Text, nullable=True, comment="竞赛环境")

    status = Column(String(30), default=CompetitionStatus.DRAFT, nullable=False)
    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)

    allow_individual = Column(Boolean, default=False, nullable=False)
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

    # 初赛/决赛关联：同系列共享 series_id；单阶段 stage=single
    series_id = Column(Integer, nullable=True, index=True, comment="初赛/决赛同系列 ID")
    stage = Column(
        String(20),
        default=CompetitionStage.SINGLE,
        nullable=False,
        comment="single | preliminary | final",
    )
    paired_competition_id = Column(
        Integer,
        nullable=True,
        index=True,
        comment="对端竞赛 id（初赛↔决赛）",
    )

    qr_code_path = Column(String(512), nullable=True)
    qr_code_path_undergraduate = Column(String(512), nullable=True)
    qr_code_path_vocational = Column(String(512), nullable=True)

    # 竞赛 Logo（创建/修改时 multipart 上传）
    logo_path = Column(String(512), nullable=True)

    # 竞赛试卷（上传即发布；dual 时本科/高职各一份；兼容旧字段）
    exam_paper_path = Column(String(512), nullable=True)
    exam_paper_filename = Column(String(255), nullable=True)
    exam_paper_path_undergraduate = Column(String(512), nullable=True)
    exam_paper_filename_undergraduate = Column(String(255), nullable=True)
    exam_paper_path_vocational = Column(String(512), nullable=True)
    exam_paper_filename_vocational = Column(String(255), nullable=True)
    # JSON：按组别+赛道存试卷 {division:{works|software|hardware:{path,filename}}}
    exam_papers_by_track = Column(Text, nullable=True)
    # JSON：分题提交配置（题数、题名、每题/总分 min-max）
    submission_question_config = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    teams = relationship("Team", back_populates="competition")
    enrollments = relationship("CompetitionEnrollment", back_populates="competition")

    @property
    def logo_image_url(self):
        if self.logo_path and str(self.logo_path).strip():
            return f"/api/v1/competitions/{self.id}/logo"
        return None


class CompetitionPromotion(Base):
    """初赛队伍/个人晋级到决赛的手动晋级记录。"""

    __tablename__ = "competition_promotions"
    __table_args__ = (
        UniqueConstraint(
            "to_competition_id",
            "source_team_id",
            name="uq_promo_final_source_team",
        ),
        UniqueConstraint(
            "to_competition_id",
            "source_student_id",
            name="uq_promo_final_source_student",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    from_competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False, index=True)
    to_competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False, index=True)
    # 初赛来源（二选一）
    source_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)
    source_student_id = Column(Integer, nullable=True, index=True, comment="初赛个人赛道学生 alt id")
    # 晋级后在决赛侧自动创建的队伍（组队晋级时）
    final_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)
    promoted_by = Column(Integer, nullable=False, index=True, comment="操作人 alt_auth_users.id")
    created_at = Column(DateTime, default=utc_now)


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
    每人每赛每个作品赛道（``work_track``：作品/软件/硬件）至多一条记录；最多可同时报满三条赛道。
    """

    __tablename__ = "competition_enrollments"
    __table_args__ = (
        UniqueConstraint(
            "competition_id",
            "student_id",
            "work_track",
            name="uq_competition_student_work_track",
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
    work_track = Column(
        String(20),
        nullable=True,
        comment="赛道：works / software / hardware",
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
    work_track = Column(
        String(20),
        nullable=True,
        comment="赛道：works / software / hardware",
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


class TeamInviteStatus(str):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class TeamInvite(Base):
    """队长/指导老师发出的入队邀请，须被邀请学生同意后才正式入队。"""

    __tablename__ = "team_invites"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    competition_id = Column(Integer, nullable=False, index=True)
    invitee_id = Column(Integer, nullable=False, index=True, comment="被邀请学生 alt_auth_users.id")
    inviter_id = Column(Integer, nullable=False, index=True, comment="邀请人 alt_auth_users.id")
    as_captain = Column(Boolean, default=False, nullable=False, comment="同意后是否以队长身份入队")
    status = Column(String(20), default=TeamInviteStatus.PENDING, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)
    responded_at = Column(DateTime, nullable=True)

    team = relationship("Team", backref="invites")


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


# 每场竞赛最多 5 道题（实际题数见 submission_question_config）
COMPETITION_QUESTION_COUNT = 5


class CompetitionQuestionAnswerStatus(str):
    DRAFT = "draft"  # 已选文件，尚未点「上传作品」
    SUBMITTED = "submitted"  # 已正式提交，管理员/专家可见


class CompetitionQuestionAnswer(Base):
    """
    队伍某道题的答案文件（每队每题至多一条，重新上传覆盖）。
    submitter_id 为实际上传的队员 alt_auth_users.id。
    status=draft 时仅本队可见；点「上传作品」后变为 submitted，管理员/专家列表才显示。
    """

    __tablename__ = "competition_question_answers"
    __table_args__ = (
        UniqueConstraint(
            "competition_id",
            "team_id",
            "question_no",
            name="uq_competition_team_question_answer",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    question_no = Column(Integer, nullable=False, comment="题号 1~5")
    submitter_id = Column(Integer, nullable=False, index=True, comment="上传者 alt_auth_users.id")
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    status = Column(
        String(20),
        default=CompetitionQuestionAnswerStatus.DRAFT,
        nullable=False,
        index=True,
        comment="draft | submitted",
    )
    uploaded_at = Column(DateTime, default=utc_now, nullable=False)
    submitted_at = Column(DateTime, nullable=True, comment="正式提交时间")

    competition = relationship("Competition")
    team = relationship("Team")


class CompetitionTeamQuestionGrade(Base):
    """专家对某队 5 题分别打分；total_score 为五题之和。每竞赛每队一条。"""

    __tablename__ = "competition_team_question_grades"
    __table_args__ = (
        UniqueConstraint(
            "competition_id",
            "team_id",
            name="uq_competition_team_question_grade",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    reviewer_id = Column(Integer, nullable=False, index=True, comment="评委 alt_auth_users.id")
    score_q1 = Column(Float, nullable=False)
    score_q2 = Column(Float, nullable=False)
    score_q3 = Column(Float, nullable=False)
    score_q4 = Column(Float, nullable=False)
    score_q5 = Column(Float, nullable=False)
    total_score = Column(Float, nullable=False, comment="五题分数之和")
    feedback = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    competition = relationship("Competition")
    team = relationship("Team")


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
    管理员为某竞赛指派的评委专家（竞赛级入口；可评队伍以 CompetitionExpertTeamAssignment 为准）。
    """

    __tablename__ = "competition_expert_assignments"
    __table_args__ = (UniqueConstraint("competition_id", "expert_id", name="uq_competition_expert"),)

    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False, index=True)
    expert_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)


class CompetitionExpertTeamAssignment(Base):
    """
    专家在某竞赛下可评阅的队伍（须同时存在竞赛级 CompetitionExpertAssignment）。
    无队伍指派时专家不可评任何队。
    """

    __tablename__ = "competition_expert_team_assignments"
    __table_args__ = (
        UniqueConstraint(
            "competition_id",
            "expert_id",
            "team_id",
            name="uq_competition_expert_team",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False, index=True)
    expert_id = Column(Integer, nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)
