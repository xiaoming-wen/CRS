# 所有可用模型清单 (Model Registry Report)

## 模态分类: 文本模型 (Text)

### 该模态通用参数列表 (含默认值)
*   **随机性 (Temperature)** (`temperature`): 默认值 = 0.7 (范围: 0.0~2.0)
*   **核采样 (Top-P)** (`top_p`): 默认值 = 0.8 (范围: 0.0~1.0)
*   **候选数 (Top-K)** (`top_k`): 默认值 = 50 (范围: 1~100)
*   **重复惩罚 (Penalty)** (`repetition_penalty`): 默认值 = 1.1 (范围: 1.0~2.0)
*   **联网思考 (Search)** (`enable_search`): 默认值 = False
*   **深度思考 (Think)** (`enable_thinking`): 默认值 = False

---

### 模型: 通义千问 Max (最强) (`qwen-max`)
**提供商**: aliyun
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持 (默认值: 0.7)
    *   [x] **核采样 (Top-P)**: 支持 (默认值: 0.8)
    *   [x] **候选数 (Top-K)**: 支持 (默认值: 50)
    *   [x] **重复惩罚 (Penalty)**: 支持 (默认值: 1.1)
    *   [x] **联网思考 (Search)**: 支持 (默认值: False)
    *   [ ] **深度思考 (Think)**: 不支持 (默认值: False)

### 模型: 通义千问 Plus (均衡) (`qwen-plus`)
**提供商**: aliyun
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持 (默认值: 0.7)
    *   [x] **核采样 (Top-P)**: 支持 (默认值: 0.8)
    *   [x] **候选数 (Top-K)**: 支持 (默认值: 50)
    *   [x] **重复惩罚 (Penalty)**: 支持 (默认值: 1.1)
    *   [x] **联网思考 (Search)**: 支持 (默认值: False)
    *   [x] **深度思考 (Think)**: 支持 (默认值: False)

### 模型: 通义千问 Turbo (极速) (`qwen-turbo`)
**提供商**: aliyun
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持 (默认值: 0.7)
    *   [x] **核采样 (Top-P)**: 支持 (默认值: 0.8)
    *   [x] **候选数 (Top-K)**: 支持 (默认值: 50)
    *   [x] **重复惩罚 (Penalty)**: 支持 (默认值: 1.1)
    *   [x] **联网思考 (Search)**: 支持 (默认值: False)
    *   [x] **深度思考 (Think)**: 支持 (默认值: False)

### 模型: DeepSeek v3.2 (`deepseek-v3.2`)
**提供商**: aliyun
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持 (默认值: 0.7)
    *   [x] **核采样 (Top-P)**: 支持 (默认值: 0.8)
    *   [x] **候选数 (Top-K)**: 支持 (默认值: 50)
    *   [x] **重复惩罚 (Penalty)**: 支持 (默认值: 1.1)
    *   [x] **联网思考 (Search)**: 支持 (默认值: False)
    *   [x] **深度思考 (Think)**: 支持 (默认值: False, 核心特性)

### 模型: Llama 3.2 3B (本地) (`llama3.2:3b`)
**提供商**: local (Ollama)
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持
    *   [x] **核采样 (Top-P)**: 支持
    *   [x] **候选数 (Top-K)**: 支持
    *   [x] **重复惩罚 (Penalty)**: 支持
    *   [x] **最大长度 (Max Tokens)**: 支持
    *   [x] **随机种子 (Seed)**: 支持
    *   [x] **话题惩罚 (Presence)**: 支持
    *   [x] **频率惩罚 (Frequency)**: 支持


### 模型: Llama 3.1 8B (本地) (`llama3.1:8b`)
**提供商**: local (Ollama)
**描述**: Meta 推出的強力 8B 模型，逻辑理解能力出色，是目前 8B 规模最推荐的版本。
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持
    *   [x] **核采样 (Top-P)**: 支持
    *   [x] **候选数 (Top-K)**: 支持
    *   [x] **重复惩罚 (Penalty)**: 支持
    *   [x] **最大长度 (Max Tokens)**: 支持
    *   [x] **随机种子 (Seed)**: 支持
    *   [x] **话题惩罚 (Presence)**: 支持
    *   [x] **频率惩罚 (Frequency)**: 支持

