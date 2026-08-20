from pydantic import BaseModel, Field, EmailStr, PlainSerializer, computed_field, field_validator
from typing import Optional, List, Dict, Any, Annotated
from datetime import datetime
from enum import Enum

from app.datetime_utils import serialize_datetime_for_api_response


# 仅影响 JSON 序列化；展示时区见 API_RESPONSE_DATETIME_TZ（默认 Asia/Shanghai）
UtcDatetime = Annotated[datetime, PlainSerializer(serialize_datetime_for_api_response, when_used="json")]
OptionalUtcDatetime = Annotated[Optional[datetime], PlainSerializer(serialize_datetime_for_api_response, when_used="json")]


class UserRole(str, Enum):
    """第二套竞赛主体角色：教师端已拆为「管理员 / 指导老师 / 专家」，学生不变。"""

    SUPER_ADMIN = "super_admin"
    ADVISOR = "advisor"  # 指导老师
    TEACHER = "teacher"  # 教师（与 advisor 并存）
    EXPERT = "expert"
    STUDENT = "student"


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    role: str
    # 数据库里 full_name 可能为空；登录时不应因为响应模型严格校验而返回 500。
    full_name: Optional[str] = None


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    role: UserRole
    student_id: Optional[str] = None
    teacher_id: Optional[str] = None

    @field_validator("role")
    @classmethod
    def _main_gateway_role_only(cls, v: UserRole) -> UserRole:
        """主网关用户库仅存 super_admin / teacher / student。"""
        if v not in (UserRole.SUPER_ADMIN, UserRole.TEACHER, UserRole.STUDENT):
            raise ValueError("主站注册用户角色仅可为 super_admin、teacher、student")
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: UtcDatetime
    student_id: Optional[str] = None
    teacher_id: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


class ResourceBase(BaseModel):
    name: str
    resource_type: str
    total_amount: float
    unit: str


class ResourceCreate(ResourceBase):
    pass


class ResourceResponse(ResourceBase):
    id: int
    created_at: UtcDatetime
    
    class Config:
        from_attributes = True


class ResourceAllocationBase(BaseModel):
    user_id: int
    resource_id: int
    allocated_amount: float
    expires_at: OptionalUtcDatetime = None
    notes: Optional[str] = None


class ResourceAllocationCreate(ResourceAllocationBase):
    pass


class ResourceAllocationResponse(ResourceAllocationBase):
    id: int
    allocated_at: UtcDatetime
    user: UserResponse
    resource: ResourceResponse
    
    class Config:
        from_attributes = True


class FileBase(BaseModel):
    filename: str
    file_type: str
    description: Optional[str] = None


class FileCreate(FileBase):
    sender_id: Optional[int] = None
    receiver_id: Optional[int] = None
    is_batch: bool = False
    batch_group_id: Optional[str] = None


class FileResponse(FileBase):
    id: int
    file_path: str
    file_size: int
    mime_type: Optional[str]
    sender_id: Optional[int]
    receiver_id: Optional[int]
    is_batch: bool
    batch_group_id: Optional[str]
    created_at: UtcDatetime
    sender: Optional[UserResponse] = None
    receiver: Optional[UserResponse] = None
    
    class Config:
        from_attributes = True


class ReportBase(BaseModel):
    title: str
    description: Optional[str] = None


class ReportCreate(ReportBase):
    student_id: int
    file_id: Optional[int] = None


class ReportResponse(ReportBase):
    id: int
    student_id: int
    teacher_id: Optional[int]
    file_id: Optional[int]
    status: str
    grade: Optional[float]
    feedback: Optional[str]
    submitted_at: UtcDatetime
    graded_at: OptionalUtcDatetime
    student: Optional[UserResponse] = None
    teacher: Optional[UserResponse] = None
    
    class Config:
        from_attributes = True


class ReportGrade(BaseModel):
    grade: float = Field(..., ge=0, le=100)
    feedback: Optional[str] = None


class KnowledgeBaseEntryBase(BaseModel):
    title: str
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class KnowledgeBaseEntryCreate(KnowledgeBaseEntryBase):
    file_id: Optional[int] = None
    uploader_id: int


