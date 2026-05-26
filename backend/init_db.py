"""
竞赛报名独立后端：初始化用户库表结构（含 competitions / files 等）。
"""
from app.database import UserBase, user_engine
import app.models.user  # noqa: F401
from app.models.competition import (  # noqa: F401
    Competition,
    CompetitionEnrollment,
    Team,
    TeamMember,
    Submission,
    Review,
)


def init_db():
    UserBase.metadata.create_all(bind=user_engine)
    print("数据库表已创建（user_management.db，路径见 DATABASE_URL）")


if __name__ == "__main__":
    init_db()
