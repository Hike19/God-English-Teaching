# God English — 英语口语练习平台

基于 Whisper ASR 的英语口语练习 Web 应用。导入本地音视频或粘贴平台链接，自动生成英汉双语同步字幕，跟随音频练习口语。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + Vite + TypeScript + Pinia |
| 后端 | Python 3.11+ / FastAPI |
| ASR | pywhispercpp (tiny.en) |
| 翻译 | Helsinki-NLP/opus-mt-en-zh（本地） |
| 媒体抓取 | yt-dlp / you-get + ffmpeg |
| 数据库 | SQLite |
| 任务处理 | 后台线程，无需 Redis/Celery |

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- ffmpeg（仅视频文件需要）

### 安装

```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 运行

需要 2 个终端窗口：

```bash
# 终端 1: FastAPI 后端
cd backend
# 国内用户需设置 HuggingFace 镜像
$env:HF_ENDPOINT="https://hf-mirror.com"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端 2: Vue 前端
cd frontend && npm run dev
```

打开 `http://localhost:5173`（局域网其他设备访问 `http://<本机IP>:5173`）

### 测试

```bash
# 后端
cd backend && python -m pytest

# 前端
cd frontend && npx vitest run
```

## 功能

- 📁 **导入素材库** — 上传本地 mp3/mp4/wav/webm/m4a/flac
- 🔗 **粘贴链接** — 支持 B站/抖音/小红书/腾讯视频/爱奇艺/网易云/QQ音乐等
- 🎤 **ASR 字幕生成** — Whisper 自动识别，字幕带时间戳
- 🌐 **英汉双语字幕** — 英文在上，中文在下，本地模型实时翻译
- ▶️ **同步播放** — 音频与字幕同步，当前句高亮，已播/未播句自动变暗
- 📜 **自由滚动字幕** — 手动翻阅上下文，停止 3 秒后自动回到当前句
- ⏱ **播放控制** — 暂停、倍速(0.5x-2x)、可拖拽进度条
- 👤 **账号系统** — 注册/登录，JWT 认证
- 📋 **历史记录** — 查看、继续、删除历史任务
- ✍️ **反馈** — 提交文字反馈