class KnowledgeBaseEntryResponse(KnowledgeBaseEntryBase):
    id: int
    file_id: Optional[int]
    uploader_id: int
    is_indexed: bool
    created_at: UtcDatetime
    updated_at: UtcDatetime
    uploader: Optional[UserResponse] = None
    
    class Config:
        from_attributes = True


class SystemMetricsResponse(BaseModel):
    gpu_usage: Optional[float] = None
    cpu_usage: float
    storage_used: float
    storage_total: float
    storage_unit: str = "GB"  # 存储单位
    cpu_unit: str = "percent"  # CPU使用率单位
    gpu_unit: Optional[str] = "percent"  # GPU使用率单位
    online_teachers: int
    online_students: int
    timestamp: UtcDatetime


class DashboardMetrics(BaseModel):
    total_teachers: int
    total_students: int
    total_resources: List[Dict[str, Any]]
    recent_activities: List[Dict[str, Any]]
    system_health: SystemMetricsResponse


class BatchFileSend(BaseModel):
    file_type: str
    description: Optional[str] = None
    receiver_ids: List[int]
    is_batch: bool = True


# ---------- llmfactory 微调/合并 接口 Schema ----------


class LoraTrainRequest(BaseModel):
    """LoRA 微调请求。路径类参数不传时使用 .env 中的默认值。dataset_id 优先于 dataset/dataset_dir"""
    model_id: Optional[str] = Field(None, description="本地模型 id（来自 GET /api/playground/llmfactory/models），与 model_path 二选一")
    model_path: Optional[str] = Field(None, description="基础模型路径（与 model_id 二选一，仅服务端可信时使用）")
    dataset_id: Optional[str] = Field(None, description="已上传训练集 ID（优先使用）")
    dataset: Optional[str] = Field(None, description="数据集名称，逗号分隔多个")
    dataset_dir: Optional[str] = Field(None, description="数据集目录路径")
    output_dir: Optional[str] = Field(None, description="输出目录路径")
    template: str = Field(default="qwen3_nothink", description="模型模板")
    lora_rank: int = Field(default=8, ge=1, le=128, description="LoRA rank")
    lora_target: str = Field(default="all", description="LoRA 目标模块")
    learning_rate: float = Field(default=1e-4, gt=0, description="学习率")
    num_train_epochs: float = Field(default=5.0, gt=0, description="训练轮数")
    bf16: bool = Field(
        default=False,
        description="是否使用 BF16。默认 False 以规避部分 GPU 的 CUBLAS_STATUS_INVALID_VALUE；设为 true 可提升兼容 BF16 的机器上的速度",
    )
    deepspeed_config: Optional[str] = Field(None, description="DeepSpeed 配置文件路径")


class QLoraTrainRequest(BaseModel):
    """QLoRA 微调请求（量化 + LoRA，省显存）。dataset_id 优先于 dataset/dataset_dir"""
    model_id: Optional[str] = Field(None, description="本地模型 id（来自 GET /api/playground/llmfactory/models），与 model_path 二选一")
    model_path: Optional[str] = Field(None, description="基础模型路径（与 model_id 二选一）")
    dataset_id: Optional[str] = Field(None, description="已上传训练集 ID（优先使用）")
    dataset: Optional[str] = Field(None, description="数据集名称，逗号分隔多个")
    dataset_dir: Optional[str] = Field(None, description="数据集目录路径")
    output_dir: Optional[str] = Field(None, description="输出目录路径")
    template: str = Field(default="qwen3_nothink", description="模型模板")
    lora_rank: int = Field(default=8, ge=1, le=128, description="LoRA rank")
    lora_target: str = Field(default="all", description="LoRA 目标模块")
    quantization_bit: int = Field(default=4, description="量化位数，常用 4 或 8")
    quantization_method: str = Field(default="bnb", description="量化方法: bnb, hqq, eetq")
    double_quantization: bool = Field(default=False, description="是否使用双重量化(仅 bnb)")
    learning_rate: float = Field(default=1e-4, gt=0, description="学习率")
    num_train_epochs: float = Field(default=5.0, gt=0, description="训练轮数")
    bf16: bool = Field(
        default=False,
        description="是否使用 BF16。默认 False 以规避部分 GPU 的 CUBLAS_STATUS_INVALID_VALUE；设为 true 可提升兼容 BF16 的机器上的速度",
    )
    deepspeed_config: Optional[str] = Field(None, description="DeepSpeed 配置文件路径")