### 模型: Qwen 2.5 7B (本地) (`qwen2.5:7b`)
**提供商**: local (Ollama)
**描述**: 通义千问 2.5 7B，最强开源 7B 模型，支持中英双语。
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持
    *   [x] **核采样 (Top-P)**: 支持
    *   [x] **候选数 (Top-K)**: 支持
    *   [x] **重复惩罚 (Penalty)**: 支持
    *   [x] **最大长度 (Max Tokens)**: 支持
    *   [x] **随机种子 (Seed)**: 支持
    *   [x] **话题惩罚 (Presence)**: 支持
    *   [x] **频率惩罚 (Frequency)**: 支持

### 模型: 豆包 1.5 Pro 32k (`doubao-1-5-pro-32k-250115`)
**提供商**: doubao
**描述**: 豆包纯文本模型，支持调参，最高32k窗口。
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持 (范围 0~2, 默认由系统控制或随前端传入)
    *   [x] **核采样 (Top-P)**: 支持 (范围 0~1)
    *   [x] **最大长度 (Max Tokens)**: 支持 (最大12k)
    *   [x] **频率惩罚 (Frequency)**: 支持 (范围 -2~2)

### 模型: 豆包 Lite 32k (角色扮演) (`doubao-lite-32k-character-250228`)
**提供商**: doubao
**描述**: 豆包纯文本角色扮演模型，固定参数不可调。
*   **参数支持情况**:
    *   此模型为固定参数模型，不支持调整任何参数。API 层已做参数屏蔽。

### 模型: 豆包 1.5 Lite 32k (基础) (`doubao-1-5-lite-32k-250115`)
**提供商**: doubao
**描述**: 豆包纯文本 1.5 Lite 模型，固定参数不可调。
*   **参数支持情况**:
    *   此模型为固定参数模型，不支持调整任何参数。API 层已做参数屏蔽。

---

## 模态分类: 图像生成 (Image Gen)

### 该模态通用参数列表 (含默认值)
*   **图片尺寸** (`size`): 默认值 = 1024x1024 (支持 1:1, 16:9, 9:16, 4:3, 3:4 等主流比例/分辨率)
*   **反向提示词** (`negative_prompt`): 不希望出现的内容 (上限500字符)
*   **智能改写** (`prompt_extend`): 默认值 = True
*   **组图模式** (`sequential_image_generation`): 默认值 = disabled (支持连贯生成最多15张参考图片组)
*   **添加水印** (`watermark`): 默认值 = True (图片右下角标志)
*   **随机种子** (`seed`): 固定生成风格

---

### 模型: Qwen Image Max (通义万相 - Max) (`qwen-image-max`)
**提供商**: aliyun
*   **参数支持情况**:
    *   [x] **图片尺寸**: 支持 (默认值: 1024x1024)
    *   [x] **反向提示词**: 支持
    *   [x] **智能改写**: 支持 (默认值: True)

### 模型: Qwen Image Plus (通义万相 - Plus) (`qwen-image-plus`)
**提供商**: aliyun
**描述**: 通义万相图像生成 Plus 版本，均衡型。
*   **参数支持情况**:
    *   [x] **图片尺寸**: 支持 (默认值: 1024x1024)
    *   [x] **反向提示词**: 支持
    *   [x] **智能改写**: 支持 (默认值: True)

### 模型: Doubao Seedream 5.0 Lite (综合旗舰) (`doubao-seedream-5-0-260128`)
**提供商**: doubao
**描述**: 豆包图像生成旗舰模型，支持文生图、图生图（需传入`image`参数），以及最多14张单/多图生组图。自带联网搜索能力。
*   **参数支持情况**:
    *   [x] **提示词 (`prompt`)**: 必填
    *   [x] **参考图 (`image`)**: 支持 （图生图模式必传，传入 Base64 编码或 OSS 图片 URL）
    *   [x] **图片尺寸 (`size`)**: 支持 (原生接受分辨率 2K, 3K, 4K 或具体如 2048x2048 像素)
    *   [x] **组图模式 (`sequential_image_generation`)**: 支持 (自动 auto, 禁用 disabled)
    *   [x] **添加水印 (`watermark`)**: 支持 (默认: True)

