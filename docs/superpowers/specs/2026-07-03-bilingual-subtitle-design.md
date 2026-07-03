# 双语字幕 — 设计文档

**日期:** 2026-07-03
**目标:** 字幕每行上方显示英文原文，下方显示中文翻译

## 问题

后端 `asr.py` 已有 EN→ZH 翻译逻辑，但依赖 MyMemory 免费 API，实际运行时全部失败（静默 fallback 返回英文原文），导致数据库中所有字幕均为纯英文。

## 方案

用离线本地翻译模型替换 MyMemory API，保持现有数据格式，优化前端双语显示样式。

## 后端改动

### `backend/app/services/asr.py`

- **删除** `_translate_batch()` 中的 MyMemory API 调用
- **新增** 基于 `transformers` 的本地翻译管道，使用 `Helsinki-NLP/opus-mt-en-zh` 模型（约 300MB）
- **模型懒加载**：首次翻译时加载模型，之后常驻内存复用
- **翻译逻辑**：逐句调用模型翻译，结果仍格式化为 `"{english}\n{_format_zh(zh)}"`
- **错误处理**：模型加载失败时 fallback 返回纯英文，不阻塞流程
- 保持 `MODEL_SIZE`、`transcribe()` 签名不变

### `backend/requirements.txt`

添加依赖：
```
transformers
torch
sentencepiece
```

## 前端改动

### `frontend/src/components/SubtitleDisplay.vue`

- 将 `{{ sub.text }}` 拆分为英文行和中文行
- 英文行：当前样式（`font-size: 1.1rem`，激活时 `1.3rem`）
- 中文行：稍小字号（`0.9rem`，激活时 `1.05rem`），颜色略淡
- 两行作为一个整体高亮/变暗/点击跳转

## 数据格式

`Subtitle.text` 字段保持不变：`"English text\n中文翻译"`

## 兼容性

- 现有英文-only 数据：只显示英文行（无 `\n`）
- 新数据：显示英中双语

## 不涉及

- 不改数据库 schema
- 不重新翻译已有数据
- 不加 API Key 或外部依赖
- 不改 Celery 任务流程
