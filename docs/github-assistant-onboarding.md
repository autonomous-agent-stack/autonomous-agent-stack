# GitHub Assistant Managed Repo Onboarding

每个新仓库接入时，只做一件事：把仓库元数据补进 `repos.yaml`。

接入完成后，既可以继续用 `./assistant ...`，也可以直接从主 API 的 `/api/v1/github-assistant/*` 入口调用同一套能力。

## 必填项

- `repo`
- `default_branch`
- `language`
- `workspace_mode: temp`
- `allowed_paths`
- `test_command`
- `lint_command`
- `reviewers`
- `labels_map`

## 推荐做法

- `allowed_paths` 先收窄，再放开
- `test_command` 保证失败时非零退出
- `lint_command` 不要带自动改写标志
- `reviewers` 填最终看 PR 的人

## Label Map 建议

- `bug`
- `feature`
- `duplicate`
- `info_needed`
- `auto_execute`

这样 triage 和后续自动化能直接复用，不需要仓库级分支逻辑。

## Executor Adapter

`assistant.yaml` 里的 `executor.adapter` 推荐四选一：

- `codex`
- `openhands`
- `shell`
- `custom`

建议：

- 本地单人工作台：`codex`
- 已有受控执行环境：`openhands`
- 团队自研脚本：`shell` 或 `custom`