### 模型: Doubao Seedream 4.5 (`doubao-seedream-4-5-251128`)
**提供商**: doubao
**描述**: 豆包图像生成进阶模型，支持高质量文生图与图生图。
*   **参数支持情况**:
    *   [x] **提示词 (`prompt`)**: 必填
    *   [x] **参考图 (`image`)**: 支持 （图生图模式必传，传入 Base64 编码或 OSS 图片 URL）
    *   [x] **图片尺寸 (`size`)**: 支持 (原生接受分辨率 2K, 3K, 4K 或像素，注：不支持1024等低小尺寸)
    *   [x] **组图模式 (`sequential_image_generation`)**: 支持 (自动 auto, 禁用 disabled)
    *   [x] **添加水印 (`watermark`)**: 支持 (默认: True)

### 模型: Doubao Seedream 4.0 (`doubao-seedream-4-0-250828`)
**提供商**: doubao
**描述**: 豆包 4.0 图像生成模型，支持文生图、图生图与组图模式。
*   **参数支持情况**:
    *   [x] **提示词 (`prompt`)**: 必填
    *   [x] **参考图 (`image`)**: 支持 （图生图模式必传，传入 Base64 编码或 OSS 图片 URL）
    *   [x] **图片尺寸 (`size`)**: 支持 (原生接受分辨率 1K, 2K, 4K 或像素)
    *   [x] **组图模式 (`sequential_image_generation`)**: 支持 (自动 auto, 禁用 disabled)
    *   [x] **添加水印 (`watermark`)**: 支持 (默认: True)

### 模型: Doubao Seedream 3.0 (文生图专用) (`doubao-seedream-3-0-t2i-250415`)
**提供商**: doubao
**描述**: 豆包 3.0 轻量级图像生成模型。仅支持纯文本生成图片，不支持图生图功能。
*   **参数支持情况**:
    *   [x] **提示词 (`prompt`)**: 必填
    *   [ ] **参考图 (`image`)**: **不支持**
    *   [x] **图片尺寸 (`size`)**: 支持 (严格像素值，默认 1024x1024，上限 2048)
    *   [x] **随机种子 (`seed`)**: 支持 (传入整数，用于固定画风随机数)


---

## 模态分类: 图像理解 (Vision)

### 该模态通用参数列表 (含默认值)
*   **随机性 (Temperature)** (`temperature`): 默认值 = 0.7 (范围: 0.0~2.0)
*   **核采样 (Top-P)** (`top_p`): 默认值 = 0.8 (范围: 0.0~1.0)
*   **深度思考 (Think)** (`enable_thinking`): 默认值 = False

---

### 模型: Qwen-VL Max (视觉理解 - Max) (`qwen-vl-max`)
**提供商**: aliyun
**描述**: 通义千问视觉理解 Max 版本，能力最强。
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持 (默认值: 0.7)
    *   [x] **核采样 (Top-P)**: 支持 (默认值: 0.8)

### 模型: Qwen-VL Plus (视觉理解 - Plus) (`qwen-vl-plus`)
**提供商**: aliyun
**描述**: 通义千问视觉理解 Plus 版本，均衡型。
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持 (默认值: 0.7)
    *   [x] **核采样 (Top-P)**: 支持 (默认值: 0.8)

### 模型: Qwen3-VL Plus (视觉理解3.0 - Plus) (`qwen3-vl-plus`)
**提供商**: aliyun
**描述**: 最新 Qwen3 视觉模型。
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持 (默认值: 0.7)
    *   [x] **核采样 (Top-P)**: 支持 (默认值: 0.8)
    *   [x] **深度思考 (Think)**: 支持 (默认值: False)

### 模型: LLaVA 7B 中文版 (本地视觉) (`llava-cn`)
**提供商**: local (Ollama)
**描述**: 本地多模态模型，支持图片理解，**自动翻译为中文输出**。内部使用 LLaVA + Qwen 2.5 7B 翻译流水线。
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持
    *   [x] **核采样 (Top-P)**: 支持
    *   [x] **候选数 (Top-K)**: 支持
    *   [x] **最大长度 (Max Tokens)**: 支持
    *   [x] **随机种子 (Seed)**: 支持


