# 竞赛报名系统（独立后端）

从 `llm_AIO` 复制分离的 FastAPI 后端，API 路径与主站一致，便于对接 `competition-registration-system/webapps` 或 `gpt-free` 前端。

## 快速开始

```bash
cd backend
pip install -r requirements.txt
copy .env.example .env
python init_db.py
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Windows 也可双击 `start.bat`。

- 文档：http://localhost:8000/docs
- 竞赛 API 前缀：`/api/v1/competitions`
- 第二套账号：`/api/alt-identity`（注册/登录，默认 admin / admin123）

## 环境变量

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | 用户库（竞赛表、files），默认 `sqlite:///./user_management.db` |
| `ALT_AUTH_DATABASE_URL` | 第二套账号库，默认 `sqlite:///./alt_auth.db` |
| `API_RESPONSE_DATETIME_TZ` | JSON 时间展示时区，默认 `Asia/Shanghai` |

## 与 llm_AIO 的关系

- 业务源码自 `llm_AIO/app` 原样复制，见 `COPY_MANIFEST_BACKEND.txt`。
- **llm_AIO 未修改**；主站仍可继续挂载同一套路由。
- 上传目录（相对后端工作目录）：`competition_submissions/`、`competition_qr_codes/`。

## 测试

先启动本服务，再执行：

```bash
python tests/test_competitions.py
```

## 前端联调

`competition-registration-system/webapps` 开发代理默认指向 `http://localhost:8000`（`VUE_APP_PROXY_TARGET`）。
