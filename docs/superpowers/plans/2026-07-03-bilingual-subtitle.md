# 双语字幕 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将字幕 ASR 的 EN→ZH 翻译从不可靠的 MyMemory API 替换为本地离线模型 Helsinki-NLP/opus-mt-en-zh，并优化前端双语显示样式。

**Architecture:** 后端 `asr.py` 用 `transformers` 管道加载 OPUS-MT 模型做本地翻译，输出格式保持 `"English\n中文"`。前端 `SubtitleDisplay.vue` 按 `\n` 拆分行，英文行维持现样式，中文行用稍小字号。

**Tech Stack:** Python 3.11+, transformers, torch, sentencepiece, Vue 3 + TypeScript

## Global Constraints

- 不修改数据库 schema
- 保持 `Subtitle.text` 字段格式为 `"English\n中文"`
- 旧数据（无 `\n`）只显示英文行
- 翻译失败时 fallback 返回纯英文，不阻塞流程

---

### Task 1: 添加后端依赖

**Files:**
- Modify: `D:\God English\backend\requirements.txt`

**Interfaces:**
- Produces: `transformers`, `torch`, `sentencepiece` 可供导入

- [ ] **Step 1: 在 requirements.txt 末尾添加三个依赖**

```txt
transformers>=4.40.0
torch>=2.0.0
sentencepiece>=0.2.0
```

修改后的完整文件内容：

```txt
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
yt-dlp>=2024.0.0
ffmpeg-python>=0.2.0
aiofiles>=23.0.0
transformers>=4.40.0
torch>=2.0.0
sentencepiece>=0.2.0
```

- [ ] **Step 2: 安装新依赖**

```bash
cd "D:/God English/backend" && pip install transformers>=4.40.0 torch>=2.0.0 sentencepiece>=0.2.0
```

预期：三个包成功安装，无错误。

- [ ] **Step 3: 提交**

```bash
cd "D:/God English" && git add backend/requirements.txt && git commit -m "chore: add transformers, torch, sentencepiece for local translation"
```

---

### Task 2: 替换 ASR 翻译引擎为本地 OPUS-MT 模型

**Files:**
- Modify: `D:\God English\backend\app\services\asr.py`

**Interfaces:**
- Consumes: `transformers` 中的 `pipeline`
- Produces: `_translate_batch(texts: list[str]) -> list[str]` — 签名不变，返回 `["English\n中文", ...]`

- [ ] **Step 1: 修改文件顶部 import**

定位到 `asr.py` 第 1-7 行，在现有 import 后添加 transformers 导入：

```python
import os
import re
import tempfile
import numpy as np
import soundfile as sf
from pywhispercpp.model import Model
from transformers import pipeline  # 新增
```

实现：将第 7 行 `from pywhispercpp.model import Model` 之后插入 `from transformers import pipeline`。

- [ ] **Step 2: 添加模型加载函数**

在 `get_model()` 函数（第 13-18 行）之后，`_format_zh()` 函数（第 22-33 行）之前，插入翻译模型加载逻辑：

```python
MODEL_SIZE = "tiny.en"
TARGET_SR = 16000
_model: Model | None = None
_translator = None  # 新增


def get_translator():
    """Lazy-load OPUS-MT en→zh translation model."""
    global _translator
    if _translator is None:
        print("[TR] Loading translation model Helsinki-NLP/opus-mt-en-zh...")
        _translator = pipeline("translation", model="Helsinki-NLP/opus-mt-en-zh")
        print("[TR] Translation model loaded.")
    return _translator
```

- [ ] **Step 3: 重写 `_translate_batch()` 函数**

将原 `_translate_batch` 函数（第 36-60 行）替换为：

```python
def _translate_batch(texts: list[str]) -> list[str]:
    """Batch translate English texts to Chinese using local OPUS-MT model.
    Returns bilingual strings in format "English\n中文"."""
    if not texts:
        return texts

    try:
        translator = get_translator()
        results = []
        for text in texts:
            if not text.strip():
                results.append(text)
                continue
            zh_result = translator(text, max_length=512)
            zh_text = zh_result[0]["translation_text"]
            results.append(f"{text}\n{_format_zh(zh_text)}")
        return results
    except Exception as e:
        print(f"[TR] Translation failed: {e}, falling back to English only")
        return texts
```

