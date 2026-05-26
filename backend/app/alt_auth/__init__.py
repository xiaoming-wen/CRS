"""
独立认证模块（第二套登录/注册），与 app.routers.auth 及 User 模型完全隔离。
主应用请使用： ``from app.alt_auth.router import router as alt_identity_router``
"""