### 模型: Qwen3-VL Flash (视觉理解3.0 - Flash) (`qwen3-vl-flash`)
**提供商**: aliyun
**描述**: 最新 Qwen3 视觉模型，极速响应。
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持 (默认值: 0.7)
    *   [x] **核采样 (Top-P)**: 支持 (默认值: 0.8)
    *   [x] **深度思考 (Think)**: 支持 (默认值: False)

---

## 模态分类: 视频生成 (Video Gen)

### 该模态通用参数列表 (含默认值)
*   **视频分辨率 (Resolution)** (`resolution`): 默认值 = 1280x720 (支持: 480P, 720P, 1080P)
*   **视频时长 (Duration)** (`duration`): 默认值 = 5 (支持: 2s~15s)
*   **生成音效 (Generate Audio)** (`generate_audio`): 默认值 = True (True/False)
*   **智能改写 (Prompt Extend)** (`prompt_extend`): 默认值 = True
*   **镜头类型 (Shot Type)** (`shot_type`): 仅部分模型支持 (默认: single)

---

### 模型: Wanx 2.6 I2V Flash (万相视频 - 极速版) (`wan2.6-i2v-flash`)
**提供商**: aliyun
**描述**: 支持图生视频，多镜头叙事，720P/1080P，时长2-15秒。
*   **参数支持情况**:
    *   [x] **视频分辨率 (Resolution)**: 支持 (默认值: 1280x720)
    *   [x] **视频时长 (Duration)**: 支持 (范围: 2~15秒, 默认5秒)
    *   [x] **生成音效 (Generate Audio)**: 支持 (默认值: True)

### 模型: Wanx 2.6 I2V (万相视频 - 标准版) (`wan2.6-i2v`)
**提供商**: aliyun
**描述**: 高质量图生视频，支持5/10/15秒时长。
*   **参数支持情况**:
    *   [x] **视频分辨率 (Resolution)**: 支持 (默认值: 1280x720)
    *   [x] **视频时长 (Duration)**: 支持 (可选: 5/10/15秒, 默认5秒)
    *   [ ] **生成音效 (Generate Audio)**: 不支持 (仅 Flash 版支持)

### 模型: Wanx 2.6 T2V (万相文生视频) (`wan2.6-t2v`)
**提供商**: aliyun
**描述**: 文生视频，支持声画同步，多镜头叙事。
*   **参数支持情况**:
    *   [x] **视频分辨率 (Resolution)**: 支持 (默认值: 1920x1080)
        *   **1080P系列**: 1920x1080 (16:9), 1080x1920 (9:16), 1440x1440 (1:1), 1632x1248 (4:3), 1248x1632 (3:4)
        *   **720P系列**: 1280x720 (16:9), 720x1280 (9:16), 960x960 (1:1), 1088x832 (4:3), 832x1088 (3:4)
    *   [x] **视频时长 (Duration)**: 支持 (5s, 10s, 15s)
    *   [x] **生成音效 (Generate Audio)**: 支持
    *   [x] **镜头类型 (Shot Type)**: 支持 (single, multi)
    *   [x] **智能改写 (Prompt Extend)**: 支持

### 模型: Wanx 2.5 T2V Preview (`wan2.5-t2v-preview`)
**提供商**: aliyun
**描述**: 文生视频预览版，支持声画同步，特有 480P 支持。
*   **参数支持情况**:
    *   [x] **视频分辨率 (Resolution)**: 支持 (默认值: 1920x1080)
        *   **1080P系列**: 同上
        *   **720P系列**: 同上
        *   **480P系列**: 832x480 (16:9), 480x832 (9:16), 624x624 (1:1)
    *   [x] **视频时长 (Duration)**: 支持 (5s, 10s)
    *   [x] **生成音效 (Generate Audio)**: 支持
    *   [ ] **镜头类型 (Shot Type)**: 不支持
    *   [x] **智能改写 (Prompt Extend)**: 支持

