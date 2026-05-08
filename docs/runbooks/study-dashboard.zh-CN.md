# Study Dashboard

Study Dashboard 是 AAS 面向 iPad 的学习入口。它把技术来源整理成每日 GoodNotes
手帐 PDF、MarginNote4 深读包，以及控制面里的长期复习条目。

## 入口

- PWA：`http://127.0.0.1:3000/study`
- API 状态：`http://127.0.0.1:8001/api/v1/study-dashboard/state`
- 手动刷新：`POST /api/v1/study-dashboard/refresh`
- 每日手帐：`POST /api/v1/study-dashboard/briefs/daily`
- 导出：`POST /api/v1/study-dashboard/briefs/{brief_id}/export`

## 来源

只配置你要用的来源。缺少凭证时页面显示未连接，不会阻塞本地项目主题。

```bash
export AUTORESEARCH_STUDY_DASHBOARD_X_USER_ID="123456"
export AUTORESEARCH_STUDY_DASHBOARD_X_BEARER_TOKEN="..."
export AUTORESEARCH_STUDY_DASHBOARD_YOUTUBE_API_KEY="..."
export AUTORESEARCH_STUDY_DASHBOARD_YOUTUBE_PLAYLIST_ID="PL..."
export AUTORESEARCH_STUDY_DASHBOARD_RSS_URLS="https://example.com/feed.xml,https://example.org/rss"
export AUTORESEARCH_STUDY_DASHBOARD_DAILY_HOUR=8
export AUTORESEARCH_STUDY_DASHBOARD_DAILY_TIMEZONE="Asia/Taipei"
```

YouTube 用专用深读播放列表。学习页对 YouTube 条目执行“深挖”时，会排入现有
`youtube_autoflow` worker，让字幕、摘要和知识库发布继续走受治理的 worker 主链。

## iPad 学习流

1. 在 iPad Safari 打开 `/study`，添加到主屏幕。
2. 点刷新，更新 X 书签、专用 YouTube 播放列表、RSS 和本地主题。
3. 点每日手帐，生成并导出 GoodNotes 可批注 PDF。
4. 同一份 brief 可导出到 MarginNote4，包含 PDF 和 Markdown sidecar。
5. 批注后，把 GoodNotes 或 MarginNote4 导出文件放回配置的 inbox，再运行 `study_ingest`。

## 存储

- Study Dashboard 条目和 brief 存在 API SQLite 数据库。
- PDF 和 Markdown 产物写入 API artifact 目录。
- GoodNotes 和 MarginNote4 inbox 继续复用 Study Workbench 配置。
- Obsidian/Git 仍是回收后的正式知识事实源。