class FullTrainRequest(BaseModel):
    """全量微调请求。与 LoRA 相同：一、使用已上传训练集（dataset_id）；二、使用本地 dataset / dataset_dir。模型为 model_id 或 model_path 二选一。"""
    model_id: Optional[str] = Field(None, description="本地模型 id（来自 GET /api/playground/llmfactory/models），与 model_path 二选一")
    model_path: Optional[str] = Field(None, description="基础模型路径（与 model_id 二选一）")
    dataset_id: Optional[str] = Field(None, description="已上传训练集 ID（优先使用）")
    dataset: Optional[str] = Field(None, description="数据集名称")
    dataset_dir: Optional[str] = Field(None, description="数据集目录路径")
    output_dir: Optional[str] = Field(None, description="输出目录路径")
    template: str = Field(default="qwen3_nothink", description="模型模板")
    learning_rate: float = Field(default=1e-4, gt=0, description="学习率")
    num_train_epochs: float = Field(default=1.0, gt=0, description="训练轮数")
    bf16: bool = Field(
        default=False,
        description="是否使用 BF16。默认 False 以规避部分 GPU 的 CUBLAS_STATUS_INVALID_VALUE；设为 true 可提升兼容 BF16 的机器上的速度",
    )
    gradient_accumulation_steps: int = Field(default=2, ge=1, description="梯度累积步数")
    deepspeed_config: Optional[str] = Field(None, description="DeepSpeed 配置文件路径")


class MergeAdapterRequest(BaseModel):
    """合并适配器请求。路径类参数不传时使用 .env 中的默认值"""
    model_id: Optional[str] = Field(None, description="本地模型 id（来自 GET /api/playground/llmfactory/models），与 model_path 二选一")
    model_path: Optional[str] = Field(None, description="基础模型路径（与 model_id 二选一）")
    adapter_path: Optional[str] = Field(None, description="task_id（来自 GET /train/jobs）或微调目录名（来自 GET /trained-models，如 Qwen2-0.5B_lora_20260311_142141）；服务端解析到 train_output/SFT 下，禁止传入任意服务器路径")
    export_dir: Optional[str] = Field(None, description="合并后模型导出目录")
    template: str = Field(default="qwen3_nothink", description="模型模板")
    export_size: int = Field(default=5, ge=1, description="单文件导出大小(GB)")
    export_device: str = Field(default="auto", description="导出设备: cpu/auto")


class StartInferenceApiRequest(BaseModel):
    """启动推理 API 服务请求。model_path 不传时使用 .env 默认值"""
    model_id: Optional[str] = Field(None, description="本地模型 id（来自 GET /api/playground/llmfactory/models），与 model_path 二选一")
    model_path: Optional[str] = Field(None, description="模型路径（与 model_id 二选一）")
    adapter_path: Optional[str] = Field(None, description="LoRA 适配器路径（可选）")
    template: str = Field(
        default="auto",
        description="模型模板，需在 GET .../templates 列表中。传 auto 或不传时按模型 config.json 的 model_type 自动选择",
    )
    api_port: str = Field(default="8001", description="已弃用：推理已整合到 8000 端口，此字段保留兼容")
    cuda_devices: str = Field(default="0", description="CUDA 设备 ID")
    bf16: bool = Field(
        default=False,
        description="设为 true 时传 --infer_dtype bfloat16；默认 false 且未传 infer_dtype 时不传 infer_dtype，由 LLaMA-Factory 默认(auto)",
    )
    infer_dtype: Optional[str] = Field(
        None,
        description="推理精度，可选: auto, float16, bfloat16, float32。不传且 bf16 为 false 时不传参，与修改前行为一致",
    )