### 模型: 豆包 Seedance 1.5 Pro (`doubao-seedance-1-5-pro-251215`)
**提供商**: doubao
**描述**: 字节火山专业级视频生成大模型，同时支持高画质“文生视频”与“图生视频”，支持音效生成。
*   **参数支持情况**:
    *   [x] **视频分辨率 (Resolution)**: 支持 (默认值: 720p, 支持 480p, 720p, 1080p)
    *   [x] **视频时长 (Duration)**: 支持 (范围: 2~12s, 默认 5秒)
    *   [x] **视频宽高比 (Ratio)**: 支持 (16:9, 4:3, 1:1, 3:4, 9:16, 21:9)
    *   [x] **固定运镜 (Camera Fixed)**: 支持
    *   [x] **随机种子 (Seed)**: 支持
    *   [x] **添加水印 (Watermark)**: 支持
    *   [x] **生成音效 (Generate Audio)**: 支持

### 模型: 豆包 Seedance 1.0 Pro (`doubao-seedance-1-0-pro-250528`)
**提供商**: doubao
**描述**: 豆包视频生成旗舰模型，支持文生视频与首尾帧/首帧图生视频。
*   **参数支持情况**:
    *   [x] **视频分辨率 (Resolution)**: 支持 (默认值: 1080p, 支持 480p, 720p, 1080p)
    *   [x] **视频时长 (Duration)**: 支持 (范围: 2~12s, 默认 5秒)
    *   [x] **视频宽高比 (Ratio)**: 支持 (16:9, 4:3, 1:1, 3:4, 9:16, 21:9, adaptive)
    *   [x] **固定运镜 (Camera Fixed)**: 支持
    *   [x] **随机种子 (Seed)**: 支持
    *   [x] **添加水印 (Watermark)**: 支持

### 模型: 豆包 Seedance 1.0 Pro Fast (`doubao-seedance-1-0-pro-fast-251015`)
**提供商**: doubao
**描述**: 豆包视频生成极速版旗舰模型，响应更快，支持文生视频与首帧图生视频。
*   **参数支持情况**:
    *   [x] **视频分辨率 (Resolution)**: 支持 (默认值: 1080p, 支持 480p, 720p, 1080p)
    *   [x] **视频时长 (Duration)**: 支持 (范围: 2~12s, 默认 5秒)
    *   [x] **视频宽高比 (Ratio)**: 支持 (16:9, 4:3, 1:1, 3:4, 9:16, 21:9, adaptive)
    *   [x] **固定运镜 (Camera Fixed)**: 支持
    *   [x] **随机种子 (Seed)**: 支持
    *   [x] **添加水印 (Watermark)**: 支持

### 模型: 豆包 Seedance 1.0 Lite I2V (`doubao-seedance-1-0-lite-i2v-250428`)
**提供商**: doubao
**描述**: 豆包图生视频轻量版，专为图生视频设计，支持传入1-4张参考图，或首尾帧连接。
*   **参数支持情况**:
    *   [x] **视频分辨率 (Resolution)**: 支持 (默认值: 720p, 支持 480p, 720p)
    *   [x] **视频时长 (Duration)**: 支持 (范围: 2~12s, 默认 5秒)
    *   [x] **视频宽高比 (Ratio)**: 支持 (16:9 等, adaptive 仅在首帧场景支持有效)
    *   [ ] **固定运镜 (Camera Fixed)**: 不支持 (参考图生视频场景不支持此参数，不生效)
    *   [x] **随机种子 (Seed)**: 支持
    *   [x] **添加水印 (Watermark)**: 支持

### 模型: 豆包 Seedance 1.0 Lite T2V (`doubao-seedance-1-0-lite-t2v-250428`)
**提供商**: doubao
**描述**: 豆包文生视频轻量版，纯文生视频专属版，速度更快。
*   **参数支持情况**:
    *   [x] **视频分辨率 (Resolution)**: 支持 (默认值: 720p, 支持 480p, 720p, 1080p)
    *   [x] **视频时长 (Duration)**: 支持 (范围: 2~12s, 默认 5秒)
    *   [x] **视频宽高比 (Ratio)**: 支持 (16:9, 4:3, 1:1, 3:4, 9:16, 21:9, adaptive)
    *   [x] **固定运镜 (Camera Fixed)**: 支持
    *   [x] **随机种子 (Seed)**: 支持
    *   [x] **添加水印 (Watermark)**: 支持
    *   [x] **生成音效 (Generate Audio)**: 不支持 (以官方文档为准)

