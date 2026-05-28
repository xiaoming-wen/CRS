import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.routers import (
    chat, models, images, audio, video, file_upload, datasets,
    auth, users, resources, user_files, reports, knowledge_base, monitor,
    competitions, exams, llmfactory, code_online, rag_retrieval
)
from app.alt_auth.router import router as alt_identity_router

load_dotenv()

# 创建 FastAPI 应用
app = FastAPI(
    title="Universal Model Playground Gateway & User Management System",
    description="Combined API for AI models and user management",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """初始化数据库表"""
    from sqlalchemy import text
    from convert_url import Base as ConvertBase
    from app.database import convert_engine, UserBase, user_engine

    # 初始化 Convert URL 数据库
    ConvertBase.metadata.create_all(bind=convert_engine)

    # 为已有 training_jobs 表补充 dataset_id、data_type 列（若不存在）
    for col_name in ("dataset_id", "data_type"):
        try:
            with convert_engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE training_jobs ADD COLUMN {col_name} VARCHAR(64)"))
                conn.commit()
        except Exception:
            pass

    # 确保用户库 ORM（含 rag_vector_kb_control 等）已注册到 metadata
    import app.models.user as _user_models_for_metadata  # noqa: F401

    import app.models.competition as _competition_models_for_metadata  # noqa: F401

    # 初始化用户管理数据库
    UserBase.metadata.create_all(bind=user_engine)

    # teams 表扩展（队名、指导老师建队）
    for ts in (
        "ALTER TABLE teams ADD COLUMN name VARCHAR(200)",
        "ALTER TABLE teams ADD COLUMN created_by_advisor_id INTEGER",
    ):
        try:
            with user_engine.connect() as conn:
                conn.execute(text(ts))
                conn.commit()
        except Exception:
            pass

    # competitions 表补列：二维码图片路径（SQLite ALTER 幂等）
    try:
        with user_engine.connect() as conn:
            conn.execute(text("ALTER TABLE competitions ADD COLUMN qr_code_path VARCHAR(512)"))
            conn.commit()
    except Exception:
        pass

    try:
        from app.competition_enrollment_migrate import migrate_competition_enrollment_dual_track

        migrate_competition_enrollment_dual_track(user_engine)
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning("Enrollment dual-track migration skipped: %s", e)

    # 第二套登录/注册：独立 SQLite（默认 ./alt_auth.db），含默认 admin / admin123
    try:
        import logging as _logging

        from app.alt_auth.bootstrap import setup_alt_auth_database

        setup_alt_auth_database(log=_logging.getLogger(__name__))
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning("Alt-auth DB init skipped: %s", e)

    # LangGraph RAG（可选，失败时记录警告，不影响主服务）
    try:
        from app.services.rag import initialize_rag

        initialize_rag()
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning("RAG 启动初始化异常（已忽略）: %s", e)


# 第二套登录/注册须最先注册，避免被 file_upload 的 /api/{file_category}/{file_id} 占坑导致 POST 405
app.include_router(alt_identity_router, prefix="/api/alt-identity")

# 注册路由 - AI 模型服务
app.include_router(chat.router)
app.include_router(models.router)
app.include_router(images.router)
app.include_router(audio.router)
app.include_router(video.router)

app.include_router(file_upload.router)
app.include_router(datasets.router)
app.include_router(llmfactory.router)
app.include_router(code_online.router)

# 注册路由 - 用户管理服务（使用 /api/v1 前缀）
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(resources.router, prefix="/api/v1")
app.include_router(user_files.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(knowledge_base.router, prefix="/api/v1")
app.include_router(rag_retrieval.router, prefix="/api/v1")
app.include_router(monitor.router, prefix="/api/v1")
app.include_router(competitions.router, prefix="/api/v1")
app.include_router(exams.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "message": "Welcome to Universal Model Playground Gateway & User Management System",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Model Playground Gateway & User Management System"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
