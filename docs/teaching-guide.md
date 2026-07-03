# God English — 使用教案与开发调试记录

## 一、项目概述

基于 Whisper ASR 的英语口语练习 Web 应用。导入本地音视频或粘贴国内平台链接，自动生成英汉双语同步字幕，跟随音频练习口语。

**技术栈：** Vue 3 + FastAPI + SQLite + whisper.cpp + you-get + Helsinki-NLP/opus-mt-en-zh 本地翻译

---

## 二、使用要点

### 2.1 启动方式（2 个终端，无需 Redis）

**终端 1 — 后端：**
```bash
cd "D:\God English\backend"
# 国内用户必须设置，否则翻译模型无法下载
$env:HF_ENDPOINT="https://hf-mirror.com"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**终端 2 — 前端：**
```bash
cd "D:\God English\frontend"
npm run dev
```

本机浏览器打开 `http://localhost:5173`

**局域网共享：** 其他设备访问 `http://<本机IP>:5173`（需先开放 Windows 防火墙 5173 端口）

### 2.2 功能操作

| 功能 | 操作方式 | 说明 |
|------|----------|------|
| 导入素材库 | 点击顶部 📁 按钮 | 支持 mp3/mp4/wav/webm/m4a/flac，上传有进度条 |
| 粘贴链接 | 顶部输入框粘贴 URL | 支持 B站/抖音/小红书/腾讯视频/爱奇艺/网易云/QQ音乐，自动提取 URL |
| 字幕播放 | 中间区域 | 英汉双语显示，当前句高亮，已播变暗 30%，未播变暗 50% |
| 自由滚动 | 手动滚动字幕列表 | 查看上下文，停止滚动 3 秒后自动回到当前播放句 |
| 点击字幕 | 点击任意字幕行 | 跳转到对应时间点 |
| 播放控制 | 底部控制栏 | 暂停/播放、拖拽进度条、倍速(0.5x-2x) |
| 登录 | 底部"登录"按钮 | 注册/登录，查看历史记录 |
| 历史任务 | 底部用户名按钮 | 查看、继续、删除历史任务 |
| 反馈 | 底部"反馈"按钮 | 提交文字反馈 |

### 2.3 字幕双语格式规则

- **英文：** 每个单词间一个空格
- **中文短词（≤4 个汉字）：** 每个字间加空格，如 `你 好`
- **中文长句（>4 个汉字）：** 保持连续，如 `你好世界`

---

## 三、架构简图

```
浏览器 (Vue 3 :5173)
    │
    ▼ REST API + Vite Proxy
FastAPI (:8000)
    ├── /api/auth/*      认证 (JWT + bcrypt)
    ├── /api/tasks/*     任务管理
    ├── /api/feedback    反馈
    │
    ▼ 后台线程
处理流程:
  上传文件 / 粘贴链接
    → you-get / yt-dlp 下载 (国内平台用 you-get)
    → 音频文件: 直接使用; 视频文件: ffmpeg 提取音频
    → soundfile 读取音频 → 重采样 16kHz → 写 WAV
    → pywhispercpp (tiny.en, 75MB) 转写
    → Helsinki-NLP/opus-mt-en-zh 本地翻译 EN→ZH (~300MB)
    → 字幕存入 SQLite
    → 前端轮询完成 → 播放器加载
```

---

## 四、调试记录（教案用）

以下按时间顺序记录开发过程中遇到的问题和解决方案，可作为软件调试教学案例。

### 4.1 依赖安装问题

