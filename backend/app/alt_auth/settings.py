"""
第二套认证的独立配置项（仅从环境变量读取，不读写 app.config.Settings）。
"""
import os

ALT_AUTH_DATABASE_URL: str = os.getenv(
    "ALT_AUTH_DATABASE_URL",
    "sqlite:///./alt_auth.db",
)

# 与主系统 SECRET_KEY 分离，请勿共用
ALT_AUTH_JWT_SECRET: str = os.getenv(
    "ALT_AUTH_JWT_SECRET",
    "alt-auth-change-this-secret-in-production",
)

ALT_AUTH_JWT_ALGORITHM: str = os.getenv("ALT_AUTH_JWT_ALGORITHM", "HS256")

ALT_AUTH_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("ALT_AUTH_TOKEN_EXPIRE_MINUTES", "1440") or 1440
)

ALT_AUTH_JWT_ISSUER: str = os.getenv("ALT_AUTH_JWT_ISSUER", "llm-aio-alt-auth")