---

## 模态分类: 全模态 (Omni)

### 该模态通用参数列表 (含默认值)
*   **随机性 (Temperature)** (`temperature`): 默认值 = 0.7 (范围: 0.0~2.0)
*   **核采样 (Top-P)** (`top_p`): 默认值 = 0.8 (范围: 0.0~1.0)
*   **候选数 (Top-K)** (`top_k`): 默认值 = 50 (范围: 1~100)
*   **重复惩罚 (Penalty)** (`repetition_penalty`): 默认值 = 1.1 (范围: 1.0~2.0)
*   **联网思考 (Search)** (`enable_search`): 默认值 = False
*   **深度思考 (Think)** (`enable_thinking`): 默认值 = False
*   **输出模态 (Modalities)** (`modalities`): 默认值 = text (支持 text, text+audio)
*   **音色 (Voice)** (`voice`): 默认值 = Cherry (仅在音频输出时生效)

---

### 模型: Qwen 3.5 Plus (全能专家 - 带推理) (`qwen3.5-plus`)
**提供商**: aliyun
**描述**: 阿里云通义千问 3.5 最新主力全能模型。同时支持文本、图片和**视频**等多模态输入。此模型还具备“深度思考”机制，能在输出最终结果前展现推理论证过程。
*   **输入支持**: 文本, 文本+图片, 文本+视频
*   **输出支持**: 文本
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持 (默认值: 0.8)
    *   [x] **核采样 (Top-P)**: 支持 (默认值: 0.8)
    *   [x] **候选数 (Top-K)**: 支持 
    *   [x] **重复惩罚 (Penalty)**: 支持 
    *   [x] **联网思考 (Search)**: 支持 
    *   [x] **深度思考 (Think / CoT)**: 支持 (通过 `extra_body: {"enable_thinking": True}` 激活)
    *   [x] **输出模态 (Modalities)**: 支持 (仅限 text)

### 模型: 通义千问 3.5 Flash (`qwen3.5-flash`)
**提供商**: aliyun
**描述**: 阿里云通义千问 3.5 极速全能模型。
*   **输入支持**: 文本, 文本+图片, 文本+视频
*   **输出支持**: 文本
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持 (默认值: 0.7)
    *   [x] **核采样 (Top-P)**: 支持 (默认值: 0.8)
    *   [x] **候选数 (Top-K)**: 支持 (默认值: 50)
    *   [x] **重复惩罚 (Penalty)**: 支持 (默认值: 1.1)
    *   [x] **联网思考 (Search)**: 支持 (默认值: False)
    *   [x] **深度思考 (Think)**: 支持 (默认值: False)

### 模型: 通义千问 3.5 35B A3B (`qwen3.5-35b-a3b`)
**提供商**: aliyun
**描述**: 阿里云通义千问 3.5 中规模型。
*   **输入支持**: 文本, 文本+图片, 文本+视频
*   **输出支持**: 文本
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持 (默认值: 0.7)
    *   [x] **核采样 (Top-P)**: 支持 (默认值: 0.8)
    *   [x] **候选数 (Top-K)**: 支持 (默认值: 50)
    *   [x] **重复惩罚 (Penalty)**: 支持 (默认值: 1.1)
    *   [x] **联网思考 (Search)**: 支持 (默认值: False)
    *   [x] **深度思考 (Think)**: 支持 (默认值: False)

---

