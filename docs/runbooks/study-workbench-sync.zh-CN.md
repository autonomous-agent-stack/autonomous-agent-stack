# Study Workbench Sync MVP

这条 runbook 用 AAS 把 iPad 学习 App 串进后台流程，但不把这些 App 当成知识事实源。Obsidian 和 Git 保存正式知识记录；GoodNotes 负责手写；MarginNote4 负责精读；AAS 负责准备和回收文件。

## 形态

MVP 只在现有 Mac standby worker 上新增三个 worker task type：

- `study_prepare`：读取 Obsidian 学习条目或显式 Markdown，生成最小 PDF，并复制到 GoodNotes / MarginNote inbox 文件夹。
- `study_ingest`：扫描 GoodNotes backup 和 MarginNote export 文件夹，用 fingerprint 去重，清洗文本类导出，并写入 Obsidian `inbox_review/YYYY-MM-DD/`。
- `study_git_sync`：只提交配置的 Obsidian Git 仓库里本次生成的 review inbox 文件。

这里不新增 daemon。定时触发仍走 `/api/v1/worker-schedules`，执行仍复用现有 worker queue / claim / report 主链。

## 配置

先配置本机桥接目录：

```bash
export AUTORESEARCH_STUDY_OBSIDIAN_VAULT_DIR="$HOME/Obsidian/MainVault"
export AUTORESEARCH_STUDY_GOODNOTES_INBOX_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/AAS/GoodNotes-Inbox"
export AUTORESEARCH_STUDY_GOODNOTES_BACKUP_DIRS="$HOME/Library/Mobile Documents/com~apple~CloudDocs/AAS/GoodNotes-Backup"
export AUTORESEARCH_STUDY_MARGINNOTE_INBOX_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/AAS/MarginNote-Inbox"
export AUTORESEARCH_STUDY_MARGINNOTE_EXPORT_DIRS="$HOME/Library/Mobile Documents/com~apple~CloudDocs/AAS/MarginNote-Export"
export AUTORESEARCH_STUDY_GIT_REPO_DIR="$HOME/Obsidian/MainVault"
export AUTORESEARCH_STUDY_REVIEW_INBOX_RELATIVE_DIR="inbox_review"
export AUTORESEARCH_STUDY_GIT_PUSH_ENABLED=false
```

可选 OCR hook：

```bash
export AUTORESEARCH_STUDY_OCR_COMMAND="your-ocr-command"
```

如果 OCR 没有配置或不可用，纯手写 PDF 会被标记为 degraded，不会被假装成 OCR 成功。

## 手动 Smoke

按常规方式启动 API 和 Mac worker：

```bash
make start
./scripts/start-mac-worker.sh
```

检查就绪状态：

```bash
curl http://127.0.0.1:8001/api/v1/study-workbench/health
```

准备一份 iPad 学习材料：

```bash
curl -X POST http://127.0.0.1:8001/api/v1/study-workbench/prepare \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Transformer Self Attention",
    "markdown_text": "# Transformer Self Attention\n\nQ/K/V and multi-head attention notes.",
    "targets": ["goodnotes", "marginnote"],
    "requested_by": "runbook"
  }'
```

回收导出的学习笔记：

```bash
curl -X POST http://127.0.0.1:8001/api/v1/study-workbench/ingest \
  -H 'Content-Type: application/json' \
  -d '{"requested_by": "runbook"}'
```

`study_ingest` 只要写入了 review notes，就会自动 enqueue `study_git_sync`。默认 git task 只创建本地 commit，不 push。

## 边界

- GoodNotes 和 MarginNote4 仍需要在 iPad 端导入或打开文件。
- AAS 负责准备 inbox 文件和回收导出，不声称完全自动操控 App。
- `study_git_sync` 只提交配置的 review inbox 下的文件。
- 除非显式设置 `AUTORESEARCH_STUDY_GIT_PUSH_ENABLED=true`，否则不会 push。
