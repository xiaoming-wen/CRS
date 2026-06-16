import logging
import mimetypes
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request, Query
from fastapi.responses import FileResponse, StreamingResponse
from openpyxl import Workbook
from starlette.datastructures import UploadFile as StarletteUploadFile
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Tuple, Union
from app.datetime_utils import utc_now, ensure_utc
import os
import uuid

from app.database import get_db
from app.alt_auth.context import get_current_alt_identity
from app.alt_auth.database import get_alt_auth_db
from app.alt_auth.models import AltAuthUserRecord
from app.permissions import Permission, require_permission
from app.models.user import File as FileModel
from app.models.competition import (
    Competition,
    CompetitionEnrollment,
    CompetitionEnrollmentScope,
    CompetitionEnrollmentStatus,
    CompetitionExpertAssignment,
    Team,
    TeamMember,
    TeamJoinRequest,
    TeamJoinRequestStatus,
    TeamStatus,
    Submission,
    SubmissionStatus,
    Review,
)
from app.schemas import (
    CompetitionCreate,
    CompetitionUpdate,
    CompetitionResponse,
    CompetitionEnrollmentCreate,
    CompetitionEnrollmentResponse,
    MyEnrollmentResponse,
    TeamCreate,
    TeamResponse,
    TeamPatch,
    TeamInviteMember,
    TeamDetailResponse,
    TeamMemberResponse,
    TeamJoinRequestResponse,
    TeamJoinRequestReview,
    IndividualParticipantItem,
    TeamParticipantDetailResponse,
    TeamMemberWithUserResponse,
    TeamTransferCaptain,
    AltUserAdminPatch,
    AltUserAdminUpdateResult,
    SchoolAdminTeamReviewListResponse,
    SchoolAdminTeamReviewItem,
    SchoolAdminTeamMemberItem,
    TeamSchoolReviewRequest,
    TeamSchoolReviewResult,
    SchoolAdminApplicationStatus,
    SchoolAdminApplicationMeResponse,
    SchoolAdminApplicationListResponse,
    SchoolAdminApplicationListItem,
    SchoolAdminApplicationReviewRequest,
    SchoolAdminApplicationReviewResult,
    CompetitionExpertsListResponse,
    CompetitionExpertListItem,
    SubmissionCreate,
    SubmissionCreateWrapped,
    SubmissionResponse,
    ReviewGrade,
    ReviewResponse,
    CompetitionScoreSummaryResponse,
    CompetitionScoreRankingItem,
    CompetitionScoreRankingResponse,
    MyCompetitionScoresResponse,
    SubmissionForStudentScoreResponse,
)

router = APIRouter(prefix="/competitions", tags=["Competition Management"])
logger = logging.getLogger(__name__)

SUBMISSION_UPLOAD_DIR = "competition_submissions"
os.makedirs(SUBMISSION_UPLOAD_DIR, exist_ok=True)

COMPETITION_QR_DIR = "competition_qr_codes"
os.makedirs(COMPETITION_QR_DIR, exist_ok=True)
MAX_QR_IMAGE_BYTES = 5 * 1024 * 1024
_ALLOWED_QR_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_ALLOWED_QR_MIME = {"image/png", "image/jpeg", "image/gif", "image/webp"}

SCHOOL_ADMIN_PHOTO_DIR = "school_admin_applications"
os.makedirs(SCHOOL_ADMIN_PHOTO_DIR, exist_ok=True)
MAX_SCHOOL_ADMIN_PHOTO_BYTES = 5 * 1024 * 1024


def _alt_users_by_id(adb: Session, ids: set[int]) -> dict[int, AltAuthUserRecord]:
    if not ids:
        return {}
    rows = adb.query(AltAuthUserRecord).filter(AltAuthUserRecord.id.in_(list(ids))).all()
    return {r.id: r for r in rows}


def _effective_alt_role(role: Optional[str]) -> str:
    return (role or "student").strip()


def _require_super_admin_identity(identity: AltAuthUserRecord) -> None:
    if _effective_alt_role(identity.role) != "super_admin":
        raise HTTPException(status_code=403, detail="Only super_admin can perform this operation")


def _expert_gate_ok(identity: AltAuthUserRecord) -> bool:
    """专家且已由管理员核验。"""
    return _effective_alt_role(identity.role) == "expert" and bool(getattr(identity, "expert_verified", False))


def _is_assigned_competition_expert(db: Session, competition_id: int, expert_user_id: int) -> bool:
    return (
        db.query(CompetitionExpertAssignment)
        .filter(
            CompetitionExpertAssignment.competition_id == competition_id,
            CompetitionExpertAssignment.expert_id == expert_user_id,
        )
        .first()
        is not None
    )


def _can_view_all_competition_submissions(db: Session, competition_id: int, identity: AltAuthUserRecord) -> bool:
    if _effective_alt_role(identity.role) == "super_admin":
        return True
    if _expert_gate_ok(identity) and _is_assigned_competition_expert(db, competition_id, identity.id):
        return True
    return False


def _can_view_competition_score_insights(db: Session, competition_id: int, identity: AltAuthUserRecord) -> bool:
    """管理员或已指派专家对竞赛查看评分汇总 / 排行榜。"""
    return _can_view_all_competition_submissions(db, competition_id, identity)


def _can_view_full_participant_rosters(db: Session, competition_id: int, identity: AltAuthUserRecord) -> bool:
    """参赛者花名册导出接口：与个人/组队 participant 详情一致权限。"""
    return _can_view_all_competition_submissions(db, competition_id, identity)


def _ensure_alt_principal_is_student(adb: Session, user_id: int) -> AltAuthUserRecord:
    row = adb.query(AltAuthUserRecord).filter(AltAuthUserRecord.id == user_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    if _effective_alt_role(row.role) != "student":
        raise HTTPException(status_code=400, detail="Target must be a student account")
    return row


def _ensure_alt_principal_is_advisor(adb: Session, user_id: int) -> AltAuthUserRecord:
    row = adb.query(AltAuthUserRecord).filter(AltAuthUserRecord.id == user_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="指导老师用户不存在")
    if _effective_alt_role(row.role) not in {"advisor", "teacher"}:
        raise HTTPException(status_code=400, detail="指定用户须为指导老师账号")
    return row


def _match_advisors_by_name(adb: Session, name: str) -> list[AltAuthUserRecord]:
    key = (name or "").strip()
    if not key:
        return []
    key_lower = key.lower()
    matches: list[AltAuthUserRecord] = []
    for row in adb.query(AltAuthUserRecord).filter(AltAuthUserRecord.is_active.is_(True)).all():
        if _effective_alt_role(row.role) not in {"advisor", "teacher"}:
            continue
        full_name = (row.full_name or "").strip()
        username = (row.username or "").strip()
        if full_name.lower() == key_lower or username.lower() == key_lower:
            matches.append(row)
    return matches


def _resolve_advisor_by_name(adb: Session, name: str) -> AltAuthUserRecord:
    key = (name or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="指导老师姓名不能为空")
    matches = _match_advisors_by_name(adb, key)
    if not matches:
        raise HTTPException(status_code=404, detail="未找到该指导老师，请确认姓名是否正确")
    if len(matches) > 1:
        raise HTTPException(status_code=400, detail="存在多位同名指导老师，请填写更准确的姓名")
    return matches[0]


def _try_resolve_advisor_by_name(adb: Session, name: str) -> Optional[AltAuthUserRecord]:
    key = (name or "").strip()
    if not key:
        return None
    matches = _match_advisors_by_name(adb, key)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise HTTPException(status_code=400, detail="存在多位同名指导老师，请填写更准确的姓名")
    return None


def _team_advisor_display_name(
    team: Team,
    users_by_id: Optional[dict[int, AltAuthUserRecord]] = None,
) -> Optional[str]:
    stored = getattr(team, "advisor_name", None)
    if stored is not None and str(stored).strip():
        return str(stored).strip()
    advisor_id = team.created_by_advisor_id
    if advisor_id and users_by_id:
        adv = users_by_id.get(advisor_id)
        if adv:
            return _display_user_name(adv, advisor_id)
    return None


def _team_advisor_managed(team: Team, identity_id: int) -> bool:
    return team.created_by_advisor_id is not None and int(team.created_by_advisor_id) == int(identity_id)


def _can_manage_team_composition(team: Team, identity: AltAuthUserRecord) -> bool:
    """队长，或指导老师建队者可调整队员。"""
    if team.captain_id == identity.id:
        return True
    return _effective_alt_role(identity.role) in {"advisor", "teacher"} and _team_advisor_managed(team, identity.id)


def _normalize_school_name(raw: Optional[str]) -> str:
    return (raw or "").strip()


def _school_admin_application_status(user: AltAuthUserRecord) -> SchoolAdminApplicationStatus:
    raw = (getattr(user, "school_admin_application_status", None) or "").strip().lower()
    if raw == SchoolAdminApplicationStatus.PENDING.value:
        return SchoolAdminApplicationStatus.PENDING
    if raw == SchoolAdminApplicationStatus.APPROVED.value:
        return SchoolAdminApplicationStatus.APPROVED
    if raw == SchoolAdminApplicationStatus.REJECTED.value:
        return SchoolAdminApplicationStatus.REJECTED
    return SchoolAdminApplicationStatus.NOT_SUBMITTED


def _school_admin_can_review_teams(user: AltAuthUserRecord) -> bool:
    return (
        _effective_alt_role(user.role) == "school_admin"
        and bool(getattr(user, "school_admin_verified", False))
    )


def _require_school_admin_role(identity: AltAuthUserRecord) -> None:
    if _effective_alt_role(identity.role) != "school_admin":
        raise HTTPException(status_code=403, detail="Only school_admin can perform this operation")
    if not _normalize_school_name(getattr(identity, "school", None)):
        raise HTTPException(status_code=400, detail="School admin account must have school configured")


def _require_school_admin_identity(identity: AltAuthUserRecord) -> None:
    _require_school_admin_role(identity)
    require_permission(identity.role, Permission.REVIEW_TEAMS)
    if not _school_admin_can_review_teams(identity):
        raise HTTPException(
            status_code=403,
            detail="School admin account pending verification; submit application with photo and wait for super_admin approval",
        )


def _resolve_school_admin_photo_fs_path(stored: str) -> str:
    if not stored or not stored.strip():
        raise HTTPException(status_code=404, detail="Photo not found")
    base_dir = os.path.abspath(SCHOOL_ADMIN_PHOTO_DIR)
    if os.path.isabs(stored):
        full = os.path.abspath(stored)
    else:
        full = os.path.abspath(os.path.normpath(os.path.join(os.getcwd(), stored)))
    if not full.startswith(base_dir + os.sep) and full != base_dir:
        raise HTTPException(status_code=404, detail="Photo not found")
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="Photo missing on server")
    return full


async def _save_school_admin_photo(upload: StarletteUploadFile, user_id: int) -> str:
    if not upload.filename or not str(upload.filename).strip():
        raise HTTPException(status_code=400, detail="photo requires a filename")
    ext = os.path.splitext(upload.filename)[1].lower()
    if ext not in _ALLOWED_QR_EXT:
        raise HTTPException(status_code=400, detail="Unsupported photo format")
    mime = (upload.content_type or "").split(";")[0].strip().lower()
    if mime and mime not in _ALLOWED_QR_MIME:
        raise HTTPException(status_code=400, detail="Unsupported photo mime type")
    content = await upload.read()
    if len(content) > MAX_SCHOOL_ADMIN_PHOTO_BYTES:
        raise HTTPException(status_code=400, detail="Photo too large (max 5MB)")
    if not content:
        raise HTTPException(status_code=400, detail="Empty photo file")
    filename = f"user_{user_id}_{uuid.uuid4().hex}{ext}"
    rel_path = f"{SCHOOL_ADMIN_PHOTO_DIR}/{filename}"
    fs_path = os.path.abspath(os.path.join(os.getcwd(), rel_path.replace("/", os.sep)))
    base_dir = os.path.abspath(SCHOOL_ADMIN_PHOTO_DIR)
    if not fs_path.startswith(base_dir + os.sep):
        raise HTTPException(status_code=400, detail="Invalid photo path")
    with open(fs_path, "wb") as f:
        f.write(content)
    return rel_path.replace("\\", "/")


def _delete_school_admin_photo(stored: Optional[str]) -> None:
    if not stored:
        return
    try:
        fs = _resolve_school_admin_photo_fs_path(stored)
        if os.path.isfile(fs):
            os.remove(fs)
    except HTTPException:
        pass
    except Exception as e:
        logger.warning("Failed to remove school admin photo %s: %s", stored, e)


def _team_composition_open_statuses() -> Tuple[str, ...]:
    """允许调整队员/队名的队伍状态（含待校审）。"""
    return (TeamStatus.PENDING_SCHOOL_REVIEW, TeamStatus.ACTIVE)


