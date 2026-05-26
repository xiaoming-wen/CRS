"""
竞赛报名系统独立后端入口（自 llm_AIO 复制分离，API 路径与主站一致）。
"""
import logging

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.alt_auth.router import router as alt_identity_router
from app.routers import competitions

load_dotenv()

app = FastAPI(
    title="Competition Registration System API",
    description="竞赛报名、组队、作品提交与评分（独立部署）",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    from app.database import user_engine, UserBase

    import app.models.user as _user_models  # noqa: F401
    import app.models.competition as _competition_models  # noqa: F401

    UserBase.metadata.create_all(bind=user_engine)

    try:
        with user_engine.connect() as conn:
            conn.execute(text("ALTER TABLE competitions ADD COLUMN qr_code_path VARCHAR(512)"))
            conn.commit()
    except Exception:
        pass

    try:
        from app.alt_auth.bootstrap import setup_alt_auth_database

        setup_alt_auth_database(log=logging.getLogger(__name__))
    except Exception as e:
        logging.getLogger(__name__).warning("Alt-auth DB init skipped: %s", e)


app.include_router(alt_identity_router, prefix="/api/alt-identity")
app.include_router(competitions.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "message": "Competition Registration System API",
        "version": "1.0.0",
        "docs_url": "/docs",
    }


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
