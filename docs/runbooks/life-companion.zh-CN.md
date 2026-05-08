# Life Companion 个人功能包

`personal.life_companion` 是 AAS 的可选个人学习娱乐操作层，依赖 `personal.study_workspace` 和 `personal.entertainment_curator`。

## 启用

```bash
AUTORESEARCH_ENABLED_PERSONAL_PACKAGES=personal.study_workspace,personal.entertainment_curator,personal.life_companion
```

无论 minimal 还是 full mode，默认都不会自动启用这个个人包。

远程 `/study` 入口同样默认关闭。如需签发短期个人控制台链接：

```bash
AUTORESEARCH_PERSONAL_REMOTE_ENABLED=true
AUTORESEARCH_PANEL_JWT_SECRET=change-me
AUTORESEARCH_PERSONAL_REMOTE_BASE_URL=http://127.0.0.1:3000/study
```

## 功能

- 建立统一个人内容图谱：study item、标注、笔记、卡片、复习、推荐、反馈、日计划、导出、source account、活动事件。
- 索引对象化 node、block、显式 backlinks、未链接 mentions、稳定 `item_id` / `card_id` / `plan_id` 回链、标签和已保存白板布局。
- 提供 AI 编排界面，而不是只靠固定 dashboard。编排器可组合 Today Home、filtered view、object dashboard、graph、canvas、portal、review queue、entertainment DJ、export status、知识盲区、去重热点、跟踪主题、无聊刷一刷等面板。
- 呈现知识盲区和反信息茧房探索：弱 backlinks、缺卡片、缺复习、未链接提及、孤立对象都会进入编排。
- 对多源热点按 URL / 标题 / topic 聚类去重；看过的内容降权；显式关注的主题有新信号时再提升。
- 生成成熟产品式推荐 rows：继续学习、深度学习、复习队列、娱乐 DJ、下一步导出。
- 生成每日学习娱乐计划，包含学习块、复习块、奖励块和自动导出。
- 自动生成 GoodNotes PDF、卡片 CSV，以及 MarginNote4 PDF、Markdown sidecar，并嵌入稳定的 `item_id`、`plan_id`、`card_id` 回链、source pins 和 graph seed。
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
- `POST /api/v1/personal/access/magic-link`
- `GET /api/v1/personal/access/verify`
- `GET /api/v1/personal/nodes`
- `GET /api/v1/personal/nodes/{node_id}`
- `GET /api/v1/personal/nodes/{node_id}/backlinks`
- `GET /api/v1/personal/links`
- `POST /api/v1/personal/links`
- `DELETE /api/v1/personal/links/{link_id}`
- `GET /api/v1/personal/mentions`
- `POST /api/v1/personal/mentions/{mention_id}/promote`
- `GET /api/v1/personal/graph`
- `GET /api/v1/personal/canvas`
- `POST /api/v1/personal/canvas`
- `POST /api/v1/personal/layout`

## Telegram

包内直接处理 `/life`、`/open-study`、`/personal`、`/today`、`/for-you`、`/review`、`/cards`、`/dj`、`/reward`、`/export`、`/promote`、`/feedback`。禁用、远程入口关闭或依赖缺失时只返回 package 结果，不创建 control-plane task，也不进入 worker queue。

`/life` 和 `/open-study` 只有在 `AUTORESEARCH_PERSONAL_REMOTE_ENABLED=true` 且 panel 签名配置可用时，才会返回带 token 的 `/study` 链接。

## 注意力策略

- 只在到期复习、关注主题出现高信息量新变化、导出失败、或用户明确要求时打断。
- 不重要不紧急的热点进入低压力 feed，适合无聊时刷。
- `done` 或负反馈后的重复内容会降权；除非用户用 `saved` 或 `more_like_this` 明确关注，且出现新信号。
- 固定保留反信息茧房空间：知识盲区、弱连接对象和缺复习主题会持续露出。

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