class LlmFactoryTaskResponse(BaseModel):
    """llmfactory 任务响应"""
    success: bool
    message: str
    return_code: Optional[int] = None
    job_id: Optional[str] = Field(None, description="训练任务 ID，用于 GET /train/jobs 查询该任务状态")


class TrainingJobItem(BaseModel):
    """单条训练任务（用于列表）"""
    id: str
    output_dir: str
    task_type: str  # lora, qlora, full
    status: str  # running, success, failed
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    download_url: Optional[str] = Field(None, description="仅当 status=success 且可下载时返回，用于保存到用户本地")
    dataset_id: Optional[str] = Field(None, description="训练使用的数据集 ID")
    data_type: Optional[str] = Field(None, description="训练集类型，如 text_conversation")


class TrainingProgressResponse(BaseModel):
    """微调任务进度（供前端轮询展示）。数据来自 output_dir 下的 trainer_state.json（HuggingFace Trainer）。"""

    job_id: str
    task_type: str
    job_status: str = Field(..., description="数据库中的任务状态: running / success / failed")
    model_display_name: str = Field(
        ...,
        description="用于前端展示：与 output_dir 末级目录名相同，如 Qwen3-0.6B_lora_20260323_102510（与已训练模型目录名一致）",
    )
    output_dir: str
    error_message: Optional[str] = Field(None, description="任务失败时的错误摘要（与列表接口一致）")
    trainer_state_found: bool = Field(..., description="是否成功读取到 trainer_state.json")
    global_step: Optional[int] = None
    max_steps: Optional[int] = None
    epoch: Optional[float] = None
    num_train_epochs: Optional[float] = Field(
        None, description="若存在 training_args.json 则填充，用于与 epoch 估算进度"
    )
    latest_loss: Optional[float] = None
    learning_rate: Optional[float] = Field(None, description="与 latest_loss 同一条 log 中的学习率")
    progress_ratio: Optional[float] = Field(
        None, description="0~1；优先 global_step/max_steps，否则 epoch/num_train_epochs"
    )
    log_history: Optional[List[Dict[str, Any]]] = Field(
        None, description="trainer_state.log_history 尾部，含 loss、learning_rate、epoch、step 等"
    )
    best_model_checkpoint: Optional[str] = None
    message: Optional[str] = Field(None, description="无状态文件或异常时的说明")


# ---------- QLoRA 兼容性检测 ----------


class QLoRASupportCheckRequest(BaseModel):
    """检查某个模型是否支持 QLoRA（用于训练前置校验）。model_id 与 model_path 二选一。"""

    model_id: Optional[str] = Field(None, description="本地模型 id（来自 GET /api/playground/llmfactory/models），与 model_path 二选一")
    model_path: Optional[str] = Field(None, description="基础模型路径（与 model_id 二选一）")


class QLoRASupportCheckResponse(BaseModel):
    """QLoRA 兼容性检查结果。supported=false 时 reasons 给出原因。"""

    supported: bool
    reasons: List[str] = Field(default_factory=list)
    detected: Dict[str, Any] = Field(default_factory=dict)


# ---------- 竞赛报名系统（Competition） ----------

class CompetitionStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class TeamStatus(str, Enum):
    ACTIVE = "active"
    DISBANDED = "disbanded"


class CompetitionEnrollmentStatus(str, Enum):
    ENROLLED = "enrolled"
    WITHDRAWN = "withdrawn"


class CompetitionEnrollmentScope(str, Enum):
    INDIVIDUAL = "individual"
    TEAM = "team"


class CompetitionDivisionMode(str, Enum):
    SINGLE = "single"
    DUAL = "dual"


class CompetitionQrLayout(str, Enum):
    SHARED = "shared"
    SEPARATE = "separate"


class CompetitionDivision(str, Enum):
    DEFAULT = "default"
    UNDERGRADUATE = "undergraduate"
    VOCATIONAL = "vocational"


class CompetitionQrSlot(BaseModel):
    path: Optional[str] = None
    image_url: Optional[str] = None


class CompetitionQrCodes(BaseModel):
    shared: Optional[CompetitionQrSlot] = None
    undergraduate: Optional[CompetitionQrSlot] = None
    vocational: Optional[CompetitionQrSlot] = None


