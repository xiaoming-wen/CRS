"""
第二套认证的独立配置项（仅从环境变量读取，不读写 app.config.Settings）。
"""
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

ALT_AUTH_DATABASE_URL: str = os.getenv(
    "ALT_AUTH_DATABASE_URL",
    "mysql+pymysql://root:root@127.0.0.1:3306/competition_alt_auth?charset=utf8mb4",
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

# 阿里云短信（注册验证码）
ALIYUN_SMS_ACCESS_KEY_ID: str = os.getenv("ALIYUN_SMS_ACCESS_KEY_ID", "") or ""
ALIYUN_SMS_ACCESS_KEY_SECRET: str = os.getenv("ALIYUN_SMS_ACCESS_KEY_SECRET", "") or ""
ALIYUN_SMS_SIGN_NAME: str = os.getenv("ALIYUN_SMS_SIGN_NAME", "") or ""
ALIYUN_SMS_TEMPLATE_CODE: str = os.getenv("ALIYUN_SMS_TEMPLATE_CODE", "") or ""
ALIYUN_SMS_TEMPLATE_PARAM_KEY: str = os.getenv("ALIYUN_SMS_TEMPLATE_PARAM_KEY", "code") or "code"
ALIYUN_SMS_REGION_ID: str = os.getenv("ALIYUN_SMS_REGION_ID", "cn-hangzhou") or "cn-hangzhou"
# true：配置不全时仍可发码（仅日志/调试返回），切勿在生产开启
ALIYUN_SMS_DEBUG: bool = (os.getenv("ALIYUN_SMS_DEBUG", "false") or "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
SMS_CODE_TTL_SECONDS: int = int(os.getenv("SMS_CODE_TTL_SECONDS", "300") or 300)
SMS_CODE_RESEND_INTERVAL_SECONDS: int = int(
    os.getenv("SMS_CODE_RESEND_INTERVAL_SECONDS", "60") or 60
)