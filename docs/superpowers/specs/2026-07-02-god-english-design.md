# God English — 英语口语练习平台 设计文档

**日期：** 2026-07-02
**版本：** 1.0

---

## 1. 概述

God English 是一个 Web 端的英语口语练习应用。用户可导入本地音视频或粘贴各大平台链接，系统通过 ASR 自动生成同步字幕，用户在中间播放器区域跟随音频和字幕练习口语。支持登录查看历史记录、继续未完成任务，以及提交文字反馈。

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────┐
│                    前端 (Vue 3)                   │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  导入上传  │  │  字幕播放器   │  │  登录/反馈 │  │
│  │  粘贴链接  │  │  (中间区域)   │  │  (底部)    │  │
│  └────┬─────┘  └──────┬───────┘  └─────┬─────┘  │
│       │               │                │        │
└───────┼───────────────┼────────────────┼────────┘
        │               │                │
    REST API (JSON)      │           REST API
        │               │                │
┌───────┼───────────────┼────────────────┼────────┐
│       ▼               ▼                ▼        │
│                 后端 (FastAPI)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ 媒体处理  │  │ ASR 引擎  │  │  用户/反馈    │  │
│  │ yt-dlp   │  │ Whisper  │  │  JWT + DB    │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       │               │               │         │
│       ▼               ▼               ▼         │
│  ┌──────────────────────────────────────────┐   │
│  │           SQLite + 文件存储               │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**核心数据流：**
1. 用户上传文件或粘贴链接 → 后端提取音频 → ASR 生成带时间戳的字幕 → 存入 DB + 返回
2. 前端播放音频 + 同步显示字幕，根据当前时间高亮对应行
3. 用户登录 → 查看历史任务列表 → 可继续未完成的任务

---

## 3. 技术栈

| 层       | 技术                                     | 说明                     |
| -------- | ---------------------------------------- | ------------------------ |
| 前端     | Vue 3 + Vite + TypeScript                | SPA，Vue Router + Pinia  |
| 后端     | Python 3.11+ / FastAPI                   | REST API，异步处理       |
| 后台任务 | Celery + Redis                            | 异步执行 ASR 和媒体处理  |
| ASR      | faster-whisper (Whisper large-v3)        | 中文识别效果好           |
| 媒体抓取 | yt-dlp                                   | 覆盖哔哩哔哩/抖音/小红书等 |
| 数据库   | SQLite                                   | 零配置，前期足够         |
| 认证     | JWT (python-jose + passlib)              | 无状态认证               |

---

## 4. 数据模型

```sql
-- 用户表
users
  id          INTEGER PRIMARY KEY AUTOINCREMENT
  username    TEXT UNIQUE NOT NULL
  password    TEXT NOT NULL  -- bcrypt hashed
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP

-- 任务表
tasks
  id          INTEGER PRIMARY KEY AUTOINCREMENT
  user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE
  source_type TEXT NOT NULL CHECK(source_type IN ('upload', 'url'))
  source_path TEXT NOT NULL  -- 本地相对路径 或 原始URL
  title       TEXT NOT NULL
  status      TEXT NOT NULL DEFAULT 'processing' CHECK(status IN ('processing', 'done', 'failed'))
  audio_path  TEXT           -- 提取/下载的音频文件路径
  error_msg   TEXT           -- status='failed' 时的错误信息
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP

-- 字幕表
subtitles
  id          INTEGER PRIMARY KEY AUTOINCREMENT
  task_id     INTEGER REFERENCES tasks(id) ON DELETE CASCADE
  index       INTEGER NOT NULL  -- 字幕序号
  start_time  REAL NOT NULL     -- 起始时间（秒）
  end_time    REAL NOT NULL     -- 结束时间（秒）
  text        TEXT NOT NULL     -- 字幕文本

-- 反馈表
feedback
  id          INTEGER PRIMARY KEY AUTOINCREMENT
  user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL
  content     TEXT NOT NULL
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
```

---

## 5. API 接口

### 5.1 认证

| 方法   | 路径                    | 说明             | 认证 |
| ------ | ----------------------- | ---------------- | ---- |
| POST   | `/api/auth/register`    | 用户注册         | 否   |
| POST   | `/api/auth/login`       | 登录 → JWT token | 否   |
| GET    | `/api/auth/me`          | 获取当前用户信息 | 是   |

### 5.2 任务

| 方法   | 路径                  | 说明                           | 认证 |
| ------ | --------------------- | ------------------------------ | ---- |
| POST   | `/api/tasks/upload`   | 上传本地文件 → 返回 task_id    | 是   |
| POST   | `/api/tasks/url`      | 提交链接 → 返回 task_id       | 是   |
| GET    | `/api/tasks`          | 我的任务列表                   | 是   |
| GET    | `/api/tasks/{id}`     | 任务详情（含字幕）             | 是   |
| DELETE | `/api/tasks/{id}`     | 删除任务                       | 是   |
| GET    | `/api/tasks/{id}/audio` | 流式返回音频文件             | 是   |