class CompetitionExamPaperSlot(BaseModel):
    published: bool = False
    filename: Optional[str] = None
    download_url: Optional[str] = None


class CompetitionExamPapers(BaseModel):
    """按组别试卷元信息（不暴露本地路径）。"""
    default: Optional[CompetitionExamPaperSlot] = None
    undergraduate: Optional[CompetitionExamPaperSlot] = None
    vocational: Optional[CompetitionExamPaperSlot] = None


class SubmissionStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class CompetitionBase(BaseModel):
    name: str
    description: Optional[str] = None
    rules_text: Optional[str] = None
    start_at: OptionalUtcDatetime = None
    end_at: OptionalUtcDatetime = None
    allow_individual: bool = False
    allow_team: bool = True


class CompetitionCreate(CompetitionBase):
    division_mode: CompetitionDivisionMode = Field(
        CompetitionDivisionMode.SINGLE,
        description="single=不分本科/高职；dual=分本科组与高职组",
    )
    qr_layout: CompetitionQrLayout = Field(
        CompetitionQrLayout.SHARED,
        description="dual 时有效：shared=两组共用一个码；separate=各传一张",
    )


class CompetitionUpdate(BaseModel):
    """修改竞赛（所有字段可选，只传需要改的）"""
    name: Optional[str] = None
    description: Optional[str] = None
    rules_text: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    allow_individual: Optional[bool] = None
    allow_team: Optional[bool] = None
    division_mode: Optional[CompetitionDivisionMode] = None
    qr_layout: Optional[CompetitionQrLayout] = None


class CompetitionResponse(CompetitionBase):
    id: int
    status: CompetitionStatus = CompetitionStatus.DRAFT
    created_at: UtcDatetime
    updated_at: UtcDatetime
    division_mode: CompetitionDivisionMode = CompetitionDivisionMode.SINGLE
    qr_layout: CompetitionQrLayout = CompetitionQrLayout.SHARED
    qr_code_path: Optional[str] = Field(None, description="共用/单组别二维码相对路径")
    qr_code_path_undergraduate: Optional[str] = Field(None, description="本科组二维码（dual+separate）")
    qr_code_path_vocational: Optional[str] = Field(None, description="高职组二维码（dual+separate）")
    qr_codes: Optional[CompetitionQrCodes] = Field(
        None,
        description="结构化二维码下载地址（详情页按组别取用）",
    )
    qr_code_image_url: Optional[str] = Field(
        None,
        description="兼容字段：single 或 dual+shared 时的二维码 URL",
    )
    logo_path: Optional[str] = Field(None, description="竞赛 Logo 相对路径")
    logo_image_url: Optional[str] = Field(
        None,
        description="竞赛 Logo 下载地址（有上传时）",
    )
    exam_papers: Optional[CompetitionExamPapers] = Field(
        None,
        description="各组别试卷是否已发布及下载地址（元信息）",
    )

    class Config:
        from_attributes = True


class CompetitionEnrollmentCreate(BaseModel):
    competition_id: int
    # team_id 为空表示“个人参赛”
    team_id: Optional[int] = None
    division: Optional[CompetitionDivision] = Field(
        None,
        description="学历组别；dual 竞赛必填（由详情页隐式传入）。undergraduate / vocational",
    )

    # 参赛学生信息（报名时填写）
    student_no: Optional[str] = None       # 学号
    real_name: Optional[str] = None        # 姓名
    college: Optional[str] = None          # 学院
    grade: Optional[str] = None            # 年级，如 "2023级"
    contact: Optional[str] = None          # 联系方式（手机/邮箱）


