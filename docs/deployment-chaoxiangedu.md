# 使用 www.chaoxiangedu.com 访问竞赛报名系统

本文说明如何通过域名 **`www.chaoxiangedu.com`** 对外提供竞赛报名系统（前端 + 后端 API），以及各页面的访问地址与分享链接规则。

---

## 1. 系统架构

```
用户浏览器
    ↓  HTTPS
www.chaoxiangedu.com（Nginx）
    ├── /          → 前端静态资源（webapps/dist）
    └── /api/      → 后端 FastAPI（127.0.0.1:8000）
```

- 前端：Vue 2 + **hash 路由**（`#/manu/...`）
- 后端：FastAPI，监听 `8000`，对外经 Nginx 反代到 `/api`
- 独立账号：Alt JWT（`/api/alt-identity`），与主站 token 不可混用
- **竞赛 ID、用户 ID**：均为 8 位数字（`10000000`–`99999999`）

---

## 2. 对外访问地址

浏览器地址格式：

```text
https://www.chaoxiangedu.com/#/路径?参数
```

| 功能 | URL |
|------|-----|
| 竞赛列表与报名（入口） | `https://www.chaoxiangedu.com/#/manu/competition-list` |
| 独立账号注册 | `https://www.chaoxiangedu.com/#/manu/competition-register` |
| 竞赛详情（分享页） | `https://www.chaoxiangedu.com/#/manu/competition-detail?id={8位竞赛ID}&share=1` |
| 双组别 · 本科组 | `...&id={竞赛ID}&division=undergraduate&share=1` |
| 双组别 · 高职组 | `...&id={竞赛ID}&division=vocational&share=1` |
| 我的报名 | `https://www.chaoxiangedu.com/#/manu/my-enrollments` |

**分享链接说明**

- 超级管理员在竞赛列表点「URL」复制；链接自动带 `share=1`。
- 访客打开分享链接默认**未登录**，可查看**已发布 / 已结束**竞赛的详情与二维码。
- 复制链接时须通过 **`https://www.chaoxiangedu.com`** 访问管理端；若用 `localhost` 复制，链接会带本地地址，不适合对外发放。

---

## 3. 部署步骤

### 3.1 DNS

将 `www.chaoxiangedu.com` 的 **A 记录** 指向服务器公网 IP。

（若仅使用 `chaoxiangedu.com` 无 `www`，需在 Nginx `server_name` 中一并配置，或做 301 跳转到统一主域名。）

### 3.2 构建前端

```bash
cd webapps
npm install
npm run build
```

产物目录：`webapps/dist/`（部署到 Nginx `root`）。

生产环境保持 `VUE_APP_API_BASE_URL=/api`（见 `webapps/.env`），前端请求走同域相对路径，无需写死域名。

### 3.3 启动后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

建议使用 systemd / supervisor 常驻进程。启动后本机可验证：

```bash
curl http://127.0.0.1:8000/
```

### 3.4 Nginx 配置示例

将 `root`、证书路径按实际环境修改后启用：

```nginx
server {
    listen 80;
    server_name www.chaoxiangedu.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name www.chaoxiangedu.com;

    ssl_certificate     /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    root /var/www/competition-registration-system/webapps/dist;
    index index.html;

    # 前端（hash 模式 SPA）
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 20m;
    }
}
```

重载 Nginx：

```bash
nginx -t && nginx -s reload
```

### 3.5 后端公网地址（可选）

若二维码图片、作品附件等接口返回的 URL 需被外网直接访问，在 `backend/.env` 配置：

```bash
SERVER_URL=https://www.chaoxiangedu.com
```

竞赛模块在「同域 Nginx 反代 `/api`」场景下，一般可不配；仅当返回资源 URL 出现 `localhost` 时再设置。

---

## 4. API 网关描述（文档 / 对接用）

对外统一前缀：

```text
{API_BASE} = https://www.chaoxiangedu.com
```

| 说明 | 方法 | 路径 |
|------|------|------|
| 健康检查 | GET | `{API_BASE}/`（根路径由后端直接响应时可经反代暴露） |
| 竞赛 API | * | `{API_BASE}/api/v1/competitions/...` |
| 独立账号注册/登录 | * | `{API_BASE}/api/alt-identity/...` |
| 匿名读竞赛详情 | GET | `{API_BASE}/api/v1/competitions/{8位竞赛ID}` |
| 匿名读二维码 | GET | `{API_BASE}/api/v1/competitions/{8位竞赛ID}/qr-code` |

已登录接口须在请求头携带：`Authorization: Bearer <alt_access_token>`。

---

## 5. 上线检查清单

1. 浏览器打开：`https://www.chaoxiangedu.com/#/manu/competition-list`，页面正常加载。
2. 开发者工具 → Network：存在 `/api/...` 请求且状态为 200（非 404/502）。
3. 超级管理员登录后复制分享 URL，确认以 `https://www.chaoxiangedu.com` 开头且含 `share=1`。
4. 未登录打开分享链接，可查看已发布竞赛详情与二维码。
5. 注册、登录、报名、组队等核心流程走通。

---

## 6. 开发与生产对比

| 环境 | 页面地址 | API |
|------|----------|-----|
| 本地开发 | `http://localhost:8010`（见项目 README） | devServer 将 `/api` 代理到 `http://localhost:8000` |
| 生产 | `https://www.chaoxiangedu.com` | 同域 `/api`，由 Nginx 转发至后端 |

本地开发默认不能直接用 `www.chaoxiangedu.com` 访问，除非将域名解析到开发机并配置本地 Nginx 反代。

---

## 7. 常见问题

**Q：分享链接里是 `localhost`，怎么办？**  
A：请用 `https://www.chaoxiangedu.com` 登录管理端后再点「URL」复制；系统按当前浏览器 `origin` 生成完整链接。

**Q：页面能开，但接口 502？**  
A：检查后端是否在 `127.0.0.1:8000` 运行，以及 Nginx `proxy_pass` 是否与后端路径一致（须保留 `/api/` 前缀）。

**Q：HTTPS 证书报错？**  
A：确认 `ssl_certificate` / `ssl_certificate_key` 路径正确，且域名与证书 SAN 匹配。

**Q：上传作品或二维码失败？**  
A：检查 Nginx `client_max_body_size` 是否足够（建议 ≥ 20m），以及后端磁盘目录写权限。
