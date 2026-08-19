"""
竞赛报名系统独立后端入口（自 llm_AIO 复制分离，API 路径与主站一致）。
"""
import logging

from dotenv import load_dotenv

load_dotenv()

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.alt_auth.router import router as alt_identity_router
from app.routers import competitions

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
    from app.database import UserBase, user_engine

    import app.models.user as _user_models  # noqa: F401
    import app.models.competition as _competition_models  # noqa: F401

    UserBase.metadata.create_all(bind=user_engine)

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

    try:
        with user_engine.connect() as conn:
            conn.execute(text("ALTER TABLE competitions ADD COLUMN qr_code_path VARCHAR(512)"))
            conn.commit()
    except Exception:
        pass

    for ts in (
        "ALTER TABLE competitions ADD COLUMN exam_paper_path VARCHAR(512)",
        "ALTER TABLE competitions ADD COLUMN exam_paper_filename VARCHAR(255)",
        "ALTER TABLE competitions ADD COLUMN exam_paper_path_undergraduate VARCHAR(512)",
        "ALTER TABLE competitions ADD COLUMN exam_paper_filename_undergraduate VARCHAR(255)",
        "ALTER TABLE competitions ADD COLUMN exam_paper_path_vocational VARCHAR(512)",
        "ALTER TABLE competitions ADD COLUMN exam_paper_filename_vocational VARCHAR(255)",
    ):
        try:
            with user_engine.connect() as conn:
                conn.execute(text(ts))
                conn.commit()
        except Exception:
            pass

    try:
        from app.competition_division_migrate import migrate_competition_division

        migrate_competition_division(user_engine)
    except Exception as e:
        logging.getLogger(__name__).warning("Competition division migration skipped: %s", e)

    try:
        from app.competition_enrollment_migrate import migrate_competition_enrollment_dual_track

        migrate_competition_enrollment_dual_track(user_engine)
    except Exception as e:
        logging.getLogger(__name__).warning("Enrollment dual-track migration skipped: %s", e)

    try:
        from app.competition_team_review_migrate import migrate_competition_team_review

        migrate_competition_team_review(user_engine)
    except Exception as e:
        logging.getLogger(__name__).warning("Team review migration skipped: %s", e)

    try:
        from app.competition_team_join_request_migrate import migrate_competition_team_join_requests

        migrate_competition_team_join_requests(user_engine)
    except Exception as e:
        logging.getLogger(__name__).warning("Team join request migration skipped: %s", e)

    try:
        from app.competition_stage_migrate import migrate_competition_stage

        migrate_competition_stage(user_engine)
    except Exception as e:
        logging.getLogger(__name__).warning("Competition stage migration skipped: %s", e)

    try:
        from app.competition_expert_team_migrate import migrate_competition_expert_team_assignments

        migrate_competition_expert_team_assignments(user_engine)
    except Exception as e:
        logging.getLogger(__name__).warning("Expert team assignment migration skipped: %s", e)

    try:
        from app.competition_team_question_grade_migrate import migrate_competition_team_question_grades

        migrate_competition_team_question_grades(user_engine)
    except Exception as e:
        logging.getLogger(__name__).warning("Team question grade migration skipped: %s", e)

    for ts in (
        "ALTER TABLE competition_question_answers ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'draft'",
        "ALTER TABLE competition_question_answers ADD COLUMN submitted_at DATETIME NULL",
        "ALTER TABLE competition_enrollments ADD COLUMN work_track VARCHAR(20) NULL",
        "ALTER TABLE teams ADD COLUMN work_track VARCHAR(20) NULL",

    ):
        try:
            with user_engine.connect() as conn:
                conn.execute(text(ts))
                conn.commit()
        except Exception:
            pass

    try:
        from app.alt_auth.bootstrap import setup_alt_auth_database

        setup_alt_auth_database(log=logging.getLogger(__name__))
    except Exception as e:
        logging.getLogger(__name__).warning("Alt-auth DB init skipped: %s", e)

    try:
        from app.alt_auth.database import engine as alt_auth_engine
        from app.eight_digit_id_migrate import run_eight_digit_id_migrations

        run_eight_digit_id_migrations(user_engine, alt_auth_engine)
    except Exception as e:
        logging.getLogger(__name__).warning("8-digit id migration skipped: %s", e)

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