| # | 问题 | 原因 | 解决方案 |
|---|------|------|----------|
| 1 | `pip install -r requirements.txt` 失败 | pydantic-core 需要编译，Windows 上缺编译器 | 改用 `>=` 版本号，pip 自动选预编译 wheel |
| 2 | `bcrypt` + `passlib` 不兼容 | bcrypt 5.0 移除了 `__about__` 属性，passlib 未适配 | 直接用 `bcrypt` 库，不用 `passlib` |
| 3 | `faster-whisper` 导入失败 | 依赖 `PyAV`，PyAV 的 C 扩展在 Python 3.14 无预编译 wheel，DLL 加载失败 | 换成 `pywhispercpp`（whisper.cpp Python 绑定） |
| 4 | `openai-whisper` 安装失败 | 依赖 `torch`（800MB+），下载超时 | 放弃，用 `pywhispercpp` |
| 5 | `pywhispercpp` 模型下载失败 | HuggingFace 被墙，无法下载 `ggml-tiny.en.bin` | 从国内镜像 `hf-mirror.com` 手动下载 75MB 模型到 `%LOCALAPPDATA%\pywhispercpp\pywhispercpp\models\` |

**教训：** Python 版本不是越新越好，依赖库的预编译 wheel 可能滞后；国内开发需考虑镜像源。

### 4.2 音频处理问题

| # | 问题 | 原因 | 解决方案 |
|---|------|------|----------|
| 6 | 上传 mp3 报 `ffmpeg 未找到` | Windows 没装 ffmpeg | 音频文件跳过 ffmpeg，用 `soundfile` 直接读取；只有视频文件才需要 ffmpeg 提取音轨 |
| 7 | 转写报 `WAV 文件必须是 16000 Hz` | `pywhispercpp` 要求 16kHz 采样率，mp3 通常是 44.1kHz | 用 numpy 线性插值重采样到 16kHz |
| 8 | 转写报 `ffmpeg not in PATH` | `pywhispercpp` 内部用 ffmpeg 解码 mp3 | 用 `soundfile` 先读成 WAV，再喂给 `pywhispercpp` |

**教训：** 链式依赖的每一步都可能引入新的环境要求，应尽量在入口处统一处理格式转换。

### 4.3 前后端交互问题

| # | 问题 | 原因 | 解决方案 |
|---|------|------|----------|
| 9 | 上传 11MB mp3 极慢/超时 | 无上传进度提示；Celery+Redis 未启动导致任务永远 `processing` | 去掉 Celery/Redis，改成后台 `Thread` 直接处理 |
| 10 | 播放器无声音 | `<audio>` 标签发 HTTP 请求不带 `Authorization` 头，后端返回 401 | 音频 URL 加 `?token=xxx` query 参数，后端新增 `get_user_from_token()` 支持 query 参数认证 |
| 11 | 进度条拖不动 | 音频加载失败导致 `duration=0`，`seek(0)` 始终跳回原位 | 同 #10，修复音频认证后进度条自动恢复正常 |
| 12 | 无法自动播放 | 同上，音频根本没加载 | 同 #10 |

**教训：** `<audio>` / `<img>` 等 HTML 标签的请求不走 JS 拦截器，需要特殊处理认证；进度条失效的根因往往是数据源没加载成功。

### 4.4 翻译功能问题

| # | 问题 | 原因 | 解决方案 |
|---|------|------|----------|
| 13 | Google 翻译超时 | Google 服务被墙 | 改用 MyMemory 免费 API（`api.mymemory.translated.net`） |
| 14 | MyMemory 报 "不支持该语言" | `deep-translator` 库的 MyMemory 封装不支持 zh-CN | 直接调 HTTP API，绕过库的封装 |
| 15 | 30 句字幕翻译极慢 | 每句单独一次 HTTP 请求，30 次网络往返 | 批量翻译：用 ` \|\|\| ` 分隔符拼接所有句子，一次请求翻译，再按分隔符拆分 |

**教训：** 批量操作比循环单次操作效率高几十倍；第三方库的封装不一定覆盖所有场景，必要时直接调 API。

### 4.5 B站链接下载问题

| # | 问题 | 原因 | 解决方案 |
|---|------|------|----------|
| 16 | 粘贴完整标题+链接报 `非有效 URL` | 前端直接提交整段文本 | 前端加 URL 提取正则，自动从文本中提取 `https://...` |
| 17 | `yt-dlp` 报 HTTP 412 | B站 API 需要特定 `User-Agent` + `Referer` 头 | 添加 Chrome UA 和 B站 Referer |
| 18 | 412 仍然出现 | B站 WBI 签名验证 + Cookie 校验 | 添加 `cookiesfrombrowser` 读取 Edge 浏览器 Cookie |
| 19 | 412 仍然出现（即使已登录） | `yt-dlp` 的 B站提取器与最新 API 不完全兼容 | 改用 `you-get`（针对国内平台的下载工具），`python -m you_get` 下载成功 |

**教训：** 不同下载工具对不同平台的适配程度不同；针对国内平台，`you-get` 比 `yt-dlp` 更可靠；通过浏览器 Cookie 可绕过大部分登录校验。

### 4.6 数据库问题

| # | 问题 | 原因 | 解决方案 |
|---|------|------|----------|
| 20 | 测试报 `Username already taken` | 测试间共享 SQLite 文件，上次测试残留数据 | 每次测试前 `rm -f god_english.db` 清库 |

**教训：** 测试需要隔离环境，每个测试用例应独立创建/清理数据。

### 4.7 JWT 认证问题

| # | 问题 | 原因 | 解决方案 |
|---|------|------|----------|
| 21 | `/api/auth/me` 返回 401 | JWT `sub` claim 必须是字符串，代码传了 `int` | `create_access_token` 中 `to_encode["sub"] = str(to_encode["sub"])` |

**教训：** JWT 规范对各 claim 有类型要求，需查阅 RFC 文档确认。

---

## 五、依赖清单

```
# backend/requirements.txt
fastapi>=0.100.0
uvicorn[standard]>=0.20.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.0
python-multipart>=0.0.5
pywhispercpp>=1.0.0
deep-translator>=1.11.0
soundfile>=0.12.0
numpy>=1.24.0
you-get>=0.4.0
yt-dlp>=2024.0.0
ffmpeg-python>=0.2.0
aiofiles>=23.0.0
```

额外系统依赖：
- Python 3.11+
- Node.js 18+
- ffmpeg（仅视频文件需要）

---

## 六、代码仓库

`https://github.com/Hike19/God-English-Teaching`

---

*文档生成日期：2026-07-03*