class CompetitionEnrollmentResponse(BaseModel):
    """报名记录。`id` 为全库主键（全局自增）；`sequence_no` 为便于展示的「本竞赛内赛道序号」。"""
    id: int
    competition_id: int
    student_id: int = Field(
        ...,
        description="竞赛主体 id，即 alt_auth_users.id（非主库 users.id）",
    )
    team_id: Optional[int] = None
    enrollment_scope: CompetitionEnrollmentScope = Field(
        ...,
        description="报名赛道：individual=个人；team=组队（可与个人赛道同时存在）",
    )
    division: CompetitionDivision = Field(
        CompetitionDivision.DEFAULT,
        description="学历组别：default / undergraduate / vocational",
    )
    is_captain: bool

    student_no: Optional[str] = None
    real_name: Optional[str] = None
    college: Optional[str] = None
    grade: Optional[str] = None
    contact: Optional[str] = None

    status: CompetitionEnrollmentStatus
    created_at: UtcDatetime
    sequence_no: Optional[int] = Field(
        None,
        description="本竞赛内序号：个人参赛=个人赛道第 N 位报名者；组队参赛=第 N 支队伍（与全局 id 无关）",
    )

    class Config:
        from_attributes = True


class MyEnrollmentResponse(BaseModel):
    """学生查看自己报名的竞赛（报名信息 + 竞赛详情）"""
    id: int
    competition_id: int
    student_id: int = Field(
        ...,
        description="竞赛主体 id，即 alt_auth_users.id",
    )
    team_id: Optional[int] = None
    enrollment_scope: CompetitionEnrollmentScope
    is_captain: bool

    student_no: Optional[str] = None
    real_name: Optional[str] = None
    college: Optional[str] = None
    grade: Optional[str] = None
    contact: Optional[str] = None

    status: CompetitionEnrollmentStatus
    created_at: datetime

    competition: Optional[CompetitionResponse] = None

    class Config:
        from_attributes = True


class TeamCreate(BaseModel):
    competition_id: int
    division: Optional[CompetitionDivision] = Field(
        None,
        description="学历组别；dual 竞赛必填，须与详情页所选组别一致",
    )
    # 若不传/传空则由服务端逻辑创建成员并设为队长（学生自建队通常为本人）
    initial_member_ids: Optional[List[int]] = None
    name: Optional[str] = Field(None, max_length=200, description="队名（展示用），可由队长后续修改")
    captain_student_id: Optional[int] = Field(
        None,
        description="指导老师建队时可指定队长 user_id；若填写 initial_member_ids 则须出现在列表中；未填初始队员时必须提供本字段",
    )


class TeamResponse(BaseModel):
    id: int
    competition_id: int
    name: Optional[str] = None
    division: CompetitionDivision = CompetitionDivision.DEFAULT
    captain_id: int
    status: TeamStatus
    created_at: UtcDatetime

    class Config:
        from_attributes = True


class TeamPatch(BaseModel):
    """修改队名等（队长或指导老师建队者可操作）"""

    name: Optional[str] = Field(None, max_length=200)


class TeamInviteMember(BaseModel):
    student_id: int = Field(..., description="加入队伍的 alt_auth 学生主体 id")


class TeamMemberResponse(BaseModel):
    id: int
    team_id: int
    user_id: int
    is_captain: bool
    joined_at: UtcDatetime

    class Config:
        from_attributes = True


class TeamDetailResponse(BaseModel):
    """队伍详情（含成员列表），用于查看竞赛下所有队伍"""
    id: int
    competition_id: int
    name: Optional[str] = None
    captain_id: int
    status: TeamStatus
    created_at: UtcDatetime
    members: List[TeamMemberResponse] = []

    class Config:
        from_attributes = True


class IndividualParticipantItem(BaseModel):
    """某竞赛下「个人赛道」有效报名列表（不含组队成员）。"""
    sequence_no: int = Field(..., description="本竞赛个人赛道内序号，从 1 起，按报名时间升序")
    enrollment_id: int = Field(..., description="报名记录主键（全局）")
    student_id: int = Field(..., description="alt_auth_users.id")
    username: str
    full_name: Optional[str] = None
    student_no: Optional[str] = None
    real_name: Optional[str] = None
    college: Optional[str] = None
    grade: Optional[str] = None
    contact: Optional[str] = None
    status: CompetitionEnrollmentStatus
    created_at: UtcDatetime


class TeamMemberWithUserResponse(BaseModel):
    """队伍成员 + 第二套帐号展示信息"""
    id: int
    team_id: int
    user_id: int = Field(..., description="alt_auth_users.id")
    username: str
    full_name: Optional[str] = None
    is_captain: bool
    joined_at: UtcDatetime


