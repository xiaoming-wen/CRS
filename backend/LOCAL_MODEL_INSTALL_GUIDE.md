# 本地模型安装与部署指南 (Llama 3.1 8B - Linux)

本文档记录了在 Linux 服务器上安装和集成 Llama 3.1 8B 本地模型的步骤。

## 1. 环境要求
*   **操作系统**: Linux (Ubuntu/CentOS/Debian 等)
*   **基础引擎**: [Ollama for Linux](https://ollama.com/download/linux)
*   **核心配置**: 建议 8GB+ 显存 (NVIDIA GPU) 或 16GB+ 内存
*   **驱动**: 若使用 GPU，请确保已安装 NVIDIA Driver 和 CUDA 12.0+

## 2. 安装步骤

### 第一步：下载并启动 Ollama
如果您尚未安装 Ollama，请运行：
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

确保服务已启动：
```bash
# 使用 systemd 启动 (推荐)
sudo systemctl enable ollama
sudo systemctl start ollama
```

### 第二步：拉取 Llama 3.1 8B 模型
```bash
ollama pull llama3.1:8b
```

### 第三步：验证安装
```bash
ollama list
```
应当看到 `llama3.1:8b` 出现在列表中。

## 3. 项目集成与后端启动

### 修改 .env 配置
确保项目根目录的 `.env` 文件指向正确的 Ollama 接口：
```env
LOCAL_MODEL_URL=http://localhost:11434/v1/chat/completions
```

### Linux 后台启动后端服务
在项目根目录下运行：
```bash
# 使用 nohup 运行并记录日志
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

## 4. 远程访问 (可选)
如果您的后端和 Ollama 不在同一台服务器，请在 Ollama 服务器上设置环境变量以允许跨域访问：
```bash
# 修改 ollama.service
sudo systemctl edit ollama.service
# 添加以下内容：
# [Service]
# Environment="OLLAMA_HOST=0.0.0.0"
# Environment="OLLAMA_ORIGINS=*"
```
然后重启服务：
```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

## 5. 常见问题
*   **显存不足**: 尝试运行 `nvidia-smi` 检查占用情况。
*   **端口冲突**: 确保 8000 (项目) 和 11434 (Ollama) 端口未被占用。