def _add_student_to_team(
    db: Session,
    competition: Competition,
    team: Team,
    student_id: int,
    *,
    is_captain: bool = False,
) -> TeamMember:
    member = TeamMember(team_id=team.id, user_id=student_id, is_captain=is_captain)
    db.add(member)
    row_any = _get_enrollment_by_scope(
        db, competition.id, student_id, CompetitionEnrollmentScope.TEAM
    )
    if row_any and row_any.status == CompetitionEnrollmentStatus.WITHDRAWN:
        row_any.team_id = team.id
        row_any.enrollment_scope = CompetitionEnrollmentScope.TEAM
        row_any.is_captain = is_captain
        row_any.status = CompetitionEnrollmentStatus.ENROLLED
    else:
        db.add(
            CompetitionEnrollment(
                competition_id=competition.id,
                student_id=student_id,
                team_id=team.id,
                enrollment_scope=CompetitionEnrollmentScope.TEAM,
                is_captain=is_captain,
                status=CompetitionEnrollmentStatus.ENROLLED,
            )
        )
    return member


def _build_team_join_request_response(
    req: TeamJoinRequest,
    users_by_id: dict[int, AltAuthUserRecord],
) -> TeamJoinRequestResponse:
    u = users_by_id.get(req.user_id)
    return TeamJoinRequestResponse(
        id=req.id,
        team_id=req.team_id,
        user_id=req.user_id,
        username=(u.username or "") if u else "",
        full_name=u.full_name if u else None,
        status=req.status,
        created_at=req.created_at,
        reviewed_at=req.reviewed_at,
        reviewed_by_id=req.reviewed_by_id,
    )


def _resolve_team_school(adb: Session, captain_id: int) -> str:
    captain = adb.query(AltAuthUserRecord).filter(AltAuthUserRecord.id == captain_id).first()
    if captain is None:
        raise HTTPException(status_code=400, detail="Captain account not found")
    school = _normalize_school_name(getattr(captain, "school", None))
    if not school:
        raise HTTPException(status_code=400, detail="Captain must have school configured")
    return school


def _team_matches_school(team: Team, school: str) -> bool:
    team_school = _normalize_school_name(getattr(team, "school", None))
    return team_school.casefold() == _normalize_school_name(school).casefold()


def _build_school_admin_team_item(
    team: Team,
    competition: Competition,
    users_by_id: dict[int, AltAuthUserRecord],
) -> SchoolAdminTeamReviewItem:
    advisor_id = team.created_by_advisor_id
    advisor_name = _team_advisor_display_name(team, users_by_id)

    captain = users_by_id.get(team.captain_id)
    captain_name = (captain.full_name or captain.username) if captain else None

    members_out: List[SchoolAdminTeamMemberItem] = []
    for m in sorted(team.members, key=lambda x: (not x.is_captain, x.joined_at or utc_now(), x.id)):
        u = users_by_id.get(m.user_id)
        members_out.append(
            SchoolAdminTeamMemberItem(
                user_id=m.user_id,
                username=u.username if u else "",
                full_name=u.full_name if u else None,
                is_captain=m.is_captain,
            )
        )

    return SchoolAdminTeamReviewItem(
        team_id=team.id,
        competition_id=competition.id,
        competition_name=competition.name,
        competition_start_at=competition.start_at,
        competition_end_at=competition.end_at,
        school=getattr(team, "school", None),
        advisor_name=advisor_name,
        advisor_id=advisor_id,
        team_name=team.name,
        captain_name=captain_name,
        captain_id=team.captain_id,
        members=members_out,
        status=TeamStatus(team.status),
        review_feedback=getattr(team, "review_feedback", None),
        reviewed_at=getattr(team, "reviewed_at", None),
        created_at=team.created_at,
    )


