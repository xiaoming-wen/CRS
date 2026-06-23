# 竞赛报名系统（独立工程）

与 `gpt-free`、`llm_AIO` 同级目录，包含：

| 目录 | 说明 |
|------|------|
| `webapps/` | 前端（自 `gpt-free/webapps` 复制分离） |
| `backend/` | 后端（自 `llm_AIO` 复制分离，FastAPI） |

**原 `gpt-free` 与 `llm_AIO` 仓库均未修改。**

---

## 后端

见 [backend/README.md](backend/README.md)。默认 `http://localhost:8000`。

```bash
cd backend
pip install -r requirements.txt
python init_db.py
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 前端

从 `gpt-free/webapps` 分离的竞赛报名模块，可单独 `npm run serve` 运行。

## 快速开始

```bash
cd webapps
npm install
npm run serve
```

浏览器访问：**http://localhost:8010**（默认 hash 路由，首页 `#/manu/competition-list`）

## 环境变量

| 变量 | 说明 |
|------|------|
| `VUE_APP_API_BASE_URL` | API 前缀，开发默认 `/api` |
| `VUE_APP_PROXY_TARGET` | devServer 代理目标，默认 `http://localhost:8000` |

示例（PowerShell）：

```powershell
$env:VUE_APP_PROXY_TARGET="http://192.168.3.238:8000"
npm run serve
```

## 路由

| 路径 | 说明 |
|------|------|
| `/manu/competition-list` | 竞赛列表与报名（入口） |
| `/manu/competition-register` | 独立账号注册 |
| `/manu/competition-detail?id=` | 竞赛详情 |
| `/manu/my-enrollments` | 我的报名 |

## 与 gpt-free 的关系

- 业务源码在 `webapps/src/views/manus`、`api/competition.js` 等，与原项目路径一致。
- 原 `gpt-free` 仓库**未修改**；本工程补齐了 `main.js`、路由、Vuex、Ant Design 等脚手架。
- 开发端口 **8010**，避免与 gpt-free（8002）冲突。

## 构建

```bash
cd webapps
npm run build
```

产物在 `webapps/dist/`。

## 生产部署（域名）

使用 **`www.chaoxiangedu.com`** 对外访问的完整说明（DNS、Nginx、分享链接、API 前缀、检查清单）见：

**[docs/deployment-chaoxiangedu.md](docs/deployment-chaoxiangedu.md)**
