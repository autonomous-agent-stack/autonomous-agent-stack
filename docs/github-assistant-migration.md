# GitHub Assistant Template Migration Guide

目标：把这套 GitHub 助理模板从一台机器迁到另一台机器，同时保持最小状态量。

## 需要迁移的内容

- 模板仓库本身
- `assistant.yaml`
- `repos.yaml`
- `policies/`
- `prompts/`
- 你的 `gh` 登录态
- 可选的 `.env.local`

## 不需要迁移的内容

- `runs/`
- `/tmp/github-assistant`
- 任意一次性的工作区副本

## 新机器恢复步骤

1. 克隆模板仓库
2. 安装 `gh` 并登录 Bot 账号
3. 复制配置文件
4. 运行 `./assistant doctor` 或 `GET /api/v1/github-assistant/doctor`
5. 对任意一个受管仓库执行一次 `triage`
6. 再执行一次 `review-pr` 或 `release-plan`，确认新的 lane 也可用

## 新增仓库

只需要改 `repos.yaml`，不需要改 Python 代码：

- 添加 `repo`
- 配默认分支
- 配 `allowed_paths`
- 配 `lint_command` / `test_command`
- 配 reviewer 和 labels