def _strip_team_name(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


def _form_optional_str(val) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s or None


def _form_bool(val, default: bool) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s == "":
        return default
    return s in ("1", "true", "yes", "on")


def _competition_create_from_form(form) -> CompetitionCreate:
    name_raw = form.get("name")
    if name_raw is None or not str(name_raw).strip():
        raise HTTPException(status_code=400, detail="name is required")
    payload = {
        "name": str(name_raw).strip(),
        "description": _form_optional_str(form.get("description")),
        "rules_text": _form_optional_str(form.get("rules_text")),
        "start_at": _form_optional_str(form.get("start_at")),
        "end_at": _form_optional_str(form.get("end_at")),
        "allow_individual": _form_bool(form.get("allow_individual"), True),
        "allow_team": _form_bool(form.get("allow_team"), True),
    }
    try:
        return CompetitionCreate.model_validate(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid form payload: {e}") from e


def _competition_update_from_form(form) -> CompetitionUpdate:
    """multipart 修改竞赛：仅解析表单中出现的字段（与 JSON exclude_unset 语义一致）。"""
    payload = {}
    if "name" in form:
        name_raw = form.get("name")
        if name_raw is None or not str(name_raw).strip():
            raise HTTPException(status_code=400, detail="name cannot be empty")
        payload["name"] = str(name_raw).strip()
    for key in ("description", "rules_text", "start_at", "end_at"):
        if key in form:
            payload[key] = _form_optional_str(form.get(key))
    if "allow_individual" in form:
        payload["allow_individual"] = _form_bool(form.get("allow_individual"), True)
    if "allow_team" in form:
        payload["allow_team"] = _form_bool(form.get("allow_team"), True)
    try:
        return CompetitionUpdate.model_validate(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid form payload: {e}") from e


def _delete_stored_qr_file(stored: Optional[str]) -> None:
    if not stored:
        return
    try:
        fs = _resolve_qr_fs_path(stored)
        if os.path.isfile(fs):
            os.remove(fs)
    except Exception as e:
        logger.warning("Failed to remove competition QR file %s: %s", stored, e)


def _normalize_stored_qr_path(rel_path: str) -> str:
    return rel_path.replace("\\", "/")


def _resolve_qr_fs_path(stored: str) -> str:
    """将库中记录的相对路径解析为绝对路径，并限制在 competition_qr_codes 目录内。"""
    if not stored or not stored.strip():
        raise HTTPException(status_code=404, detail="QR code not found")
    base_dir = os.path.abspath(COMPETITION_QR_DIR)
    if os.path.isabs(stored):
        full = os.path.abspath(stored)
    else:
        full = os.path.abspath(os.path.normpath(os.path.join(os.getcwd(), stored)))
    if not full.startswith(base_dir + os.sep) and full != base_dir:
        raise HTTPException(status_code=404, detail="QR code not found")
    return full


async def _save_qr_code_upload(upload: StarletteUploadFile, competition_id: int) -> str:
    if not upload.filename or not str(upload.filename).strip():
        raise HTTPException(status_code=400, detail="qr_code_image requires a filename")
    ext = os.path.splitext(upload.filename)[1].lower()
    if ext not in _ALLOWED_QR_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"qr_code_image: only image extensions {sorted(_ALLOWED_QR_EXT)} allowed",
        )
    ct = (upload.content_type or "").split(";")[0].strip().lower()
    if ct and ct not in _ALLOWED_QR_MIME:
        raise HTTPException(status_code=400, detail="qr_code_image: invalid image content type")

    body = await upload.read()
    if len(body) > MAX_QR_IMAGE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"qr_code_image too large (max {MAX_QR_IMAGE_BYTES // (1024 * 1024)} MiB)",
        )

    fname = f"comp_{competition_id}_{uuid.uuid4().hex}{ext}"
    rel = _normalize_stored_qr_path(os.path.join(COMPETITION_QR_DIR, fname))
    abs_path = _resolve_qr_fs_path(rel)
    with open(abs_path, "wb") as f:
        f.write(body)
    return rel


def _get_competition(db: Session, competition_id: int) -> Competition:
    competition = db.query(Competition).filter(Competition.id == competition_id).first()
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    return competition


def _is_enrollment_closed(competition: Competition) -> bool:
    """
    「停止报名」条件（与业务上“锁定竞赛”含义一致）：
    1) 状态为 closed（管理员手动关闭报名）
    2) 到达/超过 end_at（自动停止报名）
    """
    if competition.status == "closed":
        return True
    if competition.end_at is None:
        return False
    return utc_now() >= ensure_utc(competition.end_at)


def _ensure_enrollment_open(competition: Competition) -> None:
    """禁止在已停止报名后：新报名 / 新建队伍 / 加入队伍。"""
    if _is_enrollment_closed(competition):
        raise HTTPException(
            status_code=400,
            detail="Competition enrollment is closed (status closed or past end date).",
        )


def _ensure_competition_allows_submissions(competition: Competition) -> None:
    """
    作品提交：已发布（published）或已锁定报名（closed）均允许已参赛用户继续提交；
    草稿（draft）不允许。
    """
    if competition.status not in ("published", "closed"):
        raise HTTPException(
            status_code=400,
            detail="Competition is not accepting submissions (must be published or closed)",
        )


def _enrollment_scope_for_team(team_id: Optional[int]) -> str:
    return (
        CompetitionEnrollmentScope.TEAM
        if team_id is not None
        else CompetitionEnrollmentScope.INDIVIDUAL
    )


def _get_enrollment_by_scope(
    db: Session,
    competition_id: int,
    student_id: int,
    scope: str,
) -> Optional[CompetitionEnrollment]:
    return (
        db.query(CompetitionEnrollment)
        .filter(
            CompetitionEnrollment.competition_id == competition_id,
            CompetitionEnrollment.student_id == student_id,
            CompetitionEnrollment.enrollment_scope == scope,
        )
        .first()
    )


def _has_active_enrollment_in_scope(
    db: Session, competition_id: int, student_id: int, scope: str
) -> bool:
    row = _get_enrollment_by_scope(db, competition_id, student_id, scope)
    return row is not None and row.status == CompetitionEnrollmentStatus.ENROLLED


def _ensure_active_individual_enrollment(db: Session, competition_id: int, user_id: int) -> None:
    """个人赛道提交：必须存在「有效个人报名」（individual 赛道、enrolled）。"""
    if not _has_active_enrollment_in_scope(
        db, competition_id, user_id, CompetitionEnrollmentScope.INDIVIDUAL
    ):
        raise HTTPException(
            status_code=403,
            detail="Not actively enrolled as individual participant in this competition",
        )


def _individual_sequence_no(db: Session, competition_id: int, enrollment: CompetitionEnrollment) -> int:
    """本竞赛个人赛道内序号（从 1 起，按报名时间、id 稳定排序）。"""
    n = (
        db.query(func.count(CompetitionEnrollment.id))
        .filter(
            CompetitionEnrollment.competition_id == competition_id,
            CompetitionEnrollment.enrollment_scope == CompetitionEnrollmentScope.INDIVIDUAL,
            CompetitionEnrollment.status == CompetitionEnrollmentStatus.ENROLLED,
            or_(
                CompetitionEnrollment.created_at < enrollment.created_at,
                and_(
                    CompetitionEnrollment.created_at == enrollment.created_at,
                    CompetitionEnrollment.id <= enrollment.id,
                ),
            ),
        )
        .scalar()
    )
    return int(n or 0)


def _team_sequence_no(db: Session, competition_id: int, team: Team) -> int:
    """本竞赛组队赛道内队伍序号（从 1 起，按队伍创建时间、队伍 id 排序）。"""
    n = (
        db.query(func.count(Team.id))
        .filter(
            Team.competition_id == competition_id,
            Team.status == TeamStatus.ACTIVE,
            or_(
                Team.created_at < team.created_at,
                and_(Team.created_at == team.created_at, Team.id <= team.id),
            ),
        )
        .scalar()
    )
    return int(n or 0)


def _ensure_submission_access(
    db: Session, submission: Submission, identity: AltAuthUserRecord
) -> None:
    """
    作品访问边界：
    - super_admin：可访问竞赛内全部
    - 已核验且被指派的 expert：仅可访问对应竞赛的全部作品（与评分语义一致）
    - student：仅可访问本人个人作品，或其所在队伍的提交作品
    """
    r = _effective_alt_role(identity.role)
    cid = submission.competition_id

    if r == "super_admin":
        return

    if r == "expert" and _can_view_all_competition_submissions(db, cid, identity):
        return

    if r != "student":
        raise HTTPException(status_code=403, detail="Access denied")

    if submission.team_id is None:
        if submission.student_id != identity.id:
            raise HTTPException(status_code=403, detail="Access denied")
        return

    member = db.query(TeamMember).filter(
        TeamMember.team_id == submission.team_id,
        TeamMember.user_id == identity.id,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")


def _display_user_name(u: Optional[AltAuthUserRecord], fallback_id: Optional[int] = None) -> str:
    if not u:
        return str(fallback_id) if fallback_id is not None else "-"
    if u.full_name and str(u.full_name).strip():
        return str(u.full_name).strip()
    if u.username and str(u.username).strip():
        return str(u.username).strip()
    return str(fallback_id) if fallback_id is not None else str(u.id)


def _build_team_member_user_responses(
    members: list[TeamMember],
    users_by_id: dict[int, AltAuthUserRecord],
) -> list[TeamMemberWithUserResponse]:
    out: list[TeamMemberWithUserResponse] = []
    for m in sorted(members, key=lambda x: (not x.is_captain, x.joined_at or utc_now(), x.id)):
        u = users_by_id.get(m.user_id)
        out.append(
            TeamMemberWithUserResponse(
                id=m.id,
                team_id=m.team_id,
                user_id=m.user_id,
                username=u.username if u else "",
                full_name=u.full_name if u else None,
                is_captain=m.is_captain,
                joined_at=m.joined_at,
            )
        )
    return out


def _team_detail_response(adb: Session, team: Team) -> TeamDetailResponse:
    member_uids = {m.user_id for m in team.members}
    advisor_ids = {team.created_by_advisor_id} if team.created_by_advisor_id is not None else set()
    users_by_id = _alt_users_by_id(adb, member_uids | advisor_ids | {team.captain_id})
    members_out = _build_team_member_user_responses(team.members, users_by_id)
    display_name = _team_advisor_display_name(team, users_by_id)
    advisor_name = display_name if display_name else getattr(team, "advisor_name", None)
    return TeamDetailResponse(
        id=team.id,
        competition_id=team.competition_id,
        name=team.name,
        captain_id=team.captain_id,
        created_by_advisor_id=team.created_by_advisor_id,
        advisor_name=advisor_name,
        status=TeamStatus(team.status),
        created_at=team.created_at,
        members=members_out,
    )


def _team_detail_responses(adb: Session, teams: list[Team]) -> list[TeamDetailResponse]:
    return [_team_detail_response(adb, team) for team in teams]


@router.get("/{competition_id}/teams/export")
async def export_team_roster_excel(
    competition_id: int,
    db: Session = Depends(get_db),
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """
    管理员导出某竞赛队伍信息 Excel。
    字段：序号、指导老师（可多名）、队长、队员（可多名）、队伍名、参加的竞赛。
    """
    require_permission(identity.role, Permission.MANAGE_COMPETITIONS)
    competition = _get_competition(db, competition_id)

    teams = (
        db.query(Team)
        .options(joinedload(Team.members))
        .filter(Team.competition_id == competition_id, Team.status == TeamStatus.ACTIVE)
        .order_by(Team.created_at.asc(), Team.id.asc())
        .all()
    )

    user_ids = {t.captain_id for t in teams} | {m.user_id for t in teams for m in t.members}
    advisor_ids = {t.created_by_advisor_id for t in teams if t.created_by_advisor_id is not None}
    users_by_id = _alt_users_by_id(adb, user_ids | advisor_ids)

    wb = Workbook()
    ws = wb.active
    ws.title = "队伍信息"
    ws.append(["序号", "指导老师", "队长", "队员", "队伍名", "参加的竞赛"])

    for idx, team in enumerate(teams, start=1):
        display_advisor = _team_advisor_display_name(team, users_by_id)
        advisors_text = display_advisor or "-"

        captain_user = users_by_id.get(team.captain_id)
        captain_text = _display_user_name(captain_user, team.captain_id)

        member_names: list[str] = []
        for member in sorted(team.members, key=lambda x: (0 if x.is_captain else 1, x.id)):
            member_user = users_by_id.get(member.user_id)
            member_names.append(_display_user_name(member_user, member.user_id))
        members_text = "、".join(member_names) if member_names else "-"

        ws.append(
            [
                idx,
                advisors_text,
                captain_text,
                members_text,
                team.name or f"队伍{team.id}",
                competition.name,
            ]
        )

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    filename = f"competition_{competition_id}_teams.xlsx"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post("/", response_model=CompetitionResponse, status_code=status.HTTP_201_CREATED)
async def create_competition(
    request: Request,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """
    创建竞赛。
    - **application/json**：与原先一致，请求体为 CompetitionCreate（无文件上传）。
    - **multipart/form-data**：文本字段与 JSON 相同（`name`、`description`…），可选文件字段 **`qr_code_image`** 上传二维码图片（png/jpg/gif/webp，最大 5MiB）。
    """
    require_permission(identity.role, Permission.MANAGE_COMPETITIONS)

    ct = (request.headers.get("content-type") or "").lower()
    qr_upload = None
    if "application/json" in ct:
        try:
            body = await request.json()
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid JSON body") from e
        competition = CompetitionCreate.model_validate(body)
    elif "multipart/form-data" in ct:
        form = await request.form()
        competition = _competition_create_from_form(form)
        q = form.get("qr_code_image")
        if isinstance(q, StarletteUploadFile) and q.filename and str(q.filename).strip():
            qr_upload = q
    else:
        raise HTTPException(
            status_code=415,
            detail="Content-Type must be application/json or multipart/form-data",
        )

    comp = Competition(
        name=competition.name,
        description=competition.description,
        rules_text=competition.rules_text,
        status="draft",
        start_at=competition.start_at,
        end_at=competition.end_at,
        allow_individual=competition.allow_individual,
        allow_team=competition.allow_team,
        qr_code_path=None,
    )
    db.add(comp)
    db.flush()
    if qr_upload is not None:
        rel = await _save_qr_code_upload(qr_upload, comp.id)
        comp.qr_code_path = rel
    db.commit()
    db.refresh(comp)
    return comp


@router.get("/", response_model=List[CompetitionResponse])
async def list_competitions(
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    require_permission(identity.role, Permission.VIEW_COMPETITIONS)
    return db.query(Competition).order_by(Competition.created_at.desc()).all()


@router.get("/{competition_id}/qr-code")
async def get_competition_qr_code(
    competition_id: int,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """下载/查看创建竞赛时上传的二维码图片（需登录且具备 VIEW_COMPETITIONS）。"""
    require_permission(identity.role, Permission.VIEW_COMPETITIONS)
    competition = _get_competition(db, competition_id)
    if not competition.qr_code_path:
        raise HTTPException(status_code=404, detail="No QR code for this competition")
    fs_path = _resolve_qr_fs_path(competition.qr_code_path)
    if not os.path.isfile(fs_path):
        raise HTTPException(status_code=404, detail="QR code file missing on server")
    mime, _ = mimetypes.guess_type(fs_path)
    return FileResponse(
        path=fs_path,
        filename=os.path.basename(fs_path),
        media_type=mime or "application/octet-stream",
    )


@router.get("/enrollments/me", response_model=List[MyEnrollmentResponse])
async def my_enrollments(
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """查看当前用户报名的所有竞赛（含竞赛详情）"""
    require_permission(identity.role, Permission.VIEW_COMPETITIONS)
    enrollments = (
        db.query(CompetitionEnrollment)
        .filter(
            CompetitionEnrollment.student_id == identity.id,
            CompetitionEnrollment.status == CompetitionEnrollmentStatus.ENROLLED,
        )
        .order_by(CompetitionEnrollment.created_at.desc())
        .all()
    )
    results = []
    for e in enrollments:
        comp = db.query(Competition).filter(Competition.id == e.competition_id).first()
        data = MyEnrollmentResponse.model_validate(e)
        if comp:
            data.competition = CompetitionResponse.model_validate(comp)
        results.append(data)
    return results


@router.get("/experts", response_model=CompetitionExpertsListResponse)
async def list_all_experts(
    db: Session = Depends(get_db),
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """
    管理员获取全部第二套专家帐号（``role=expert``），含各专家已指派的竞赛 id 列表。
    指派 / 取消指派仍使用 ``POST|DELETE /{competition_id}/experts/{expert_user_id}``。
    """
    _require_super_admin_identity(identity)

    expert_rows = (
        adb.query(AltAuthUserRecord)
        .filter(AltAuthUserRecord.role == "expert")
        .order_by(AltAuthUserRecord.id.asc())
        .all()
    )
    expert_ids = [u.id for u in expert_rows]

    assignments_by_expert: dict[int, List[int]] = {eid: [] for eid in expert_ids}
    if expert_ids:
        assign_rows = (
            db.query(
                CompetitionExpertAssignment.expert_id,
                CompetitionExpertAssignment.competition_id,
            )
            .filter(CompetitionExpertAssignment.expert_id.in_(expert_ids))
            .all()
        )
        for expert_id, comp_id in assign_rows:
            assignments_by_expert.setdefault(int(expert_id), []).append(int(comp_id))

    items: List[CompetitionExpertListItem] = []
    for u in expert_rows:
        cids = sorted(set(assignments_by_expert.get(u.id, [])))
        items.append(
            CompetitionExpertListItem(
                expert_user_id=u.id,
                username=u.username or "",
                email=u.email,
                full_name=u.full_name,
                school=u.school,
                expert_verified=bool(getattr(u, "expert_verified", False)),
                assigned_competition_ids=cids,
            )
        )

    return CompetitionExpertsListResponse(total=len(items), items=items)


@router.put("/{competition_id}/publish", response_model=CompetitionResponse)
async def publish_competition(
    competition_id: int,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    require_permission(identity.role, Permission.MANAGE_COMPETITIONS)
    competition = _get_competition(db, competition_id)
    competition.status = "published"
    db.commit()
    db.refresh(competition)
    return competition


@router.put("/{competition_id}/lock", response_model=CompetitionResponse)
async def lock_competition(
    competition_id: int,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """停止报名：将竞赛标记为 closed（禁止新报名/新建队伍/加入队伍，不禁止提交与评分等）。"""
    require_permission(identity.role, Permission.MANAGE_COMPETITIONS)
    competition = _get_competition(db, competition_id)
    competition.status = "closed"
    db.commit()
    db.refresh(competition)
    return competition


@router.patch("/admin/alt-users/{target_user_id}", response_model=AltUserAdminUpdateResult)
async def competition_admin_patch_alt_user(
    target_user_id: int,
    body: AltUserAdminPatch,
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """管理员调整第二套帐号（含专家审核、角色指派）。"""
    _require_super_admin_identity(identity)
    row = adb.query(AltAuthUserRecord).filter(AltAuthUserRecord.id == target_user_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Target user not found")
    if body.role is not None:
        r = body.role.value if hasattr(body.role, "value") else str(body.role)
        r = r.strip()
        if r not in {"student", "advisor", "teacher", "expert", "super_admin", "school_admin"}:
            raise HTTPException(status_code=400, detail="Invalid role for alt user")
        row.role = r
    if body.expert_verified is not None:
        if body.expert_verified and _effective_alt_role(row.role) != "expert":
            raise HTTPException(status_code=400, detail="expert_verified only applies to expert role")
        row.expert_verified = bool(body.expert_verified)
    if body.school_admin_verified is not None:
        if body.school_admin_verified and _effective_alt_role(row.role) != "school_admin":
            raise HTTPException(status_code=400, detail="school_admin_verified only applies to school_admin role")
        row.school_admin_verified = bool(body.school_admin_verified)
        if row.school_admin_verified:
            row.school_admin_application_status = SchoolAdminApplicationStatus.APPROVED.value
        elif _school_admin_application_status(row) == SchoolAdminApplicationStatus.APPROVED:
            row.school_admin_application_status = SchoolAdminApplicationStatus.REJECTED.value
    adb.commit()
    adb.refresh(row)
    return AltUserAdminUpdateResult(
        id=row.id,
        role=_effective_alt_role(row.role),
        expert_verified=bool(getattr(row, "expert_verified", False)),
        school_admin_verified=bool(getattr(row, "school_admin_verified", False)),
    )


@router.get("/school-admin/application/me", response_model=SchoolAdminApplicationMeResponse)
async def get_school_admin_application_me(
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """校管理员查看本人申请状态（未通过审核前不可查看组队校审列表）。"""
    _require_school_admin_role(identity)
    app_status = _school_admin_application_status(identity)
    photo_url = (
        "/api/v1/competitions/school-admin/application/photo"
        if getattr(identity, "school_admin_photo_path", None)
        else None
    )
    return SchoolAdminApplicationMeResponse(
        user_id=identity.id,
        school=identity.school,
        full_name=identity.full_name,
        school_admin_verified=bool(getattr(identity, "school_admin_verified", False)),
        application_status=app_status,
        application_contact=getattr(identity, "school_admin_application_contact", None),
        application_remark=getattr(identity, "school_admin_application_remark", None),
        application_submitted_at=getattr(identity, "school_admin_application_submitted_at", None),
        review_feedback=getattr(identity, "school_admin_review_feedback", None),
        reviewed_at=getattr(identity, "school_admin_reviewed_at", None),
        photo_url=photo_url,
        can_review_teams=_school_admin_can_review_teams(identity),
    )


@router.post("/school-admin/application", response_model=SchoolAdminApplicationMeResponse)
async def submit_school_admin_application(
    photo: UploadFile = File(..., description="校管理员申请照片（必填）"),
    contact: Optional[str] = Form(None, description="联系方式"),
    remark: Optional[str] = Form(None, description="申请备注"),
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """校管理员提交资料申请（须含照片）；待 super_admin 审核通过后方可组队校审。"""
    _require_school_admin_role(identity)
    row = adb.query(AltAuthUserRecord).filter(AltAuthUserRecord.id == identity.id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")

    app_status = _school_admin_application_status(row)
    if app_status == SchoolAdminApplicationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Application already pending review")
    if _school_admin_can_review_teams(row):
        raise HTTPException(status_code=400, detail="School admin already verified")

    old_photo = getattr(row, "school_admin_photo_path", None)
    rel_path = await _save_school_admin_photo(photo, row.id)
    if old_photo and old_photo != rel_path:
        _delete_school_admin_photo(old_photo)

    row.school_admin_photo_path = rel_path
    row.school_admin_application_contact = (contact or "").strip() or None
    row.school_admin_application_remark = (remark or "").strip() or None
    row.school_admin_application_status = SchoolAdminApplicationStatus.PENDING.value
    row.school_admin_application_submitted_at = utc_now()
    row.school_admin_verified = False
    row.school_admin_review_feedback = None
    row.school_admin_reviewed_at = None
    row.school_admin_reviewed_by_id = None
    adb.commit()
    adb.refresh(row)

    return SchoolAdminApplicationMeResponse(
        user_id=row.id,
        school=row.school,
        full_name=row.full_name,
        school_admin_verified=False,
        application_status=SchoolAdminApplicationStatus.PENDING,
        application_contact=row.school_admin_application_contact,
        application_remark=row.school_admin_application_remark,
        application_submitted_at=row.school_admin_application_submitted_at,
        review_feedback=None,
        reviewed_at=None,
        photo_url="/api/v1/competitions/school-admin/application/photo",
        can_review_teams=False,
    )


@router.get("/school-admin/application/photo")
async def download_school_admin_application_photo_self(
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """校管理员下载本人申请照片。"""
    _require_school_admin_role(identity)
    row = adb.query(AltAuthUserRecord).filter(AltAuthUserRecord.id == identity.id).first()
    if row is None or not getattr(row, "school_admin_photo_path", None):
        raise HTTPException(status_code=404, detail="Photo not found")
    fs_path = _resolve_school_admin_photo_fs_path(row.school_admin_photo_path)
    ext = os.path.splitext(fs_path)[1].lower()
    media = mimetypes.guess_type(fs_path)[0] or "application/octet-stream"
    return FileResponse(path=fs_path, filename=f"school_admin_{row.id}{ext}", media_type=media)


@router.get("/admin/school-admin-applications", response_model=SchoolAdminApplicationListResponse)
async def list_school_admin_applications(
    status_filter: Optional[str] = Query(
        SchoolAdminApplicationStatus.PENDING.value,
        alias="status",
        description="申请状态：pending / approved / rejected / not_submitted",
    ),
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """超级管理员查看校管理员资料申请列表。"""
    _require_super_admin_identity(identity)
    q = adb.query(AltAuthUserRecord).filter(AltAuthUserRecord.role == "school_admin")
    if status_filter and status_filter != "all":
        if status_filter == SchoolAdminApplicationStatus.NOT_SUBMITTED.value:
            q = q.filter(
                or_(
                    AltAuthUserRecord.school_admin_application_status.is_(None),
                    AltAuthUserRecord.school_admin_application_status == "",
                )
            )
        else:
            q = q.filter(AltAuthUserRecord.school_admin_application_status == status_filter)
    rows = q.order_by(
        AltAuthUserRecord.school_admin_application_submitted_at.desc(),
        AltAuthUserRecord.id.desc(),
    ).all()

    items: List[SchoolAdminApplicationListItem] = []
    for row in rows:
        app_status = _school_admin_application_status(row)
        items.append(
            SchoolAdminApplicationListItem(
                user_id=row.id,
                username=row.username or "",
                email=row.email,
                full_name=row.full_name,
                school=row.school,
                application_status=app_status,
                application_contact=getattr(row, "school_admin_application_contact", None),
                application_remark=getattr(row, "school_admin_application_remark", None),
                application_submitted_at=getattr(row, "school_admin_application_submitted_at", None),
                school_admin_verified=bool(getattr(row, "school_admin_verified", False)),
                review_feedback=getattr(row, "school_admin_review_feedback", None),
                reviewed_at=getattr(row, "school_admin_reviewed_at", None),
                photo_url=(
                    f"/api/v1/competitions/admin/school-admin-applications/{row.id}/photo"
                    if getattr(row, "school_admin_photo_path", None)
                    else None
                ),
            )
        )
    return SchoolAdminApplicationListResponse(total=len(items), items=items)


@router.get("/admin/school-admin-applications/{user_id}/photo")
async def download_school_admin_application_photo_admin(
    user_id: int,
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """超级管理员查看校管申请照片。"""
    _require_super_admin_identity(identity)
    row = adb.query(AltAuthUserRecord).filter(AltAuthUserRecord.id == user_id).first()
    if row is None or _effective_alt_role(row.role) != "school_admin":
        raise HTTPException(status_code=404, detail="School admin user not found")
    if not getattr(row, "school_admin_photo_path", None):
        raise HTTPException(status_code=404, detail="Photo not found")
    fs_path = _resolve_school_admin_photo_fs_path(row.school_admin_photo_path)
    ext = os.path.splitext(fs_path)[1].lower()
    media = mimetypes.guess_type(fs_path)[0] or "application/octet-stream"
    return FileResponse(path=fs_path, filename=f"school_admin_{row.id}{ext}", media_type=media)


@router.put(
    "/admin/school-admin-applications/{user_id}",
    response_model=SchoolAdminApplicationReviewResult,
)
async def review_school_admin_application(
    user_id: int,
    body: SchoolAdminApplicationReviewRequest,
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """超级管理员审核校管理员资料申请。"""
    _require_super_admin_identity(identity)
    row = adb.query(AltAuthUserRecord).filter(AltAuthUserRecord.id == user_id).first()
    if row is None or _effective_alt_role(row.role) != "school_admin":
        raise HTTPException(status_code=404, detail="School admin user not found")
    if _school_admin_application_status(row) != SchoolAdminApplicationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Application is not pending review")
    if not getattr(row, "school_admin_photo_path", None):
        raise HTTPException(status_code=400, detail="Application has no photo")

    action = body.action.value if hasattr(body.action, "value") else str(body.action)
    feedback = (body.feedback or "").strip() or None
    now = utc_now()

    if action == "approve":
        row.school_admin_verified = True
        row.school_admin_application_status = SchoolAdminApplicationStatus.APPROVED.value
    elif action == "reject":
        row.school_admin_verified = False
        row.school_admin_application_status = SchoolAdminApplicationStatus.REJECTED.value
    else:
        raise HTTPException(status_code=400, detail="action must be approve or reject")

    row.school_admin_review_feedback = feedback
    row.school_admin_reviewed_at = now
    row.school_admin_reviewed_by_id = identity.id
    adb.commit()
    adb.refresh(row)

    return SchoolAdminApplicationReviewResult(
        user_id=row.id,
        school_admin_verified=bool(row.school_admin_verified),
        application_status=_school_admin_application_status(row),
        review_feedback=row.school_admin_review_feedback,
        reviewed_at=row.school_admin_reviewed_at,
    )


@router.get("/school-admin/teams", response_model=SchoolAdminTeamReviewListResponse)
async def list_school_admin_teams(
    status_filter: Optional[str] = Query(
        TeamStatus.PENDING_SCHOOL_REVIEW,
        alias="status",
        description="队伍状态筛选，默认 pending_school_review",
    ),
    competition_id: Optional[int] = Query(None, description="按竞赛 id 筛选"),
    db: Session = Depends(get_db),
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """
    校管理员查看本校组队人员审核列表。
    列表字段：竞赛名、开始/结束时间、学校、指导老师、队伍名、队长、队员、状态。
    """
    _require_school_admin_identity(identity)
    admin_school = _normalize_school_name(identity.school)

    q = (
        db.query(Team)
        .join(Competition, Team.competition_id == Competition.id)
        .options(joinedload(Team.members))
        .filter(Team.school.isnot(None))
    )
    if status_filter:
        q = q.filter(Team.status == status_filter)
    if competition_id is not None:
        q = q.filter(Team.competition_id == competition_id)

    teams = q.order_by(Team.created_at.desc(), Team.id.desc()).all()
    teams = [t for t in teams if _team_matches_school(t, admin_school)]

    all_uids: set[int] = set()
    for t in teams:
        all_uids.add(t.captain_id)
        if t.created_by_advisor_id:
            all_uids.add(t.created_by_advisor_id)
        for m in t.members:
            all_uids.add(m.user_id)
    users_by_id = _alt_users_by_id(adb, all_uids)

    items = [
        _build_school_admin_team_item(t, t.competition, users_by_id)
        for t in teams
    ]
    return SchoolAdminTeamReviewListResponse(total=len(items), items=items)


@router.put("/teams/{team_id}/school-review", response_model=TeamSchoolReviewResult)
async def school_review_team(
    team_id: int,
    body: TeamSchoolReviewRequest,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """校管理员审核本校队伍：通过或驳回。"""
    _require_school_admin_identity(identity)
    admin_school = _normalize_school_name(identity.school)

    team = (
        db.query(Team)
        .options(joinedload(Team.members))
        .filter(Team.id == team_id)
        .first()
    )
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if not _team_matches_school(team, admin_school):
        raise HTTPException(status_code=403, detail="Team does not belong to your school")
    if team.status != TeamStatus.PENDING_SCHOOL_REVIEW:
        raise HTTPException(status_code=400, detail="Team is not pending school review")

    action = body.action.value if hasattr(body.action, "value") else str(body.action)
    feedback = (body.feedback or "").strip() or None
    now = utc_now()

    if action == "approve":
        team.status = TeamStatus.ACTIVE
        team.reviewed_by_id = identity.id
        team.reviewed_at = now
        team.review_feedback = feedback
    elif action == "reject":
        team.status = TeamStatus.REJECTED
        team.reviewed_by_id = identity.id
        team.reviewed_at = now
        team.review_feedback = feedback
        enrollments = (
            db.query(CompetitionEnrollment)
            .filter(
                CompetitionEnrollment.competition_id == team.competition_id,
                CompetitionEnrollment.team_id == team.id,
                CompetitionEnrollment.status == CompetitionEnrollmentStatus.ENROLLED,
            )
            .all()
        )
        for enr in enrollments:
            enr.status = CompetitionEnrollmentStatus.WITHDRAWN
    else:
        raise HTTPException(status_code=400, detail="action must be approve or reject")

    db.commit()
    db.refresh(team)
    return TeamSchoolReviewResult(
        team_id=team.id,
        status=team.status,
        reviewed_at=team.reviewed_at,
        review_feedback=team.review_feedback,
    )


@router.post(
    "/{competition_id}/experts/{expert_user_id}",
    status_code=status.HTTP_201_CREATED,
)
async def assign_competition_expert(
    competition_id: int,
    expert_user_id: int,
    db: Session = Depends(get_db),
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    _require_super_admin_identity(identity)
    _get_competition(db, competition_id)
    user = adb.query(AltAuthUserRecord).filter(AltAuthUserRecord.id == expert_user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Expert user not found")
    if _effective_alt_role(user.role) != "expert":
        raise HTTPException(status_code=400, detail="Target role must be expert")
    if not bool(getattr(user, "expert_verified", False)):
        raise HTTPException(status_code=400, detail="Expert must be verified before assignment")
    dup = (
        db.query(CompetitionExpertAssignment)
        .filter(
            CompetitionExpertAssignment.competition_id == competition_id,
            CompetitionExpertAssignment.expert_id == expert_user_id,
        )
        .first()
    )
    if dup:
        raise HTTPException(status_code=400, detail="Expert already assigned")
    db.add(CompetitionExpertAssignment(competition_id=competition_id, expert_id=expert_user_id))
    db.commit()
    return {"ok": True}


@router.delete("/{competition_id}/experts/{expert_user_id}", status_code=status.HTTP_200_OK)
async def unassign_competition_expert(
    competition_id: int,
    expert_user_id: int,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    _require_super_admin_identity(identity)
    row = (
        db.query(CompetitionExpertAssignment)
        .filter(
            CompetitionExpertAssignment.competition_id == competition_id,
            CompetitionExpertAssignment.expert_id == expert_user_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.put("/{competition_id}", response_model=CompetitionResponse)
async def update_competition(
    competition_id: int,
    request: Request,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """
    修改竞赛（字段可选，只传需要改的）。
    - **application/json**：与原先一致，请求体为 CompetitionUpdate（无文件上传）。
    - **multipart/form-data**：文本字段同名且仅提交需修改项；可选 **`qr_code_image`** 替换二维码（规则同创建）。
    """
    require_permission(identity.role, Permission.MANAGE_COMPETITIONS)
    competition = _get_competition(db, competition_id)

    ct = (request.headers.get("content-type") or "").lower()
    qr_upload = None
    if "application/json" in ct:
        try:
            body = await request.json()
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid JSON body") from e
        payload = CompetitionUpdate.model_validate(body)
        update_data = payload.model_dump(exclude_unset=True)
    elif "multipart/form-data" in ct:
        form = await request.form()
        payload = _competition_update_from_form(form)
        update_data = payload.model_dump(exclude_unset=True)
        q = form.get("qr_code_image")
        if isinstance(q, StarletteUploadFile) and q.filename and str(q.filename).strip():
            qr_upload = q
    else:
        raise HTTPException(
            status_code=415,
            detail="Content-Type must be application/json or multipart/form-data",
        )

    for field, value in update_data.items():
        setattr(competition, field, value)

    if qr_upload is not None:
        old_path = competition.qr_code_path
        rel = await _save_qr_code_upload(qr_upload, competition_id)
        competition.qr_code_path = rel
        if old_path and old_path != rel:
            _delete_stored_qr_file(old_path)

    db.commit()
    db.refresh(competition)
    return competition


@router.delete("/{competition_id}", status_code=status.HTTP_200_OK)
async def delete_competition(
    competition_id: int,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    require_permission(identity.role, Permission.MANAGE_COMPETITIONS)
    competition = _get_competition(db, competition_id)
    qr_storage = competition.qr_code_path

    db.query(Review).filter(
        Review.submission_id.in_(
            db.query(Submission.id).filter(Submission.competition_id == competition_id)
        )
    ).delete(synchronize_session=False)
    db.query(Submission).filter(Submission.competition_id == competition_id).delete(synchronize_session=False)
    db.query(CompetitionEnrollment).filter(CompetitionEnrollment.competition_id == competition_id).delete(synchronize_session=False)
    db.query(TeamMember).filter(
        TeamMember.team_id.in_(
            db.query(Team.id).filter(Team.competition_id == competition_id)
        )
    ).delete(synchronize_session=False)
    db.query(Team).filter(Team.competition_id == competition_id).delete(synchronize_session=False)
    db.delete(competition)

    db.commit()
    _delete_stored_qr_file(qr_storage)

    return {"ok": True, "detail": f"Competition {competition_id} and all related data deleted"}


@router.post("/enroll", response_model=CompetitionEnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_competition(
    enroll: CompetitionEnrollmentCreate,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    require_permission(identity.role, Permission.ENROLL_COMPETITIONS)

    competition = _get_competition(db, enroll.competition_id)
    _ensure_enrollment_open(competition)
    if competition.status != "published":
        raise HTTPException(status_code=400, detail="Competition not published")

    if _effective_alt_role(identity.role) != "student":
        # 当前版本仅允许 student 报名
        raise HTTPException(status_code=403, detail="Only students can enroll")

    # 允许个人/队伍模式校验
    is_team = enroll.team_id is not None
    if is_team and not competition.allow_team:
        raise HTTPException(status_code=400, detail="Team enrollment not allowed")
    if (not is_team) and not competition.allow_individual:
        raise HTTPException(status_code=400, detail="Individual enrollment not allowed")

    scope = _enrollment_scope_for_team(enroll.team_id)
    existing_row = _get_enrollment_by_scope(db, competition.id, identity.id, scope)
    if existing_row and existing_row.status == CompetitionEnrollmentStatus.ENROLLED:
        if is_team:
            raise HTTPException(
                status_code=400,
                detail="Already enrolled in the team track for this competition",
            )
        raise HTTPException(
            status_code=400,
            detail="Already enrolled in the individual track for this competition",
        )

    team: Optional[Team] = None
    if is_team:
        team = db.query(Team).filter(Team.id == enroll.team_id, Team.competition_id == competition.id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found in this competition")

        # 同一队伍：成员表必须存在
        member = db.query(TeamMember).filter(
            TeamMember.team_id == team.id, TeamMember.user_id == identity.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="User is not a team member")

        is_captain = bool(member.is_captain)
        if existing_row and existing_row.status == CompetitionEnrollmentStatus.WITHDRAWN:
            existing_row.team_id = team.id
            existing_row.enrollment_scope = CompetitionEnrollmentScope.TEAM
            existing_row.is_captain = is_captain
            existing_row.status = CompetitionEnrollmentStatus.ENROLLED
            existing_row.student_no = enroll.student_no
            existing_row.real_name = enroll.real_name
            existing_row.college = enroll.college
            existing_row.grade = enroll.grade
            existing_row.contact = enroll.contact
            enrollment = existing_row
        else:
            enrollment = CompetitionEnrollment(
                competition_id=competition.id,
                student_id=identity.id,
                team_id=team.id,
                enrollment_scope=CompetitionEnrollmentScope.TEAM,
                is_captain=is_captain,
                status=CompetitionEnrollmentStatus.ENROLLED,
                student_no=enroll.student_no,
                real_name=enroll.real_name,
                college=enroll.college,
                grade=enroll.grade,
                contact=enroll.contact,
            )
            db.add(enrollment)
    else:
        if existing_row and existing_row.status == CompetitionEnrollmentStatus.WITHDRAWN:
            existing_row.team_id = None
            existing_row.enrollment_scope = CompetitionEnrollmentScope.INDIVIDUAL
            existing_row.is_captain = False
            existing_row.status = CompetitionEnrollmentStatus.ENROLLED
            existing_row.student_no = enroll.student_no
            existing_row.real_name = enroll.real_name
            existing_row.college = enroll.college
            existing_row.grade = enroll.grade
            existing_row.contact = enroll.contact
            enrollment = existing_row
        else:
            enrollment = CompetitionEnrollment(
                competition_id=competition.id,
                student_id=identity.id,
                team_id=None,
                enrollment_scope=CompetitionEnrollmentScope.INDIVIDUAL,
                is_captain=False,
                status=CompetitionEnrollmentStatus.ENROLLED,
                student_no=enroll.student_no,
                real_name=enroll.real_name,
                college=enroll.college,
                grade=enroll.grade,
                contact=enroll.contact,
            )
            db.add(enrollment)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Enrollment failed: {str(e)}")

    db.refresh(enrollment)
    base = CompetitionEnrollmentResponse.model_validate(enrollment)
    if not is_team:
        seq = _individual_sequence_no(db, competition.id, enrollment)
        return base.model_copy(update={"sequence_no": seq})
    assert team is not None
    seq = _team_sequence_no(db, competition.id, team)
    return base.model_copy(update={"sequence_no": seq})


@router.post("/{competition_id}/withdraw", response_model=CompetitionEnrollmentResponse)
async def withdraw_from_competition(
    competition_id: int,
    track: Optional[str] = Query(
        None,
        description="退赛赛道：individual（个人）或 team（组队）。同时存在两条有效报名时必填。",
    ),
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """
    参赛学生退赛（取消当前竞赛中某一赛道的有效报名）。
    - 个人赛道：将个人报名置为 withdrawn（不影响组队赛道）
    - 组队赛道：从 team_members 移除；队长若队伍内仍有其他成员，须先转让队长；
      若队长为队内唯一成员，则退赛同时解散队伍（team 标记为 disbanded）
    """
    require_permission(identity.role, Permission.ENROLL_COMPETITIONS)
    if _effective_alt_role(identity.role) != "student":
        raise HTTPException(status_code=403, detail="Only students can withdraw")

    competition = _get_competition(db, competition_id)

    has_individual = _has_active_enrollment_in_scope(
        db, competition.id, identity.id, CompetitionEnrollmentScope.INDIVIDUAL
    )
    team_enrollment = (
        db.query(CompetitionEnrollment)
        .filter(
            CompetitionEnrollment.competition_id == competition.id,
            CompetitionEnrollment.student_id == identity.id,
            CompetitionEnrollment.enrollment_scope == CompetitionEnrollmentScope.TEAM,
            CompetitionEnrollment.status == CompetitionEnrollmentStatus.ENROLLED,
        )
        .first()
    )
    has_team = team_enrollment is not None

    if not has_individual and not has_team:
        raise HTTPException(status_code=404, detail="No active enrollment in this competition")

    resolved_track = (track or "").strip().lower() or None
    if resolved_track not in (None, CompetitionEnrollmentScope.INDIVIDUAL, CompetitionEnrollmentScope.TEAM):
        raise HTTPException(
            status_code=400,
            detail="Invalid track; use individual or team",
        )
    if resolved_track is None:
        if has_individual and has_team:
            raise HTTPException(
                status_code=400,
                detail="Specify track=individual or track=team when enrolled in both tracks",
            )
        resolved_track = (
            CompetitionEnrollmentScope.TEAM if has_team else CompetitionEnrollmentScope.INDIVIDUAL
        )
    elif resolved_track == CompetitionEnrollmentScope.INDIVIDUAL and not has_individual:
        raise HTTPException(status_code=404, detail="No active individual enrollment in this competition")
    elif resolved_track == CompetitionEnrollmentScope.TEAM and not has_team:
        raise HTTPException(status_code=404, detail="No active team enrollment in this competition")

    if resolved_track == CompetitionEnrollmentScope.INDIVIDUAL:
        enrollment = _get_enrollment_by_scope(
            db, competition.id, identity.id, CompetitionEnrollmentScope.INDIVIDUAL
        )
        assert enrollment is not None
        enrollment.status = CompetitionEnrollmentStatus.WITHDRAWN
        db.commit()
        db.refresh(enrollment)
        return enrollment

    enrollment = team_enrollment
    assert enrollment is not None

    if enrollment.team_id is None:
        enrollment.status = CompetitionEnrollmentStatus.WITHDRAWN
        db.commit()
        db.refresh(enrollment)
        return enrollment

    team = (
        db.query(Team)
        .filter(Team.id == enrollment.team_id, Team.competition_id == competition.id)
        .first()
    )
    member = db.query(TeamMember).filter(
        TeamMember.team_id == enrollment.team_id,
        TeamMember.user_id == identity.id,
    ).first()

    if team is None:
        enrollment.status = CompetitionEnrollmentStatus.WITHDRAWN
        enrollment.is_captain = False
        if member:
            db.delete(member)
        db.commit()
        db.refresh(enrollment)
        return enrollment

    is_captain = team.captain_id == identity.id or (member is not None and member.is_captain)

    if is_captain and team is not None:
        other_members = (
            db.query(TeamMember)
            .filter(TeamMember.team_id == team.id, TeamMember.user_id != identity.id)
            .count()
        )
        if other_members > 0:
            raise HTTPException(
                status_code=400,
                detail="Captain must transfer captaincy before withdrawing from the competition",
            )
        if member:
            db.delete(member)
        team.status = TeamStatus.DISBANDED
        enrollment.status = CompetitionEnrollmentStatus.WITHDRAWN
        enrollment.is_captain = False
        db.commit()
        db.refresh(enrollment)
        return enrollment

    if member:
        db.delete(member)
    enrollment.status = CompetitionEnrollmentStatus.WITHDRAWN
    enrollment.is_captain = False
    db.commit()
    db.refresh(enrollment)
    return enrollment


@router.get("/{competition_id}/teams/lookup", response_model=TeamResponse)
async def lookup_team_by_name(
    competition_id: int,
    name: str = Query(..., min_length=1, description="队名（精确匹配，忽略大小写）"),
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """按队名查找可加入的队伍（pending_school_review / active）。"""
    require_permission(identity.role, Permission.VIEW_COMPETITIONS)
    _get_competition(db, competition_id)
    target = _strip_team_name(name)
    if not target:
        raise HTTPException(status_code=404, detail="Team not found")
    target_key = target.casefold()
    teams = (
        db.query(Team)
        .filter(
            Team.competition_id == competition_id,
            Team.status.in_(_team_composition_open_statuses()),
        )
        .all()
    )
    for team in teams:
        tn = _strip_team_name(team.name)
        if tn and tn.casefold() == target_key:
            return team
    raise HTTPException(status_code=404, detail="Team not found")


@router.get("/{competition_id}/teams", response_model=List[TeamDetailResponse])
async def list_teams(
    competition_id: int,
    db: Session = Depends(get_db),
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """查看某竞赛下队伍（含成员列表）；指导老师/教师仅见本人创建的队伍（含待校审）。"""
    require_permission(identity.role, Permission.VIEW_COMPETITIONS)
    _get_competition(db, competition_id)

    role_eff = _effective_alt_role(identity.role)
    q = db.query(Team).filter(Team.competition_id == competition_id)
    if role_eff in {"advisor", "teacher"}:
        teams = (
            q.options(joinedload(Team.members))
            .filter(
                Team.created_by_advisor_id == identity.id,
                Team.status.in_(
                    [
                        TeamStatus.ACTIVE,
                        TeamStatus.PENDING_SCHOOL_REVIEW,
                        TeamStatus.REJECTED,
                    ]
                ),
            )
            .order_by(Team.created_at.desc())
            .all()
        )
    else:
        teams = (
            q.options(joinedload(Team.members))
            .filter(Team.status == TeamStatus.ACTIVE)
            .order_by(Team.created_at.desc())
            .all()
        )
    return _team_detail_responses(adb, teams)


@router.get("/{competition_id}/participants/individual", response_model=List[IndividualParticipantItem])
async def list_individual_participants(
    competition_id: int,
    db: Session = Depends(get_db),
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """
    查看某竞赛「个人赛道」全部有效报名者（`team_id` 为空、`enrolled`）。
    `sequence_no` 为本竞赛个人赛道内序号（从 1 起）；`enrollment_id` 为数据库主键。
    """
    require_permission(identity.role, Permission.VIEW_COMPETITIONS)
    _get_competition(db, competition_id)
    if not _can_view_full_participant_rosters(db, competition_id, identity):
        raise HTTPException(status_code=403, detail="Only super_admin or assigned verified experts may view roster")

    rows = (
        db.query(CompetitionEnrollment)
        .filter(
            CompetitionEnrollment.competition_id == competition_id,
            CompetitionEnrollment.enrollment_scope == CompetitionEnrollmentScope.INDIVIDUAL,
            CompetitionEnrollment.status == CompetitionEnrollmentStatus.ENROLLED,
        )
        .order_by(CompetitionEnrollment.created_at.asc(), CompetitionEnrollment.id.asc())
        .all()
    )
    alt_ids = {r.student_id for r in rows}
    alt_map = _alt_users_by_id(adb, alt_ids)
    out: List[IndividualParticipantItem] = []
    for seq, enr in enumerate(rows, start=1):
        au = alt_map.get(enr.student_id)
        out.append(
            IndividualParticipantItem(
                sequence_no=seq,
                enrollment_id=enr.id,
                student_id=enr.student_id,
                username=(au.username or "") if au else "",
                full_name=au.full_name if au else None,
                student_no=enr.student_no,
                real_name=enr.real_name,
                college=enr.college,
                grade=enr.grade,
                contact=enr.contact,
                status=enr.status,
                created_at=enr.created_at,
            )
        )
    return out


@router.get("/{competition_id}/participants/teams", response_model=List[TeamParticipantDetailResponse])
async def list_team_participants(
    competition_id: int,
    db: Session = Depends(get_db),
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """
    查看某竞赛「组队赛道」全部活跃队伍及成员（含账号名）。
    `sequence_no` 为本竞赛内队伍序号（从 1 起）；队伍的 `id` 仍为全局队伍主键。
    """
    require_permission(identity.role, Permission.VIEW_COMPETITIONS)
    _get_competition(db, competition_id)
    if not _can_view_full_participant_rosters(db, competition_id, identity):
        raise HTTPException(status_code=403, detail="Only super_admin or assigned verified experts may view roster")

    teams = (
        db.query(Team)
        .options(joinedload(Team.members))
        .filter(Team.competition_id == competition_id, Team.status == TeamStatus.ACTIVE)
        .order_by(Team.created_at.asc(), Team.id.asc())
        .all()
    )
    all_uids = {m.user_id for t in teams for m in t.members} | {t.captain_id for t in teams}
    users_by_id = _alt_users_by_id(adb, all_uids)

    out: List[TeamParticipantDetailResponse] = []
    for seq, team in enumerate(teams, start=1):
        members_out: List[TeamMemberWithUserResponse] = []
        for m in sorted(team.members, key=lambda x: (x.joined_at or utc_now(), x.id)):
            u = users_by_id.get(m.user_id)
            members_out.append(
                TeamMemberWithUserResponse(
                    id=m.id,
                    team_id=m.team_id,
                    user_id=m.user_id,
                    username=u.username if u else "",
                    full_name=u.full_name if u else None,
                    is_captain=m.is_captain,
                    joined_at=m.joined_at,
                )
            )
        out.append(
            TeamParticipantDetailResponse(
                sequence_no=seq,
                id=team.id,
                competition_id=team.competition_id,
                name=team.name,
                captain_id=team.captain_id,
                status=team.status,
                created_at=team.created_at,
                members=members_out,
            )
        )
    return out


@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_create: TeamCreate,
    db: Session = Depends(get_db),
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    require_permission(identity.role, Permission.MANAGE_TEAMS)

    competition = _get_competition(db, team_create.competition_id)
    _ensure_enrollment_open(competition)
    if competition.status != "published":
        raise HTTPException(status_code=400, detail="Competition not published")
    if not competition.allow_team:
        raise HTTPException(status_code=400, detail="Team enrollment not allowed")

    role_eff = _effective_alt_role(identity.role)
    tn = _strip_team_name(team_create.name)

    if role_eff in {"advisor", "teacher"}:
        ids = team_create.initial_member_ids or []
        if not ids:
            raise HTTPException(
                status_code=400,
                detail="指导老师建队须提供 initial_member_ids（至少一名学生），并由 captain_student_id 指定队长",
            )
        seen = set()
        ordered_ids = []
        for x in ids:
            if x not in seen:
                seen.add(x)
                ordered_ids.append(x)
        captain_id = team_create.captain_student_id if team_create.captain_student_id is not None else ordered_ids[0]
        if captain_id not in ordered_ids:
            raise HTTPException(status_code=400, detail="captain_student_id 必须出现在 initial_member_ids 中")

        if identity.id in ordered_ids:
            raise HTTPException(status_code=400, detail="指导老师不能以队员身份写入队伍名单")

        for sid in ordered_ids:
            _ensure_alt_principal_is_student(adb, sid)
            if _has_active_enrollment_in_scope(
                db, competition.id, sid, CompetitionEnrollmentScope.TEAM
            ):
                raise HTTPException(status_code=400, detail=f"学生 {sid} 已在该竞赛组队赛道报名")

        team_school = _resolve_team_school(adb, captain_id)
        # 指导老师/教师代建队：自动将当前登录老师设为建队指导老师（忽略请求体中的 advisor_id/advisor_name）
        team = Team(
            competition_id=competition.id,
            name=tn,
            captain_id=captain_id,
            created_by_advisor_id=identity.id,
            advisor_name=_display_user_name(identity, identity.id),
            school=team_school,
            status=TeamStatus.PENDING_SCHOOL_REVIEW,
        )
        db.add(team)
        db.flush()

        for sid in ordered_ids:
            ic = sid == captain_id
            db.add(TeamMember(team_id=team.id, user_id=sid, is_captain=ic))
            row_any = _get_enrollment_by_scope(
                db, competition.id, sid, CompetitionEnrollmentScope.TEAM
            )
            if row_any and row_any.status == CompetitionEnrollmentStatus.WITHDRAWN:
                row_any.team_id = team.id
                row_any.enrollment_scope = CompetitionEnrollmentScope.TEAM
                row_any.is_captain = ic
                row_any.status = CompetitionEnrollmentStatus.ENROLLED
            else:
                enrollment = CompetitionEnrollment(
                    competition_id=competition.id,
                    student_id=sid,
                    team_id=team.id,
                    enrollment_scope=CompetitionEnrollmentScope.TEAM,
                    is_captain=ic,
                    status=CompetitionEnrollmentStatus.ENROLLED,
                )
                db.add(enrollment)

    elif role_eff == "student":
        if _has_active_enrollment_in_scope(
            db, competition.id, identity.id, CompetitionEnrollmentScope.TEAM
        ):
            raise HTTPException(
                status_code=400,
                detail="You have already enrolled in the team track for this competition",
            )

        team_school = _resolve_team_school(adb, identity.id)
        created_by_advisor_id = None
        advisor_display_name = None
        if team_create.advisor_id is not None:
            if int(team_create.advisor_id) == int(identity.id):
                raise HTTPException(status_code=400, detail="不能将自己指定为指导老师")
            adv_row = _ensure_alt_principal_is_advisor(adb, team_create.advisor_id)
            created_by_advisor_id = team_create.advisor_id
            advisor_display_name = _display_user_name(adv_row, team_create.advisor_id)
        elif team_create.advisor_name and str(team_create.advisor_name).strip():
            advisor_display_name = str(team_create.advisor_name).strip()
            advisor_row = _try_resolve_advisor_by_name(adb, advisor_display_name)
            if advisor_row:
                if int(advisor_row.id) == int(identity.id):
                    raise HTTPException(status_code=400, detail="不能将自己指定为指导老师")
                created_by_advisor_id = advisor_row.id

        team = Team(
            competition_id=competition.id,
            name=tn,
            captain_id=identity.id,
            created_by_advisor_id=created_by_advisor_id,
            advisor_name=advisor_display_name,
            school=team_school,
            status=TeamStatus.PENDING_SCHOOL_REVIEW,
        )
        db.add(team)
        db.flush()

        captain_member = TeamMember(team_id=team.id, user_id=identity.id, is_captain=True)
        db.add(captain_member)

        row_any = _get_enrollment_by_scope(
            db, competition.id, identity.id, CompetitionEnrollmentScope.TEAM
        )
        if row_any and row_any.status == CompetitionEnrollmentStatus.WITHDRAWN:
            row_any.team_id = team.id
            row_any.enrollment_scope = CompetitionEnrollmentScope.TEAM
            row_any.is_captain = True
            row_any.status = CompetitionEnrollmentStatus.ENROLLED
        else:
            enrollment = CompetitionEnrollment(
                competition_id=competition.id,
                student_id=identity.id,
                team_id=team.id,
                enrollment_scope=CompetitionEnrollmentScope.TEAM,
                is_captain=True,
                status=CompetitionEnrollmentStatus.ENROLLED,
            )
            db.add(enrollment)

        extras = team_create.initial_member_ids or []
        extras = [x for x in extras if x != identity.id]
        for sid in extras:
            _ensure_alt_principal_is_student(adb, sid)
            if _has_active_enrollment_in_scope(
                db, competition.id, sid, CompetitionEnrollmentScope.TEAM
            ):
                db.rollback()
                raise HTTPException(status_code=400, detail=f"学生 {sid} 已在竞赛组队赛道报名")
            db.add(TeamMember(team_id=team.id, user_id=sid, is_captain=False))
            row_other = _get_enrollment_by_scope(
                db, competition.id, sid, CompetitionEnrollmentScope.TEAM
            )
            if row_other and row_other.status == CompetitionEnrollmentStatus.WITHDRAWN:
                row_other.team_id = team.id
                row_other.enrollment_scope = CompetitionEnrollmentScope.TEAM
                row_other.is_captain = False
                row_other.status = CompetitionEnrollmentStatus.ENROLLED
            else:
                db.add(
                    CompetitionEnrollment(
                        competition_id=competition.id,
                        student_id=sid,
                        team_id=team.id,
                        enrollment_scope=CompetitionEnrollmentScope.TEAM,
                        is_captain=False,
                        status=CompetitionEnrollmentStatus.ENROLLED,
                    )
                )

    else:
        raise HTTPException(status_code=403, detail="Only student, advisor, or teacher can create teams")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Create team failed: {str(e)}")

    db.refresh(team)
    return team


@router.get("/teams/{team_id}", response_model=TeamDetailResponse)
async def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """队员/队长/建队指导老师查看本队详情（含校审状态 pending_school_review / active / rejected）。"""
    require_permission(identity.role, Permission.VIEW_COMPETITIONS)
    team = (
        db.query(Team)
        .options(joinedload(Team.members))
        .filter(Team.id == team_id)
        .first()
    )
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    _get_competition(db, team.competition_id)

    role_eff = _effective_alt_role(identity.role)
    if role_eff == "super_admin":
        return _team_detail_response(adb, team)
    if team.captain_id == identity.id:
        return _team_detail_response(adb, team)
    if _team_advisor_managed(team, identity.id):
        return _team_detail_response(adb, team)
    member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == identity.id)
        .first()
    )
    if member:
        return _team_detail_response(adb, team)
    raise HTTPException(status_code=403, detail="Not a member of this team")


@router.patch("/teams/{team_id}", response_model=TeamResponse)
async def patch_team(
    team_id: int,
    body: TeamPatch,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    body = TeamPatch.model_validate(body)
    require_permission(identity.role, Permission.MANAGE_TEAMS)
    team = (
        db.query(Team)
        .filter(Team.id == team_id, Team.status.in_(_team_composition_open_statuses()))
        .first()
    )
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if team.captain_id != identity.id and not (
        _effective_alt_role(identity.role) in {"advisor", "teacher"} and _team_advisor_managed(team, identity.id)
    ):
        raise HTTPException(status_code=403, detail="Only captain or advising teacher can rename team")

    if body.name is not None:
        team.name = _strip_team_name(body.name)
    db.commit()
    db.refresh(team)
    return team


@router.post("/teams/{team_id}/invite", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_team_member(
    team_id: int,
    body: TeamInviteMember,
    db: Session = Depends(get_db),
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    body = TeamInviteMember.model_validate(body)
    require_permission(identity.role, Permission.MANAGE_TEAMS)

    team = (
        db.query(Team)
        .filter(Team.id == team_id, Team.status.in_(_team_composition_open_statuses()))
        .first()
    )
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    competition = team.competition
    _ensure_enrollment_open(competition)
    if competition.status != "published":
        raise HTTPException(status_code=400, detail="Competition not published")

    if not _can_manage_team_composition(team, identity):
        raise HTTPException(status_code=403, detail="Only captain or advising teacher may invite")

    sid = body.student_id
    if sid == team.captain_id:
        raise HTTPException(status_code=400, detail="Captain is already on the team")

    _ensure_alt_principal_is_student(adb, sid)

    if db.query(TeamMember).filter(TeamMember.team_id == team.id, TeamMember.user_id == sid).first():
        raise HTTPException(status_code=400, detail="Already a team member")

    if _has_active_enrollment_in_scope(db, competition.id, sid, CompetitionEnrollmentScope.TEAM):
        raise HTTPException(
            status_code=400,
            detail="Student already enrolled in the team track for this competition",
        )

    member = _add_student_to_team(db, competition, team, sid, is_captain=False)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Invite failed: {str(e)}")
    db.refresh(member)
    return member


@router.delete("/teams/{team_id}/members/{user_id}", status_code=status.HTTP_200_OK)
async def kick_team_member(
    team_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    require_permission(identity.role, Permission.MANAGE_TEAMS)

    team = (
        db.query(Team)
        .filter(Team.id == team_id, Team.status.in_(_team_composition_open_statuses()))
        .first()
    )
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    competition = team.competition

    if not _can_manage_team_composition(team, identity):
        raise HTTPException(status_code=403, detail="Only captain or advising teacher may remove members")

    if user_id == team.captain_id:
        raise HTTPException(status_code=400, detail="Cannot kick captain")

    tm = db.query(TeamMember).filter(TeamMember.team_id == team.id, TeamMember.user_id == user_id).first()
    if not tm:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(tm)
    enrollment = db.query(CompetitionEnrollment).filter(
        CompetitionEnrollment.competition_id == competition.id,
        CompetitionEnrollment.team_id == team.id,
        CompetitionEnrollment.student_id == user_id,
    ).first()
    if enrollment:
        enrollment.status = CompetitionEnrollmentStatus.WITHDRAWN

    db.commit()
    return {"ok": True}


@router.post("/teams/{team_id}/members", response_model=TeamJoinRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_join_team(
    team_id: int,
    db: Session = Depends(get_db),
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """学生申请加入队伍（须队长或建队指导老师审核通过后正式入队）。"""
    require_permission(identity.role, Permission.MANAGE_TEAMS)

    if _effective_alt_role(identity.role) != "student":
        raise HTTPException(status_code=403, detail="Only students can request to join teams")

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team or team.status not in _team_composition_open_statuses():
        raise HTTPException(status_code=404, detail="Team not found")

    competition = team.competition
    if not competition or competition.status != "published":
        raise HTTPException(status_code=400, detail="Competition not published")
    _ensure_enrollment_open(competition)

    if db.query(TeamMember).filter(TeamMember.team_id == team.id, TeamMember.user_id == identity.id).first():
        raise HTTPException(status_code=400, detail="Already a team member")

    if _has_active_enrollment_in_scope(
        db, competition.id, identity.id, CompetitionEnrollmentScope.TEAM
    ):
        raise HTTPException(
            status_code=400,
            detail="You have already enrolled in the team track for this competition",
        )

    pending = (
        db.query(TeamJoinRequest)
        .filter(
            TeamJoinRequest.team_id == team.id,
            TeamJoinRequest.user_id == identity.id,
            TeamJoinRequest.status == TeamJoinRequestStatus.PENDING,
        )
        .first()
    )
    if pending:
        raise HTTPException(status_code=400, detail="您已提交过入队申请，请等待队长审核")

    req = TeamJoinRequest(team_id=team.id, user_id=identity.id, status=TeamJoinRequestStatus.PENDING)
    db.add(req)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Join request failed: {str(e)}")

    db.refresh(req)
    users_by_id = _alt_users_by_id(adb, {identity.id})
    return _build_team_join_request_response(req, users_by_id)


@router.get("/teams/{team_id}/join-requests", response_model=List[TeamJoinRequestResponse])
async def list_team_join_requests(
    team_id: int,
    status_filter: str = Query("pending", alias="status", description="pending | approved | rejected"),
    db: Session = Depends(get_db),
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """队长或建队指导老师查看入队申请列表。"""
    require_permission(identity.role, Permission.MANAGE_TEAMS)

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    _get_competition(db, team.competition_id)

    if not _can_manage_team_composition(team, identity):
        raise HTTPException(status_code=403, detail="Only captain or advising teacher may view join requests")

    st = (status_filter or "pending").strip().lower()
    if st not in {
        TeamJoinRequestStatus.PENDING,
        TeamJoinRequestStatus.APPROVED,
        TeamJoinRequestStatus.REJECTED,
    }:
        raise HTTPException(status_code=400, detail="Invalid status filter")

    rows = (
        db.query(TeamJoinRequest)
        .filter(TeamJoinRequest.team_id == team_id, TeamJoinRequest.status == st)
        .order_by(TeamJoinRequest.created_at.asc(), TeamJoinRequest.id.asc())
        .all()
    )
    users_by_id = _alt_users_by_id(adb, {r.user_id for r in rows})
    return [_build_team_join_request_response(r, users_by_id) for r in rows]


@router.post(
    "/teams/{team_id}/join-requests/{request_id}/review",
    response_model=TeamJoinRequestResponse,
)
async def review_team_join_request(
    team_id: int,
    request_id: int,
    body: TeamJoinRequestReview,
    db: Session = Depends(get_db),
    adb: Session = Depends(get_alt_auth_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """队长或建队指导老师同意/拒绝入队申请。"""
    body = TeamJoinRequestReview.model_validate(body)
    require_permission(identity.role, Permission.MANAGE_TEAMS)

    team = (
        db.query(Team)
        .filter(Team.id == team_id, Team.status.in_(_team_composition_open_statuses()))
        .first()
    )
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    competition = team.competition
    if not competition or competition.status != "published":
        raise HTTPException(status_code=400, detail="Competition not published")
    _ensure_enrollment_open(competition)

    if not _can_manage_team_composition(team, identity):
        raise HTTPException(status_code=403, detail="Only captain or advising teacher may review join requests")

    req = (
        db.query(TeamJoinRequest)
        .filter(
            TeamJoinRequest.id == request_id,
            TeamJoinRequest.team_id == team_id,
            TeamJoinRequest.status == TeamJoinRequestStatus.PENDING,
        )
        .first()
    )
    if not req:
        raise HTTPException(status_code=404, detail="Join request not found or already reviewed")

    if body.action == "reject":
        req.status = TeamJoinRequestStatus.REJECTED
        req.reviewed_at = utc_now()
        req.reviewed_by_id = identity.id
        db.commit()
        db.refresh(req)
        users_by_id = _alt_users_by_id(adb, {req.user_id})
        return _build_team_join_request_response(req, users_by_id)

    _ensure_alt_principal_is_student(adb, req.user_id)
    if db.query(TeamMember).filter(TeamMember.team_id == team.id, TeamMember.user_id == req.user_id).first():
        raise HTTPException(status_code=400, detail="Already a team member")
    if _has_active_enrollment_in_scope(
        db, competition.id, req.user_id, CompetitionEnrollmentScope.TEAM
    ):
        raise HTTPException(
            status_code=400,
            detail="Student already enrolled in the team track for this competition",
        )

    _add_student_to_team(db, competition, team, req.user_id, is_captain=False)
    req.status = TeamJoinRequestStatus.APPROVED
    req.reviewed_at = utc_now()
    req.reviewed_by_id = identity.id

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Approve join request failed: {str(e)}")

    db.refresh(req)
    users_by_id = _alt_users_by_id(adb, {req.user_id})
    return _build_team_join_request_response(req, users_by_id)


@router.post("/teams/{team_id}/transfer-captain", response_model=TeamResponse)
async def transfer_captain(
    team_id: int,
    payload: TeamTransferCaptain,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    require_permission(identity.role, Permission.MANAGE_TEAMS)

    if _effective_alt_role(identity.role) != "student":
        raise HTTPException(status_code=403, detail="Only students can transfer captain")

    team = (
        db.query(Team)
        .filter(Team.id == team_id, Team.status.in_(_team_composition_open_statuses()))
        .first()
    )
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if team.captain_id != identity.id:
        raise HTTPException(status_code=403, detail="Only current captain can transfer")

    new_captain_member = db.query(TeamMember).filter(
        TeamMember.team_id == team.id,
        TeamMember.user_id == payload.new_captain_id,
    ).first()
    if not new_captain_member:
        raise HTTPException(status_code=404, detail="New captain must be a team member")

    # 一致性：captain_id + team_members.is_captain
    old_captain_id = team.captain_id
    team.captain_id = payload.new_captain_id

    db.query(TeamMember).filter(TeamMember.team_id == team.id, TeamMember.is_captain == True).update(  # noqa: E712
        {"is_captain": False}
    )
    new_captain_member.is_captain = True

    # 同步 enrollment.is_captain（这也是“队长身份”在报名维度上的一致性来源）
    db.query(CompetitionEnrollment).filter(
        CompetitionEnrollment.competition_id == team.competition_id,
        CompetitionEnrollment.team_id == team.id,
        CompetitionEnrollment.student_id == old_captain_id,
    ).update({"is_captain": False})
    db.query(CompetitionEnrollment).filter(
        CompetitionEnrollment.competition_id == team.competition_id,
        CompetitionEnrollment.team_id == team.id,
        CompetitionEnrollment.student_id == payload.new_captain_id,
    ).update({"is_captain": True})

    db.commit()
    db.refresh(team)
    return team


@router.post("/teams/{team_id}/leave", status_code=status.HTTP_200_OK)
async def leave_team(
    team_id: int,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """
    队长退队：强制先转让。
    - 如果当前登录者为队长，则要求其先通过 transfer 接受“等价的队长身份转移”
    - 允许直接退队后成员仍可继续提交（本接口只处理“退队/移除成员”）
    """
    require_permission(identity.role, Permission.MANAGE_TEAMS)

    if _effective_alt_role(identity.role) != "student":
        raise HTTPException(status_code=403, detail="Only students can leave team")

    team = (
        db.query(Team)
        .filter(Team.id == team_id, Team.status.in_(_team_composition_open_statuses()))
        .first()
    )
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    member = db.query(TeamMember).filter(TeamMember.team_id == team.id, TeamMember.user_id == identity.id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if member.is_captain or team.captain_id == identity.id:
        raise HTTPException(status_code=400, detail="Captain must transfer before leaving")

    db.delete(member)

    # 更新报名状态（同一竞赛同一学生/同一队伍一条报名）
    enrollment = db.query(CompetitionEnrollment).filter(
        CompetitionEnrollment.competition_id == team.competition_id,
        CompetitionEnrollment.team_id == team.id,
        CompetitionEnrollment.student_id == identity.id,
    ).first()
    if enrollment:
        enrollment.status = CompetitionEnrollmentStatus.WITHDRAWN

    db.commit()
    return {"ok": True}


@router.post("/submissions", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_submission(
    body: Union[SubmissionCreate, SubmissionCreateWrapped],
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """
    仅接受 `application/json`。需要上传文件请使用 `POST /competitions/submissions/upload`。
    请求体可为 **扁平** `SubmissionCreate`，或 `{"payload": { ...同上字段... }}`（兼容易与 multipart 字段名混淆的前端）。
    若与本接口混用 `UploadFile`，FastAPI 会强制 multipart 并要求名为 `payload` 的字段，导致纯 JSON 返回 422。
    """
    payload = body.payload if isinstance(body, SubmissionCreateWrapped) else body

    require_permission(identity.role, Permission.SUBMIT_SUBMISSIONS)

    if _effective_alt_role(identity.role) != "student":
        raise HTTPException(status_code=403, detail="Only students can submit")

    competition = _get_competition(db, payload.competition_id)
    _ensure_competition_allows_submissions(competition)

    # 校验提交目标：个人 or 队伍
    team_id = payload.team_id
    if team_id is None:
        # 个人提交：student_id 必须是当前用户，且个人报名仍有效
        student_id = identity.id
        _ensure_active_individual_enrollment(db, competition.id, identity.id)
    else:
        team = db.query(Team).filter(Team.id == team_id, Team.competition_id == competition.id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        if team.status != TeamStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Team must be approved by school admin before submitting")

        # 队伍提交：须为队长提交
        member = db.query(TeamMember).filter(TeamMember.team_id == team.id, TeamMember.user_id == identity.id).first()
        if not member:
            raise HTTPException(status_code=403, detail="User is not a team member")
        if team.captain_id != identity.id:
            raise HTTPException(status_code=403, detail="Only team captain may submit for the team")
        student_id = identity.id

    if not payload.file_id and not payload.content_text:
        raise HTTPException(status_code=400, detail="Provide file_id or content_text")

    file_id = payload.file_id
    content_text = payload.content_text

    submission = Submission(
        competition_id=competition.id,
        team_id=payload.team_id,
        student_id=student_id,
        submitter_id=identity.id,
        title=payload.title,
        description=payload.description,
        file_id=file_id,
        content_text=content_text,
        status=SubmissionStatus.SUBMITTED,
    )
    db.add(submission)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Create submission failed: {str(e)}")

    db.refresh(submission)
    return submission


@router.post("/submissions/upload", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_submission_upload(
    competition_id: int = Form(...),
    team_id: Optional[int] = Form(None),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    content_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """
    multipart/form-data 方式提交作品（支持文件上传）。
    """
    require_permission(identity.role, Permission.SUBMIT_SUBMISSIONS)
    if _effective_alt_role(identity.role) != "student":
        raise HTTPException(status_code=403, detail="Only students can submit")

    competition = _get_competition(db, competition_id)
    _ensure_competition_allows_submissions(competition)

    # 校验提交目标：个人 or 队伍
    if team_id is None:
        student_id = identity.id
        _ensure_active_individual_enrollment(db, competition.id, identity.id)
    else:
        team = db.query(Team).filter(Team.id == team_id, Team.competition_id == competition.id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        if team.status != TeamStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Team must be approved by school admin before submitting")
        member = db.query(TeamMember).filter(TeamMember.team_id == team.id, TeamMember.user_id == identity.id).first()
        if not member:
            raise HTTPException(status_code=403, detail="User is not a team member")
        if team.captain_id != identity.id:
            raise HTTPException(status_code=403, detail="Only team captain may submit for the team")
        student_id = identity.id

    if not content_text and not (file and file.filename):
        raise HTTPException(status_code=400, detail="Provide content_text or upload file")

    file_id = None
    if file is not None and file.filename:
        file_uuid = str(uuid.uuid4())
        ext = os.path.splitext(file.filename)[1]
        filename = f"{file_uuid}{ext}"
        file_path = os.path.join(SUBMISSION_UPLOAD_DIR, filename)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        file_record = FileModel(
            filename=file.filename,
            file_type="submission",
            file_path=file_path,
            file_size=len(content),
            mime_type=file.content_type,
            sender_id=None,
        )
        db.add(file_record)
        db.flush()
        file_id = file_record.id

    submission = Submission(
        competition_id=competition.id,
        team_id=team_id,
        student_id=student_id,
        submitter_id=identity.id,
        title=title,
        description=description,
        file_id=file_id,
        content_text=content_text,
        status=SubmissionStatus.SUBMITTED,
    )
    db.add(submission)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Create submission failed: {str(e)}")

    db.refresh(submission)
    return submission


@router.get("/{competition_id}/submissions", response_model=List[SubmissionResponse])
async def list_submissions(
    competition_id: int,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    require_permission(identity.role, Permission.VIEW_COMPETITIONS)
    _get_competition(db, competition_id)

    if _can_view_all_competition_submissions(db, competition_id, identity):
        return db.query(Submission).filter(Submission.competition_id == competition_id).order_by(Submission.submitted_at.desc()).all()

    if _effective_alt_role(identity.role) != "student":
        raise HTTPException(
            status_code=403,
            detail="Only super_admin, assigned experts, or enrolled students may list submissions here",
        )

    # student：仅看自己的个人提交 + 自己所在队伍的提交
    team_ids = [tm.team_id for tm in db.query(TeamMember).join(Team).filter(
        TeamMember.user_id == identity.id,
        Team.competition_id == competition_id,
    ).all()]

    q = db.query(Submission).filter(Submission.competition_id == competition_id).filter(
        (Submission.student_id == identity.id) | (Submission.team_id.in_(team_ids) if team_ids else False)  # noqa: E712
    )
    return q.order_by(Submission.submitted_at.desc()).all()


@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    require_permission(identity.role, Permission.VIEW_COMPETITIONS)
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    _ensure_submission_access(db, submission, identity)
    return submission


@router.get("/submissions/{submission_id}/download")
async def download_submission_file(
    submission_id: int,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    require_permission(identity.role, Permission.VIEW_COMPETITIONS)
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    _ensure_submission_access(db, submission, identity)

    if not submission.file_id:
        raise HTTPException(status_code=404, detail="No file attached")

    file_record = db.query(FileModel).filter(FileModel.id == submission.file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    if not file_record.file_path or not os.path.exists(file_record.file_path):
        raise HTTPException(status_code=404, detail="File missing on server")

    return FileResponse(
        path=file_record.file_path,
        filename=file_record.filename,
        media_type=file_record.mime_type or "application/octet-stream",
    )


def _require_expert_reviewer_for_submission(
    db: Session, submission: Submission, identity: AltAuthUserRecord
) -> None:
    if _effective_alt_role(identity.role) != "expert":
        raise HTTPException(status_code=403, detail="Only competition experts may grade submissions")
    require_permission(identity.role, Permission.REVIEW_SUBMISSIONS)
    if not _expert_gate_ok(identity):
        raise HTTPException(status_code=403, detail="Expert account must be verified by admin before grading")
    if not _is_assigned_competition_expert(db, submission.competition_id, identity.id):
        raise HTTPException(status_code=403, detail="You are not assigned as expert for this competition")


@router.get("/submissions/{submission_id}/review-grade", response_model=ReviewResponse)
async def get_review_grade(
    submission_id: int,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """查询作品评分记录（与 PUT/PATCH 响应体一致）；未评分返回 404。"""
    require_permission(identity.role, Permission.VIEW_COMPETITIONS)
    submission = (
        db.query(Submission)
        .options(joinedload(Submission.review))
        .filter(Submission.id == submission_id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    _ensure_submission_access(db, submission, identity)
    if submission.review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return submission.review


@router.put("/submissions/{submission_id}/review-grade", response_model=ReviewResponse)
async def review_submission(
    submission_id: int,
    grade: ReviewGrade,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """首次评分/审核；已评分请使用 PATCH 同路径修改。"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    _require_expert_reviewer_for_submission(db, submission, identity)

    if submission.review is not None:
        raise HTTPException(status_code=400, detail="Submission already reviewed")

    review = Review(
        submission_id=submission.id,
        reviewer_id=identity.id,
        status=SubmissionStatus.APPROVED,
        score=grade.score,
        feedback=grade.feedback,
        reviewed_at=utc_now(),
    )
    db.add(review)
    submission.status = SubmissionStatus.APPROVED
    db.commit()
    db.refresh(review)
    return review


@router.patch("/submissions/{submission_id}/review-grade", response_model=ReviewResponse)
async def update_review_grade(
    submission_id: int,
    grade: ReviewGrade,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """修改已有评分/反馈；未评分作品请使用 PUT 首次评分。"""
    submission = (
        db.query(Submission)
        .options(joinedload(Submission.review))
        .filter(Submission.id == submission_id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    _require_expert_reviewer_for_submission(db, submission, identity)

    review = submission.review
    if review is None:
        raise HTTPException(status_code=400, detail="Submission not reviewed yet")

    review.score = grade.score
    review.feedback = grade.feedback
    review.reviewed_at = utc_now()
    review.reviewer_id = identity.id
    if submission.status != SubmissionStatus.APPROVED:
        submission.status = SubmissionStatus.APPROVED

    db.commit()
    db.refresh(review)
    return review


@router.get("/{competition_id}/scores/summary", response_model=CompetitionScoreSummaryResponse)
async def score_summary(
    competition_id: int,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """
    竞赛评分汇总（聚合统计）。
    - super_admin：可查看任意竞赛汇总
    - verified expert：仅可查看被指派的竞赛汇总
    """
    require_permission(identity.role, Permission.VIEW_COMPETITIONS)
    _get_competition(db, competition_id)
    if not _can_view_competition_score_insights(db, competition_id, identity):
        raise HTTPException(status_code=403, detail="Not allowed to view scores for this competition")

    submissions_total = db.query(func.count(Submission.id)).filter(Submission.competition_id == competition_id).scalar() or 0
    reviewed_total = (
        db.query(func.count(Review.id))
        .join(Submission, Submission.id == Review.submission_id)
        .filter(Submission.competition_id == competition_id)
        .scalar()
        or 0
    )

    agg = (
        db.query(
            func.avg(Review.score),
            func.max(Review.score),
            func.min(Review.score),
        )
        .join(Submission, Submission.id == Review.submission_id)
        .filter(Submission.competition_id == competition_id)
        .first()
    )

    avg_score = float(agg[0]) if agg and agg[0] is not None else None
    max_score = float(agg[1]) if agg and agg[1] is not None else None
    min_score = float(agg[2]) if agg and agg[2] is not None else None

    return CompetitionScoreSummaryResponse(
        competition_id=competition_id,
        submissions_total=int(submissions_total),
        reviewed_total=int(reviewed_total),
        avg_score=avg_score,
        max_score=max_score,
        min_score=min_score,
    )


@router.get("/{competition_id}/scores/rankings", response_model=CompetitionScoreRankingResponse)
async def score_rankings(
    competition_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """
    排行榜：个人参赛与组队参赛**同一排名池**，按各参赛者（队伍或个人）的 `best_score` 全局排序。
    - 先分别聚合「有评分作品」的队伍与个人，再合并排序；**不在**各自赛道单独截断 limit（避免名次被截断错误）。
    - `limit` 仅作用于合并排序后的最终结果条数。
    """
    require_permission(identity.role, Permission.VIEW_COMPETITIONS)
    _get_competition(db, competition_id)
    if not _can_view_competition_score_insights(db, competition_id, identity):
        raise HTTPException(status_code=403, detail="Not allowed to view rankings for this competition")

    # 队伍参赛：按 team_id 聚合（本竞赛内有已评分作品的所有队伍）
    team_rows = (
        db.query(
            Submission.team_id.label("team_id"),
            func.max(Review.score).label("best_score"),
            func.count(Review.id).label("reviewed_submissions"),
        )
        .join(Review, Review.submission_id == Submission.id)
        .filter(Submission.competition_id == competition_id, Submission.team_id.isnot(None))
        .group_by(Submission.team_id)
        .all()
    )

    # 个人参赛：按 student_id 聚合（team_id 为空）
    individual_rows = (
        db.query(
            Submission.student_id.label("student_id"),
            func.max(Review.score).label("best_score"),
            func.count(Review.id).label("reviewed_submissions"),
        )
        .join(Review, Review.submission_id == Submission.id)
        .filter(Submission.competition_id == competition_id, Submission.team_id.is_(None))
        .group_by(Submission.student_id)
        .all()
    )

    # 合并为统一列表后再排序（同分按队伍优先、再按 id 稳定次序）
    pool: List[Tuple[Optional[int], Optional[int], float, int]] = []
    for r in team_rows:
        pool.append((int(r.team_id), None, float(r.best_score), int(r.reviewed_submissions)))
    for r in individual_rows:
        pool.append((None, int(r.student_id), float(r.best_score), int(r.reviewed_submissions)))

    pool.sort(key=lambda x: (-x[2], 0 if x[0] is not None else 1, x[0] or 0, x[1] or 0))

    items: List[CompetitionScoreRankingItem] = []
    rank_val = 1
    for i, (tid, sid, best, rcnt) in enumerate(pool):
        if i > 0 and best < pool[i - 1][2]:
            rank_val = i + 1
        items.append(
            CompetitionScoreRankingItem(
                rank=rank_val,
                team_id=tid,
                student_id=sid,
                best_score=best,
                reviewed_submissions=rcnt,
            )
        )

    return CompetitionScoreRankingResponse(competition_id=competition_id, items=items[:limit])


@router.get("/{competition_id}/scores/me", response_model=MyCompetitionScoresResponse)
async def my_scores(
    competition_id: int,
    db: Session = Depends(get_db),
    identity: AltAuthUserRecord = Depends(get_current_alt_identity),
):
    """
    学生查看自己在某竞赛的提交与成绩。
    """
    require_permission(identity.role, Permission.VIEW_COMPETITIONS)
    if _effective_alt_role(identity.role) != "student":
        raise HTTPException(status_code=403, detail="Only students can view my scores")

    _get_competition(db, competition_id)
    # 自己个人提交 + 自己所在队伍提交
    team_ids = [tm.team_id for tm in db.query(TeamMember).join(Team).filter(
        TeamMember.user_id == identity.id,
        Team.competition_id == competition_id,
    ).all()]

    q = (
        db.query(Submission)
        .options(joinedload(Submission.review))
        .filter(Submission.competition_id == competition_id)
        .filter(
            (Submission.student_id == identity.id)
            | (Submission.team_id.in_(team_ids) if team_ids else False)  # noqa: E712
        )
    )
    submissions = q.order_by(Submission.submitted_at.desc()).all()
    items: List[SubmissionForStudentScoreResponse] = []
    for s in submissions:
        base = SubmissionResponse.model_validate(s)
        rev = s.review
        items.append(
            SubmissionForStudentScoreResponse(
                **base.model_dump(),
                score=rev.score if rev else None,
                feedback=rev.feedback if rev else None,
                reviewed_at=rev.reviewed_at if rev else None,
            )
        )
    return MyCompetitionScoresResponse(competition_id=competition_id, submissions=items)