### 5.3 反馈

| 方法   | 路径                | 说明     | 认证 |
| ------ | ------------------- | -------- | ---- |
| POST   | `/api/feedback`     | 提交反馈 | 是   |

### 5.4 异步处理流程

1. `POST /api/tasks/upload` 或 `POST /api/tasks/url` 立即返回 `{ task_id, status: "processing" }`
2. Celery 后台任务：URL 抓取（或直接使用上传文件）→ 音频提取 → Whisper ASR → 字幕写入 DB → 更新 status 为 "done" 或 "failed"
3. 前端通过轮询 `GET /api/tasks/{id}` 或 WebSocket 获知处理完成

---

## 6. 前端组件结构

```
App
├── HeaderBar
│   ├── ImportUpload    → 点击弹文件选择器，支持视频/音频格式
│   └── PasteUrl        → 输入框 + 提交按钮
│
├── PlayerPanel         → 中间核心区域
│   ├── SubtitleDisplay → 字幕滚动展示区
│   │   └── 当前句全亮，已播句半暗(30%)，未播句半暗(50%)
│   └── PlayerControls  → 控制栏
│       ├── 播放/暂停按钮
│       ├── 倍速选择 (0.5x / 0.75x / 1x / 1.25x / 1.5x / 2x)
│       └── 进度条 (可拖拽，显示已播/剩余时间)
│
├── FooterBar
│   ├── LoginButton     → 打开登录/注册弹窗
│   └── FeedbackButton  → 打开反馈表单弹窗
│
├── LoginModal          → 登录 / 注册 Tab 切换
├── FeedbackModal       → 文字反馈表单
└── TaskHistory         → 历史任务列表页面（登录后可见）
```

**字幕同步机制：**
- 监听 `<audio>` 元素的 `timeupdate` 事件
- 遍历字幕数组，找到 `start_time <= currentTime <= end_time` 的字幕
- 对应字幕行添加 `active` CSS class 实现高亮
- 自动滚动到当前字幕位置

---

## 7. 目录结构

```
God English/
├── frontend/                # Vue 3 前端
│   ├── src/
│   │   ├── components/      # 可复用组件
│   │   ├── views/           # 页面视图
│   │   ├── stores/          # Pinia 状态管理
│   │   ├── api/             # API 调用封装
│   │   ├── router/          # 路由配置
│   │   └── App.vue
│   ├── package.json
│   └── vite.config.ts
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── main.py          # 应用入口
│   │   ├── models.py        # SQLAlchemy 模型
│   │   ├── schemas.py       # Pydantic schemas
│   │   ├── routes/          # 路由模块
│   │   │   ├── auth.py
│   │   │   ├── tasks.py
│   │   │   └── feedback.py
│   │   ├── services/        # 业务逻辑
│   │   │   ├── media.py     # yt-dlp 抓取 + 音频提取
│   │   │   └── asr.py       # Whisper ASR
│   │   └── tasks/           # Celery 任务定义
│   │       └── process.py
│   ├── media/               # 上传/提取的音频文件存储
│   ├── requirements.txt
│   └── alembic/             # 数据库迁移（可选）
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-07-02-god-english-design.md
```

---

## 8. 错误处理

- **上传失败：** 文件格式不支持、文件过大 → 返回 400 + 具体错误信息
- **链接抓取失败：** 链接无效、平台反爬、网络超时 → task status 标记 `failed`，`error_msg` 记录原因
- **ASR 失败：** 音频质量太差、静音文件 → task status 标记 `failed`，`error_msg` 记录原因
- **认证失败：** 返回 401；Token 过期返回 401，前端自动跳转登录弹窗
- **前端错误：** 音频加载失败显示 toast 提示；网络断开显示离线提示并自动重试

---

## 9. 测试策略

| 层级       | 工具              | 覆盖范围                     |
| ---------- | ----------------- | ---------------------------- |
| 后端单元   | pytest            | 模型、业务逻辑函数           |
| 后端接口   | pytest + httpx    | 所有 API 端点                |
| 前端组件   | Vitest            | 关键组件渲染和交互           |
| 前端 E2E   | Playwright        | 核心流程：上传→播放→登录     |

---

## 10. 非功能需求

- **安全：** 密码 bcrypt 哈希；JWT token 有效期 24h；文件上传白名单校验（mp3, mp4, wav, webm, m4a, flac）；上传文件大小限制 500MB
- **性能：** Whisper 处理 1 分钟音频在 30s 内完成（GPU）或 2 分钟内（CPU）；前端首屏加载 < 3s
- **浏览器兼容：** 支持 Chrome / Edge / Firefox 最新两个大版本