class TeamParticipantDetailResponse(BaseModel):
    """某竞赛下「组队赛道」一支队伍及成员（带本竞赛内队伍序号）。"""
    sequence_no: int = Field(..., description="本竞赛组队赛道内队伍序号，从 1 起，按队伍创建时间升序")
    id: int
    competition_id: int
    name: Optional[str] = None
    captain_id: int
    status: TeamStatus
    created_at: UtcDatetime
    members: List[TeamMemberWithUserResponse] = Field(default_factory=list)


class CompetitionExpertAssignedTeam(BaseModel):
    """专家在某竞赛下被指派的队伍。"""

    competition_id: int
    team_id: int
    team_name: Optional[str] = None


class CompetitionExpertAssignRequest(BaseModel):
    """指派专家到竞赛下的队伍（至少一支）。"""

    team_ids: List[int] = Field(..., min_length=1, description="该竞赛下至少一支队伍 id")


class CompetitionExpertListItem(BaseModel):
    """第二套帐号中 role=expert 的专家条目。"""

    expert_user_id: int
    username: str = ""
    email: Optional[str] = None
    full_name: Optional[str] = None
    school: Optional[str] = None
    expert_verified: bool = False
    assigned_competition_ids: List[int] = Field(
        default_factory=list,
        description="该专家已被指派的竞赛 id 列表（可多场；空列表表示尚未指派任何竞赛）",
    )
    assigned_teams: List[CompetitionExpertAssignedTeam] = Field(
        default_factory=list,
        description="该专家已被指派可评阅的队伍（按竞赛+队伍）",
    )


class CompetitionExpertsListResponse(BaseModel):
    """全部专家帐号（管理员专家管理列表）。"""

    total: int
    items: List[CompetitionExpertListItem] = Field(default_factory=list)


class AltUserAdminPatch(BaseModel):
    """竞赛管理员变更第二套用户角色或专家资质（仅限 super_admin 调用）。"""

    role: Optional[UserRole] = None
    expert_verified: Optional[bool] = None


class AltUserAdminUpdateResult(BaseModel):
    id: int
    role: str
    expert_verified: bool


class TeamMemberCreate(BaseModel):
    competition_id: int
    team_id: int


class TeamTransferCaptain(BaseModel):
    team_id: int
    new_captain_id: int = Field(..., description="新队长在 team_members 中的 user_id，即 alt_auth_users.id")


class SubmissionCreate(BaseModel):
    competition_id: int
    # team_id 为空表示个人提交；不为空表示队伍提交
    team_id: Optional[int] = None
    division: Optional[CompetitionDivision] = Field(
        None,
        description="学历组别；dual 竞赛必填（undergraduate / vocational），与详情页及报名一致",
    )
    title: str
    description: Optional[str] = None

    # 二选一：file_id（复用已有 files 表） 或 content_text（纯文本）
    file_id: Optional[int] = None
    content_text: Optional[str] = None


class SubmissionCreateWrapped(BaseModel):
    """
    兼容部分前端误用：把 `POST /submissions` 的 JSON 包在 `payload` 里
    （与 `multipart` 上传里常见字段名一致，易混淆）。
    """

    payload: SubmissionCreate


class SubmissionResponse(BaseModel):
    id: int
    competition_id: int
    team_id: Optional[int] = None
    division: CompetitionDivision = Field(
        CompetitionDivision.DEFAULT,
        description="学历组别，与 POST 提交作品时传入并落库的 division 一致",
    )
    student_id: int = Field(..., description="个人赛道归属：alt_auth_users.id")
    submitter_id: int = Field(..., description="提交操作者：alt_auth_users.id")
    title: str
    description: Optional[str] = None
    file_id: Optional[int] = None
    content_text: Optional[str] = None
    status: SubmissionStatus
    submitted_at: UtcDatetime

    class Config:
        from_attributes = True


