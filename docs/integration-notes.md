# 与原项目 gpt-free 的集成关系

## 依赖链（简要）

```
CompetitionRegistrationFullPage
  ├── CompetitionRegistrationSystem → @/api/competition, competitionSubmissionCycle, qrImageValidate, altIdentity
  ├── MyCompetitionEnrollments → competition API + submission cycle
  └── ManuAltIdentityPanel → altIdentity API

competition.js → @/utils/request (axios)
request.js → competitionRequestAuth, altIdentity, store, mutation-types

qrImageValidate → window.jsQR（需在 index.html 加载 public/vendor/jsQR.umd.js）
```

## 主站侧关联（未复制到本目录）

以下文件仍在 `gpt-free` 中，与竞赛模块有耦合：

| 文件 | 作用 |
|------|------|
| `webapps/src/config/router.config.js` | 注册四条 `/manu/competition-*` 路由 |
| `webapps/src/layouts/BasicLayout.vue` | 竞赛全屏页隐藏平台顶栏 |
| `webapps/src/utils/request.js` | 主站 axios；竞赛 API 双 token 逻辑 |
| `webapps/src/views/user/Login.vue` | 主站登录后竞赛独立账号门禁 |
| `webapps/public/index.html` | 引入 `vendor/jsQR.umd.js` |

## 开发代理

原项目 `vue.config.js` 将 `/api` 代理到后端（默认 `http://localhost:8000`）。独立部署时需同样配置 `VUE_APP_API_BASE_URL` 或 devServer proxy。

## 同步副本

若 gpt-free 中竞赛相关文件有更新，可重新执行复制脚本或手动覆盖 `competition-registration-system/webapps` 下对应路径。