### 模型: Qwen3 Omni Flash (全模态 - 极速版) (`qwen3-omni-flash`)
**提供商**: aliyun
**描述**: 阿里云最新全模态模型，支持文本/语音/图片/视频输入，支持高质量语音对话（类似 TTS 语音合成输出）。
*   **语音输出用法**: `config.modalities = ["text", "audio"]` 或 `"text,audio (文本+音频)"`，`config.voice = "Cherry"`（可选 Serena/Ethan/Chelsie）。响应中 `delta.audio.data` 或 `message.audio` 为 base64 编码的 WAV 音频。
*   **输入支持**: 文本, 文本+图片, 文本+视频, 文本+音频
单个图片文件的大小不超过10 MB
单个音频不能超过  100MB，时长最长 20 分钟
单个视频限制为 256 MB，时长限制为 150s；
*   **输出支持**: 文本, 文本+音频
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持 (默认值: 0.7)
    *   [x] **核采样 (Top-P)**: 支持 (默认值: 0.8)
    *   [x] **候选数 (Top-K)**: 支持 (默认值: 50)
    *   [x] **重复惩罚 (Penalty)**: 支持 (默认值: 1.1)
    *   [x] **联网思考 (Search)**: 支持 (默认值: False)
    *   [x] **深度思考 (Think)**: 支持 (开启后不支持音频输出)
    *   [x] **输出模态 (Modalities)**: 支持 (text / text+audio)
    *   [x] **音色 (Voice)**: 支持 (Cherry, Serena, Ethan, Chelsie)

### 模型: 豆包 Seed 2.0 Pro (全模态/推理) (`doubao-seed-2-0-pro-260215`)
**提供商**: doubao
**描述**: 豆包最新旗舰版多模态大模型，支持长上下文、图片视频理解与高强度推理。
*   **输入支持**: 文本, 文本+图片, 文本+视频
*   **输出支持**: 文本
*   **参数支持情况**:
    *   [-] **随机性 (Temperature)**: 固定 (受官方后台限制，强制固定为 1，前端手动传值将被忽略)
    *   [-] **核采样 (Top-P)**: 固定 (受官方后台限制，强制固定为 0.95，前端手动传值将被忽略)
    *   [x] **深度思考开关 (Think / CoT)**: 支持 (可通过 thinking 开关控制)
    *   [x] **推理强度 (Reasoning Effort)**: 支持 (配合深度思考时，可通过 reasoning_effort 调整，支持 minimal, low, medium, high 模式)
    *   [x] **最大长度 (Max Tokens)**: 支持

### 模型: 豆包 Seed 多模态常规家族 (`doubao-seed-2-0-mini-260215`, `doubao-seed-1-8` 等)
**提供商**: doubao
**描述**: 豆包多模态系列精简模型 (Seed 1.6 / Seed 1.6 Flash / Seed 1.8 / Seed 2.0 Mini)，响应急速，支持图片视频理解。
*   **输入支持**: 文本, 文本+图片, 文本+视频
*   **输出支持**: 文本
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持 (正常可调)
    *   [x] **核采样 (Top-P)**: 支持 (正常可调)
    *   [x] **深度思考开关 (Think / CoT)**: 支持 (全家族均支持开启深度思考)
    *   [x] **推理强度 (Reasoning Effort)**: 仅 1.8, 2.0 Mini 支持进一步调整思考强度
    *   [x] **最大长度 (Max Tokens)**: 支持

## 模态分类: 语音合成 (TTS / Text-to-Speech)

### 该模态通用参数列表 (含默认值)
*   **音色 (Voice)** (`config.voice`): 默认值 = default (支持 longanyang, longyingxiao 等)
*   **语速 (Speed)** (`config.speed`): 默认值 = 1.0 (范围: 0.5~2.0)
*   **音量 (Volume)** (`config.volume`): 默认值 = 50 (范围: 0~100)
*   **音频格式 (Format)** (`config.format`): 默认值 = mp3 (支持: mp3, wav)

---

### 模型: CosyVoice v3 Flash (`cosyvoice-v3-flash`)
**提供商**: aliyun
**描述**: CosyVoice 最新极速版，低延迟，适合实时交互。支持丰富的音色。
*   **参数支持情况**:
    *   [x] **音色 (Voice)**: 支持
    *   [x] **语速 (Speed)**: 支持
    *   [x] **音量 (Volume)**: 支持
    *   [x] **音频格式 (Format)**: 支持

