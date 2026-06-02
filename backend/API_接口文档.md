# 统一网关 API 文档

## 📋 目录

1. [快速开始](#快速开始)
2. [认证与授权](#认证与授权)
3. [AI 模型服务 API](#ai-模型服务-api)
4. [用户管理服务 API](#用户管理服务-api)
5. [数据模型](#数据模型)
6. [错误处理](#错误处理)
7. [前端集成示例](#前端集成示例)

---

## 快速开始

### 基础信息

- **Base URL**: `http://localhost:8000`
- **API 文档**: `http://localhost:8000/docs` (Swagger UI)
- **健康检查**: `http://localhost:8000/health`
- **通信协议**: HTTP/1.1, SSE (Server-Sent Events)
- **数据格式**: JSON
- **日期时间**：内部以 UTC 存储。响应中的 `datetime` 字符串由环境变量 **`API_RESPONSE_DATETIME_TZ`** 决定：默认 **`Asia/Shanghai`** 时为北京时间（例：`2026-03-20T09:47:36.957025+08:00`）；设为 **`UTC`** 时为 UTC（例：`...Z`）。请求体中的时间字段建议带时区（`Z` 或 `+08:00`）。

### API 路径前缀

- **AI 模型服务**: `/api/playground/*` (无需认证)
- **用户管理服务**: `/api/v1/*` (需要 JWT Token 认证)
- **文件上传服务**: `/api/{file_category}/*` (无需认证)

### 环境配置

API 密钥需要在后端 `.env` 文件中配置：

```env
# 阿里云 DashScope
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx

# DeepSeek
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx

# 豆包 (Volcengine)
VOLCENGINE_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# 讯飞语音转写 (Xunfei Lfasr)
XUNFEI_APP_ID=xxxxxxxx
XUNFEI_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 文件存储配置
STORAGE_TYPE=local  # 或 'oss'
SERVER_URL=http://localhost:8000  # ⚠️ 重要：如果大模型API需要访问文件，必须配置公网可访问的地址

# OSS 配置（仅当 STORAGE_TYPE=oss 时需要）
OSS_ENDPOINT=your_oss_endpoint
OSS_ACCESS_KEY_ID=your_access_key_id
OSS_ACCESS_KEY_SECRET=your_access_key_secret
OSS_BUCKET_NAME=your_bucket_name
OSS_REGION=your_oss_region

# 用户管理系统配置
SECRET_KEY=your-secret-key-here-change-in-production
DATABASE_URL=sqlite:///./user_management.db
ACCESS_TOKEN_EXPIRE_MINUTES=30

# llmfactory 微调集成（可选）
LLMFACTORY_COMMAND_PREFIX=   # llamafactory-cli 所在目录，留空则自动检测
# 模型/数据集/输出路径请在每次 API 请求中显式传入
```

**⚠️ 重要提示：文件 URL 配置**

如果上传文件后需要将 URL 传给大模型 API，必须确保 URL 是**公网可访问**的：

- ❌ **不能使用**: `http://localhost:8000/api/video/xxx`（大模型 API 无法访问本地地址）
- ✅ **可以使用**:
  - 公网 IP: `http://123.456.789.0:8000/api/video/xxx`
  - 域名: `http://your-domain.com/api/video/xxx`
  - OSS 存储: 自动生成公网可访问的 URL（推荐）

---

## 认证与授权

本服务存在 **两套互不兼容** 的 JWT：主站用户库与第二套独立库。请按所调用的 API 前缀选用对应登录与刷新接口，**禁止混用 Token**。

### 用户管理服务认证（主站）

用户管理服务的所有接口（`/api/v1/*`）需要 **主站** JWT Bearer Token 认证。

#### 认证流程

1. **注册 / 登录获取 Token**
   - 注册：`POST /api/v1/auth/register`（JSON）
   - 登录：`POST /api/v1/auth/login`（`application/x-www-form-urlencoded`，字段 `username`、`password`）

2. **在请求头中携带 Token**
   ```
   Authorization: Bearer <access_token>
   ```

3. **Token 过期后刷新**
   ```javascript
   POST /api/v1/auth/refresh-token
   ```
   需在请求头携带当前有效主站 `access_token`（与登录响应字段一致）。

### 第二套独立登录（Alt Identity）

适用于 **`/api/alt-identity/*`**；**以及** **`/api/v1/competitions/*`** 竞赛报名全链路（鉴权、报名与作品中的 `student_id` / `user_id` / `captain_id` / `reviewer_id` 等均为 **`alt_auth_users.id`**，与主库 `users` 无关）。其它 **`/api/v1/*`**（用户管理、文件收发、考试等）仍须使用主站 JWT。

#### 认证流程（与主站步骤对应）

1. **注册 / 登录获取 Token**
   - 注册：`POST /api/alt-identity/register`（JSON；字段与主站注册对齐并多 **`school`**，见下文 **§8.0**）
   - 登录：`POST /api/alt-identity/session`（JSON：`username`、`password`）

2. **在请求头中携带 Token**（与主站相同写法，但值为 **第二套** 登录返回的 `access_token`）
   ```
   Authorization: Bearer <access_token>
   ```

3. **Token 过期后刷新**
   ```javascript
   POST /api/alt-identity/refresh-token
   ```
   需在请求头携带当前有效 **第二套** `access_token`。响应体与登录一致（含 `school` 等字段）。

#### 角色说明

| 角色 | 说明 | 权限范围 |
|------|------|----------|
| `super_admin` | 超级管理员 | 所有权限 |
| `teacher` | 教师 | 管理学生、批改报告、上传知识库等 |
| `student` | 学生 | 提交报告、接收文件、查看知识库 |
#### 默认管理员账户

以下凭据在 **主站**（`/api/v1/auth/*`，用户库）与 **第二套独立登录**（`/api/alt-identity/*`，独立库 `alt_auth.db`）首次初始化时保持一致；第二套仅在库中 **尚不存在用户名为 `admin` 的帐号** 时由服务端或 `python init_db.py` 自动写入，**不会覆盖**已存在的 `admin` 密码。

- **用户名**: `admin`
- **密码**: `admin123`
- **⚠️ 首次登录后请立即修改密码！**


---

## AI 模型服务 API

> **注意**: AI 模型服务无需认证，API 密钥在后端配置。

### 1. 系统接口

#### 1.1 健康检查

**端点**: `GET /health`

**描述**: 检查服务是否正常运行

**权限**: 无需认证

**响应示例** (200 OK):
```json
{
  "status": "ok",
  "service": "Model Playground Gateway & User Management System"
}
```

---

#### 1.2 获取模型列表

**端点**: `GET /api/playground/models`

**描述**: 获取所有可用的模型及其配置参数

**权限**: 无需认证

**响应示例** (200 OK):
```json
{
  "models": [
    {
      "id": "qwen-max",
      "type": "text",
      "provider": "aliyun",
      "description": "通义千问 Max (最强)",
      "parameters": [
        {
          "name": "temperature",
          "type": "float",
          "min": 0.0,
          "max": 2.0,
          "default": 0.7
        }
      ]
    },
    {
      "id": "deepseek-v3.2",
      "type": "text",
      "provider": "aliyun",
      "description": "DeepSeek v3.2 (支持深度思考)",
      "parameters": [
        {
          "name": "enable_thinking",
          "type": "boolean",
          "default": false,
          "description": "是否开启深度思考模式 (Reasoning)"
        }
      ]
    },
    {
      "id": "qwen3.5-plus",
      "type": "omni",
      "provider": "aliyun",
      "description": "千问 3.5 Plus全能模型 (支持多模态及深度思考)",
      "parameters": [
        {
          "name": "enable_thinking",
          "type": "boolean",
          "default": false,
          "description": "是否开启深度思考流式输出"
        }
      ]
    }
  ]
}
```

---

### 2. 对话接口

#### 2.1 文本对话

**端点**: `POST /api/playground/chat`

**描述**: 用于纯文本的对话交互，支持流式输出

**✨ 新特性**: 
- 支持直接在 `content` 中传入 Base64 编码的图片/音频/视频（需以 `data:image/xxx;base64,` 等开头），后端会自动转换为 URL。
- **本地模型 (Local)**: 对于 `provider="local"`，可以直接传递 Base64 图片数据，无需先上传获取 URL。

**权限**: 无需认证

**特别说明 - 本地模型 (Ollama)**:
- `provider`: 设为 `"local"`
- `model`: 支持 `llama3.2:3b`, `llava` (视觉), `qwen2.5:7b` (最新推荐)
- `config`: 与其他模型一致


**请求体**:
```json
{
  "provider": "aliyun",
  "model": "qwen-max",
  "messages": [
    {
      "role": "user",
      "content": "你好，请简短地介绍一下你自己。"
    }
  ],
  "config": {
    "temperature": 0.7,
    "top_p": 0.8,
    "stream": true
  }
}
```

**请求示例**:

- **curl（流式，Windows CMD 一行）**:
```cmd
curl -X POST http://localhost:8000/api/playground/chat -H "Content-Type: application/json" -d "{\"provider\":\"aliyun\",\"model\":\"qwen-max\",\"messages\":[{\"role\":\"user\",\"content\":\"你好\"}],\"config\":{\"stream\":true}}"
```

- **curl（非流式，一次性返回完整内容）**:
```cmd
curl -X POST http://localhost:8000/api/playground/chat -H "Content-Type: application/json" -d "{\"provider\":\"aliyun\",\"model\":\"qwen-max\",\"messages\":[{\"role\":\"user\",\"content\":\"你好\"}],\"config\":{\"stream\":false}}"
```

- **JavaScript fetch（非流式，直接拿完整文本）**:
```javascript
const res = await fetch('http://localhost:8000/api/playground/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    provider: 'aliyun',
    model: 'qwen-max',
    messages: [{ role: 'user', content: '你好' }],
    config: { stream: false }
  })
});
const data = await res.json();
const fullText = data.choices[0].message.content;  // 完整回复
```

- **JavaScript fetch（流式，逐段输出）**:
```javascript
const res = await fetch('http://localhost:8000/api/playground/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    provider: 'aliyun',
    model: 'qwen-max',
    messages: [{ role: 'user', content: '你好' }],
    config: { stream: true }
  })
});
const reader = res.body.getReader();
const decoder = new TextDecoder();
let buffer = '';
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split('\n');
  buffer = lines.pop() || '';
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const raw = line.slice(6);
      if (raw === '[DONE]') break;
      try {
        const json = JSON.parse(raw);
        const content = json.choices?.[0]?.delta?.content;
        if (content) console.log(content);
      } catch (e) {}
    }
  }
}
```

**响应**:
- **`stream: true`（默认）**：SSE 流式输出（Content-Type: `text/event-stream`），前端需按 SSE 逐条解析。
- **`stream: false`**：后端先拼接完整内容再一次性返回，响应为单个 JSON（`application/json`），结构示例：
  `{"choices":[{"message":{"role":"assistant","content":"完整回复文本"},"finish_reason":"stop"}]}`，前端直接 `response.json()` 即可。

---

#### 2.2 视觉理解

**端点**: `POST /api/playground/chat`

**描述**: 用于图片分析和描述，使用相同的 `/chat` 端点，但消息内容包含图片

**权限**: 无需认证

**请求体**:
```json
{
  "provider": "aliyun",
  "model": "qwen-vl-max",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "image": "https://example.com/image.jpg"
        },
        {
          "text": "请详细描述这张图片。"
        }
      ]
    }
  ]
}
```

**说明**：多模态 `content` 可为列表，每项支持以下写法（后端会规范为阿里云要求的带 `type` 格式）：
- 文本：`{"text": "..."}` 或 `{"type": "text", "text": "..."}`
- 图片：`{"image": "url"}` 或 `{"type": "image", "image": "url"}`
- 音频：`{"audio": "url"}` 或 `{"type": "audio", "audio": "url"}`
- 视频：`{"video": "url"}` 或 `{"type": "video", "video": "url"}`

---

#### 2.3 全模态对话（含语音输出）

**端点**: `POST /api/playground/chat`

**描述**: 支持文本、图片、音频、视频输入，并可同时输出文本和语音（类似 TTS 语音合成）

**适用模型**: `qwen3-omni-flash`（Qwen3 Omni Flash 全模态）

**权限**: 无需认证

**请求体示例（文本+视频输入，输出文本+语音）**:
```json
{
  "provider": "aliyun",
  "model": "qwen3-omni-flash",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "这段视频里发生了什么？"
        },
        {
          "type": "video", 
          "video": "https://example.com/video.mp4"
        }
      ]
    }
  ],
  "config": {
    "modalities": ["text", "audio"],
    "voice": "Cherry"
  }
}
```

**config 参数说明（语音输出）**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `modalities` | `string` 或 `string[]` | 输出模态。`["text"]` 仅文本；`["text", "audio"]` 文本+语音。也支持 `"text,audio (文本+音频)"` 等字符串格式 |
| `voice` | `string` | 音色，可选：`Cherry`、`Serena`、`Ethan`、`Chelsie`，默认 `Cherry` |
| `audio` | `object` | 可选，`{"voice": "Cherry", "format": "wav"}`，与 `voice` 二选一 |

**响应格式**:
- **流式** (`stream: true`)：每个 chunk 的 `choices[0].delta` 可能包含：
  - `content`: 文本内容
  - `audio`: `{"data": "base64..."}` 音频数据（WAV 格式，24000Hz，16bit）
- **非流式** (`stream: false`)：`choices[0].message` 可能包含：
  - `content`: 完整文本
  - `audio`: 最后一个音频 chunk 的 base64 数据

**前端播放语音示例**:
```javascript
// 流式收集音频 base64 并播放
let audioBase64 = '';
const reader = res.body.getReader();
const decoder = new TextDecoder();
let buffer = '';
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split('\n');
  buffer = lines.pop() || '';
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const raw = line.slice(6);
      if (raw === '[DONE]') break;
      try {
        const json = JSON.parse(raw);
        const audio = json.choices?.[0]?.delta?.audio;
        if (audio?.data) audioBase64 += audio.data;
      } catch (e) {}
    }
  }
}
// 解码并播放
if (audioBase64) {
  const wavBytes = Uint8Array.from(atob(audioBase64), c => c.charCodeAt(0));
  const blob = new Blob([wavBytes], { type: 'audio/wav' });
  const url = URL.createObjectURL(blob);
  const audioEl = new Audio(url);
  audioEl.play();
}
```

**说明**：
- **仅要文字回复**：传 `"modalities": ["text"]` 或不传（默认仅文本）
- **要文字+语音**：传 `"modalities": ["text", "audio"]` 或 `"modalities": "text,audio (文本+音频)"`
- 支持图文音视频多模态输入，格式同 [2.2 视觉理解](#22-视觉理解)

---

#### 2.4 代码在线（code-online）

用于在服务端执行用户提供的 Python 代码片段，并可将代码/报错交给大模型做分析建议。

**重要提示**：`run-code` 会在服务器端执行任意 Python 代码，存在安全风险。可通过环境变量 `CODE_ONLINE_ENABLE_RUN_CODE=false` 禁用该功能（默认启用）。

##### 2.4.1 运行代码

**端点**: `POST /api/playground/code-online/run-code`

**请求体**:
```json
{
  "code": "print('hello')",
  "env": "default",
  "timeout_seconds": 10
}
```

**响应**:
- 成功：`{"success": true, "output": "stdout内容"}`
- 失败：`{"success": false, "error": "stderr内容/修正后的错误原因"}`

##### 2.4.2 结合代码/错误的模型分析

**端点**: `POST /api/playground/code-online/chat-with-llm`

**请求体**:
```json
{
  "input": "这段代码报错如何修复？",
  "code": "（可选：你的代码）",
  "error": "（可选：你的报错信息）"
}
```

**响应**:
- 成功：`{"success": true, "reply": "模型回复内容"}`
- 失败：`{"success": false, "error": "大模型调用失败原因"}`

**说明**：
- 后端使用 DashScope `chat/completions` OpenAI-compatible 接口
- API Key 来自后端环境变量 `DASHSCOPE_API_KEY`
- 默认模型为 `qwen-plus`，且不进行流式输出

---

### 3. 图像生成接口

#### 3.1 生成图像

**端点**: `POST /api/playground/images/generations`

**描述**: 根据文本描述生成图片

**权限**: 无需认证

**请求体 (文生图)**:
```json
{
  "provider": "aliyun",
  "model": "qwen-image-plus",
  "prompt": "一个充满未来感的赛博朋克风格城市，有飞行汽车，霓虹灯闪烁",
  "config": {
    "size": "1024x1024"
  }
}
```

**请求体 (图生图 - 仅限特定 Doubao Seedream 模型)**:
```json
{
  "provider": "doubao",
  "model": "doubao-seedream-5-0-260128",
  "prompt": "把这张图片改成赛博朋克风格",
  "image": "https://example.com/reference_image.jpg",
  "config": {
    "size": "2K",
    "watermark": true,
    "sequential_image_generation": "disabled"
  }
}
```
**说明**:
* `image` 字段可以接受 HTTP(s) 图片外链，或者 Base64 编码的源数据（例如：`data:image/png;base64,...`）。
* 目前支持图生图的模型包含：`doubao-seedream-5-0-260128`, `doubao-seedream-4-5-251128`, `doubao-seedream-4-0-250828`。
* `doubao-seedream-3-0-t2i-250415` 作为轻量版，仅支持前一种文生图请求。

**响应示例** (200 OK):
```json
{
  "data": [
    {
      "url": "https://dashscope-result-xxx.oss-cn-xxx.com/xxx.png"
    }
  ]
}
```

---

#### 3.2 获取提示词模板

**端点**: `GET /api/playground/images/prompts/templates`

**描述**: 获取内置的教育与科研场景提示词模板列表，包含专业课件、教学素材、科研成果呈现等高频场景的推荐提示词。

**权限**: 无需认证

**响应示例** (200 OK):
```json
{
  "count": 8,
  "templates": [
    {
      "id": "stem_structure_viz",
      "category": "专业课件可视化 (Specialized Courseware)",
      "title": "神经网络与算法结构",
      "description": "生成神经网络或算法（如CNN, Transformer）的结构示意图。",
      "prompt": "大学人工智能专业课件插图...",
      "negative_prompt": "模糊，杂乱...",
      "config": {
        "style": "auto",
        "size": "1024x1024",
        "prompt_extend": true
      }
    }
  ]
}
```

---

### 4. 视频生成模块 (Video Generation)

此模块处理所有的文生视频和图生视频请求。由于视频生成属于长耗时异步任务，平台底层做了异步轮询包装，最终会同步返回视频 URL 或者报错。

#### 4.1 生成视频 (Generate Video)

**端点**: `POST /api/playground/video/generations`

**描述**: 根据文本或文本加图片输入生成视频。

**权限**: 无需认证

**请求体 (文生视频)**:
```json
{
  "provider": "doubao",
  "model": "doubao-seedance-1-0-pro-250528",
  "prompt": "一只科幻赛博朋克风格的机器猫穿梭在城市屋顶，4K高画质，电影级质感",
  "config": {
    "resolution": "720p",
    "ratio": "16:9",
    "duration": 5,
    "camera_fixed": false,
    "watermark": true
  }
}
```

**请求体 (图生视频)**:
```json
{
  "provider": "doubao",
  "model": "doubao-seedance-1-0-lite-i2v-250428",
  "prompt": "让图片生动起来，展示出电影级的运镜感",
  "image_url": "https://example.com/start_frame.jpeg",
  "config": {
    "resolution": "720p",
    "ratio": "16:9",
    "duration": 4
  }
}
```
**说明**:
* `image_url` 字段接受 HTTP(s) 图片外链用于提供首帧或者参考图。
* Config 中的参数 (`resolution`, `ratio`, `duration`, `camera_fixed`, `seed`, `watermark`) 会根据具体的模型有所区分。例如 `doubao-seedance-1-0-lite-i2v-250428` 是参考图生成专门针对图像驱动设计，不支持 `camera_fixed` 运动镜头的设置。

**响应示例** (200 OK):
```json
{
  "output": {
    "video_url": "https://ark-content-generation-xxx...mp4"
  }
}
```

---
### 4. 视频生成接口

#### 4.1 生成视频

**端点**: `POST /api/playground/videos/generations`

**描述**: 根据图片和文本描述生成视频（图生视频）

**权限**: 无需认证

**请求体**:
```json
{
  "provider": "aliyun",
  "model": "wan2.6-i2v-flash",
  "prompt": "一只小狗在公园里奔跑的电影质感镜头",
  "image_url": "https://example.com/dog.jpg", // 必填 (图生视频模型) - 支持 URL 或 Base64 (data:image/png;base64,...)
  "config": {
    "resolution": "1280x720",
    "duration": 5
  }
}
```

**响应示例** (200 OK):
```json
{
  "output": {
    "video_url": "https://dashscope-result-xxx.oss-cn-xxx.com/video.mp4"
  }
}
```

#### 4.2 生成视频 (文生视频 T2V)

**适用于**: `wan2.6-t2v`, `wan2.5-t2v-preview`

**描述**: 仅根据文本描述生成视频，**无需上传图片**。

**请求体**:
```json
{
  "provider": "aliyun",
  "model": "wan2.6-t2v",
  "prompt": "一段史诗感的电影片头，展示古代中国山水画变活了...",
  "config": {
    "resolution": "1280x720", 
    "duration": 5,
    "generate_audio": true,
    "shot_type": "multi"  // 仅 wan2.6-t2v 支持 (single/multi)
  }
}
```

**模型差异说明**:
- **wan2.6-t2v**:
    - **特有参数**: `shot_type` (single: 单镜头, multi: 多镜头叙事)
    - **分辨率**: 支持 720P (16:9, 9:16, 1:1, 4:3, 3:4) 和 1080P 全系列。
    - **时长**: 5s, 10s, 15s。
- **wan2.5-t2v-preview**:
    - **特有分辨率**: 支持 **480P** (832x480 等), 720P, 1080P。
    - **时长**: 5s, 10s。
    - **注意**: 不支持 `shot_type`。

#### 4.3 生成视频 (豆包 Seedance)

**端点**: `POST /api/playground/videos/generations`

**描述**: 适用模型 `doubao-seedance-1-5-pro-251215`。支持**纯文生视频**和**图生视频**。若提供 `image_url` 或 `Base64` 则自动作为图生视频的首帧。

**请求体示例**:
```json
{
  "provider": "doubao",
  "model": "doubao-seedance-1-5-pro-251215",
  "prompt": "无人机以极快速度穿越复杂障碍，带来沉浸式飞行体验",
  "image_url": "https://example.com/start_frame.png", // 选填
  "config": {
    "resolution": "720p",       // 清晰度 (例如 720p)
    "duration": 5,              // 时长，支持 5 (默认)
    "ratio": "16:9",            // 画面比例 (例如 16:9, 9:16)
    "camera_fixed": false,      // 镜头是否固定 (默认 false)
    "watermark": true           // 是否含水印 (默认 true)
  }
}
```


---

### 5. 语音服务接口

#### 5.1 语音合成 (TTS)

将文本转换为语音音频。

**接口地址**: `/api/playground/audio/speech`  
**请求方式**: `POST`

#### 请求参数 (AudioSpeechRequest)
- `provider`: 供应商，目前支持 `aliyun`
- `model`: 模型名称
  - `aliyun`: `cosyvoice-v3-flash` (推荐, 极速版), `cosyvoice-v3-plus` (高音质), `cosyvoice-v2` (支持方言), `sambert-zhichu-v1` (经典稳定)
- `input`: 需要合成的文本内容
- `config`: (可选) 合成配置
  - `voice`: 音库名称
    - **CosyVoice v3 Flash**: 支持约 70 个音色，包括 `longanyang` (阳光大男孩), `longanhuan` (欢脱元气女), `longjielidou_v3` 等。
    - **CosyVoice v3 Plus**: 支持 `longanyang`, `longanhuan` (高音质)。
    - **CosyVoice v2**: 支持约 100+ 个音色，涵盖方言、多语种、多情感 (如 `longyingxiao` 粤语, `loongkyong_v2` 韩语等)。
    - > 💡 **提示**: 完整音色列表请通过 `GET /api/playground/models` 接口获取动态数据。
    - **Sambert 系列**: **不使用此参数**。Sambert 通过更改 `model` ID 来切换音色（例如 `sambert-zhichu-v1`, `sambert-zhibei-v1`）。
  - `speed`: 语速 (0.5 - 2.0)，默认 `1.0`
  - `volume`: 音量 (0 - 100)，默认 `50`
  - `format`: 音频格式 (`mp3`, `wav`, `pcm`)，默认 `mp3`
  - `sample_rate`: 采样率 (8000, 16000, 24000, 48000)，默认 `16000` (注意：CosyVoice v2/v3 接口内部会自动处理，建议保留默认)

> [!TIP]
> **模型选择建议**:
> - **实时对话/极速响应**: 首选 `cosyvoice-v3-flash`。
> - **高质量内容创作**: 使用 `cosyvoice-v3-plus`。
> - **多语言/方言需求**: 使用 `cosyvoice-v2`。

#### 响应
直接返回音频二进制数据。

#### 示例 (Python)
```python
import requests

payload = {
    "provider": "aliyun",
    "model": "cosyvoice-v3-flash",
    "input": "你好，这是一段来自 CosyVoice v3 的测试语音。",
    "config": {
        "voice": "longanyang",
        "speed": 1.0,
        "format": "mp3"
    }
}

response = requests.post("http://localhost:8000/api/playground/audio/speech", json=payload)
with open("output.mp3", "wb") as f:
    f.write(response.content)
```

**响应**: 音频文件的二进制流（Content-Type: `audio/mpeg` 或 `audio/wav`）

---

#### 5.2 语音识别 (ASR)

**端点**: `POST /api/playground/audio/transcription`

**描述**: 将音频转换为文字（语音识别）

**权限**: 无需认证

**请求体**:
```json
{
  "provider": "aliyun",              // 必填：服务提供商 (aliyun / xunfei)
  "model": "qwen3-asr-flash",        // 必填：模型ID（从模型列表获取）
  "input": "https://example.com/audio.wav",  // 必填：音频文件 URL 或 Base64 编码 (data:audio/wav;base64,...),
  "config": {                         // 可选：配置参数
    "format": "wav",                  // 音频格式：mp3, wav, m4a 等（默认 wav）
    "sample_rate": 16000,             // 采样率：16000, 8000 等（默认 16000）
    "enable_punctuation_prediction": true,      // 启用标点预测（默认 true）
    "enable_inverse_text_normalization": true,  // 启用逆文本归一化（默认 true）
    "disfluency_removal_enabled": false,        // 启用流畅度优化/去语气词（默认 false）
    "speaker_diarization_enabled": false,       // 启用说话人分离（仅 fun-asr）
    "max_speaker_count": 2                      // 最大说话人数量（仅 fun-asr）
  }
}
```

**响应示例** (200 OK):
```json
{
  "text": "你好，这是一段测试语音。",
  "raw": "原始识别结果数据"
}
```

**可用模型**:
| 模型ID | 提供商 | 名称 | 说明 |
|--------|--------|------|------|
| `qwen3-asr-flash` | aliyun | Qwen3 ASR (实时识别) | 实时语音识别，**仅适合 60秒以内 的短音频** |
| `qwen3-asr-flash-filetrans` | aliyun | Qwen3 ASR (文件转写) | 文件级转写，支持长音频、语义分段 |
| `fun-asr` | aliyun | FunASR (说话人分离) | 支持说话人分离（Speaker Diarization） |
| `xunfei-lfasr` | xunfei | 讯飞语音转写 | 讯飞长语音转写，支持长达5小时音频 |
| `local-whisper-large` | local | Whisper Large v3 (本地) | OpenAI 离线模型，高精度，支持多语言自动识别 |

**输入格式**:
- **HTTP URL**: `https://example.com/audio.wav`（在线音频链接）
- **Base64**: `data:audio/wav;base64,xxxxxx`（无需手动上传，后端自动转 URL）
- 讯飞模型也支持 URL，系统会自动下载后上传至讯飞服务器

**完整流程示例**（上传音频 → 识别）:
```javascript
// 1. 上传音频文件
async function uploadAndTranscribe(audioFile, provider = 'aliyun', modelId = 'qwen3-asr-flash') {
  // 先上传音频
  const formData = new FormData();
  formData.append('file', audioFile);
  
  const uploadResponse = await fetch('http://localhost:8000/api/audio/upload', {
    method: 'POST',
    body: formData
  });
  
  const uploadData = await uploadResponse.json();
  const audioUrl = uploadData.url;
  
  // 2. 使用上传的音频URL进行语音识别
  const transcriptionResponse = await fetch('http://localhost:8000/api/playground/audio/transcription', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      provider: provider,
      model: modelId,
      input: audioUrl,
      config: {}
    })
  });
  
  const transcriptionData = await transcriptionResponse.json();
  return transcriptionData.text;
}
```

---

### 6. 文件上传接口

> **注意**: 文件上传接口使用统一的实现，通过路径参数 `{file_category}` 区分文件类型。支持的类别：`video`、`audio`、`image`。

#### 6.1 上传文件

**端点**: `POST /api/{file_category}/upload`

**描述**: 上传文件并获取访问URL

**权限**: 无需认证

**路径参数**:
- `file_category`: `video` | `audio` | `image`

**请求格式**: `multipart/form-data`

**请求参数**:
- `file` (File, 必填): 文件
- `user_id` (String, 可选): 用户ID

**响应示例** (200 OK):
```json
{
  "success": true,
  "video_id": "abc123...",
  "url": "http://localhost:8000/api/video/abc123...",
  "message": "上传成功"
}
```

---

#### 6.2 获取文件列表

**端点**: `GET /api/{file_category}/list`

**描述**: 获取文件列表，支持分页和用户筛选

**权限**: 无需认证

**查询参数**:
- `user_id` (String, 可选): 用户ID
- `page` (Integer, 可选): 页码，默认 1
- `per_page` (Integer, 可选): 每页数量，默认 20

---

#### 6.3 获取文件URL

**端点**: `GET /api/{file_category}/{file_id}`

**描述**: 根据文件ID获取文件访问URL

**权限**: 无需认证

---

#### 6.4 删除文件

**端点**: `DELETE /api/{file_category}/{file_id}`

**描述**: 删除已上传的文件

**权限**: 无需认证

---

### 7. 训练集上传与管理接口

> **说明**: 支持用户上传 LlamaFactory 兼容格式的训练集，存储到已配置的 OSS（或本地）。格式支持 Alpaca、ShareGPT，文件格式支持 json/jsonl/csv，最大 500MB。

#### 7.1 上传训练集

**端点**: `POST /api/playground/datasets/upload`

**描述**: 上传训练集，校验格式符合 LlamaFactory（Alpaca 或 ShareGPT），存入 OSS 或本地。

**请求格式**: `multipart/form-data`

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | ✓ | 数据文件（json/jsonl/csv） |
| name | string | ✓ | 数据集名称 |
| description | string | | 数据集描述 |
| data_type | string | ✓ | 数据类型：text_conversation, text2image, image_classification, text_classification, pretrain, dpo, kto, tool_call |
| dataset_type | string | ✓ | 训练集/推理集：train, inference |
| data_usage | string | ✓ | 用途：sft, dpo, kto, pretrain |
| data_format | string | ✓ | 格式：alpaca, sharegpt |
| user_id | string | | 用户ID |

**响应示例** (200 OK):
```json
{
  "success": true,
  "dataset": {
    "id": "xxx",
    "name": "我的训练集",
    "description": "...",
    "data_type": "text_conversation",
    "dataset_type": "train",
    "data_usage": "sft",
    "data_format": "alpaca",
    "dataset_info_name": "user_xxx_xxx",
    "created_at": "2025-02-05T..."
  },
  "message": "上传成功"
}
```

**curl 示例**（将 `data.json` 替换为你的数据文件路径）:
```bash
curl -X POST "http://localhost:8000/api/playground/datasets/upload" \
  -F "file=@data.json" \
  -F "name=我的训练集" \
  -F "description=Alpaca 格式的 SFT 数据" \
  -F "data_type=text_conversation" \
  -F "dataset_type=train" \
  -F "data_usage=sft" \
  -F "data_format=alpaca" \
  -F "user_id=user001"
```

---

#### 7.2 获取训练集列表

**端点**: `GET /api/playground/datasets/list`

**查询参数**: `user_id`, `page`, `per_page`

**curl 示例**:
```bash
curl -s "http://localhost:8000/api/playground/datasets/list?page=1&per_page=20"
# 按用户筛选
curl -s "http://localhost:8000/api/playground/datasets/list?user_id=user001&page=1"
```

---

#### 7.3 获取前端选项

**端点**: `GET /api/playground/datasets/options`

**描述**: 返回 data_types、dataset_types、data_usages、data_formats 枚举，供前端创建表单使用。

**curl 示例**:
```bash
curl -s "http://localhost:8000/api/playground/datasets/options"
```

---

### 8. llmfactory 微调与推理接口

> **说明**: 基于 llmfactory（LlamaFactory 封装）的 LoRA/全量微调、模型合并及推理 API 启动。需确保 llmfactory 与 LlamaFactory 已正确安装，且 `app/main.py` 已启用 llmfactory 路由。
>
> **Linux curl 命令**：详见 [llmfactory_curl命令.md](llmfactory_curl命令.md)
>
> **训练集**: 可使用 `dataset_id` 指定已上传的训练集（见 §7），或使用 `dataset` + `dataset_dir` 指定本地/HuggingFace 数据集。
>
> **模型选择**: 训练/合并/推理时传 **model_id**（来自下方「获取本地模型列表」接口）或 **model_path** 二选一；推荐使用 **model_id**，不向前端暴露服务器路径。
>
> **显存下限（可选）**: 若在 `.env` 中设置 **`LLMFACTORY_MIN_FREE_VRAM_MIB`** 为大于 0 的整数（单位 MiB，与 `nvidia-smi` 一致），则在提交 **LoRA / QLoRA / 全量微调**（含同步）、**合并适配器**（含同步）、**启动推理 API**（`POST .../api/start`）之前，服务端会通过 **`nvidia-smi`** 检查指定 GPU 的**当前空闲显存**；若低于阈值则直接返回 **HTTP 503**，不创建训练任务、不启动子进程。`LLMFACTORY_GPU_VRAM_GUARD_INDEX` 指定 GPU 索引（默认 0）；`LLMFACTORY_GPU_VRAM_GUARD_STRICT=true` 时在无法执行 `nvidia-smi` 时也拒绝请求，`false`（默认）则查询失败时跳过检查（便于无 NVIDIA 环境或 CI）。设为 **0** 或不配置即关闭该功能。

#### 8.0 获取 llmfactory 本地模型列表

**端点**: `GET /api/playground/llmfactory/models`

**描述**: 列出 `LLMFACTORY_MODELS_DIR` 下已下载的本地模型。**仅返回抽象元数据（id、name、model_type），不返回服务器物理路径**；前端用返回的 `id` 作为 `model_id` 调用训练/合并/推理接口即可。

**响应示例** (200 OK，已配置且目录存在时):
```json
{
  "models": [
    { "id": "Qwen3-0.6B", "name": "Qwen3-0.6B", "model_type": "qwen2" },
    { "id": "Qwen2.5-1.5B", "name": "Qwen2.5-1.5B", "model_type": "qwen2" }
  ],
  "message": ""
}
```

未配置或目录不可用时，`models` 为空数组，`message` 会说明原因。

**curl 示例**:
```bash
curl -s "http://localhost:8000/api/playground/llmfactory/models"
```

---

#### 8.1 LoRA 微调（异步）

**端点**: `POST /api/playground/llmfactory/train/lora`

**描述**: 提交 LoRA 微调任务，后台在线程池执行，接口立即返回。支持 `dataset_id` 使用已上传训练集；否则需传 `dataset` + `dataset_dir` 或配置 .env 默认值。

**请求体**（model_id 与 model_path 二选一；dataset 可用 dataset_id 或 dataset + dataset_dir）:
```json
{
  "model_id": "Qwen3-0.6B",
  "model_path": "/path/to/base/model",
  "dataset_id": "已上传训练集ID",
  "dataset": "identity",
  "dataset_dir": "/path/to/dataset",
  "output_dir": "/path/to/output",
  "template": "qwen3_nothink",
  "lora_rank": 8,
  "lora_target": "all",
  "learning_rate": 0.0001,
  "num_train_epochs": 5,
  "bf16": true
}
```
（推荐传 `model_id`，来自 `GET /api/playground/llmfactory/models` 返回的 id，不暴露服务器路径。）

**响应示例** (200 OK):
```json
{
  "success": true,
  "message": "LoRA 训练任务已提交，正在后台执行。请查看服务日志了解进度。",
  "return_code": null
}
```

**curl 示例**（使用 model_id + dataset_id，推荐）:
```bash
curl -X POST "http://localhost:8000/api/playground/llmfactory/train/lora" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "Qwen3-0.6B",
    "dataset_id": "已上传训练集的ID",
    "output_dir": "/path/to/output/qwen3_lora",
    "template": "qwen3_nothink",
    "lora_rank": 8,
    "num_train_epochs": 5
  }'
```

**curl 示例**（使用 model_path + 本地 dataset/dataset_dir）:
```bash
curl -X POST "http://localhost:8000/api/playground/llmfactory/train/lora" \
  -H "Content-Type: application/json" \
  -d '{
    "model_path": "/path/to/Qwen3-0.6B",
    "dataset": "identity",
    "dataset_dir": "/path/to/llmfactory_data",
    "output_dir": "/path/to/output/qwen3_lora",
    "template": "qwen3_nothink",
    "lora_rank": 8,
    "num_train_epochs": 5
  }'
```

**说明**: 训练完成后，适配器保存在 `output_dir`。可通过 `logs/error.log` 或 `logs/server.log` 查看进度，日志中出现 `LoRA train finished with return_code=0` 表示成功。

---

#### 8.2 QLoRA 微调（异步）

**端点**: `POST /api/playground/llmfactory/train/qlora`

**描述**: QLoRA（量化 + LoRA）微调，显存占用更低，后台执行，接口立即返回。请求体与 LoRA 类似，额外支持 `quantization_bit`、`quantization_method`、`double_quantization`。

**QLoRA 相关参数可选值**（与 llmfactory 校验一致）：

| 参数 | 类型 | 可选值 / 约束 | 说明 |
|------|------|----------------|------|
| `lora_rank` | int | 1 ~ 128，默认 8 | LoRA 秩，越大参数量越多，常用 8、16、32、64 |
| `quantization_bit` | int | **2、3、4、8**，默认 4 | 量化位数。8：bnb/hqq/eetq；4：bnb/hqq；3、2：仅 hqq |
| `quantization_method` | string | **bnb**、**hqq**、**eetq**，默认 bnb | 量化方法。需与 `quantization_bit` 搭配：4bit 不可用 eetq；2/3bit 仅 hqq |
| `num_train_epochs` | float | 大于 0 的实数，默认 5.0 | 训练轮数，如 1、2、3、5.0 |

**bit 与 method 组合规则**（后端会校验，不合法会报错）：
- `quantization_bit=8` → method 可为 **bnb / hqq / eetq**
- `quantization_bit=4` → method 可为 **bnb / hqq**（不可用 eetq）
- `quantization_bit=3` 或 `2` → method 仅可为 **hqq**

**请求体**（model_id 与 model_path 二选一；路径类为必填或使用 dataset_id）:
```json
{
  "model_id": "Qwen3-0.6B",
  "model_path": "/path/to/base/model",
  "dataset": "identity",
  "dataset_dir": "/path/to/dataset",
  "output_dir": "/path/to/output",
  "template": "qwen3_nothink",
  "lora_rank": 8,
  "lora_target": "all",
  "quantization_bit": 4,
  "quantization_method": "bnb",
  "double_quantization": false,
  "learning_rate": 0.0001,
  "num_train_epochs": 5,
  "bf16": true
}
```

**curl 示例**（使用 model_id + dataset_id）:
```bash
curl -X POST "http://localhost:8000/api/playground/llmfactory/train/qlora" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "Qwen3-0.6B",
    "dataset_id": "已上传训练集的ID",
    "output_dir": "/path/to/output/qwen3_qlora",
    "template": "qwen3_nothink",
    "lora_rank": 8,
    "quantization_bit": 4,
    "quantization_method": "bnb",
    "num_train_epochs": 5
  }'
```

**curl 示例**（使用 model_path + dataset/dataset_dir）:
```bash
curl -X POST "http://localhost:8000/api/playground/llmfactory/train/qlora" \
  -H "Content-Type: application/json" \
  -d '{
    "model_path": "/path/to/Qwen3-0.6B",
    "dataset": "identity",
    "dataset_dir": "/path/to/llmfactory_data",
    "output_dir": "/path/to/output/qwen3_qlora",
    "template": "qwen3_nothink",
    "lora_rank": 8,
    "quantization_bit": 4,
    "quantization_method": "bnb",
    "num_train_epochs": 5
  }'
```

**响应**: 同 8.1，`message` 为「QLoRA 训练任务已提交，正在后台执行」。

---

#### 8.2.1 QLoRA 兼容性检查（单模型）

**端点**: `POST /api/playground/llmfactory/models/qlora-support`

**描述**: 检查某个基础模型是否适合使用 QLoRA（再量化 + LoRA）训练。若模型已是 GPTQ/AWQ/AQLM/GGUF 等量化/特定推理格式，一般不支持或不建议再启用 QLoRA。

**请求体**（`model_id` 与 `model_path` 二选一；推荐 `model_id`）:

```json
{
  "model_id": "Qwen3-0.6B",
  "model_path": "/path/to/base/model"
}
```

**响应示例**:

```json
{
  "supported": false,
  "reasons": [
    "config.json 字段包含关键字 awq（通常代表已量化/特定推理格式，不能作为 QLoRA 的基础模型）"
  ],
  "detected": {
    "model_path": "/path/to/model",
    "model_type": "llama",
    "architectures": ["LlamaForCausalLM"]
  }
}
```

---

#### 8.2.2 QLoRA 兼容性检查（扫描本地模型目录）

**端点**: `GET /api/playground/llmfactory/models/qlora-support`

**描述**: 扫描 `GET /api/playground/llmfactory/models` 同源的本地模型目录，对每个模型返回是否支持 QLoRA 及原因，同时汇总 `unsupported_models`。

**响应**（字段较多，示例略）: 返回 `models`（全量）与 `unsupported_models`（不支持的简表）。

---

#### 8.3 全量微调（异步）

**端点**: `POST /api/playground/llmfactory/train/full`

**描述**: 全量微调，后台执行，接口立即返回。

**请求体**（model_id 与 model_path 二选一）:
```json
{
  "model_id": "Qwen3-0.6B",
  "model_path": "/path/to/base/model",
  "dataset": "identity",
  "dataset_dir": "/path/to/dataset",
  "output_dir": "/path/to/output",
  "template": "qwen3_nothink",
  "learning_rate": 0.0001,
  "num_train_epochs": 1,
  "gradient_accumulation_steps": 2,
  "deepspeed_config": "/path/to/ds_z3_config.json"
}
```

**curl 示例**（使用 model_id + dataset_id）:
```bash
curl -X POST "http://localhost:8000/api/playground/llmfactory/train/full" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "Qwen3-0.6B",
    "dataset_id": "已上传训练集的ID",
    "output_dir": "/path/to/output/qwen3_full",
    "template": "qwen3_nothink",
    "learning_rate": 0.0001,
    "num_train_epochs": 1,
    "gradient_accumulation_steps": 2
  }'
```

**curl 示例**（使用 model_path + dataset/dataset_dir）:
```bash
curl -X POST "http://localhost:8000/api/playground/llmfactory/train/full" \
  -H "Content-Type: application/json" \
  -d '{
    "model_path": "/path/to/Qwen3-0.6B",
    "dataset": "identity",
    "dataset_dir": "/path/to/llmfactory_data",
    "output_dir": "/path/to/output/qwen3_full",
    "num_train_epochs": 1
  }'
```

**响应**: 同 8.1，`message` 为「全量训练任务已提交，正在后台执行」。

---

#### 8.4 合并 LoRA 适配器（异步）

**端点**: `POST /api/playground/llmfactory/merge`

**描述**: 将 LoRA 适配器与基础模型合并为完整模型，后台执行。**model_id 与 model_path 二选一**（推荐 model_id）；adapter_path、export_dir 需传入或配置 .env 默认值。`adapter_path` 通常为训练时的 `output_dir`。

**请求体**:
```json
{
  "model_id": "Qwen3-0.6B",
  "model_path": "/path/to/base/model",
  "adapter_path": "/path/to/lora/output",
  "export_dir": "/path/to/merged/model",
  "template": "qwen3_nothink",
  "export_size": 5,
  "export_device": "auto"
}
```

**响应示例** (200 OK):
```json
{
  "success": true,
  "message": "合并任务已提交，正在后台执行。请使用 job_id 在 GET /merge/jobs 中查看该任务状态。",
  "return_code": null,
  "job_id": "merge-job-id"
}
```

**curl 示例**（使用 model_id，推荐）:
```bash
curl -X POST "http://localhost:8000/api/playground/llmfactory/merge" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "Qwen3-0.6B",
    "adapter_path": "/path/to/output/qwen3_lora",
    "export_dir": "/path/to/merged_model",
    "template": "qwen3_nothink",
    "export_size": 5,
    "export_device": "auto"
  }'
```

**说明**: 合并完成后，`export_dir` 下可得到完整模型（`config.json`、`model.safetensors` 等），可直接用于推理。

---

#### 8.4.1 查询微调任务训练进度

**端点**: `GET /api/playground/llmfactory/train/jobs/{job_id}/progress`

**描述**: 根据异步训练/合并接口返回的 **`job_id`**，读取该任务 `output_dir` 下的 **`trainer_state.json`**（由 HuggingFace Trainer / LlamaFactory 写入），将步数、epoch、loss、`log_history` 等返回给前端，用于进度条与损失曲线。**无需认证**（与 `GET /train/jobs` 列表一致）。

**Query 参数**:

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `log_limit` | int | 100 | `log_history` 返回的最大条数（从文件尾部截取），范围 1～500 |

**响应字段说明**（200 OK，`application/json`）:

| 字段 | 说明 |
|------|------|
| `job_id` | 任务 ID |
| `task_type` | `lora` / `qlora` / `full` / `merge` |
| `job_status` | 数据库中的状态：`running` / `success` / `failed` |
| `model_display_name` | **前端展示名**：与 `output_dir` **末级目录名**相同，例如 `Qwen3-0.6B_lora_20260323_102510`（与 `GET /trained-models` 下列表项目录名一致，便于对照） |
| `output_dir` | 任务输出目录路径 |
| `error_message` | 任务失败时的错误摘要（若有） |
| `trainer_state_found` | 是否成功解析到 `trainer_state.json` |
| `global_step` / `max_steps` / `epoch` | 训练步数与轮次 |
| `num_train_epochs` | 若同目录存在 `training_args.json` 则尽量填充 |
| `latest_loss` / `learning_rate` | 最近一条带 `loss` 的日志 |
| `progress_ratio` | 0～1；优先 `global_step/max_steps`，否则 `epoch/num_train_epochs`（能算则填） |
| `log_history` | `trainer_state` 中日志列表的尾部，便于前端绘图 |
| `best_model_checkpoint` | 最优检查点路径（若有） |
| `message` | 无状态文件、目录不存在、合并任务说明等 |

**合并任务**（`task_type=merge`）：无 Trainer 步进信息，`trainer_state_found` 为 `false`，`message` 会说明；请以 `job_status` 为准。

**错误**: `404` 任务不存在；`403` 任务的 `output_dir` 不在服务端允许的训练输出根目录下（防路径穿越）。

**curl 示例**:
```bash
curl -s "http://localhost:8000/api/playground/llmfactory/train/jobs/<job_id>/progress?log_limit=50"
```

**前端建议**: 在 `job_status === "running"` 时每 2～5 秒轮询一次；`success` 或 `failed` 后停止。

---

#### 8.5 同步接口

以下接口会阻塞直至任务完成，适合脚本或短时任务：

| 端点 | 说明 |
|------|------|
| `POST /api/playground/llmfactory/train/lora/sync` | 同步 LoRA 训练，返回 `return_code` |
| `POST /api/playground/llmfactory/train/qlora/sync` | 同步 QLoRA 训练 |
| `POST /api/playground/llmfactory/train/full/sync` | 同步全量训练 |
| `POST /api/playground/llmfactory/merge/sync` | 同步合并 |

**curl 示例**（以 LoRA 同步为例，使用 model_id）:
```bash
curl -X POST "http://localhost:8000/api/playground/llmfactory/train/lora/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "Qwen3-0.6B",
    "dataset_id": "已上传训练集的ID",
    "output_dir": "/path/to/output/qwen3_lora",
    "template": "qwen3_nothink",
    "lora_rank": 8,
    "num_train_epochs": 1
  }'
```

**响应示例**（同步接口，以训练为例）:
```json
{
  "success": true,
  "message": "训练完成",
  "return_code": 0,
  "job_id": "train-job-id"
}
```
`return_code` 为 0 表示成功。

---

#### 8.6 启动推理 API 服务

**端点**: `POST /api/playground/llmfactory/api/start`

**描述**: 启动 OpenAI 兼容的推理服务，**统一通过主服务 8000 端口访问**（无需再开 8001）。推理子进程在内部端口运行，对外由 8000 代理。**model_id 与 model_path 二选一**（推荐 model_id）；`model_id` 既可以来自 `GET /api/playground/llmfactory/models`，也可以直接使用 `GET /api/playground/llmfactory/merged-models` 返回的合并后模型 id/name。也可配合 `adapter_path` 使用未合并的适配器。推理进程由 llm_AIO 管理，服务重启后需重新调用。

**请求体**:
```json
{
  "model_id": "Qwen3-0.6B",
  "model_path": "/path/to/merged/model",
  "adapter_path": "/path/to/adapter",
  "template": "auto",
  "cuda_devices": "0",
  "bf16": false,
  "infer_dtype": null
}
```
- `template`：对话模板，须在 `GET .../templates` 列表中。**不传或传 `auto` 时，按模型目录下 `config.json` 的 `model_type` 自动选择**（如 qwen2→qwen、qwen3→qwen3_nothink、llama3→llama3 等）；显式传入则使用该模板。
- `bf16`：设为 `true` 时向推理子进程传递 `LLAMAFACTORY_INFER_DTYPE=bfloat16`；默认 `false` 且未传 `infer_dtype` 时不传该环境变量，子进程使用自身默认。
- `infer_dtype`：推理精度，**优先于 bf16**。可选 `auto`、`float16`、`bfloat16`、`float32`，通过环境变量 `LLAMAFACTORY_INFER_DTYPE` 传给子进程。需推理后端（如 LLaMA-Factory）读取该环境变量方可生效。

**响应示例** (200 OK):
```json
{
  "success": true,
  "message": "推理 API 服务已启动，请使用下方 api_url（8000 端口）调用",
  "api_url": "http://localhost:8000/api/playground/llmfactory/v1",
  "pid": 73991,
  "note": "进程在后台运行，重启 llm_AIO 后需重新启动"
}
```

**curl 示例**（使用 model_id，推荐）:
```bash
curl -X POST "http://localhost:8000/api/playground/llmfactory/api/start" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "Qwen3-0.6B",
    "template": "qwen3_nothink",
    "cuda_devices": "0"
  }'
```

**使用推理 API**: 以返回的 `api_url`（8000 端口）调用 OpenAI 兼容接口。请求体中的 `model` 须与 `GET .../v1/models` 返回的 `data[].id` 一致（可能是 `gpt-3.5-turbo` 或 `default` 等）：
```bash
curl -X POST "http://localhost:8000/api/playground/llmfactory/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"你好"}],"max_tokens":128}'
```

---

#### 8.7 关闭推理 API 服务

**端点**: `POST /api/playground/llmfactory/api/stop`

**描述**: 关闭已启动的推理子进程，释放 GPU 显存。无需请求体。

**响应示例** (200 OK):
```json
{
  "success": true,
  "message": "已发送关闭信号给推理进程 (PID xxx)，显存将逐步释放"
}
```

若推理未在运行：
```json
{
  "success": true,
  "message": "推理服务未在运行，无需关闭"
}
```

**curl 示例**:
```bash
curl -X POST "http://localhost:8000/api/playground/llmfactory/api/stop"
```

---

## 用户管理服务 API

> **注意**: 所有用户管理服务接口都需要 JWT Token 认证。

### 1. 认证接口

#### 1.1 用户注册

**端点**: `POST /api/v1/auth/register`

**描述**: 注册新用户账户

**权限**: 无需认证

**请求体**:
```json
{
  "username": "string",
  "email": "user@example.com",
  "full_name": "string",
  "password": "string",
  "role": "student",
  "student_id": "S12345",
  "teacher_id": "T001"
}
```

**响应**: 201 Created

---

#### 1.2 用户登录

**端点**: `POST /api/v1/auth/login`

**描述**: 用户登录获取访问令牌

**权限**: 无需认证

**请求格式**: `application/x-www-form-urlencoded`

**请求参数**:
- `username`: 用户名
- `password`: 密码

**响应示例** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": 1,
  "role": "super_admin",
  "full_name": "System Administrator"
}
```

#### 1.3 获取当前用户信息

**端点**: `GET /api/v1/auth/me`

**描述**: 获取当前登录用户的详细信息

**权限**: 需要有效 Token

---

### 2. 用户管理接口

#### 2.1 获取用户列表

**端点**: `GET /api/v1/users/`

**描述**: 获取所有用户列表

**权限**: 超级管理员

---

### 3. 资源管理接口

#### 3.1 获取所有资源

**端点**: `GET /api/v1/resources/`

**描述**: 获取系统所有资源类型（CPU、GPU等）

**权限**: 超级管理员

---

### 4. 文件管理接口

#### 4.1 发送文件

**端点**: `POST /api/v1/user-files/send`

**描述**: 发送文件给用户（支持个人发送与批量发送）

**权限**: 超级管理员、教师

---
### 5. 报告管理接口

#### 5.1 获取待批改报告

**端点**: `GET /api/v1/reports/pending`

**描述**: 获取待批改的报告列表

**权限**: 教师

---

### 6. 知识库接口

本章分为两类能力，路由前缀不同，**数据互不打通**，前端页面建议做成两个模块（或 Tab）以免混淆：

| 类别 | 前缀 | 说明 |
|------|------|------|
| **静态知识库** | `/api/v1/knowledge-base` | 富文本/标题/分类/标签 + 可选附件，存 **SQL 业务库**；用于「知识库文章列表、详情页」 |
| **领域检索（RAG）** | `/api/v1/knowledge-retrieval` | **PDF 向量** 存 **Chroma**，对话走 LangGraph；用于「上传 PDF → 按文档问答」 |

#### 给前端的通用约定

- **网关根地址**：下文用 `{API_BASE}` 表示，例如 `http://localhost:8000` 或 `https://你的域名`（若经 Nginx 反代，请用对外统一前缀）。
- **API 前缀**：两类接口的完整路径均为 `{API_BASE}/api/v1/...`。
- **认证**：除登录接口外，请求头需带  
  `Authorization: Bearer <access_token>`  
  Token 来自 `POST /api/v1/auth/login`（`application/x-www-form-urlencoded`，字段 `username`、`password`），与文档「认证与授权」章节一致。
- **角色**：学生通常 **无**「管理知识库」权限 → 静态库的 **创建/改/删**、RAG 的 **PDF 入库** 会 **403**；**查看列表/详情**、**RAG 状态与对话** 一般为 **VIEW_KNOWLEDGE_BASE**（以实际角色配置为准）。

**推荐调用顺序（RAG 场景）**：登录拿 Token → `GET .../knowledge-retrieval/status` 确认 `ready` →（管理员）`POST .../ingest-pdf` 上传 PDF → `POST .../chat/completions` 提问。  
**推荐调用顺序（静态知识库场景）**：登录 → `GET .../knowledge-base/` 列表 → `GET .../knowledge-base/{id}` 详情；管理员再使用 `POST` 创建 / `PUT` 更新 / `DELETE` 删除。

---

#### 6.1 静态知识库（`knowledge-base`）

**路由前缀**：`/api/v1/knowledge-base`  
**Content-Type 注意**：创建条目用 **`multipart/form-data`**（不是 JSON），字段名必须与下表一致。

##### 6.1.0 接口一览

| 方法 | 完整 URL 模板 | 说明 | 权限 |
|------|----------------|------|------|
| `POST` | `{API_BASE}/api/v1/knowledge-base/` | 新建一条（表单 + 可选文件） | `MANAGE_KNOWLEDGE_BASE` |
| `GET` | `{API_BASE}/api/v1/knowledge-base/` | 分页列表 | `VIEW_KNOWLEDGE_BASE` |
| `GET` | `{API_BASE}/api/v1/knowledge-base/categories` | 分类列表 | `VIEW_KNOWLEDGE_BASE` |
| `GET` | `{API_BASE}/api/v1/knowledge-base/{entry_id}` | 单条详情 | 需登录 JWT（见下说明） |
| `PUT` | `{API_BASE}/api/v1/knowledge-base/{entry_id}` | 更新条目 | `MANAGE_KNOWLEDGE_BASE` |
| `DELETE` | `{API_BASE}/api/v1/knowledge-base/{entry_id}` | 删除条目 | `MANAGE_KNOWLEDGE_BASE` |

---

##### 6.1.1 创建条目 `POST /api/v1/knowledge-base/`

**请求**：`multipart/form-data`（可用 `<form>` 或 `FormData`）。

| 表单字段名 | 必填 | 类型 | 说明 |
|------------|------|------|------|
| `title` | ✓ | 文本 | 标题 |
| `content` | | 文本 | 正文，可空 |
| `category` | | 文本 | 分类 |
| `tags` | | 文本 | **多个标签用英文逗号分隔**，如 `标签1,标签2`（后端再拆成数组存储） |
| `file` | | 文件 | 可选附件；任意扩展名均可上传 |

**响应**：`201`，JSON 体为条目对象，主要字段示例：

```json
{
  "id": 1,
  "title": "标题",
  "content": "正文",
  "category": "课程",
  "tags": ["标签1", "标签2"],
  "file_id": 12,
  "uploader_id": 1,
  "is_indexed": false,
  "created_at": "2025-01-01T12:00:00",
  "updated_at": "2025-01-01T12:00:00",
  "uploader": null
}
```

**前端示例（浏览器 `fetch` + `FormData`）**：

```javascript
const form = new FormData();
form.append("title", "第一章导论");
form.append("content", "正文内容……");
form.append("category", "计算机");
form.append("tags", "基础,入门");  // 逗号分隔字符串
// form.append("file", fileInput.files[0]);  // 可选

await fetch(`${API_BASE}/api/v1/knowledge-base/`, {
  method: "POST",
  headers: { Authorization: `Bearer ${accessToken}` },
  body: form,  // 不要手动设 Content-Type，浏览器会自动带 boundary
});
```

---

##### 6.1.2 列表 `GET /api/v1/knowledge-base/`

**Query 参数**（全部可选）：

| 参数 | 说明 | 默认 |
|------|------|------|
| `skip` | 跳过条数（分页） | `0` |
| `limit` | 返回条数上限 | `100` |
| `category` | 按分类精确筛选 | — |
| `search` | 在 **标题、正文** 中模糊匹配（SQL `contains`） | — |

**请求头**：`Authorization: Bearer <token>`  

**响应**：`200`，JSON **数组**，元素结构同 6.1.1 响应体。

**示例**：

```
GET {API_BASE}/api/v1/knowledge-base/?skip=0&limit=20&search=导论
```

---

##### 6.1.3 分类列表 `GET /api/v1/knowledge-base/categories`

**响应**：`200`，JSON 数组，元素为分类名字符串（已去重、不含空值）。

---

##### 6.1.4 单条详情 `GET /api/v1/knowledge-base/{entry_id}`

**路径参数**：`entry_id` 整数。  

**权限说明**：当前实现为 **只要带有效 JWT 即可访问**；前端仍应对齐产品：仅向允许使用知识库的用户展示入口。  

**响应**：`200` 同 6.1.1 单条结构；无此 ID 时 **404**。

---

##### 6.1.5 更新条目 `PUT /api/v1/knowledge-base/{entry_id}`

**重要**：后端将 `title`、`content`、`category`、`tags` 定义为 **URL Query 参数**，**不是** JSON Body。`tags` 仍为 **逗号分隔字符串**。未传的字段保持原值；传入的字段会被更新。更新后 `is_indexed` 会被置为 `false`。

**示例**：

```
PUT {API_BASE}/api/v1/knowledge-base/3?title=新标题&content=新正文&category=数学&tags=a,b
Authorization: Bearer <token>
```

（实际项目中注意对 Query 做 `encodeURIComponent`，避免中文乱码。）

**响应**：`200`，更新后的条目 JSON。

---

##### 6.1.6 删除条目 `DELETE /api/v1/knowledge-base/{entry_id}`

**响应**：成功为 **`204 No Content`**，无 JSON 体。若条目曾有关联文件，服务端会尝试删除磁盘上的文件。

---

#### 6.2 领域检索（RAG）（`knowledge-retrieval`）

**路由前缀**：`/api/v1/knowledge-retrieval`

依赖环境变量与可选依赖包（Chroma、LangGraph 等）；与 **6.1 静态知识库** 无自动同步——**不会**因为你发了 `POST /knowledge-base/` 就把正文送进向量库。要向 RAG 喂文档，请用 **6.2.3** 上传 **PDF**，或由运维按后端约定写入 Chroma。

| 方法 | 完整 URL 模板 | 说明 |
|------|----------------|------|
| `GET` | `{API_BASE}/api/v1/knowledge-retrieval/status` | 是否初始化完成 + **向量库是否被暂停**（`vector_kb_disabled`） |
| `GET` | `{API_BASE}/api/v1/knowledge-retrieval/library` | 向量库位置、块数、已入库文档来源名汇总（只读） |
| `GET` | `{API_BASE}/api/v1/knowledge-retrieval/admin/vector-settings` | 教师/管理员：查看暂停开关 |
| `PUT` | `{API_BASE}/api/v1/knowledge-retrieval/admin/vector-settings` | 教师/管理员：**暂停/启用**向量知识库 |
| `DELETE` | `{API_BASE}/api/v1/knowledge-retrieval/library` | 教师/管理员：**清空**整库（删 Chroma 集合） |
| `DELETE` | `{API_BASE}/api/v1/knowledge-retrieval/library/by-source?source_file=` | 教师/管理员：按**文件名**删该文档全部分块（便于替换上传） |
| `POST` | `{API_BASE}/api/v1/knowledge-retrieval/chat/completions` | 对话（JSON 体） |
| `POST` | `{API_BASE}/api/v1/knowledge-retrieval/ingest-pdf` | 上传 PDF 入库（`multipart`，字段名 `file`） |

**数据存哪**：RAG 的「知识」是 **Chroma 持久化目录**（环境变量 **`RAG_CHROMADB_DIRECTORY`**，默认常如 `chroma_db_rag`）下、集合 **`RAG_CHROMADB_COLLECTION`** 中的**向量与分块元数据**。通过 **`ingest-pdf` 上传的 PDF 原文件默认不长期保存在业务目录**，仅切块嵌入后写入该库；**LangGraph 对话状态**另存在 **`RAG_LANGGRAPH_SQLITE`** 指向的 SQLite。

---

##### 6.2.1 RAG 服务状态

**端点**: `GET /api/v1/knowledge-retrieval/status`

**描述**: 查询 LangGraph + Chroma 是否已完成启动初始化；并返回**业务侧暂停开关**（存用户库表 `rag_vector_kb_control`，与进程级 `RAG_ENABLED` 独立）。前端若见 **`vector_kb_disabled: true`**，应禁用入库与对话（与 **`503` 暂停文案**一致）。

**权限**: `VIEW_KNOWLEDGE_BASE`

**请求头**：
```
Authorization: Bearer <access_token>
```

**响应示例**（200）：
```json
{
  "ready": true,
  "error": null,
  "vector_kb_disabled": false,
  "vector_kb_note": null,
  "vector_kb_updated_at": "2025-03-21T10:00:00"
}
```

`ready` 为 `false` 时，`error` 为字符串，例如缺少依赖、未配置嵌入模型 API Key、SQLite 路径不可写等。

**前端示例**：

```javascript
const r = await fetch(`${API_BASE}/api/v1/knowledge-retrieval/status`, {
  headers: { Authorization: `Bearer ${accessToken}` },
});
const { ready, error, vector_kb_disabled, vector_kb_note } = await r.json();
```

---

##### 6.2.2 RAG 对话补全（OpenAI 风格）

**端点**: `POST /api/v1/knowledge-retrieval/chat/completions`

**描述**: 后端用 LangGraph 编排（向量检索、可选联网、评分与重写等），对外返回 **OpenAI Chat Completions 形状**的 JSON；支持 **SSE** 流式。

**权限**: `VIEW_KNOWLEDGE_BASE`

**前置条件**: **6.2.1** 中 `ready === true` 且 **`vector_kb_disabled` 为 false**。若管理员已暂停向量库，返回 **503**（文案含说明）。若仅 `ready === false`，亦为 **503**。

**请求头**：
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**请求体（JSON）**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `messages` | array | ✓ | 每项形如 `{ "role": "user" \| "assistant" \| "system", "content": "..." }`。后端**只取最后一条**的 `content` 作为本轮用户问题（前面的消息当前不参与拼接上下文，但可预留兼容） |
| `stream` | boolean | | 默认 `false`。`true` 时响应 **`Content-Type: text/event-stream`**（SSE） |
| `userId` | string | | 可选；不传则用**当前登录用户**的 ID，写入 LangGraph 的 `user_id` |
| `conversationId` | string | | 可选；与 `userId` 拼成内部 `thread_id`（格式 `userId@@conversationId`），用于**多轮会话隔离**；默认 `default` |

**非流式请求示例（curl）**：
```bash
curl -X POST "http://localhost:8000/api/v1/knowledge-retrieval/chat/completions" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "请根据知识库简要说明……"}],
    "stream": false,
    "conversationId": "conv-001"
  }'
```

**非流式前端示例（`fetch`）**：

```javascript
const res = await fetch(`${API_BASE}/api/v1/knowledge-retrieval/chat/completions`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    messages: [{ role: "user", content: userText }],
    stream: false,
    conversationId: sessionId, // 同一聊天窗口固定一个字符串即可
  }),
});
const data = await res.json();
const answer = data.choices?.[0]?.message?.content ?? "";
```

**响应示例**（200，非流式）：
```json
{
  "id": "chatcmpl-xxxxxxxx",
  "object": "chat.completion",
  "created": 1710000000,
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "……"
      },
      "finish_reason": "stop"
    }
  ],
  "system_fingerprint": null
}
```

**流式（`stream: true`）**：

- 响应为 **SSE**：多行 `data: {...}\n\n`，每段为 JSON。
- 正文中增量在 **`choices[0].delta.content`**（可能多次推送）。
- 结束帧：`choices[0].finish_reason === "stop"` 且 `delta` 常为空对象 `{}`。
- 前端可用 **`fetch` + `ReadableStream`** 解析，或 **`EventSource`**（仅支持 GET 的浏览器需注意：本接口为 **POST**，一般用 `fetch` 读流）。

**流式解析要点（伪代码）**：

```javascript
const res = await fetch(/* 同上 */, {
  body: JSON.stringify({ messages: [...], stream: true, conversationId: sessionId }),
});
const reader = res.body.getReader();
const dec = new TextDecoder();
let buf = "";
for (;;) {
  const { value, done } = await reader.read();
  if (done) break;
  buf += dec.decode(value, { stream: true });
  const parts = buf.split("\n\n");
  buf = parts.pop() ?? "";
  for (const block of parts) {
    if (!block.startsWith("data:")) continue;
    const json = JSON.parse(block.slice(5).trim());
    const piece = json.choices?.[0]?.delta?.content;
    if (piece) appendToUI(piece);
  }
}
```

**常见错误**：

| HTTP | 说明 |
|------|------|
| 400 | `messages` 为空，或最后一条无 `content` |
| 401/403 | 未登录或缺少 `VIEW_KNOWLEDGE_BASE` |
| 503 | RAG 未初始化（依赖、环境变量或检查点数据库异常） |

---

##### 6.2.3 PDF 向量入库（写入 RAG Chroma）

**端点**: `POST /api/v1/knowledge-retrieval/ingest-pdf`

**描述**: 上传 **一个** PDF 文件，服务端切块、调用嵌入模型、写入 **Chroma**（集合与目录由后端 `RAG_*` 环境变量决定）。成功后，**6.2.2** 中的对话才能检索到该文件内容。

**权限**: `MANAGE_KNOWLEDGE_BASE`（学生一般会 **403**）

**请求**：`multipart/form-data`，字段名必须为 **`file`**（与 `curl -F file=@...` 一致）。

**请求头**：仅需 `Authorization: Bearer <token>`；**不要**手写 `Content-Type`（由 `FormData` 自动带 `boundary`）。

**表单字段**：

| 字段 | 必填 | 说明 |
|------|------|------|
| `file` | ✓ | PDF；`filename` 需以 `.pdf` 结尾（大小写不敏感） |

**curl 示例**：
```bash
curl -X POST "http://localhost:8000/api/v1/knowledge-retrieval/ingest-pdf" \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@/path/to/document.pdf"
```

**前端示例（`FormData`）**：

```javascript
const form = new FormData();
form.append("file", pdfFile); // pdfFile 为 File/Blob，来自 <input type="file" accept=".pdf">

const res = await fetch(`${API_BASE}/api/v1/knowledge-retrieval/ingest-pdf`, {
  method: "POST",
  headers: { Authorization: `Bearer ${accessToken}` },
  body: form,
});
const data = await res.json(); // { ok, message, filename }
```

**响应示例**（200）：
```json
{
  "ok": true,
  "message": "已向量化并写入 Chroma",
  "filename": "document.pdf"
}
```

**常见错误**：400（非 PDF 或缺文件）、403（权限不足）、503（嵌入模型不可用，如未配置 `DASHSCOPE_API_KEY` 等）。

---

##### 6.2.4 命令行 curl 串联示例（复制即用）

以下在 **Bash**（Linux / macOS / Git Bash）下可直接跑；把 **`BASE` 主机与端口**、**用户名密码**、**PDF 路径** 换成你的环境。  
**`jq`** 用于格式化 JSON；若未安装，去掉命令末尾的 `| jq .` 即可，或从原始 JSON 里肉眼找 `access_token` / `choices`。

**1）登录，得到 `TOKEN`**

```bash
export BASE=http://127.0.0.1:8000/api/v1
export TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r .access_token)
echo "TOKEN 前 20 字符: ${TOKEN:0:20}..."
```

**2）查询 RAG 是否就绪**

```bash
curl -s -X GET "$BASE/knowledge-retrieval/status" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

期望见 `"ready": true`。若为 `false`，看 `error` 字段排查依赖与 `.env`。

**2b）查看向量库索引摘要**（仅需 **`VIEW_KNOWLEDGE_BASE`**；**不要求** `ready`）

```bash
curl -s -X GET "$BASE/knowledge-retrieval/library" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

可选：`?metadata_scan_limit=5000`。响应含 **`persist_directory_resolved`**、**`chunk_count`**、**`unique_sources`**（已入库文档文件名汇总）。

**3）上传 PDF 入库**（需 **`MANAGE_KNOWLEDGE_BASE`**，如 admin / teacher）

```bash
curl -s -X POST "$BASE/knowledge-retrieval/ingest-pdf" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/your/document.pdf" | jq .
```

**4）非流式对话**（需 **`VIEW_KNOWLEDGE_BASE`**；`ready` 为 true）

```bash
curl -s -X POST "$BASE/knowledge-retrieval/chat/completions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "根据知识库简要回答：……"}],
    "stream": false,
    "conversationId": "curl-demo-1"
  }' | jq .
```

助手正文一般在 **`choices[0].message.content`**。

**5）流式对话（SSE）**（终端观察增量；`-N` 避免缓冲）

```bash
curl -sN -X POST "$BASE/knowledge-retrieval/chat/completions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "用两三句话介绍 RAG"}],
    "stream": true,
    "conversationId": "curl-stream-1"
  }'
```

输出为多段 `data: {...}`；每段 JSON 里 **`choices[0].delta.content`** 为增量；结束帧含 **`"finish_reason":"stop"`**。更稳妥的解析方式见上文 **6.2.2** 前端流式示例。

**6）尝试触发联网搜索**（需 **`RAG_ENABLE_WEB_SEARCH=true`** 且服务器能访问 DuckDuckGo；是否调用 `web_search` 由模型选工具决定，可多试几种问法）

```bash
curl -s -X POST "$BASE/knowledge-retrieval/chat/completions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "请用联网搜索简要概括：近期一条与本项目无关的公开科技新闻标题级信息（说明来自网络）"}],
    "stream": false,
    "conversationId": "curl-web-search-1"
  }' | jq .
```

可在服务端日志中搜索 **`RAG: web_search`** 或 **`RAG: 搜索:`** 确认是否走到搜索工具。

**7）批量 PDF**（Python，非 curl）

```bash
cd /path/to/llm_AIO
python scripts/rag_ingest_pdfs.py --dir /path/to/pdf_folder \
  --base "$BASE" --user admin --password 'admin123'
```

---

##### 6.2.5 RAG 向量库索引摘要（查看已入库文档）

**端点**: `GET /api/v1/knowledge-retrieval/library`

**描述**: 只读查看当前 RAG **Chroma** 索引：持久化路径（配置值与解析后的绝对路径）、集合名、**chunk 总数**、根据元数据汇总的 **`unique_sources`**（上传时的原始文件名；**新入库**接口会为每块写入 `source_file`，旧数据可能仅有 PyPDF 的 `source` 临时路径 basename）。**不依赖** LangGraph 是否 `ready`，也**不调用**嵌入 API。

**权限**: `VIEW_KNOWLEDGE_BASE`

**Query 参数**：

| 参数 | 说明 | 默认 |
|------|------|------|
| `metadata_scan_limit` | 为汇总 `unique_sources` 最多扫描的元数据条数（≤ 100000） | `20000` |

**请求头**：`Authorization: Bearer <token>`

**响应示例**（200）：

```json
{
  "persist_directory": "chroma_db_rag",
  "persist_directory_resolved": "/home/llm/PycharmProjects/llm_AIO/chroma_db_rag",
  "collection_name": "demo001",
  "chunk_count": 128,
  "unique_sources": ["manual.pdf", "notes.pdf"],
  "scanned_metadata_rows": 128,
  "has_chunks_without_source_metadata": false,
  "storage_hint": "向量与分块元数据在服务端 persist_directory 下；通过 ingest-pdf 上传的 PDF 默认不落盘保留原文件，仅写入向量与元数据。"
}
```

若目录或集合尚不存在，可能带 `note`；仅部分扫描时可能带 `note_truncated`。

---

##### 6.2.6 教师/管理员：暂停、清空、按文档删除（向量知识库）

以下接口均需 **`MANAGE_KNOWLEDGE_BASE`**（默认 **超级管理员、教师**；学生 **403**）。

**说明**：**暂停**（`vector_kb_disabled=true`）后，**`POST .../ingest-pdf`** 与 **`POST .../chat/completions`** 返回 **503**；**`GET .../library`**、**`GET .../status`**、**清空/按文件删除**仍可调用（便于维护）。**清空或大量删块后**，建议 **重启网关**，以免进程内 LangGraph 已绑定的 Chroma 客户端与磁盘状态不一致。

###### `GET /api/v1/knowledge-retrieval/admin/vector-settings`

返回当前 `vector_kb_disabled`、`note`、`updated_by_id`、`updated_at`。

###### `PUT /api/v1/knowledge-retrieval/admin/vector-settings`

**JSON 体**：

```json
{
  "vector_kb_disabled": true,
  "note": "期末考试封库，暂停更新"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `vector_kb_disabled` | bool | ✓ | `true` 暂停入库与对话；`false` 恢复 |
| `note` | string | | 可选，最长 2000 字 |

**响应**：`{ "ok": true, "message": "…", ...状态字段 }`。

###### `DELETE /api/v1/knowledge-retrieval/library`

删除当前环境下 **整个 Chroma 集合**（**清空向量知识库**）。

###### `DELETE /api/v1/knowledge-retrieval/library/by-source?source_file=某.pdf`

删除元数据中 **`source_file`**（或与旧数据 `source` basename）等于该文件名的**所有分块**。典型「编辑」：**先删再 `ingest-pdf` 同文件名**。

---

##### 6.2.7 环境变量与测试

**RAG 相关环境变量（后端 `.env`）**：

```env
# 关闭后跳过 LangGraph 初始化，主服务仍可启动
RAG_ENABLED=true
# qwen | openai | oneapi | ollama（与 rag_llms 中配置一致）
RAG_LLM_TYPE=qwen
RAG_CHROMADB_DIRECTORY=chroma_db_rag
RAG_CHROMADB_COLLECTION=demo001
RAG_LANGGRAPH_SQLITE=sqlite:///./data/langgraph_rag.db
RAG_ENABLE_WEB_SEARCH=true
# 阿里云兼容模式时需配置
# DASHSCOPE_API_KEY=sk-...
```

**相关测试**：

- 单元 / 接口（排版逻辑不依赖完整依赖；若本机可 `import app.main` 则同时跑 mock 接口用例）：
  ```bash
  python -m unittest tests.test_rag_retrieval -v
  ```
- 联调脚本 `tests/test_rag_retrieval_live.py`：**直接运行即可**，默认连 `http://127.0.0.1:8000/api/v1` 且**不**自动起 uvicorn（适配 `systemctl` 已托管）。按环境修改脚本内常量 `DEFAULT_RAG_LIVE_BASE` / `DEFAULT_RAG_LIVE_AUTO_SERVER` 等即可，**不必**事先 `export`（环境变量仍可覆盖常量）。
  ```bash
  python tests/test_rag_retrieval_live.py
  ```
  - 开发机需要脚本临时起 uvicorn：将脚本内 `DEFAULT_RAG_LIVE_AUTO_SERVER = True`，或 `export RAG_LIVE_AUTO_SERVER=1`。
  - CI 跳过：`RAG_LIVE_TEST=0 python tests/test_rag_retrieval_live.py`。
  - systemd 可选在 unit 中写 `Environment=RAG_LIVE_BASE=https://.../api/v1`，与脚本内常量二选一。

---

### 7. 系统监控接口

#### 7.1 GPU监控

**端点**: `GET /api/v1/monitor/gpu`

**描述**: 获取详细的GPU使用情况（支持多GPU）

**权限**: 超级管理员、教师

---

### 8. 竞赛报名系统接口

> **注意**：**仅接受第二套 Alt JWT**（`POST /api/alt-identity/session` 签发）。请求头：`Authorization: Bearer <alt_access_token>`。  
> 竞赛相关表中的 **`student_id` / `team_members.user_id` / `captain_id` / `submitter_id` / `reviewer_id`** 等整型字段语义均为 **`alt_auth_users.id`**，**不再引用**主库 **`users.id`**；ORM 已去掉对 `users` 的外键与关联。从旧版本升级时：可 **清空竞赛相关数据**，或运行仓库脚本 **`python scripts/migrate_competition_user_ids_to_alt.py --dry-run`** 预览、去掉 `--dry-run` 执行，将旧 **`users.id`** 按 **username / email** 匹配改写为 **`alt_auth_users.id`**（支持 **`--mapping-csv`** 手工覆盖）。  
> 作品上传落 **`files`** 表时 **`sender_id` 可为空**（不强制主站用户）。

#### 竞赛第二套帐号：四类角色

| 角色（`role` / JWT claim） | 说明 | 赛制与运维 | 报名/组队/作品 | 查看名单与作品范围 | 评分 |
|---------------------------|------|------------|----------------|-------------------|------|
| **`super_admin`（管理员）** | 竞赛系统最高权限 | ✅ 创建/发布/修改/删除/锁定（停止报名） | ❌ | ✅ 可看全竞赛作品、`GET …/participants/*` | ❌ |
| **`advisor`（指导老师）** | 与 `teacher` 并存，竞赛侧权限一致 | ❌ 无 `MANAGE_COMPETITIONS` | ✅ 可建队、拉人、`PATCH` 队名、踢队员；❌ **不能**报名、`join_team`/`leave`/`transfer`、`POST`/`upload` 作品 | ✅ 可看 `GET …/teams`、**只读** `GET …/participants/*`；❌ **不能**看别人作品详情/下载、本赛全量 `GET …/submissions` | ❌ |
| **`teacher`（教师）** | 与 `advisor` 并存，竞赛侧权限一致 | ❌ 无 `MANAGE_COMPETITIONS` | ✅ 可建队、拉人、`PATCH` 队名、踢队员；❌ **不能**报名、`join_team`/`leave`/`transfer`、`POST`/`upload` 作品 | ✅ 可看 `GET …/teams`、**只读** `GET …/participants/*`；❌ **不能**看别人作品详情/下载、本赛全量 `GET …/submissions` | ❌ |
| **`expert`（专家）** | 必须由管理员核验并指派到具体竞赛后才可批改 | ❌ | ❌ | ✅ 被指派的竞赛：**全量 submissions**、花名册、`GET`/下载；✅ **`scores/summary`、`scores/rankings`** | ✅ 仅被指派的 **`expert_verified=true`** 帐号可 `PUT`/`PATCH …/review-grade` |
| **`student`（学生）** | — | ❌ | ✅ 报名、自建队、`join`、`transfer`、`leave`；组队提交作品 **必须由队长** 调用 `POST …/submissions*` | ✅ 仅本人个人作品或与本人相关的队伍提交；❌ participants 名册 | ❌ |

**专家注册与指派**：用户可在 **`POST /api/alt-identity/register`** 选择 **`role=expert`**，注册成功时 **`expert_verified=false`**，**不可登录**（`POST /api/alt-identity/session` 返回 **403**）。管理员通过 **`GET /api/v1/competitions/experts`** 拉取 **全部专家帐号**（含各专家已指派的竞赛 id 列表）；列表页点「指派」弹窗选择竞赛后 **`POST …/competitions/{cid}/experts/{expert_user_id}`**，取消指派用 **`DELETE`** 同路径。核验身份：**`PATCH …/admin/alt-users/{id}`** 设 **`expert_verified=true`**（须先于指派）。同一专家可指派多场竞赛，同一竞赛可有多名专家。

**统一鉴权请求头**：
```
Authorization: Bearer <alt_access_token>
Content-Type: application/json
```

> 说明：下文示例均以 `http://localhost:8000` 为 Base URL。将 **`<alt_access_token>`** 替换为 **§8.0.2** `POST /api/alt-identity/session` 响应中的 `access_token`（或通过 **§8.0.3** 刷新得到的新 token）。**切勿**使用主站 **`POST /api/v1/auth/login`** 的 token，否则竞赛接口将 **401 Not authenticated**。管理员、指导老师、专家、学生角色权限不同（见上表）；请求头写法相同，均为第二套 JWT。

#### 8.0 第二套独立登录 / 注册（Alt Identity）

> **定位**：与 `/api/v1/auth/*` **完全隔离** 的另一套账号体系（独立库 **`alt_auth.db`**、独立 JWT 密钥、独立用户表 `alt_auth_users`）。请求体为 **`application/json`**，**不是** OAuth2 表单。  
> **与主站对齐**：注册/登录**字段名与语义**与 `POST /api/v1/auth/register`、`UserLogin` 一致（见上文 **1.1 / 1.2**）；**仅注册多出必填字段** **`school`**。  
> **与竞赛接口关系**：**`/api/v1/competitions/*`** 全部使用第二套 JWT 与 **`alt_auth_users`** 角色（`ROLE_PERMISSIONS`）鉴权；下列 **`/api/alt-identity/*`** 用于注册、登录与查看当前第二套身份。

**前缀**: `/api/alt-identity`（与 `/api/v1` 区分）

**可选环境变量**（`.env`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ALT_AUTH_DATABASE_URL` | `sqlite:///./alt_auth.db` | 第二套用户库 |
| `ALT_AUTH_JWT_SECRET` | （内置占位，生产必改） | 与主站 `SECRET_KEY` 分离 |
| `ALT_AUTH_TOKEN_EXPIRE_MINUTES` | `1440` | JWT 有效期（分钟） |

**默认管理员**（与上文「默认管理员账户」一致）：第二套在 `alt_auth.db` 无 `username=admin` 时自动创建 `super_admin`，登录 `POST /api/alt-identity/session` 使用相同用户名与密码。**首次登录后请及时改密。**

##### 8.0.1 注册

**端点**: `POST /api/alt-identity/register`  
**权限**: 无需认证（与 `POST /api/v1/auth/register` 相同策略：公开注册）

**请求体**（JSON）：与主站 **UserCreate** 相同字段 + **`school`**（必填）。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | ✓ | 与主站一致，1–100 字符，去空白后非空 |
| email | string | ✓ | 合法邮箱（`EmailStr`） |
| full_name | string | | 可选 |
| password | string | ✓ | 与主站一致，**最少 6 位**，最长 128 |
| role | string | ✓ | **`student`** \| **`advisor`** \| **`teacher`** \| **`expert`** |
| student_id | string | | 可选 |
| teacher_id | string | | 可选 |
| school | string | ✓ | **相对主站多出的字段**：学校名称，1–200 字符，去空白后非空 |

**说明**：**`super_admin`** 不可自助注册。选 **`expert`** 时注册成功但 **`expert_verified` 恒为 `false`**，须等管理员核验（§8.0.6）并指派赛事（§8.0.7）后方可登录评分。`teacher` 与 `advisor` 在竞赛侧并存，不做自动角色转换。

**响应**（201）：与主站 **`UserResponse`** 形态一致（`id`、`username`、`email`、`full_name`、`role`、`is_active`、`student_id`、`teacher_id`、`created_at`），并包含 **`school`**、**`expert_verified`**（专家注册为 **`false`**，其它角色一般为 **`false`**）。

**错误**：`400` — 校验失败，或 `detail` 为 **`Username or email already registered`**（与主站注册重复语义一致）。`500` — 服务端异常，`detail` 含错误类型简述。

**curl 示例**：

```bash
curl -s -X POST "http://localhost:8000/api/alt-identity/register" ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"stu001\",\"email\":\"student01@school.edu\",\"full_name\":\"张三\",\"password\":\"secret12\",\"role\":\"student\",\"school\":\"示例大学\"}"
```

##### 8.0.2 登录（签发第二套会话令牌）

**端点**: `POST /api/alt-identity/session`  
**权限**: 无需认证（对应主站登录语义；路径不使用 `/login` 以免混淆）

**请求体**（JSON）：与 **`UserLogin`** 一致。

| 字段 | 类型 | 必填 |
|------|------|------|
| username | string | ✓ |
| password | string | ✓ |

**响应**（200）：与主站登录 **`Token`** 一致：`access_token`、`token_type`（`bearer`）、`user_id`、`role`、`full_name`，并 **额外返回** **`school`**（历史数据可能为 `null`）。

**停用账号**：`is_active=false` 时 **`403`**，`detail`：`User account is inactive`（与主站一致）。  
**专家待审核**：`role=expert` 且 **`expert_verified=false`** 时 **`403`**，`detail`：`Expert account pending verification; please wait for administrator approval`（须管理员 **§8.0.6** 核验后方可登录）。  
**凭据错误**：**`401`**，`detail`：`Incorrect username or password`。

**curl 示例**：

```bash
curl -s -X POST "http://localhost:8000/api/alt-identity/session" ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"stu001\",\"password\":\"secret12\"}"
```

##### 8.0.3 刷新访问令牌（需第二套 JWT）

**端点**: `POST /api/alt-identity/refresh-token`  
**权限**: 与主站 `POST /api/v1/auth/refresh-token` 相同策略——请求头携带 **`Authorization: Bearer <alt_access_token>`**（须为未过期的第二套 JWT）。

**请求体**: 无（或空 JSON 均可，服务端不读 body）。

**响应**（200）：与 **8.0.2 登录** 相同字段（`access_token`、`token_type`、`user_id`、`role`、`full_name`、`school`）。

**curl 示例**：

```bash
curl -s -X POST "http://localhost:8000/api/alt-identity/refresh-token" ^
  -H "Authorization: Bearer <alt_access_token>"
```

##### 8.0.4 当前身份与权限列表（需第二套 JWT）

**端点**: `GET /api/alt-identity/me`  
**权限**: 须在请求头携带 **`Authorization: Bearer <alt_access_token>`**（与主站 Token **不可互换**）。

**响应**（200）：`id`、`username`、`email`、`full_name`、`role`、`is_active`、`student_id`、`teacher_id`、`school`、`created_at`，**`expert_verified`**（专家资质是否已由管理员核验），**`assigned_competition_ids`**（`role=expert` 时为本帐号已被指派的竞赛 id 列表，否则为 `[]`），以及 **`effective_permissions`**（字符串数组，即 **`ROLE_PERMISSIONS`** 对该角色展开）。

**响应示例**（专家，已指派竞赛 1、3）：

```json
{
  "id": 12,
  "username": "expert1",
  "role": "expert",
  "expert_verified": true,
  "assigned_competition_ids": [1, 3],
  "effective_permissions": ["view_competitions", "review_submissions"]
}
```

**curl 示例**：

```bash
curl -s "http://localhost:8000/api/alt-identity/me" ^
  -H "Authorization: Bearer <alt_access_token>"
```

##### 8.0.5 与其它接口的共存说明

1. Swagger 分组名为 **Alt Identity — independent auth**，可与主站接口对照调试。  
2. 服务端注册 **`/api/alt-identity`** 路由时须在通用文件路由 **`/api/{file_category}/...`** **之前**，否则路径可能被误解析（部署本仓库已实现该顺序）。  
3. **密码**：第二套仅存 **BCrypt** 哈希，与主库 `users` 表互不关联。

##### 8.0.6 管理员：调整第二套帐号（竞赛专家核验 / 改角）

**端点**：`PATCH /api/v1/competitions/admin/alt-users/{target_user_id}`  
**权限**：仅 **`super_admin`**（第二套 JWT）。

**描述**：变更某 **`alt_auth_users`** 记录的 **`role`**、**`expert_verified`**。典型流程：**先以学生身份注册占位帐号** → 管理员将 **`role` 设为 `expert`** 并将 **`expert_verified`** 设为 **`true`** → 再为该赛指派（**§8.0.7**）。

**请求体 JSON**（均可选字段，但至少传其一）：
| 字段 | 类型 | 说明 |
|------|------|------|
| role | string | `student` \| `advisor` \| `expert` \| `super_admin` |
| expert_verified | bool | **`true`** 仅当 **`role`** 为 **`expert`** 时有意义 |

**响应**（200）：`{ "id", "role", "expert_verified" }`。改角后客户端应 **`POST /session` 重新登录** 换新 JWT。

**curl**：
```bash
curl -X PATCH "http://localhost:8000/api/v1/competitions/admin/alt-users/12" ^
  -H "Authorization: Bearer <admin_alt_token>" ^
  -H "Content-Type: application/json" ^
  -d "{\"role\":\"expert\",\"expert_verified\":true}"
```

##### 8.0.7 管理员：专家列表与指派 / 取消指派

**专家列表（全局，供管理页 + 指派弹窗）**

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/v1/competitions/experts` | 列出 **全部** 专家帐号（`role=expert`），含每人已指派的竞赛 id 列表 |

**权限**：**`super_admin`**（第二套 JWT）。

**`GET` 响应**（200）示例：

```json
{
  "total": 2,
  "items": [
    {
      "expert_user_id": 12,
      "username": "expert1",
      "email": "expert1@school.edu",
      "full_name": "专家甲",
      "school": "示例大学",
      "expert_verified": true,
      "assigned_competition_ids": [1, 3]
    },
    {
      "expert_user_id": 15,
      "username": "expert_new",
      "email": "expert_new@school.edu",
      "full_name": "待审专家",
      "school": "示例大学",
      "expert_verified": false,
      "assigned_competition_ids": []
    }
  ]
}
```

- **`assigned_competition_ids`**：该专家已被指派的竞赛 id（可 **0 个、1 个或多个**）。
- **`expert_verified`**：`true` 才可登录；指派前须 **`PATCH …/admin/alt-users/{id}`** 核验。

**竞赛下拉**：弹窗中选择目标竞赛时，可调用 **`GET /api/v1/competitions/`** 获取竞赛列表。

**指派 / 取消指派（按「竞赛 + 专家」维度）**

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/v1/competitions/{competition_id}/experts/{expert_user_id}` | 将专家指派到该竞赛（须 **`expert_verified=true`**） |
| `DELETE` | `/api/v1/competitions/{competition_id}/experts/{expert_user_id}` | 取消该专家在本赛的指派 |

均为 **`super_admin`**。`POST` 成功 **`201`**：`{"ok": true}`。

**前端推荐流程**：

1. `GET /api/v1/competitions/experts` 渲染专家列表；展示 `assigned_competition_ids` 与核验状态。
2. 点击「指派」→ 弹窗内 `GET /api/v1/competitions/` 选竞赛 → `POST …/competitions/{cid}/experts/{expert_user_id}`。
3. 取消某场指派 → `DELETE …/competitions/{cid}/experts/{expert_user_id}`。
4. 同一专家可对多场竞赛重复步骤 2；同一竞赛可对多名专家分别指派。

**curl 示例**：

```bash
curl "http://localhost:8000/api/v1/competitions/experts" \
  -H "Authorization: Bearer <admin_alt_token>"

curl -X POST "http://localhost:8000/api/v1/competitions/1/experts/12" \
  -H "Authorization: Bearer <admin_alt_token>"

curl -X DELETE "http://localhost:8000/api/v1/competitions/1/experts/12" \
  -H "Authorization: Bearer <admin_alt_token>"
```


---

#### 8.1 创建竞赛（管理员）
**端点**: `POST /api/v1/competitions/`
**权限**: `MANAGE_COMPETITIONS`（**仅** `super_admin`；指导老师 **`advisor`** 无此权限）

**请求格式**（二选一，`Content-Type` 必须与实际一致）：

| 类型 | Content-Type | 说明 |
|------|----------------|------|
| JSON | `application/json` | 与原先一致；仅文本字段 |
| multipart | `multipart/form-data` | 文本字段同名；按组别策略上传二维码（见下表） |

**学历组别与二维码**：

| division_mode | 含义 |
|---------------|------|
| `single` | 不分本科/高职（默认） |
| `dual` | 分本科组、高职组 |

| qr_layout | 适用 | 含义 |
|-----------|------|------|
| `shared` | `dual` 或 `single` | 共用一个二维码（`single` 时固定为此策略） |
| `separate` | 仅 `dual` | 本科、高职各一张二维码 |

**二维码上传（multipart 可选）**：支持 png / jpeg / gif / webp，单文件最大 **5MiB**。

| 场景 | 文件字段 |
|------|----------|
| 不分组 / 双组共用 | `qr_code_image` 或 `qr_code_image_shared` |
| 双组分开 | `qr_code_image_undergraduate`、`qr_code_image_vocational` |

创建成功后响应含 **`qr_codes`**（结构化 URL）及兼容字段 **`qr_code_image_url`**（`single` 或 `dual+shared` 时）。

**请求体参数**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✓ | 竞赛名称 |
| description | string | | 简介 |
| rules_text | string | | 规则说明 |
| start_at | string(datetime) | | 开始时间（ISO8601） |
| end_at | string(datetime) | | 结束时间（ISO8601） |
| allow_individual | bool | | 是否允许个人参赛（默认 true） |
| allow_team | bool | | 是否允许团队参赛（默认 true） |
| division_mode | string | | `single`（默认）或 `dual` |
| qr_layout | string | | `dual` 时：`shared`（默认）或 `separate` |
| qr_code_image | file | | **仅 multipart**：共用/单组别二维码 |
| qr_code_image_undergraduate | file | | **仅 multipart**：本科组二维码（`dual`+`separate`） |
| qr_code_image_vocational | file | | **仅 multipart**：高职组二维码（`dual`+`separate`） |

**请求示例（JSON）**：
```bash
curl -X POST "http://localhost:8000/api/v1/competitions/" \
  -H "Authorization: Bearer <alt_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Test Competition",
    "description":"desc",
    "rules_text":"rules",
    "allow_individual":true,
    "allow_team":true
  }'
```

**请求示例（multipart + 二维码）**：
```bash
curl -X POST "http://localhost:8000/api/v1/competitions/" \
  -H "Authorization: Bearer <alt_access_token>" \
  -F 'name=Test Competition' \
  -F 'description=desc' \
  -F 'rules_text=rules' \
  -F 'allow_individual=true' \
  -F 'allow_team=true' \
  -F 'qr_code_image=@/path/to/qrcode.png'
```

**响应示例**（201，无二维码时 `qr_code_path` / `qr_code_image_url` 为 null）：
```json
{
  "id": 1,
  "name": "Test Competition",
  "description": "desc",
  "rules_text": "rules",
  "start_at": null,
  "end_at": null,
  "allow_individual": true,
  "allow_team": true,
  "status": "draft",
  "created_at": "2026-03-18T07:00:00.000000",
  "updated_at": "2026-03-18T07:00:00.000000",
  "division_mode": "dual",
  "qr_layout": "separate",
  "qr_code_path": null,
  "qr_code_path_undergraduate": "competition_qr_codes/comp_1_undergraduate_xxx.png",
  "qr_code_path_vocational": "competition_qr_codes/comp_1_vocational_xxx.png",
  "qr_codes": {
    "shared": null,
    "undergraduate": {
      "path": "competition_qr_codes/comp_1_undergraduate_xxx.png",
      "image_url": "/api/v1/competitions/1/qr-code?division=undergraduate"
    },
    "vocational": {
      "path": "competition_qr_codes/comp_1_vocational_xxx.png",
      "image_url": "/api/v1/competitions/1/qr-code?division=vocational"
    }
  },
  "qr_code_image_url": null
}
```

> 单条竞赛详情、列表及二维码下载见 **§8.1.1**、**§8.1.2**。

#### 8.1.1 获取竞赛详情（单条）
**端点**: `GET /api/v1/competitions/{competition_id}`
**权限**: `VIEW_COMPETITIONS`（学生、指导老师、管理员等具备该权限的角色均可）

**描述**: 按竞赛 ID 返回单场竞赛的完整信息，供**详情页**展示名称、规则、时间、是否允许个人/组队、学历组别策略及二维码下载地址等。  
与 **`GET /api/v1/competitions/`**（列表）相比，本接口返回单条记录且包含结构化的 **`qr_codes`**，便于前端在「本科详情 / 高职详情」中只展示对应组别的二维码。

**路径参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| competition_id | int | ✓ | 竞赛 ID |

**Query 参数**：无（前端在 `division_mode=dual` 时通过路由/状态保存当前组别 `undergraduate` / `vocational`，从响应 `qr_codes` 中取对应项即可，无需在本接口传 `division`）。

**请求示例**：
```bash
curl "http://localhost:8000/api/v1/competitions/1" \
  -H "Authorization: Bearer <alt_access_token>"
```

**响应字段说明**（200，`CompetitionResponse`）：
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 竞赛 ID |
| name | string | 竞赛名称 |
| description | string/null | 简介 |
| rules_text | string/null | 规则说明 |
| start_at | string(datetime)/null | 开始时间 |
| end_at | string(datetime)/null | 结束时间 |
| allow_individual | bool | 是否允许个人赛道报名 |
| allow_team | bool | 是否允许组队赛道报名 |
| status | string | `draft` / `published` / `closed` |
| division_mode | string | `single` 不分组；`dual` 分本科组与高职组 |
| qr_layout | string | `shared` 共用一码；`separate` 两组各一码（仅 `dual` 有意义） |
| qr_code_path | string/null | 共用二维码存储路径 |
| qr_code_path_undergraduate | string/null | 本科组二维码路径（`dual`+`separate`） |
| qr_code_path_vocational | string/null | 高职组二维码路径（`dual`+`separate`） |
| qr_codes | object/null | 结构化二维码：`shared` / `undergraduate` / `vocational`，每项含 `path`、`image_url` |
| qr_code_image_url | string/null | 兼容字段：`single` 或 `dual+shared` 时的单 URL；`dual+separate` 时为 null |
| created_at | string(datetime) | 创建时间 |
| updated_at | string(datetime) | 更新时间 |

**响应示例（`dual` + `separate`，详情页按组别取 `qr_codes`）**：
```json
{
  "id": 1,
  "name": "2026 技能竞赛",
  "description": "简介",
  "rules_text": "规则全文",
  "start_at": null,
  "end_at": null,
  "allow_individual": true,
  "allow_team": true,
  "status": "published",
  "division_mode": "dual",
  "qr_layout": "separate",
  "qr_code_path": null,
  "qr_code_path_undergraduate": "competition_qr_codes/comp_1_undergraduate_xxx.png",
  "qr_code_path_vocational": "competition_qr_codes/comp_1_vocational_xxx.png",
  "qr_codes": {
    "shared": null,
    "undergraduate": {
      "path": "competition_qr_codes/comp_1_undergraduate_xxx.png",
      "image_url": "/api/v1/competitions/1/qr-code?division=undergraduate"
    },
    "vocational": {
      "path": "competition_qr_codes/comp_1_vocational_xxx.png",
      "image_url": "/api/v1/competitions/1/qr-code?division=vocational"
    }
  },
  "qr_code_image_url": null,
  "created_at": "2026-03-18T07:00:00.000000",
  "updated_at": "2026-03-18T07:00:00.000000"
}
```

**响应示例（`single` 或 `dual` + `shared`）**：
```json
{
  "id": 2,
  "name": "通用赛",
  "division_mode": "single",
  "qr_layout": "shared",
  "qr_code_path": "competition_qr_codes/comp_2_shared_xxx.png",
  "qr_codes": {
    "shared": {
      "path": "competition_qr_codes/comp_2_shared_xxx.png",
      "image_url": "/api/v1/competitions/2/qr-code"
    },
    "undergraduate": null,
    "vocational": null
  },
  "qr_code_image_url": "/api/v1/competitions/2/qr-code",
  "status": "published",
  "allow_individual": true,
  "allow_team": true
}
```

**前端对接建议**：
| 步骤 | 做法 |
|------|------|
| 列表点「查看详情」 | 若 `division_mode === 'dual'`，弹窗选本科/高职（纯前端），再进入详情页 |
| 进入详情页 | 调用本接口拉取数据；`division` 保存在页面状态（不必作为 query 传给本接口） |
| 展示二维码 | `separate`：本科页用 `qr_codes.undergraduate.image_url`；高职页用 `qr_codes.vocational`；`shared`/`single`：用 `qr_code_image_url` 或 `qr_codes.shared` |
| 报名 | `POST /enroll` 或 `POST /teams` 时在 body 中带与当前详情页一致的 **`division`**（见 §8.7、§8.12） |

**错误响应**：
| 状态码 | 说明 |
|--------|------|
| 401 | 未登录或 Token 无效 |
| 403 | 无 `VIEW_COMPETITIONS` 权限 |
| 404 | `{"detail": "Competition not found"}` |

**相关接口**：
- 竞赛列表：`GET /api/v1/competitions/`（§8.1.2）
- 二维码图片二进制：`GET /api/v1/competitions/{competition_id}/qr-code`（§8.1.2）
- 我是否已报名及组别：`GET /api/v1/competitions/enrollments/me`（§8.6）

> **组别与报名**：同一学生**不能**在同一竞赛同时报名本科组与高职组；详情页进入某组后，报名/建队须隐式携带对应 `division`（见 §8.7、§8.12）。

#### 8.1.2 竞赛列表与二维码图片
**竞赛列表**  
**端点**: `GET /api/v1/competitions/`  
**权限**: `VIEW_COMPETITIONS`  
**描述**: 返回全部竞赛，按创建时间倒序；字段与 **§8.1.1** 单条响应相同（含 `division_mode`、`qr_codes`）。用于管理端列表、专家指派弹窗选赛等。

**请求示例**：
```bash
curl "http://localhost:8000/api/v1/competitions/" \
  -H "Authorization: Bearer <alt_access_token>"
```

**获取竞赛二维码图片（二进制）**  
**端点**: `GET /api/v1/competitions/{competition_id}/qr-code`  
**权限**: `VIEW_COMPETITIONS`  

| 条件 | Query |
|------|--------|
| `division_mode=single` 或 `qr_layout=shared` | 无需参数 |
| `division_mode=dual` 且 `qr_layout=separate` | **必填** `division=undergraduate` 或 `division=vocational` |

未上传对应图片时 **404**。亦可直接使用 **§8.1.1** 响应中 `qr_codes.*.image_url` 作为图片地址（需带相同 `Authorization`）。

#### 8.2 发布竞赛（管理员）
**端点**: `PUT /api/v1/competitions/{competition_id}/publish`
**权限**: `MANAGE_COMPETITIONS`（**仅** `super_admin`）

**路径参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| competition_id | int | ✓ | 竞赛 ID |

**请求示例**：
```bash
curl -X PUT "http://localhost:8000/api/v1/competitions/1/publish" \
  -H "Authorization: Bearer <alt_access_token>"
```

**响应示例**（200）：
```json
{
  "id": 1,
  "status": "published",
  "name": "Test Competition",
  "allow_individual": true,
  "allow_team": true
}
```

#### 8.3 修改竞赛（管理员）
**端点**: `PUT /api/v1/competitions/{competition_id}`
**权限**: `MANAGE_COMPETITIONS`（**仅** `super_admin`）

**描述**: 修改竞赛信息（名称、描述、规则、时间、参赛模式、学历组别与二维码策略等）。**只传需要修改的字段**；未传的文本字段保持不变，未传的二维码文件不替换。

**路径参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| competition_id | int | ✓ | 竞赛 ID |

**请求格式**（二选一，`Content-Type` 必须与实际一致）：

| 类型 | Content-Type | 说明 |
|------|----------------|------|
| JSON | `application/json` | 仅文本字段；语义同 `exclude_unset`，只更新请求体中出现的键 |
| multipart | `multipart/form-data` | 文本字段**仅提交需修改项**；可按组别策略上传/替换二维码（规则同 **§8.1**） |

**学历组别与二维码**（与 **§8.1 创建竞赛** 一致）：

| division_mode | 含义 |
|---------------|------|
| `single` | 不分本科/高职 |
| `dual` | 分本科组、高职组 |

| qr_layout | 适用 | 含义 |
|-----------|------|------|
| `shared` | `dual` 或 `single` | 共用一个二维码（`single` 时服务端固定为此策略） |
| `separate` | 仅 `dual` | 本科、高职各一张二维码 |

**二维码上传（multipart 可选）**：支持 png / jpeg / gif / webp，单文件最大 **5MiB**。上传新图后替换对应路径上的旧文件；**未传的文件字段保留原图**。

| 场景 | 文件字段 |
|------|----------|
| 不分组 / 双组共用 | `qr_code_image` 或 `qr_code_image_shared` |
| 双组分开 | `qr_code_image_undergraduate`、`qr_code_image_vocational`（可只传其中一张以单独替换） |

> 修改 `division_mode` / `qr_layout` 时，请与实际上传的二维码字段一致；`single` 时若改为 `dual+separate`，需补传两张分组码（或先改策略再分次上传）。

**请求体参数**（均可选，只传需要改的）：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | | 竞赛名称 |
| description | string | | 简介 |
| rules_text | string | | 规则说明 |
| start_at | string(datetime) | | 开始时间（ISO8601） |
| end_at | string(datetime) | | 结束时间（ISO8601） |
| allow_individual | bool | | 是否允许个人参赛 |
| allow_team | bool | | 是否允许团队参赛 |
| division_mode | string | | `single` 或 `dual` |
| qr_layout | string | | `dual` 时：`shared` 或 `separate` |
| qr_code_image | file | | **仅 multipart**：共用/单组别二维码（替换 `qr_code_path`） |
| qr_code_image_undergraduate | file | | **仅 multipart**：本科组二维码（`dual`+`separate`） |
| qr_code_image_vocational | file | | **仅 multipart**：高职组二维码（`dual`+`separate`） |

**请求示例（JSON，只改文案与组别策略）**：
```bash
curl -X PUT "http://localhost:8000/api/v1/competitions/1" \
  -H "Authorization: Bearer <alt_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "rules_text":"Updated rules v2",
    "description":"New description",
    "division_mode":"dual",
    "qr_layout":"shared"
  }'
```

**请求示例（multipart，替换共用二维码）**：
```bash
curl -X PUT "http://localhost:8000/api/v1/competitions/1" \
  -H "Authorization: Bearer <alt_access_token>" \
  -F 'description=New description' \
  -F 'qr_code_image=@/path/to/qrcode.png'
```

**请求示例（multipart，仅替换本科组二维码）**：
```bash
curl -X PUT "http://localhost:8000/api/v1/competitions/1" \
  -H "Authorization: Bearer <alt_access_token>" \
  -F 'qr_code_image_undergraduate=@/path/ug.png'
```

**响应示例**（200；结构同 **§8.1** 创建响应）：
```json
{
  "id": 1,
  "name": "Test Competition",
  "description": "New description",
  "rules_text": "Updated rules v2",
  "start_at": null,
  "end_at": null,
  "allow_individual": true,
  "allow_team": true,
  "status": "published",
  "division_mode": "dual",
  "qr_layout": "separate",
  "created_at": "2026-03-18T07:00:00.000000",
  "updated_at": "2026-03-19T10:00:00.000000",
  "qr_code_path": null,
  "qr_code_path_undergraduate": "competition_qr_codes/comp_1_undergraduate_xxx.png",
  "qr_code_path_vocational": "competition_qr_codes/comp_1_vocational_xxx.png",
  "qr_codes": {
    "shared": null,
    "undergraduate": {
      "path": "competition_qr_codes/comp_1_undergraduate_xxx.png",
      "image_url": "/api/v1/competitions/1/qr-code?division=undergraduate"
    },
    "vocational": {
      "path": "competition_qr_codes/comp_1_vocational_xxx.png",
      "image_url": "/api/v1/competitions/1/qr-code?division=vocational"
    }
  },
  "qr_code_image_url": null
}
```

**说明**：二维码与详情字段见 **§8.1.1**、**§8.1.2**。

#### 8.4 删除竞赛（管理员）
**端点**: `DELETE /api/v1/competitions/{competition_id}`
**权限**: `MANAGE_COMPETITIONS`（**仅** `super_admin`）

**描述**: 删除竞赛及其所有关联数据（报名记录、队伍、作品、评审等），不可恢复。

**请求示例**：
```bash
curl -X DELETE "http://localhost:8000/api/v1/competitions/1" \
  -H "Authorization: Bearer <alt_access_token>"
```

**响应示例**（200）：
```json
{"ok": true, "detail": "Competition 1 and all related data deleted"}
```

#### 8.5 锁定竞赛（管理员）
**端点**: `PUT /api/v1/competitions/{competition_id}/lock`
**权限**: `MANAGE_COMPETITIONS`（**仅** `super_admin`）

**描述**: 手动**停止报名**：将竞赛状态置为 `closed`。含义是**不再接受新的参赛入口**，具体为：
- **禁止**：`POST /enroll` 报名、**新建队伍**（`POST /teams`）、**加入队伍**（`POST /teams/{id}/members`）
- **不禁止**（已报名/已在队内的用户仍可进行）：提交/上传作品、**已指派核验专家**评分（§8.17）、修改竞赛信息（**仅**具备 `MANAGE_COMPETITIONS` 的管理员）、队长转让、队员退队、`POST /withdraw` 退赛等

> 到达或超过 `end_at` 时，也会**自动视为停止报名**（与 `status=closed` 使用同一套校验逻辑）。

> 若需禁止提交或改规则，请通过业务配置（如另行增加「作品截止」字段）或运营流程控制；本接口**仅**表示「关闭报名」。

**请求示例**：
```bash
curl -X PUT "http://localhost:8000/api/v1/competitions/1/lock" \
  -H "Authorization: Bearer <alt_access_token>"
```

**响应示例**（200）：
```json
{
  "id": 1,
  "name": "Test Competition",
  "status": "closed",
  "created_at": "2026-03-18T07:00:00.000000",
  "updated_at": "2026-03-19T10:00:00.000000"
}
```

**停止报名后仍尝试报名/组队返回示例**（400）：
```json
{"detail": "Competition enrollment is closed (status closed or past end date)."}
```

#### 8.6 查看我报名的竞赛

**端点**: `GET /api/v1/competitions/enrollments/me`
**权限**: `VIEW_COMPETITIONS`

**描述**: 列出 **当前第二套帐号 `id`** 在 **`competition_enrollments`** 中 **`status=enrolled`** 的记录（与账号是否「学生角色」无硬编码；**指导老师/管理员等**若从未产生报名行则通常得到 **空数组**）。

**请求示例**：
```bash
curl "http://localhost:8000/api/v1/competitions/enrollments/me" \
  -H "Authorization: Bearer <alt_access_token>"
```

**响应示例**（200）：
```json
[
  {
    "id": 20,
    "competition_id": 10,
    "student_id": 6,
    "team_id": null,
    "is_captain": false,
    "student_no": "2023010001",
    "real_name": "张三",
    "college": "计算机学院",
    "grade": "2023级",
    "contact": "13800000001",
    "status": "enrolled",
    "created_at": "2026-03-19T09:01:05.268978",
    "competition": {
      "id": 10,
      "name": "Test Competition",
      "description": "desc",
      "rules_text": "rules",
      "start_at": null,
      "end_at": null,
      "allow_individual": true,
      "allow_team": true,
      "status": "published",
      "created_at": "2026-03-18T07:00:00.000000",
      "updated_at": "2026-03-18T07:00:00.000000"
    }
  }
]
```

#### 8.7 报名参赛（学生：个人/队伍）

**端点**: `POST /api/v1/competitions/enroll`
**权限**: `ENROLL_COMPETITIONS`

> `team_id = null` 表示个人参赛；传 `team_id` 表示队伍参赛。

**请求体参数**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| competition_id | int | ✓ | 竞赛 ID |
| team_id | int/null | | 为空=个人报名；非空=队伍报名 |
| division | string | 条件 | `dual` 竞赛**必填**：`undergraduate` 或 `vocational`（由详情页隐式传入，无需单独选组 UI） |
| student_no | string | | 学号 |
| real_name | string | | 姓名 |
| college | string | | 学院 |
| grade | string | | 年级（如 `"2023级"`） |
| contact | string | | 联系方式（手机/邮箱） |

**说明（个人报名仅 `competition_id` + `team_id: null` 仍可能 400）**：请求体校验通过后，服务端还会校验竞赛状态与规则。若返回 **400**，请看响应 **`detail` 英文原文** 对照下表（与代码一致）：

| `detail` 内容 | 含义与处理 |
|----------------|------------|
| `Competition not published` | 竞赛仍为 **`draft`**（未发布）。需 **`super_admin`** 执行 **`PUT /api/v1/competitions/{id}/publish`** 后再报名。 |
| `Competition enrollment is closed (status closed or past end date).` | 已停止报名：竞赛 **`status=closed`**，或当前时间 **≥ `end_at`**。需改 `end_at` / 状态或由管理员重新开放（视业务而定）。 |
| `Individual enrollment not allowed` | 该竞赛 **`allow_individual=false`**，不允许个人赛道；只能走组队（`team_id` 传队伍 ID）。 |
| `Team enrollment not allowed` | 组队报名时竞赛 **`allow_team=false`**。 |
| `Already enrolled in the individual track for this competition` | 个人赛道已是 **`enrolled`**，无需重复个人报名（可与组队赛道并存）。 |
| `Already enrolled in the team track for this competition` | 组队赛道已是 **`enrolled`**（`team_id` 报名或已在某队），无需重复。 |
| `Enrollment failed: ...` | 数据库提交失败（如约束冲突），`detail` 后缀为具体异常信息。 |
| `division is required (undergraduate or vocational)` | `division_mode=dual` 但未传 `division`。 |
| `Already enrolled in division 'undergraduate'; cannot enroll in 'vocational' for the same competition` | 已在另一学历组别有效报名，不可跨组（个人+组队赛道均受此限制）。 |
| `division must match team` | 组队报名时 `division` 与队伍所属组别不一致。 |

**非 400 的常见情况**：**403** `Only students can enroll` — 当前第二套 Token 对应账号的有效角色不是 **`student`**（**指导老师 `advisor`/管理员/专家等均不可**在本接口报名）。

> **双组别**：同一学生**不能**同时持有本科组与高职组的有效报名；可在同一组别内同时有个人赛道与组队赛道。

**请求示例（个人）**：
```bash
curl -X POST "http://localhost:8000/api/v1/competitions/enroll" \
  -H "Authorization: Bearer <alt_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "competition_id":1,
    "team_id":null,
    "division":"undergraduate",
    "student_no":"2023010001",
    "real_name":"张三",
    "college":"计算机学院",
    "grade":"2023级",
    "contact":"13800000001"
  }'
```

**请求示例（队伍）**：
```bash
curl -X POST "http://localhost:8000/api/v1/competitions/enroll" \
  -H "Authorization: Bearer <alt_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "competition_id":1,
    "team_id":10,
    "student_no":"2023010002",
    "real_name":"李四",
    "college":"软件学院",
    "grade":"2022级",
    "contact":"li4@example.com"
  }'
```

**响应示例**（201）：
```json
{
  "id": 1,
  "competition_id": 1,
  "student_id": 7,
  "team_id": null,
  "enrollment_scope": "individual",
  "is_captain": false,
  "student_no": "2023010001",
  "real_name": "张三",
  "college": "计算机学院",
  "grade": "2023级",
  "contact": "13800000001",
  "status": "enrolled",
  "created_at": "2026-03-18T07:00:00.000000"
}
```

> **双赛道报名**：同一学生可在同一竞赛**同时**持有个人赛道（`enrollment_scope=individual`，`team_id=null`）与组队赛道（`enrollment_scope=team`，`team_id` 为所属队伍）各一条有效报名。数据库唯一约束为 `(competition_id, student_id, enrollment_scope)`。
>
> **退赛后再次报名**：退赛仅影响对应赛道；再次报名或组队时系统会**复用该赛道原记录**并改回 `enrolled`。

#### 8.8 退赛（学生）

**端点**: `POST /api/v1/competitions/{competition_id}/withdraw`  
**权限**: `ENROLL_COMPETITIONS`  
**说明**: 取消**当前第二套 Token 对应学生**在本竞赛中**某一赛道**的有效报名（`status=enrolled`）。停止报名（`closed` 或已过 `end_at`）后仍可退赛。若个人与组队两条报名均有效，须通过查询参数指定赛道。

**路径参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| competition_id | int | ✓ | 竞赛 ID |

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| track | string | 条件必填 | `individual`（个人赛道）或 `team`（组队赛道）。仅一条有效报名时可省略；两条同时存在时**必填**，否则 `400`。 |

**行为摘要**：
| 情形 | 处理 |
|------|------|
| `track=individual` 或仅个人报名 | 个人报名状态改为 `withdrawn`（不影响组队赛道） |
| `track=team` 且非队长 | 从 `team_members` 移除，组队报名改为 `withdrawn` |
| `track=team` 且为队长，队内仍有其他成员 | `400`，需先 **队长转让** 后再退赛 |
| `track=team` 且为队长且队内仅自己 | 移除成员、队伍标记为 `disbanded`，组队报名改为 `withdrawn` |

**请求示例**（仅退个人赛道）：
```bash
curl -X POST "http://localhost:8000/api/v1/competitions/1/withdraw?track=individual" \
  -H "Authorization: Bearer <alt_access_token>"
```

**响应示例**（200）：与报名接口结构相同，`status` 为 `"withdrawn"`。

**常见错误**：
| 状态码 | 说明 |
|--------|------|
| 400 | 队长未转让即退赛等 |
| 403 | 非学生角色 |
| 404 | 无有效报名 |

#### 8.9 查看竞赛队伍列表
**端点**: `GET /api/v1/competitions/{competition_id}/teams`

**描述**: 获取某竞赛下活跃队伍及其成员列表（**学生选队**、**管理员/指导老师查看队况**等）。**`division_mode=dual`** 时须按学历组别分别查询，每次只返回该组队伍。

**权限**: `VIEW_COMPETITIONS`（**不**隐含作品或花名册权限；花名册须 §8.10 / §8.11）。

**路径参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| competition_id | int | ✓ | 竞赛 ID |

**Query 参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| division | string | dual 时 ✓ | `undergraduate` 或 `vocational`；`single` 竞赛可省略（按 `default` 筛选） |

**请求示例**：
```bash
curl "http://localhost:8000/api/v1/competitions/1/teams?division=undergraduate" \
  -H "Authorization: Bearer <alt_access_token>"
```

**响应示例**（200）：
```json
[
  {
    "id": 10,
    "competition_id": 1,
    "name": null,
    "captain_id": 7,
    "status": "active",
    "created_at": "2026-03-18T07:00:00.000000",
    "members": [
      {
        "id": 101,
        "team_id": 10,
        "user_id": 7,
        "is_captain": true,
        "joined_at": "2026-03-18T07:00:00.000000"
      },
      {
        "id": 102,
        "team_id": 10,
        "user_id": 8,
        "is_captain": false,
        "joined_at": "2026-03-18T07:01:00.000000"
      }
    ]
  }
]
```

#### 8.10 查看个人参赛者（花名册）

**端点**: `GET /api/v1/competitions/{competition_id}/participants/individual`  
**权限**: `VIEW_COMPETITIONS`，且服务端二次校验，允许：**`super_admin`**；**`expert`** 且 **`expert_verified=true`** 且已 **指派到本竞赛**；**`advisor` / `teacher`** 且具备 **`MANAGE_TEAMS`**（只读花名册）。学生及其他角色 **403**。

**描述**: 列出该竞赛 **个人赛道** 有效报名（`status=enrolled`）。**不**包含组队成员；组队请用下一节。**`division_mode=dual`** 时 **必填** `division`，仅返回该组别；**`sequence_no` 在指定组别内**从 1 起编号。响应含 **`division`**（与 query 一致）。

| 字段含义 | 说明 |
|----------|------|
| `sequence_no` | **当前 query `division` 对应组别内**序号，从 **1** 起，按报名时间升序 |
| `division` | 报名所属学历组别 |
| `enrollment_id` | 报名记录在库里的主键（全局自增，与 `sequence_no` 不同） |

**Query 参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| division | string | dual 时 ✓ | `undergraduate` 或 `vocational` |

**请求示例**：
```bash
curl "http://localhost:8000/api/v1/competitions/1/participants/individual?division=undergraduate" \
  -H "Authorization: Bearer <alt_access_token>"
```

**响应示例**（200）：
```json
[
  {
    "sequence_no": 1,
    "division": "undergraduate",
    "enrollment_id": 31,
    "student_id": 15,
    "username": "stu1",
    "full_name": "学生一",
    "student_no": "2023010001",
    "real_name": "学生一",
    "college": "计算机学院",
    "grade": "2023级",
    "contact": "13800000001",
    "status": "enrolled",
    "created_at": "2026-03-20T10:33:59.629498+08:00"
  }
]
```

#### 8.11 查看组队参赛者（队伍 + 成员，花名册）

**端点**: `GET /api/v1/competitions/{competition_id}/participants/teams`  
**权限**: 与 **§8.10** 相同（**管理员**、**已指派且已核验专家**、或 **`advisor`/`teacher`（`MANAGE_TEAMS`）**）。

**描述**: 列出该竞赛 **活跃队伍** 及成员（含 **`username` / `full_name`**）。**`division_mode=dual`** 时 **必填** `division`，仅该组队伍；**`sequence_no` 组内**从 1 起。响应含 **`division`**。

| 字段含义 | 说明 |
|----------|------|
| `sequence_no` | **当前 query `division` 对应组别内**队伍序号，从 **1** 起 |
| `division` | 队伍所属学历组别 |
| `id` | 队伍主键（全局）；与 `sequence_no` 不同 |

**Query 参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| division | string | dual 时 ✓ | `undergraduate` 或 `vocational` |

**请求示例**：
```bash
curl "http://localhost:8000/api/v1/competitions/1/participants/teams?division=vocational" \
  -H "Authorization: Bearer <alt_access_token>"
```

**响应示例**（200）：
```json
[
  {
    "sequence_no": 1,
    "id": 10,
    "competition_id": 1,
    "division": "vocational",
    "name": "一班代表队",
    "captain_id": 7,
    "status": "active",
    "created_at": "2026-03-18T07:00:00.000000+08:00",
    "members": [
      {
        "id": 101,
        "team_id": 10,
        "user_id": 7,
        "username": "stu2",
        "full_name": null,
        "is_captain": true,
        "joined_at": "2026-03-18T07:00:00.000000+08:00"
      }
    ]
  }
]
```

> 兼容：原 `GET /api/v1/competitions/{id}/teams` 仍可用，成员项不含 `username`；新接口更适合「名单展示」。

#### 8.11.1 导出队伍信息 Excel（管理员）

**端点**: `GET /api/v1/competitions/{competition_id}/teams/export`  
**权限**: `MANAGE_COMPETITIONS`（管理员）

**描述**: 导出该竞赛活跃队伍为 `.xlsx`。**`division_mode=dual`** 时 **必填** `division`，仅导出该组；文件名含组别后缀（如 `competition_1_teams_undergraduate.xlsx`）。Excel 字段至少包含：

- `序号`（**组内**从 1 起）
- `指导老师`（可能存在多名；系统内若有多个则使用 `、` 拼接）
- `队长`
- `队员`（可能存在多名，使用 `、` 拼接）
- `队伍名`
- `参加的竞赛`

**Query 参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| division | string | dual 时 ✓ | `undergraduate` 或 `vocational` |

**请求示例**：
```bash
curl -L "http://localhost:8000/api/v1/competitions/1/teams/export?division=undergraduate" \
  -H "Authorization: Bearer <alt_access_token>" \
  -o teams_undergraduate.xlsx
```

**响应说明**：
- `200 OK`
- `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- `Content-Disposition: attachment; filename="competition_<id>_teams.xlsx"`（single）或 `competition_<id>_teams_<division>.xlsx`（dual）

#### 8.12 创建队伍（学生自建队长 / 指导老师组班）

**端点**: `POST /api/v1/competitions/teams`  
**权限**: `MANAGE_TEAMS`（仅此权限的角色为 **`student`** 与 **`advisor`**；**`super_admin` / `expert`（第二套）无 `MANAGE_TEAMS`**，无法建队或在 §8.12.x / §8.13–§8.15 中写入队务）。

**共性前置条件**：竞赛已 **`published`**、`allow_team=true`、仍处于**开放报名期**（未 `closed` / 未到 `end_at`）。

**请求体参数**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| competition_id | int | ✓ | 竞赛 ID |
| name | string | | 可选队名（展示用）；**学生**不传则服务端可为空/`null`；指导老师可顺带命名 |
| initial_member_ids | array\<int\> \| null | 视角色 | 成员 **`alt_auth_users.id`** 列表 |
| captain_student_id | int \| null | 指导老师建队时与 `initial_member_ids` 联用 | **`advisor`**：**队长必须在** `initial_member_ids` 中；本字段若省略则默认 **`initial_member_ids`** 的首元素为队长。若填写则必须与列表中某一元素一致。**`student`** 自建：**忽略**，队长恒为本人 |

**学生 `student`**：当前账号尚未在本赛存在**组队赛道**有效报名（`enrollment_scope=team`）；**允许**已有个人的 `individual` 报名后再建队。可先只建空队仅有本人队长，或通过 `initial_member_ids` 顺带拉入其他同学（写入 `team_members` 与组队赛道 `enrolled`；对方须未在组队赛道报名，但可已有个人的 individual 报名）。

**指导老师 `advisor`**：`initial_member_ids` **至少一人**（不可仅空列表）；指导老师本人 **不可**写入队员名单。**所列学生均未在本赛组队赛道处于 `enrolled`**。服务端记录 **`created_by_advisor_id`**；后续 **§8.12.2 邀请**、**§8.12.3 踢人**、**§8.12.1 改队名** 可与队长共同参与队务。

**请求示例（学生自建）**：
```bash
curl -X POST "http://localhost:8000/api/v1/competitions/teams" \
  -H "Authorization: Bearer <alt_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"competition_id":1,"name":"筑梦队"}'
```

**请求示例（指导老师组班）**：
```bash
curl -X POST "http://localhost:8000/api/v1/competitions/teams" \
  -H "Authorization: Bearer <advisor_alt_token>" \
  -H "Content-Type: application/json" \
  -d "{\"competition_id\":1,\"name\":\"一班代表队\",\"captain_student_id\":7,\"initial_member_ids\":[7,8,9]}"
```

**响应示例**（201）：
```json
{
  "id": 10,
  "competition_id": 1,
  "name": "筑梦队",
  "captain_id": 7,
  "status": "active",
  "created_at": "2026-03-18T07:00:00.000000"
}
```

#### 8.12.1 修改队名（队长或指导老师）

**端点**: `PATCH /api/v1/competitions/teams/{team_id}`  
**权限**: `MANAGE_TEAMS`；且须为 **本队队长**，或 **`advisor`** 且为本队 **`created_by_advisor_id`**

**请求体**：
| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 新队名；可传空串表示清空展示名 |

**示例**：

```bash
curl -X PATCH "http://localhost:8000/api/v1/competitions/teams/10" \
  -H "Authorization: Bearer <alt_access_token>" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"新队名\"}"
```

#### 8.12.2 邀请队员并入队（队长或指导老师）

**端点**: `POST /api/v1/competitions/teams/{team_id}/invite`  
**权限**: `MANAGE_TEAMS`；**队长**或 **建队指导老师**（`created_by_advisor_id`）

**前置**：开放报名、`published`。请求体：`{ "student_id": <alt_auth 学生 id> }`。该学生须未在本赛其它有效报名。**不能**替换队长——队长已在队内会 **400**。

#### 8.12.3 移除队员（队长或指导老师）

**端点**: `DELETE /api/v1/competitions/teams/{team_id}/members/{user_id}`  
**权限**：同 **§8.12.2**。  
**约束**：不可踢 **队长**（须先 **`transfer-captain`**）。被移除学生对应本队报名改为 **`withdrawn`**。

```bash
curl -X DELETE "http://localhost:8000/api/v1/competitions/teams/10/members/8" \
  -H "Authorization: Bearer <alt_access_token>"
```

#### 8.13 加入队伍（学生自助申请）

**端点**: `POST /api/v1/competitions/teams/{team_id}/members`  
**权限**: `MANAGE_TEAMS`，且 **`student` 专享**（403：指导老师/管理员不可「自己加队」）。

**路径参数**：`team_id`（int）

**请求示例**：
```bash
curl -X POST "http://localhost:8000/api/v1/competitions/teams/10/members" \
  -H "Authorization: Bearer <alt_access_token>"
```

**响应示例**（201）：
```json
{
  "id": 123,
  "team_id": 10,
  "user_id": 8,
  "is_captain": false,
  "joined_at": "2026-03-18T07:00:00.000000"
}
```

#### 8.14 队长转让（学生）

**端点**: `POST /api/v1/competitions/teams/{team_id}/transfer-captain`
**权限**: `MANAGE_TEAMS`

仅 **`student`** 且 **现任队长** 可调用。**403**。

**请求体参数**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| team_id | int | ✓ | 队伍 ID（需与路径一致） |
| new_captain_id | int | ✓ | 新队长的 **`alt_auth_users.id`**（必须是队伍中已有成员的 **`team_members.user_id`**；**非**主库 `users.id`） |

**请求示例**：
```bash
curl -X POST "http://localhost:8000/api/v1/competitions/teams/10/transfer-captain" \
  -H "Authorization: Bearer <alt_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"team_id":10,"new_captain_id":8}'
```

**响应示例**（200）：
```json
{
  "id": 10,
  "competition_id": 1,
  "name": null,
  "captain_id": 8,
  "status": "active",
  "created_at": "2026-03-18T07:00:00.000000"
}
```

#### 8.15 队员退队（非队长）

**端点**: `POST /api/v1/competitions/teams/{team_id}/leave`
**权限**: `MANAGE_TEAMS`

> **仅限非队长**。若当前用户为队长，须先 **`transfer-captain`**；否则 **`400`** `Captain must transfer before leaving`。

**描述**：从队伍中移除本人并更新对应报名。**学生**专享（403：`advisor` 不可伪装退队）。

> 同一竞赛允许「个人参赛」和「队伍参赛」共存，退队仅影响该赛、该队维度。

**请求示例**：
```bash
curl -X POST "http://localhost:8000/api/v1/competitions/teams/10/leave" \
  -H "Authorization: Bearer <alt_access_token>"
```

**响应示例**（200）：
```json
{"ok": true}
```

**失败示例**（400，队长未转让）：
```json
{"detail":"Captain must transfer before leaving"}
```

#### 8.16 提交作品（学生：个人/队伍）

**端点**: `POST /api/v1/competitions/submissions`
**权限**: `SUBMIT_SUBMISSIONS`

> **必须**使用 `Content-Type: application/json`（**不要**用 `multipart/form-data` 调本接口）。请求体支持两种等价写法：① **扁平对象**（下表字段直接在根上）；② **`{"payload": { ...下表字段... }}`**（与部分前端/上传接口习惯一致，避免再出现「字段都在 payload 里却报缺 competition_id」的 422）。

> 若把本接口与文件上传混在同一个 `multipart` 请求里，FastAPI 会按表单解析并提示缺少字段，应改用 `POST .../submissions/upload`。

> `team_id = null` 表示个人提交；传 `team_id` 表示**队伍提交**。**组队提交必须由该队队长发起**（403：`Only team captain may submit...`）；个人提交须存在**有效的个人报名**（`enroll` 且 `team_id` 为空、`status=enrolled`）；已退赛（`withdrawn`）则无法以个人身份提交。

> 如需上传二进制文件，请使用 `multipart/form-data` 端点：`POST /api/v1/competitions/submissions/upload`。

> 竞赛 `status` 为 **`published`** 或 **`closed`（锁定报名后）** 时均可提交作品；**`draft`** 不可提交。

> **`division`** 与 **§8.7 报名** 一致：`division_mode=dual` 时**必填** `undergraduate` 或 `vocational`，须与当前详情页组别及本人有效报名（个人/组队）一致；`single` 竞赛勿传或传 `default`。

**请求体参数**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| competition_id | int | ✓ | 竞赛 ID |
| team_id | int/null | | 为空=个人；非空=队伍 |
| division | string | 条件 | `dual` 竞赛**必填**：`undergraduate` 或 `vocational`（由详情页隐式传入） |
| title | string | ✓ | 作品标题 |
| description | string | | 描述 |
| file_id | int/null | | 复用 `files` 表（可选） |
| content_text | string/null | | 文本内容（可选） |

**请求示例（JSON 提交文本）**：
```bash
curl -X POST "http://localhost:8000/api/v1/competitions/submissions" \
  -H "Authorization: Bearer <alt_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "competition_id":1,
    "team_id":10,
    "division":"undergraduate",
    "title":"My Work",
    "description":"desc",
    "content_text":"hello"
  }'
```

**常见 400**（与报名类似）：
| `detail` | 含义 |
|----------|------|
| `division is required (undergraduate or vocational)` | 双组别竞赛未传 `division` |
| `division must match your individual enrollment for this competition` | 个人提交组别与报名不一致 |
| `division must match team's division for this competition` | 组队提交组别与队伍不一致 |

**响应示例**（201）：
```json
{
  "id": 2,
  "competition_id": 1,
  "team_id": 10,
  "division": "undergraduate",
  "student_id": 7,
  "submitter_id": 7,
  "title": "My Work",
  "description": "desc",
  "file_id": null,
  "content_text": "hello",
  "status": "submitted",
  "submitted_at": "2026-03-18T07:01:30.989262"
}
```

#### 8.16.1 提交作品（multipart 文件上传）

**端点**: `POST /api/v1/competitions/submissions/upload`

**描述**: 使用 `multipart/form-data` 提交作品，可同时上传文件。竞赛状态须为 `published` 或 `closed`（与 JSON 提交接口一致）。

**权限**: `SUBMIT_SUBMISSIONS`

**表单字段**（Form）:
- `competition_id` (int, 必填)
- `team_id` (int, 可选)
- `division` (string, 条件) — `dual` 竞赛必填：`undergraduate` / `vocational`（规则同 §8.16 JSON）
- `title` (string, 必填)
- `description` (string, 可选)
- `content_text` (string, 可选；与 file 二选一至少一个)
- `file` (File, 可选；与 content_text 二选一至少一个)

**请求示例（上传文件）**：
```bash
curl -X POST "http://localhost:8000/api/v1/competitions/submissions/upload" \
  -H "Authorization: Bearer <alt_access_token>" \
  -F "competition_id=1" \
  -F "team_id=10" \
  -F "division=undergraduate" \
  -F "title=My Work" \
  -F "description=desc" \
  -F "file=@./submission.zip"
```

**响应示例**（201）：
```json
{
  "id": 3,
  "competition_id": 1,
  "team_id": 10,
  "division": "undergraduate",
  "student_id": 7,
  "submitter_id": 7,
  "title": "My Work",
  "description": "desc",
  "file_id": 3,
  "content_text": null,
  "status": "submitted",
  "submitted_at": "2026-03-18T07:02:20.371980"
}
```

#### 8.16.2 查看作品列表

**端点**: `GET /api/v1/competitions/{competition_id}/submissions`

**描述**: 获取某竞赛的作品提交列表。每条记录的 **`division`** 来自 **提交作品时**（§8.16 JSON / §8.16.1 multipart）写入库中的值，**不是**详情页临时参数。

| 视角 | 可见范围 |
|------|----------|
| **`super_admin`** | 全部提交 |
| **已指派且 `expert_verified` 的专家**（**本赛**） | 全部提交 |
| **`student`** | 仅限 **本人的个人提交** + **本人所在队伍的提交**（非队内他人个人赛道作品） |
| **`advisor` 等非上表主体** | **403**（`Only super_admin, assigned experts, or enrolled students may list submissions here`） |

**权限**: `VIEW_COMPETITIONS`（专家侧**不额外**要求 `REVIEW_SUBMISSIONS` 亦可拉列表）。

**Query 参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| division | string | | 按提交时的组别筛选：`undergraduate` / `vocational` / `default`（本科/高职详情页可只拉本组作品） |
| page | int | | 页码，从 `1` 开始；默认 `1` |
| page_size | int | | 每页条数，默认 `20`，最大 `100` |

**响应字段**（`SubmissionResponse`，节选）：
| 字段 | 说明 |
|------|------|
| division | 提交时写入的学历组别，与 §8.16 请求体 `division` 一致 |

**请求示例**：
```bash
curl "http://localhost:8000/api/v1/competitions/1/submissions?division=undergraduate&page=1&page_size=20" \
  -H "Authorization: Bearer <alt_access_token>"
```

**响应示例**（200）：
```json
{
  "page": 1,
  "page_size": 20,
  "total": 57,
  "items": [
    {
      "id": 3,
      "competition_id": 1,
      "team_id": 10,
      "division": "undergraduate",
      "student_id": 7,
      "submitter_id": 7,
      "title": "My Work",
      "description": "desc",
      "file_id": 3,
      "content_text": null,
      "status": "submitted",
      "submitted_at": "2026-03-18T07:02:20.371980"
    }
  ]
}
```

#### 8.16.3 查看作品详情

**端点**: `GET /api/v1/competitions/submissions/{submission_id}`

**描述**: 获取单个作品提交详情；可见范围与 **§8.16.2 列表**一致。**`division`** 同样为提交时落库字段（只读返回，本接口无需再传 `division`）。

**权限**: `VIEW_COMPETITIONS`

**请求示例**：
```bash
curl "http://localhost:8000/api/v1/competitions/submissions/3" \
  -H "Authorization: Bearer <alt_access_token>"
```

**响应示例**（200）：
```json
{
  "id": 3,
  "competition_id": 1,
  "team_id": 10,
  "division": "undergraduate",
  "student_id": 7,
  "submitter_id": 7,
  "title": "My Work",
  "description": "desc",
  "file_id": 3,
  "content_text": null,
  "status": "submitted",
  "submitted_at": "2026-03-18T07:02:20.371980"
}
```

**越权示例**（403）：
```json
{"detail":"Access denied"}
```

#### 8.16.4 下载作品文件

**端点**: `GET /api/v1/competitions/submissions/{submission_id}/download`

**描述**: 下载该作品绑定的文件（若该提交未上传文件则返回 404）。**访问边界**同 **§8.16.3**。响应为文件流，不含 JSON；作品所属组别请通过 **§8.16.3** 的 `division` 字段获取。

**权限**: `VIEW_COMPETITIONS`

**请求示例**：
```bash
curl -L "http://localhost:8000/api/v1/competitions/submissions/3/download" \
  -H "Authorization: Bearer <alt_access_token>" \
  -o submission.bin
```

**响应**：二进制文件流（200）；若无文件则 404。

#### 8.17 评分 / 审核（首次，竞赛专家）

**端点**: `PUT /api/v1/competitions/submissions/{submission_id}/review-grade`

**权限**: **`expert`** 且 **`expert_verified=true`** 且已由管理员 **指派至该作品所属竞赛**；同时具备 `REVIEW_SUBMISSIONS`。**`super_admin` 不包含**竞赛评分权限（服务端 **403**：`Only competition experts may grade …`）。

> **仅首次评分**：若该作品已有 `reviews` 记录，返回 **400** `Submission already reviewed`，请改用 **§8.17.1** `PATCH` 修改评分。
>
> 审核后直接把提交状态置为 `approved`。请求体中的 **`score` / `feedback`** 会写入该作品的 **`reviews`** 记录；学生调用 **§8.20** `GET .../scores/me` 时，对应提交项会多出 **`score`（成绩，与本条接口 `score` 同源）**、**`feedback`**、**`reviewed_at`**，未评分前这三项为 **`null`**。

**请求体参数**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| score | number | ✓ | 分数 |
| feedback | string | | 反馈 |

**请求示例**：
```bash
curl -X PUT "http://localhost:8000/api/v1/competitions/submissions/3/review-grade" \
  -H "Authorization: Bearer <verified_expert_alt_token>" \
  -H "Content-Type: application/json" \
  -d '{"score":95.0,"feedback":"great"}'
```

**响应示例**（200）：
```json
{
  "id": 2,
  "submission_id": 3,
  "reviewer_id": 8,
  "status": "approved",
  "score": 95.0,
  "feedback": "great",
  "reviewed_at": "2026-03-18T07:02:20.385584"
}
```

#### 8.17.1 修改评分（竞赛专家）

**端点**: `PATCH /api/v1/competitions/submissions/{submission_id}/review-grade`

**权限**: 与 **§8.17** 相同（指派 + 核验 **`expert`**）。

**描述**: 更新已评分作品的 **`score` / `feedback`**，并刷新 **`reviewed_at`**、**`reviewer_id`**（记录最后一次改分操作者）。未评分作品返回 **400** `Submission not reviewed yet`，请先用 §8.17 `PUT` 首次评分。改分后 **§8.18** 汇总、**§8.19** 排行榜、**§8.20** 我的成绩会自动反映新分数。

**请求体参数**（与 §8.17 相同）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| score | number | ✓ | 分数 |
| feedback | string | | 反馈 |

**请求示例**：

```bash
curl -X PATCH "http://localhost:8000/api/v1/competitions/submissions/3/review-grade" \
  -H "Authorization: Bearer <verified_expert_alt_token>" \
  -H "Content-Type: application/json" \
  -d '{"score":90.0,"feedback":"revised after discussion"}'
```

**响应示例**（200）：与 §8.17 相同，为更新后的 `ReviewResponse`（`score` / `feedback` / `reviewed_at` 等为最新值）。

**常见错误**：

| 状态码 | 说明 |
|--------|------|
| 400 | 尚未评分（须先 `PUT`） |
| 403 | 非指派专家、未核验、或 **`super_admin`** 等无批改权主体 |
| 404 | `submission_id` 不存在 |

#### 8.17.2 查询作品评分

**端点**: `GET /api/v1/competitions/submissions/{submission_id}/review-grade`

**权限**: `VIEW_COMPETITIONS`；**数据可见性**与 **§8.16.3** 一致（管理员 / 指派专家 / 相关学生）。**指导老师**若无法通过详情接口访问该作品，则本接口同样 **403**。

**描述**: 返回该作品当前 `ReviewResponse`（与 §8.17 / §8.17.1 响应体一致）。作品列表 `GET .../submissions` 含 **`division`**（提交时写入），不含 `score`；已评分时可调用本接口或 §8.20 我的成绩。

**请求示例**：

```bash
curl "http://localhost:8000/api/v1/competitions/submissions/3/review-grade" \
  -H "Authorization: Bearer <alt_access_token>"
```

**响应示例**（200）：与 §8.17 相同。

**常见错误**：

| 状态码 | 说明 |
|--------|------|
| 403 | 无权限访问该作品 |
| 404 | 作品不存在，或尚未评分（无 `reviews` 记录） |

#### 8.18 评分汇总（竞赛维度）

**端点**: `GET /api/v1/competitions/{competition_id}/scores/summary`

**描述**: 获取竞赛评分聚合统计（总提交数、已评分数、平均分/最高分/最低分）。统计范围为本 query **`division`** 下 **`submissions.division`** 匹配的作品。**`division_mode=dual`** 时 **必填** `division`，本科组与高职组分别统计。

**权限**: `VIEW_COMPETITIONS`；且须为 **`super_admin`** 或 **已指派且已核验的本赛专家**。

**Query 参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| division | string | dual 时 ✓ | `undergraduate` 或 `vocational` |

**请求示例**：
```bash
curl "http://localhost:8000/api/v1/competitions/1/scores/summary?division=undergraduate" \
  -H "Authorization: Bearer <admin_or_expert_alt_token>"
```

**响应示例**（200）：
```json
{
  "competition_id": 1,
  "division": "undergraduate",
  "submissions_total": 1,
  "reviewed_total": 1,
  "avg_score": 95.0,
  "max_score": 95.0,
  "min_score": 95.0
}
```

#### 8.19 排行榜（竞赛维度）

**端点**: `GET /api/v1/competitions/{competition_id}/scores/rankings?limit=50`

**描述**: 获取竞赛排行榜。在指定 **`division`** 内，**个人与组队同一排名池**：合并该组内有评分作品的队伍与个人，按 `best_score` 降序；**不在全赛跨组混排**。`limit` 只限制返回条数。响应含 **`division`**；`rank` 为组内名次（同分并列）。

**权限**: `VIEW_COMPETITIONS`；且须为 **`super_admin`** 或 **已指派且已核验的本赛专家**（与 **§8.18** 相同）。

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| division | string | dual 时 ✓ | `undergraduate` 或 `vocational` |
| limit | int | | 默认 50 |

**请求示例**：
```bash
curl "http://localhost:8000/api/v1/competitions/1/scores/rankings?division=undergraduate&limit=50" \
  -H "Authorization: Bearer <admin_or_expert_alt_token>"
```

**响应示例**（200）：
```json
{
  "competition_id": 1,
  "division": "undergraduate",
  "items": [
    {
      "rank": 1,
      "team_id": 10,
      "student_id": null,
      "best_score": 95.0,
      "reviewed_submissions": 1
    },
    {
      "rank": 2,
      "team_id": null,
      "student_id": 5,
      "best_score": 88.0,
      "reviewed_submissions": 1
    }
  ]
}
```

#### 8.20 我的成绩（学生）

**端点**: `GET /api/v1/competitions/{competition_id}/scores/me`

**描述**: 学生查看自己在该竞赛中的提交与成绩（包含个人提交与所属队伍提交）。每项含 **`division`**（提交作品时写入，规则同 §8.16）。

**权限**: `VIEW_COMPETITIONS`（且必须为 student）

**Query 参数**（可选）：
| 参数 | 类型 | 说明 |
|------|------|------|
| division | string | 按提交时的组别筛选：`undergraduate` / `vocational` / `default` |

**请求示例**：
```bash
curl "http://localhost:8000/api/v1/competitions/1/scores/me?division=undergraduate" \
  -H "Authorization: Bearer <alt_access_token>"
```

**响应示例**（200）：
```json
{
  "competition_id": 1,
  "submissions": [
    {
      "id": 3,
      "competition_id": 1,
      "team_id": 10,
      "division": "undergraduate",
      "student_id": 7,
      "submitter_id": 7,
      "title": "My Work",
      "description": "desc",
      "file_id": 3,
      "content_text": null,
      "status": "approved",
      "submitted_at": "2026-03-18T07:02:20.371980",
      "score": 92.5,
      "feedback": "很好",
      "reviewed_at": "2026-03-20T10:00:00.000000"
    }
  ]
}
```

---
### 9. 考试模块接口（MVP）

> **注意**: 考试模块接口同样使用 `/api/v1/*` 前缀并需要 JWT Token。

**统一鉴权请求头**：
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### 9.1 题库：创建题目（单选/多选/判断）

**端点**: `POST /api/v1/exams/question-bank`

**描述**: 创建题库题目，支持 `single`（单选）、`multiple`（多选）、`true_false`（判断）。

**权限**: `MANAGE_QUESTION_BANK`

**请求体参数**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| question_type | string | ✓ | `single`/`multiple`/`true_false` |
| stem | string | ✓ | 题干 |
| options | array/null | | 选项（单选/多选必填；判断可为 null） |
| correct_answer | any | ✓ | 正确答案：单选/判断为 string，多选为 array |
| score | number | ✓ | 分值（>0） |

**请求示例（单选）**：
```bash
curl -X POST "http://localhost:8000/api/v1/exams/question-bank" \
  -H "Authorization: Bearer <teacher_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "question_type":"single",
    "stem":"1+1=?",
    "options":[{"key":"A","text":"1"},{"key":"B","text":"2"}],
    "correct_answer":"B",
    "score":2.0
  }'
```

**请求示例（多选）**：
```json
{
  "question_type":"multiple",
  "stem":"选择质数",
  "options":[{"key":"A","text":"2"},{"key":"B","text":"3"},{"key":"C","text":"4"}],
  "correct_answer":["A","B"],
  "score":3.0
}
```

**请求示例（判断）**：
```json
{
  "question_type":"true_false",
  "stem":"地球是圆的",
  "options": null,
  "correct_answer":"true",
  "score":1.0
}
```

**响应示例**（201）：
```json
{
  "id": 1,
  "created_by": 8,
  "question_type": "single",
  "stem": "1+1=?",
  "options": [{"key":"A","text":"1"},{"key":"B","text":"2"}],
  "correct_answer": "B",
  "score": 2.0,
  "is_active": true,
  "created_at": "2026-03-18T07:00:00.000000",
  "updated_at": "2026-03-18T07:00:00.000000"
}
```

#### 9.2 题库：题目列表

**端点**: `GET /api/v1/exams/question-bank?qtype=single&skip=0&limit=100`

**权限**: `MANAGE_QUESTION_BANK`

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| qtype | string | | 按题型过滤 |
| skip | int | | 默认 0 |
| limit | int | | 默认 100 |

**请求示例**：
```bash
curl "http://localhost:8000/api/v1/exams/question-bank?qtype=single&skip=0&limit=20" \
  -H "Authorization: Bearer <teacher_token>"
```

**响应示例**（200）：
```json
[
  {
    "id": 1,
    "created_by": 8,
    "question_type": "single",
    "stem": "1+1=?",
    "options": [{"key":"A","text":"1"},{"key":"B","text":"2"}],
    "correct_answer": "B",
    "score": 2.0,
    "is_active": true,
    "created_at": "2026-03-18T07:00:00.000000",
    "updated_at": "2026-03-18T07:00:00.000000"
  }
]
```

#### 9.3 创建考试（绑定题目）

**端点**: `POST /api/v1/exams/`

**权限**: `MANAGE_EXAMS`

**请求体参数**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| competition_id | int/null | | 可选关联竞赛 |
| title | string | ✓ | 考试标题 |
| description | string/null | | 描述 |
| start_at | string(datetime)/null | | 开始时间（可选） |
| end_at | string(datetime)/null | | 结束时间（可选） |
| duration_minutes | int | ✓ | 时长（1~600） |
| question_ids | array<int> | ✓ | 题目 ID 列表 |

**请求示例**：
```bash
curl -X POST "http://localhost:8000/api/v1/exams/" \
  -H "Authorization: Bearer <teacher_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "competition_id": null,
    "title":"MVP Exam",
    "description":"desc",
    "duration_minutes":30,
    "question_ids":[1,2,3]
  }'
```

**响应示例**（201）：
```json
{"id":1,"title":"MVP Exam","status":"draft","duration_minutes":30,"created_by":8}
```

#### 9.4 发布考试

**端点**: `PUT /api/v1/exams/{exam_id}/publish`

**权限**: `MANAGE_EXAMS`

**请求示例**：
```bash
curl -X PUT "http://localhost:8000/api/v1/exams/1/publish" \
  -H "Authorization: Bearer <teacher_token>"
```

**响应示例**（200）：
```json
{"exam_id":1,"status":"published"}
```

#### 9.5 考试列表（学生仅看到已发布）

**端点**: `GET /api/v1/exams/`

**权限**: `VIEW_COMPETITIONS`

**请求示例**：
```bash
curl "http://localhost:8000/api/v1/exams/" \
  -H "Authorization: Bearer <student_token>"
```

**响应示例**（200）：
```json
[
  {
    "id": 1,
    "competition_id": null,
    "title": "MVP Exam",
    "description": "desc",
    "status": "published",
    "start_at": null,
    "end_at": null,
    "duration_minutes": 30,
    "total_score": 6.0,
    "created_by": 8,
    "created_at": "2026-03-18T07:10:00.000000"
  }
]
```

#### 9.6 开始考试（学生）

**端点**: `POST /api/v1/exams/{exam_id}/start`

**权限**: `TAKE_EXAMS`

**时间规则**:
- 若设置了 `start_at/end_at`：仅允许在时间窗内开始；已结束的考试返回 `400`。

**请求示例**：
```bash
curl -X POST "http://localhost:8000/api/v1/exams/1/start" \
  -H "Authorization: Bearer <student_token>"
```

**响应示例**（200）：
```json
{"attempt_id":1,"status":"started"}
```

#### 9.7 提交答案并自动阅卷（客观题）

**端点**: `POST /api/v1/exams/{exam_id}/submit`

**描述**: 提交答案后自动判分（单选/多选/判断）。多选题答案需传数组，如 `["A","C"]`。

**权限**: `TAKE_EXAMS`

**时间规则**:
- 若设置了 `start_at/end_at`：仅允许在时间窗内提交
- 若超过 `attempt.started_at + duration_minutes`：返回 `400`（超时）

**请求体参数**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| answers | array | ✓ | 答案数组 |
| answers[].question_id | int | ✓ | 题目 ID |
| answers[].answer | any | ✓ | 单选/判断=string，多选=array |

**请求示例**：
```bash
curl -X POST "http://localhost:8000/api/v1/exams/1/submit" \
  -H "Authorization: Bearer <student_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "answers":[
      {"question_id":1,"answer":"B"},
      {"question_id":2,"answer":["A","B"]},
      {"question_id":3,"answer":"false"}
    ]
  }'
```

**响应示例**（200）：
```json
{
  "id": 1,
  "exam_id": 1,
  "user_id": 10,
  "status": "graded",
  "started_at": "2026-03-18T08:39:43.015184",
  "submitted_at": "2026-03-18T08:39:43.021263",
  "graded_at": "2026-03-18T08:39:43.021271",
  "total_score": 5.0
}
```

#### 9.8 学生查看自己的成绩

**端点**: `GET /api/v1/exams/{exam_id}/attempts/me`

**权限**: `VIEW_EXAM_RESULTS`（且必须为 student）

**请求示例**：
```bash
curl "http://localhost:8000/api/v1/exams/1/attempts/me" \
  -H "Authorization: Bearer <student_token>"
```

**响应示例**（200）：
```json
{
  "id": 1,
  "exam_id": 1,
  "user_id": 10,
  "status": "graded",
  "started_at": "2026-03-18T08:39:43.015184",
  "submitted_at": "2026-03-18T08:39:43.021263",
  "graded_at": "2026-03-18T08:39:43.021271",
  "total_score": 5.0
}
```

#### 9.9 监考：查看考试 attempt 列表

**端点**: `GET /api/v1/exams/{exam_id}/attempts`

**描述**: 查看该场考试下所有考生的作答记录（started/submitted/graded 等）。

**权限**: `INVIGILATE_EXAMS`

**请求示例**：
```bash
curl "http://localhost:8000/api/v1/exams/1/attempts" \
  -H "Authorization: Bearer <teacher_token>"
```

**响应示例**（200）：
```json
[
  {
    "id": 1,
    "exam_id": 1,
    "user_id": 10,
    "status": "graded",
    "started_at": "2026-03-18T08:39:43.015184",
    "submitted_at": "2026-03-18T08:39:43.021263",
    "graded_at": "2026-03-18T08:39:43.021271",
    "total_score": 5.0
  }
]
```

#### 9.10 监考：查看 attempt 详情（含答案与判分）

**端点**: `GET /api/v1/exams/attempts/{attempt_id}`

**描述**: 查看某次作答的答案明细（含 `is_correct` 与 `earned_score`）。

**权限**: `INVIGILATE_EXAMS`

**请求示例**：
```bash
curl "http://localhost:8000/api/v1/exams/attempts/1" \
  -H "Authorization: Bearer <teacher_token>"
```

**响应示例**（200）：
```json
{
  "id": 1,
  "exam_id": 1,
  "user_id": 10,
  "status": "graded",
  "started_at": "2026-03-18T08:39:43.015184",
  "submitted_at": "2026-03-18T08:39:43.021263",
  "graded_at": "2026-03-18T08:39:43.021271",
  "total_score": 5.0,
  "answers": [
    {"id": 1, "attempt_id": 1, "question_id": 1, "answer": "B", "is_correct": true, "earned_score": 2.0},
    {"id": 2, "attempt_id": 1, "question_id": 2, "answer": ["A","B"], "is_correct": true, "earned_score": 3.0},
    {"id": 3, "attempt_id": 1, "question_id": 3, "answer": "false", "is_correct": false, "earned_score": 0.0}
  ]
}
```

#### 9.11 监考：强制交卷（并自动阅卷）

**端点**: `POST /api/v1/exams/attempts/{attempt_id}/force-submit`

**描述**: 强制将 attempt 提交并自动阅卷。\n- 按已存在的答案记录计分（未作答得 0 分）\n- 监考可在超时后执行（用于收卷）

**权限**: `INVIGILATE_EXAMS`

**请求示例**：
```bash
curl -X POST "http://localhost:8000/api/v1/exams/attempts/1/force-submit" \
  -H "Authorization: Bearer <teacher_token>"
```

**响应示例**（200）：
```json
{
  "id": 5,
  "exam_id": 2,
  "user_id": 10,
  "status": "graded",
  "total_score": 0.0
}
```

---

## 数据模型

### ChatRequest (对话请求)

```typescript
interface ChatRequest {
  provider: "aliyun" | "deepseek" | "doubao" | "local";
  model: string;
  messages: Message[];
  config?: ModelConfig;
}

interface Message {
  role: "user" | "assistant" | "system";
  content: string | ContentItem[];
}

interface ContentItem {
  image?: string;
  audio?: string;
  text?: string;
}

interface ModelConfig {
  temperature?: number;
  top_p?: number;
  stream?: boolean;
  modalities?: string[] | string;  // ["text"] | ["text","audio"] | "text,audio (文本+音频)"
  voice?: string;                 // 音色: Cherry, Serena, Ethan, Chelsie（qwen3-omni-flash 语音输出）
  audio?: {
    voice?: string;
    format?: string;              // "wav"
  };
}
```

---

## 错误处理

### HTTP 状态码

| 状态码 | 说明 | 处理方式 |
|--------|------|----------|
| 200 | 请求成功 | 正常处理响应数据 |
| 401 | 未授权 | 重新登录获取Token |
| 403 | 禁止访问 | 检查用户权限 |
| 500 | 服务器错误 | 联系管理员 |

---

## 前端集成示例

### 1. Axios 配置

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  timeout: 10000
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
```

---

## API 端点总览

### AI 模型服务（无需认证）

| 功能 | 方法 | 端点 |
|------|------|------|
| 获取模型列表 | GET | `/api/playground/models` |
| 文本对话 | POST | `/api/playground/chat` |
| 语音识别 | POST | `/api/playground/audio/transcription` |
| 上传训练集 | POST | `/api/playground/datasets/upload` |
| 训练集列表 | GET | `/api/playground/datasets/list` |
| 训练集选项 | GET | `/api/playground/datasets/options` |
| llmfactory 本地模型列表 | GET | `/api/playground/llmfactory/models` |
| LoRA 微调（异步） | POST | `/api/playground/llmfactory/train/lora` |
| LoRA 微调（同步） | POST | `/api/playground/llmfactory/train/lora/sync` |
| QLoRA 微调（异步） | POST | `/api/playground/llmfactory/train/qlora` |
| QLoRA 微调（同步） | POST | `/api/playground/llmfactory/train/qlora/sync` |
| 全量微调（异步） | POST | `/api/playground/llmfactory/train/full` |
| 全量微调（同步） | POST | `/api/playground/llmfactory/train/full/sync` |
| 微调任务训练进度 | GET | `/api/playground/llmfactory/train/jobs/{job_id}/progress` |
| 合并适配器（异步） | POST | `/api/playground/llmfactory/merge` |
| 合并适配器（同步） | POST | `/api/playground/llmfactory/merge/sync` |
| 启动推理 API | POST | `/api/playground/llmfactory/api/start` |
| 关闭推理 API | POST | `/api/playground/llmfactory/api/stop` |

**竞赛报名（均需第二套 JWT，路径前缀 `/api/v1/competitions`）**

| 功能 | 方法 | 端点 |
|------|------|------|
| 创建竞赛 | POST | `/api/v1/competitions/` |
| 竞赛列表 | GET | `/api/v1/competitions/` |
| 获取竞赛详情 | GET | `/api/v1/competitions/{competition_id}` |
| 下载竞赛二维码 | GET | `/api/v1/competitions/{competition_id}/qr-code` |
| 修改竞赛信息 | PUT | `/api/v1/competitions/{competition_id}` |
| 删除竞赛 | DELETE | `/api/v1/competitions/{competition_id}` |
| 锁定报名 | PUT | `/api/v1/competitions/{competition_id}/lock` |
| 发布竞赛 | PUT | `/api/v1/competitions/{competition_id}/publish` |
| 管理员改第二套帐号 / 核验专家 | PATCH | `/api/v1/competitions/admin/alt-users/{target_user_id}` |
| 全部专家列表 | GET | `/api/v1/competitions/experts` |
| 指派专家到竞赛 | POST | `/api/v1/competitions/{competition_id}/experts/{expert_user_id}` |
| 取消专家指派 | DELETE | `/api/v1/competitions/{competition_id}/experts/{expert_user_id}` |
| 我报名的竞赛 | GET | `/api/v1/competitions/enrollments/me` |
| 报名参赛 | POST | `/api/v1/competitions/enroll` |
| 退赛 | POST | `/api/v1/competitions/{competition_id}/withdraw` |
| 查看队伍列表（无花名册语义） | GET | `/api/v1/competitions/{competition_id}/teams` |
| 导出队伍信息 Excel（管理员） | GET | `/api/v1/competitions/{competition_id}/teams/export` |
| 个人参赛者花名册 | GET | `/api/v1/competitions/{competition_id}/participants/individual` |
| 组队参赛者花名册 | GET | `/api/v1/competitions/{competition_id}/participants/teams` |
| 创建队伍（学生或指导老师） | POST | `/api/v1/competitions/teams` |
| 修改队名 | PATCH | `/api/v1/competitions/teams/{team_id}` |
| 邀请队员 | POST | `/api/v1/competitions/teams/{team_id}/invite` |
| 学生自助入队 | POST | `/api/v1/competitions/teams/{team_id}/members` |
| 移除队员 | DELETE | `/api/v1/competitions/teams/{team_id}/members/{user_id}` |
| 队长转让 | POST | `/api/v1/competitions/teams/{team_id}/transfer-captain` |
| 队员退队（非队长） | POST | `/api/v1/competitions/teams/{team_id}/leave` |
| 提交作品（JSON） | POST | `/api/v1/competitions/submissions` |
| 提交作品（文件上传） | POST | `/api/v1/competitions/submissions/upload` |
| 作品列表 | GET | `/api/v1/competitions/{competition_id}/submissions` |
| 作品详情 | GET | `/api/v1/competitions/submissions/{submission_id}` |
| 下载作品文件 | GET | `/api/v1/competitions/submissions/{submission_id}/download` |
| 评分/审核（首次，指派专家） | PUT | `/api/v1/competitions/submissions/{submission_id}/review-grade` |
| 修改评分 | PATCH | `/api/v1/competitions/submissions/{submission_id}/review-grade` |
| 查询作品评分 | GET | `/api/v1/competitions/submissions/{submission_id}/review-grade` |
| 评分汇总 | GET | `/api/v1/competitions/{competition_id}/scores/summary` |
| 排行榜 | GET | `/api/v1/competitions/{competition_id}/scores/rankings` |
| 我的成绩 | GET | `/api/v1/competitions/{competition_id}/scores/me` |

---

**文档版本**: v4.2.0  
**最后更新**: 2026-05-29  
**服务端口**: 8000