替换时注意：删除原函数中所有 MyMemory API + requests 相关代码。

- [ ] **Step 4: 验证后端 ASR 流程**

```bash
cd "D:/God English/backend"
python -c "
from app.services.asr import get_translator
t = get_translator()
result = t('Hello, how are you?', max_length=512)
print('Translation test:', result[0]['translation_text'])
"
```

预期：首次运行会下载模型（约 300MB），然后输出中文翻译如 `你好，你好吗？`

- [ ] **Step 5: 运行后端现有测试**

```bash
cd "D:/God English/backend" && python -m pytest tests/ -v
```

预期：所有测试通过，特别是 `test_tasks.py` 中的任务处理测试。

- [ ] **Step 6: 提交**

```bash
cd "D:/God English" && git add backend/app/services/asr.py && git commit -m "feat: replace MyMemory API with local OPUS-MT EN→ZH translation model"
```

---

### Task 3: 优化前端双语字幕显示

**Files:**
- Modify: `D:\God English\frontend\src\components\SubtitleDisplay.vue`

**Interfaces:**
- Consumes: `Subtitle` 接口 — `text: string`（可能含 `\n` 分隔符）
- Produces: 双语字幕 UI — 英文行在上（正常样式），中文行在下（较小字体）

- [ ] **Step 1: 在 `<script setup>` 中添加文本拆分方法**

在 `seekTo` 函数（第 45-47 行）之后插入：

```typescript
function splitLines(text: string): { en: string; zh: string } {
  const idx = text.indexOf('\n')
  if (idx === -1) return { en: text, zh: '' }
  return { en: text.slice(0, idx), zh: text.slice(idx + 1) }
}
```

- [ ] **Step 2: 修改模板中的字幕行渲染**

将模板第 13-14 行：

```html
      @click="seekTo(sub.start_time)"
    >
      {{ sub.text }}
    </div>
```

替换为：

```html
      @click="seekTo(sub.start_time)"
    >
      <span class="en-line">{{ splitLines(sub.text).en }}</span>
      <span v-if="splitLines(sub.text).zh" class="zh-line">{{ splitLines(sub.text).zh }}</span>
    </div>
```

- [ ] **Step 3: 新增中文行样式**

在 CSS 的 `.subtitle-line.active` 规则之后（第 79 行之后）添加：

```css
.en-line { display: block; }
.zh-line { display: block; font-size: 0.85em; opacity: 0.75; }
.subtitle-line.active .zh-line { opacity: 0.85; }
```

- [ ] **Step 4: 运行前端测试**

```bash
cd "D:/God English/frontend" && npx vitest run src/components/__tests__/SubtitleDisplay.test.ts
```

预期：SubtitleDisplay 测试通过。

- [ ] **Step 5: 提交**

```bash
cd "D:/God English" && git add frontend/src/components/SubtitleDisplay.vue && git commit -m "feat: split subtitle into English/Chinese lines with distinct styles"
```

---

### Task 4: 端到端验证

- [ ] **Step 1: 启动后端**

```bash
cd "D:/God English/backend" && python -m uvicorn app.main:app --reload --port 8000
```

启动后检查控制台是否有 `[TR] Loading translation model` 和 `[TR] Translation model loaded.` 日志。

- [ ] **Step 2: 启动前端**

```bash
cd "D:/God English/frontend" && npm run dev
```

- [ ] **Step 3: 手动测试**

1. 打开 `http://localhost:5173`
2. 上传一个英文音频文件或粘贴英文视频链接
3. 等待处理完成
4. 确认字幕同时显示英文（上）和中文（下）
5. 播放时确认：当前句高亮、已播放变暗、点击跳转均正常

- [ ] **Step 4: 提交（如有修改）**

```bash
cd "D:/God English" && git add -A && git commit -m "chore: final verification tweaks"
```