### 模型: CosyVoice v3 Plus (`cosyvoice-v3-plus`)
**提供商**: aliyun
**描述**: CosyVoice 高音质版，适合内容创作、有声读物。音质更自然。
*   **参数支持情况**:
    *   [x] **音色 (Voice)**: 支持
    *   [x] **语速 (Speed)**: 支持
    *   [x] **音量 (Volume)**: 支持
    *   [x] **音频格式 (Format)**: 支持

### 模型: CosyVoice v2 (`cosyvoice-v2`)
**提供商**: aliyun
**描述**: 支持方言（如粤语）、多情感控制，功能丰富。
*   **参数支持情况**:
    *   [x] **音色 (Voice)**: 支持 (支持粤语等方言音色)
    *   [x] **语速 (Speed)**: 支持
    *   [x] **音量 (Volume)**: 支持
    *   [x] **音频格式 (Format)**: 支持
---

## 模态分类: 语音识别 (ASR / Speech-to-Text)

### 该模态通用参数列表 (含默认值)
*   **音频格式 (Format)** (`format`): 默认值 = wav (支持: wav, mp3, m4a, flac, opus)
*   **采样率 (Sample Rate)** (`sample_rate`): 默认值 = 16000 (支持: 8000, 16000, 24000, 48000)
*   **标点预测 (Punctuation)** (`enable_punctuation_prediction`): 默认值 = True (仅老模型支持)
*   **文本归一化 (ITN)** (`enable_itn`): 默认值 = False (Qwen3 ASR 核心参数)
*   **逆文本归一化 (ITN)** (`enable_inverse_text_normalization`): 默认值 = True (仅老模型支持)
*   **去语气词 (Disfluency)** (`disfluency_removal_enabled`): 默认值 = False (仅老模型支持)
*   **说话人分离 (Diarization)** (`speaker_diarization_enabled`): 默认值 = False (仅 fun-asr)

---

### 模型: Qwen3 ASR Flash (实时识别) (`qwen3-asr-flash`)
**提供商**: aliyun
**描述**: 阿里云实时语音识别模型，适合短音频流式识别。
*   **参数支持情况**:
    *   [x] **文本归一化 (ITN)**: 支持 (`enable_itn`)


### 模型: Qwen3 ASR Flash FileTrans (文件转写) (`qwen3-asr-flash-filetrans`)
**提供商**: aliyun
**描述**: 阿里云文件转写模型，支持长音频、语义分段。
*   **参数支持情况**:
    *   [x] **文本归一化 (ITN)**: 支持 (`enable_itn`)


### 模型: FunASR (说话人分离) (`fun-asr`)
**提供商**: aliyun
**描述**: 阿里云 FunASR 模型，支持说话人分离（Speaker Diarization）。
*   **参数支持情况**:
    *   [x] **音频格式 (Format)**: 支持
    *   [x] **采样率 (Sample Rate)**: 支持
    *   [x] **去语气词 (Disfluency)**: 支持
    *   [x] **说话人分离 (Diarization)**: 支持 (默认值: True)
    *   [x] **最大说话人数 (Max Speakers)**: 支持 (默认值: 2)

### 模型: 讯飞语音转写 (`xunfei-lfasr`)
**提供商**: xunfei (讯飞)
**描述**: 讯飞长语音转写服务，支持长达 5 小时的音频文件。适合会议录音、课堂录音等长语音场景。
**所需凭证**: `XUNFEI_APP_ID`, `XUNFEI_SECRET_KEY`
*   **参数支持情况**:
    *   [x] **音频格式 (Format)**: 支持 (wav, mp3, m4a, speex 等)
    *   [ ] **采样率 (Sample Rate)**: 自动检测
    *   [ ] **标点预测 (Punctuation)**: 自动启用
    *   [ ] **说话人分离 (Diarization)**: 自动启用


### 模型: Whisper Large v3 (本地) (`local-whisper-large`)
**提供商**: local
**描述**: OpenAI 开源的最强 ASR 模型 (Large V3)，支持多语言识别和自动翻译。离线可用。
*   **参数支持情况**:
    *   [x] **随机性 (Temperature)**: 支持
    *   [x] **语言 (Language)**: 支持 (如 `zh`, `en`)

