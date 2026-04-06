# GitHub Assistant Safety Rules

## 默认红线

- 不直推默认分支
- 不自动 merge
- 不修改未声明的仓库
- 不修改 `allowed_paths` 外的文件
- 不在校验失败时开正式 PR

## Draft PR 是默认终点

v1 永远走：

1. Bot 分支
2. Commit
3. Push
4. Draft PR

## 什么时候会被拦截

- `gh auth status` 不通过
- 目标仓库不在 `repos.yaml`
- issue 信息不足
- patch 超过 `max_patch_lines`
- 变更文件超过 `max_changed_files`
- 修改了 `forbidden_paths`
- 修改了 `allowed_paths` 外的文件

## 审计产物

每次运行都会留下：

- `summary.json`
- `plan.md`
- `patch.diff`
- `pr_payload.json`

PR review 和 release plan 也会留下：

- `review.md`
- `review.json`
- `release-plan.md`
- `release-plan.json`

先看这些产物，再决定是否扩大权限。
