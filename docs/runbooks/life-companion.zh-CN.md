# Life Companion 个人功能包

`personal.life_companion` 是 AAS 的可选个人学习娱乐操作层，依赖 `personal.study_workspace` 和 `personal.entertainment_curator`。

## 启用

```bash
AUTORESEARCH_ENABLED_PERSONAL_PACKAGES=personal.study_workspace,personal.entertainment_curator,personal.life_companion
```

无论 minimal 还是 full mode，默认都不会自动启用这个个人包。

## 功能

- 建立统一个人内容图谱：study item、笔记、卡片、推荐、反馈、日计划、导出、活动事件。
- 生成成熟产品式推荐 rows：继续学习、深度学习、复习队列、娱乐 DJ、下一步导出。
- 生成每日学习娱乐计划，包含学习块、复习块、奖励块和自动导出。
- 自动生成 GoodNotes PDF、卡片 CSV，以及 MarginNote4 PDF、Markdown sidecar，并嵌入稳定的 `item_id`、`plan_id`、`card_id` 回链。
- 扫描配置好的 GoodNotes backup 和 MarginNote export 目录，把导出的笔记和学习记录回流到 AAS。

## API

- `GET /api/v1/personal/state`
- `POST /api/v1/personal/ingest`
- `POST /api/v1/personal/recommendations`
- `POST /api/v1/personal/plans/daily`
- `POST /api/v1/personal/reviews`
- `POST /api/v1/personal/cards`
- `POST /api/v1/personal/entertainment/session`
- `POST /api/v1/personal/exports`
- `POST /api/v1/personal/feedback`
- `POST /api/v1/personal/promote`
- `GET /api/v1/personal/search?q=...`

## Telegram

包内直接处理 `/personal`、`/today`、`/for-you`、`/review`、`/cards`、`/dj`、`/reward`、`/export`、`/promote`、`/feedback`。禁用或依赖缺失时只返回 package 结果，不创建 control-plane task，也不进入 worker queue。

## 导出配置

复用 Study Workbench 的路径：

```bash
AUTORESEARCH_STUDY_GOODNOTES_INBOX_DIR=/path/to/GoodNotes-Inbox
AUTORESEARCH_STUDY_GOODNOTES_BACKUP_DIRS=/path/to/GoodNotes-Backup
AUTORESEARCH_STUDY_MARGINNOTE_INBOX_DIR=/path/to/MarginNote-Inbox
AUTORESEARCH_STUDY_MARGINNOTE_EXPORT_DIRS=/path/to/MarginNote-Export
```

导出文件会写入配置好的 inbox 目录，并记录 `prepared`、`copied`、`awaiting_import`、`imported`、`backfilled`、`failed` 状态。

## 边界

这个包只保存 metadata、笔记、摘要、标注、卡片、导出文件、本地路径和官方/来源 URL；不保存受保护的媒体本体，也不写入 GoodNotes 或 MarginNote 的私有数据库。