class SubmissionForStudentScoreResponse(SubmissionResponse):
    """学生「我的成绩」：在作品字段上附加评审计分（与 Review 表一致；未评分时为 null）。"""

    score: Optional[float] = Field(
        default=None,
        description="成绩：与 PUT/PATCH .../review-grade 请求体 score 及 Review.score 一致；未审核时为 null",
    )
    feedback: Optional[str] = Field(default=None, description="评委反馈；未审核时为 null")
    reviewed_at: OptionalUtcDatetime = Field(default=None, description="评分时间；未审核时为 null")


class ReviewGrade(BaseModel):
    score: float
    feedback: Optional[str] = None


class ReviewResponse(BaseModel):
    id: int
    submission_id: int
    reviewer_id: int = Field(..., description="评委：alt_auth_users.id")
    status: SubmissionStatus
    score: Optional[float] = None
    feedback: Optional[str] = None
    reviewed_at: OptionalUtcDatetime = None

    class Config:
        from_attributes = True


class CompetitionScoreSummaryResponse(BaseModel):
    competition_id: int
    submissions_total: int
    reviewed_total: int
    avg_score: Optional[float] = None
    max_score: Optional[float] = None
    min_score: Optional[float] = None


class CompetitionScoreRankingItem(BaseModel):
    """
    排行榜一行：个人与队伍**同一排名池**，按 `best_score` 统一排序后的名次见 `rank`。
    - `team_id` 非空：组队参赛（以队伍为单位）
    - `team_id` 为空且 `student_id` 非空：个人参赛（以学生为单位）
    """

    rank: int = Field(..., description="统一排名名次（同分并列同名次，下一名次跳过；仅对已产生评分的参赛者）")
    team_id: Optional[int] = None
    student_id: Optional[int] = None
    best_score: float
    reviewed_submissions: int


class CompetitionScoreRankingResponse(BaseModel):
    competition_id: int
    items: List[CompetitionScoreRankingItem]


class MyCompetitionScoresResponse(BaseModel):
    competition_id: int
    submissions: List[SubmissionForStudentScoreResponse]


# ---------- 考试模块（Exam） ----------

class QuestionBankItemCreate(BaseModel):
    question_type: str  # single/multiple/true_false
    stem: str
    options: Optional[List[dict]] = None
    correct_answer: Any
    score: float = Field(default=1.0, gt=0)


class QuestionBankItemResponse(BaseModel):
    id: int
    created_by: int
    question_type: str
    stem: str
    options: Optional[Any] = None
    correct_answer: Any
    score: float
    is_active: bool
    created_at: UtcDatetime
    updated_at: UtcDatetime

    class Config:
        from_attributes = True


class ExamCreate(BaseModel):
    competition_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    start_at: OptionalUtcDatetime = None
    end_at: OptionalUtcDatetime = None
    duration_minutes: int = Field(default=60, ge=1, le=600)
    question_ids: List[int]


class ExamResponse(BaseModel):
    id: int
    competition_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: str
    start_at: OptionalUtcDatetime = None
    end_at: OptionalUtcDatetime = None
    duration_minutes: int
    created_by: int
    created_at: UtcDatetime
    updated_at: UtcDatetime

    class Config:
        from_attributes = True


class ExamPublishResponse(BaseModel):
    exam_id: int
    status: str


class ExamAttemptStartResponse(BaseModel):
    attempt_id: int
    status: str


class ExamAnswerSubmitItem(BaseModel):
    question_id: int
    answer: Any


class ExamSubmitRequest(BaseModel):
    answers: List[ExamAnswerSubmitItem]


class ExamAttemptResponse(BaseModel):
    id: int
    exam_id: int
    user_id: int
    status: str
    started_at: UtcDatetime
    submitted_at: OptionalUtcDatetime = None
    graded_at: OptionalUtcDatetime = None
    total_score: Optional[float] = None

    class Config:
        from_attributes = True


class ExamAnswerResponse(BaseModel):
    id: int
    attempt_id: int
    question_id: int
    answer: Any
    is_correct: Optional[bool] = None
    earned_score: Optional[float] = None

    class Config:
        from_attributes = True


class ExamAttemptDetailResponse(ExamAttemptResponse):
    answers: List[ExamAnswerResponse] = Field(default_factory=list)
