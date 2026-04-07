# GitHub Assistant Template Migration Guide

目标：把这套 GitHub 助理模板从一台机器迁到另一台机器，同时保持最小状态量，并支持按 profile 复制不同 GitHub 身份。

## 需要迁移的内容

- 模板仓库本身
- root-only 模式：`assistant.yaml`、`repos.yaml`、`policies/`、`prompts/`
- multi-profile 模式：`profiles.yaml` 和目标 `profiles/<profile_id>/`
- 可选的 `.env.local`

## 不需要迁移的内容

- `runs/`
- `/tmp/github-assistant`
- `.gh-profiles/`
- 任意一次性的工作区副本

## 新机器恢复步骤

1. 克隆模板仓库
2. 安装 `gh`
3. 复制 root 配置或目标 profile 目录
4. 对每个 profile 单独执行 `./assistant auth login --profile <id>`
5. 运行 `./assistant doctor` 或 `./assistant --profile <id> doctor`
6. 如需总览，调用 `GET /api/v1/github-assistant/profiles`
7. 对任意一个受管仓库执行一次 `triage`
8. 再执行一次 `review-pr` 或 `release-plan`，确认新的 lane 也可用

## Profile 复制

如果你只想迁移一个 GitHub 身份，不需要复制整套模板仓库，只需要：

1. 复制 `profiles.yaml`
2. 复制目标 `profiles/<profile_id>/`
3. 在新机器上重新执行一次该 profile 的 `gh auth login`

## 新增仓库

root-only 模式只需要改 `repos.yaml`；multi-profile 模式只需要改对应 profile 的 `repos.yaml`，不需要改 Python 代码：

- 添加 `repo`
- 配默认分支
- 配 `allowed_paths`
- 配 `lint_command` / `test_command`
- 配 reviewer 和 labels
