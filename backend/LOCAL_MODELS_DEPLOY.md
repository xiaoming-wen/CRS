# 本地模型部署指南 (Linux 服务器)

本指南帮助您在 Linux 服务器上部署三个本地大模型：`llama3.2:3b`、`qwen2.5:7b`、`llava-cn`。

---

## 📋 前置条件

| 项目 | 最低要求 | 推荐配置 |
|------|----------|----------|
| **显存 (GPU)** | 8GB VRAM | 16GB+ VRAM |
| **内存 (RAM)** | 16GB | 32GB+ |
| **存储** | 30GB 可用空间 | SSD 推荐 |
| **GPU 驱动** | NVIDIA 驱动 (如有 GPU) | CUDA 12.0+ |

> ⚠️ **无 GPU 也可运行**，但速度会显著下降（约 10 倍慢）。

---

## 🚀 第一步：安装 Ollama

```bash
# 一键安装脚本
curl -fsSL https://ollama.com/install.sh | sh

# 验证安装
ollama --version
```

### 启动 Ollama 服务

```bash
# 前台运行（测试用）
ollama serve

# 或后台运行（推荐）
nohup ollama serve > /var/log/ollama.log 2>&1 &

# 或使用 systemd（生产环境推荐）
sudo systemctl enable ollama
sudo systemctl start ollama
```

### 验证服务运行

```bash
curl http://localhost:11434/api/tags
# 应返回 {"models":[]}（空列表）
```

---

## 📥 第二步：下载模型

```bash
# 1. 下载 Llama 3.2 3B（约 2GB）
ollama pull llama3.2:3b

# 2. 下载 Qwen 2.5 7B（约 4.5GB）
ollama pull qwen2.5:7b

# 3. 下载 LLaVA（约 4.5GB，用于 llava-cn）
ollama pull llava
```

### 验证模型

```bash
ollama list
# 应显示三个模型
```

---

## ⚙️ 第三步：配置后端

在您的项目 `.env` 文件中添加/修改：

```env
# 本地模型 URL（Ollama 默认端口）
LOCAL_MODEL_URL=http://localhost:11434/v1/chat/completions
```

### 如果 Ollama 和后端不在同一台机器

```env
# 替换为 Ollama 服务器的 IP
LOCAL_MODEL_URL=http://192.168.1.100:11434/v1/chat/completions
```

> ⚠️ 如果跨机器访问，需要配置 Ollama 监听所有地址：
> ```bash
> OLLAMA_HOST=0.0.0.0 ollama serve
> ```

---

## 🔄 第四步：重启后端

```bash
# 停止旧进程
pkill -f "uvicorn app.main:app"

# 启动后端
cd /path/to/llm_AIO-main
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

---

## ✅ 第五步：验证部署

### 5.1 检查模型列表

```bash
curl http://localhost:8000/api/playground/models | jq '.models[] | select(.provider=="local")'
```

应返回 `llama3.2:3b`、`qwen2.5:7b`、`llava`、`llava-cn` 四个模型。

### 5.2 测试文本模型

```bash
curl -X POST http://localhost:8000/api/playground/chat \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "local",
    "model": "qwen2.5:7b",
    "messages": [{"role": "user", "content": "你好"}],
    "config": {"temperature": 0.7, "stream": false}
  }'
```

### 5.3 测试视觉模型 (llava-cn)

```bash
# 需要先将图片转为 Base64
BASE64_IMG=$(base64 -w 0 /path/to/image.jpg)

curl -X POST http://localhost:8000/api/playground/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"provider\": \"local\",
    \"model\": \"llava-cn\",
    \"messages\": [{
      \"role\": \"user\",
      \"content\": [
        {\"type\": \"text\", \"text\": \"描述这张图片\"},
        {\"type\": \"image_url\", \"image_url\": {\"url\": \"data:image/jpeg;base64,$BASE64_IMG\"}}
      ]
    }],
    \"config\": {\"stream\": false}
  }"
```

---

## 🛠️ 常见问题

### Q1: 报错 "Could not connect to local model server"
**原因**: Ollama 服务未运行
**解决**: 
```bash
sudo systemctl status ollama  # 检查状态
sudo systemctl restart ollama # 重启服务
```

### Q2: 模型响应很慢
**原因**: 没有 GPU 或显存不足
**解决**: 
- 确保 NVIDIA 驱动已安装：`nvidia-smi`
- 使用更小的模型（如 `llama3.2:3b`）

### Q3: 跨机器访问 Ollama 失败
**原因**: Ollama 默认只监听 localhost
**解决**:
```bash
# 方法1: 环境变量
OLLAMA_HOST=0.0.0.0 ollama serve

# 方法2: systemd 配置
sudo vim /etc/systemd/system/ollama.service
# 添加 Environment="OLLAMA_HOST=0.0.0.0"
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### Q4: 显存不足 (OOM)
**原因**: 模型太大
**解决**: 同时只加载一个模型，或使用量化版本

---

## 📊 资源占用参考

| 模型 | 显存占用 | 首次加载时间 |
|------|----------|--------------|
| `llama3.2:3b` | ~3GB | ~5s |
| `qwen2.5:7b` | ~5GB | ~10s |
| `llava` | ~5GB | ~10s |
| `llava-cn` | ~10GB (峰值) | ~15s |

> 💡 `llava-cn` 需要先调用 `llava`，再调用 `qwen2.5:7b`，所以峰值显存较高。

---

## 🔧 生产环境建议

1. **使用 systemd 管理 Ollama**
2. **配置日志轮转** (`logrotate`)
3. **设置内存限制** 避免 OOM 影响其他服务
4. **使用 Nginx 反向代理** 统一入口和 HTTPS
5. **监控 GPU 使用率** (`nvidia-smi dmon`)

---

## 🎙️ 额外篇：Whisper 离线语音识别 (Linux)

除了 Ollama 的大语言模型，本项目还支持使用 OpenAI Whisper 进行离线语音识别。

### 1. 安装系统依赖 (FFmpeg)

Whisper 严重依赖 FFmpeg 进行音频处理。

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**CentOS/RHEL:**
```bash
sudo yum install ffmpeg
```

### 2. 安装 Python 依赖

在您的项目 Python 环境中安装：

```bash
pip install openai-whisper
```

### 3. 模型下载与加载

*   **自动下载**：首次调用 API 时，代码会自动下载模型（Large v3 约 3GB）。
*   **模型位置**：默认下载到项目根目录下的 `models/whisper/` 文件夹。
*   **手动下载**（如果服务器无法联网）：
    1.  在有网机器上运行 python 脚本下载模型。
    2.  找到下载的 `.pt` 文件（通常在 `~/.cache/whisper` 或指定的 `models/whisper`）。
    3.  复制到服务器的 `models/whisper` 目录。

### 4. 验证运行

```bash
# 测试本地 Whisper 接口 (确保后端服务已开启)
curl -X POST http://localhost:8000/api/playground/audio/transcription \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "local",
    "model": "local-whisper-large",
    "input": "https://example.com/test.wav"
  }'
```
