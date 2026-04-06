# GitHub Assistant Template Quickstart

## 1. Bootstrap

```bash
cp .env.template .env.local
chmod +x ./assistant
PATH="$PWD:$PATH" assistant doctor
```

也可以直接运行：

```bash
./assistant doctor
```

## 2. Configure

先改这 3 个文件：

- `assistant.yaml`
- `repos.yaml`
- `policies/default-policy.yaml`

至少要完成：

- 把 `bot_account` 改成你的独立 GitHub Bot 用户
- 把 `repos.yaml` 里的 `repo` 改成你要托管的仓库
- 给每个仓库填好 `allowed_paths`、`test_command`、`lint_command`

运行时也支持环境变量覆盖：

- `GH_ASSISTANT_BOT_ACCOUNT`
- `GH_ASSISTANT_WORKSPACE_ROOT`
- `GH_ASSISTANT_EXECUTOR_ADAPTER`
- `GH_ASSISTANT_EXECUTOR_BINARY`
- `GH_ASSISTANT_EXECUTOR`

## 3. Authenticate

```bash
gh auth login
gh auth status
```

建议直接用 Bot 账号登录，不要把 PAT 写死在模板里。

如果本机 GitHub 认证失效，`doctor` 会明确报错，不会假装通过。例如 token 失效时会看到 `gh auth` 为 `FAIL`，主 API 的 `/api/v1/github-assistant/health` 也会返回 `degraded`。

## 4. Main Product API

启动主 API 后，这套功能可以直接从产品主路径调用：

```bash
curl http://127.0.0.1:8001/api/v1/github-assistant/health
curl http://127.0.0.1:8001/api/v1/github-assistant/doctor
curl -X POST http://127.0.0.1:8001/api/v1/github-assistant/triage \
  -H 'Content-Type: application/json' \
  -d '{"repo":"your-org/your-repo","issue_number":123}'
```

如果本地 `gh auth status` 不通过，涉及真实 GitHub 调用的接口会直接返回 `503`，提示当前环境不可执行。

## 5. Triage

```bash
./assistant triage your-org/your-repo 123
./assistant review-pr your-org/your-repo 456
./assistant release-plan your-org/your-repo --version v1.2.3
```

产物会写到：

```text
runs/<timestamp>/<owner>/<repo>/issue-123/
```

## 6. Execute

默认模板已经预填：

- `bot_account: nxs9bg24js-tech`
- `repos.yaml` 样例仓库：`srxly888-creator/autonomous-agent-stack`

如果你要迁移到自己的仓库，先把这两个值改掉。

再根据你的执行器选择 `assistant.executor`：

- `adapter: codex`
- `adapter: openhands`
- `adapter: shell`
- `adapter: custom`

如果你用 `shell` / `custom`，再补 `executor.command`；如果你用 `codex` / `openhands`，模板有内建默认命令。

然后执行：

```bash
./assistant execute your-org/your-repo 123
```

执行成功后会生成：

- `plan.md`
- `patch.diff`
- `pr_payload.json`
- `summary.json`

如果校验通过，会走 Bot 分支并开 Draft PR。

## 7. Review / Release

PR 复核：

```bash
./assistant review-pr your-org/your-repo 456
```

发布计划：

```bash
./assistant release-plan your-org/your-repo --version v1.2.3
```
