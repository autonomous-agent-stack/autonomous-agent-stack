# Admin View 填写教程（可直接照填）

适用页面：`/api/v1/admin/view`

## 0. 先准备三个环境变量

```bash
export AUTORESEARCH_ADMIN_JWT_SECRET="replace-with-long-random-secret"
export AUTORESEARCH_ADMIN_BOOTSTRAP_KEY="replace-with-bootstrap-key"
export AUTORESEARCH_ADMIN_SECRET_KEY="replace-with-fernet-key"
```

说明：

- `AUTORESEARCH_ADMIN_JWT_SECRET`：用于签发和校验后台 token。
- `AUTORESEARCH_ADMIN_BOOTSTRAP_KEY`：用于调用 `/api/v1/admin/auth/token`。
- `AUTORESEARCH_ADMIN_SECRET_KEY`：只有你要保存 `secret_value`（例如 bot token）时才必须配置。

## 1. 先拿 Admin Token，再打开页面

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/v1/admin/auth/token" \
  -H "Content-Type: application/json" \
  -H "x-admin-bootstrap-key: ${AUTORESEARCH_ADMIN_BOOTSTRAP_KEY}" \
  -d '{"subject":"admin-ui","roles":["admin"],"ttl_seconds":3600}'
```

返回里会有 `token`。打开页面后点 `设置 Admin Token`，粘贴 token（不用加 `Bearer ` 前缀）。

## 2. Channel 怎么填（建议先配）

### A) Telegram 快速配置（推荐）

只填 4 个字段：

- `key`：通道唯一标识，建议 `telegram-main`。
- `bot token`：BotFather 发给你的 token（例如 `123456:ABC...`）。
- `allowed ids`：允许接收/发送的 ID，英文逗号分隔。
- `actor`：操作者标识，建议 `admin-ui`。

点击 `一键保存 Telegram Channel` 即可。

### B) Channel 表单逐项解释

- `key`：唯一键，建议小写 + 中划线，例如 `telegram-main`。
- `display_name`：页面展示名，例如 `Telegram Main`。
- `provider`：
  - `telegram`：Telegram 通道。
  - `webhook`/`http`/`custom`：留给其他通道。
- `endpoint_url`：`webhook/http` 才常用，Telegram 通常留空。
- `secret_ref`：外部密钥引用名（可选）。
- `secret_value`：敏感值本体（可选，例如 bot token）。
- `allowed_chat_ids`：允许的 chat id 列表（逗号分隔）。
- `allowed_user_ids`：允许的 user id 列表（逗号分隔）。
- `actor`：本次变更操作者名，写 `admin-ui` 即可。
- `enabled`：勾选表示立即启用。

## 3. Agent 怎么填

### Agent 表单逐项解释

- `name`：Agent 展示名，例如 `assistant-main`。
- `task_name`：任务名（机器侧标识），例如 `general-task`。
- `default_timeout_seconds`：超时秒数，推荐 `900`。
- `default_generation_depth`：深度，推荐 `1`（新手先别调大）。
- `description`：备注说明。
- `prompt_template`：该 Agent 的系统提示词（核心）。
- `channel_bindings`：绑定通道 key，逗号分隔，通常填 `telegram-main`。
- `actor`：操作者名，建议 `admin-ui`。
- `append_prompt`：一般保持勾选（会把 prompt 追加到命令）。
- `enabled`：勾选表示创建后立即生效。

### 首次可直接用这组值

- `name`: `assistant-main`
- `task_name`: `general-task`
- `default_timeout_seconds`: `900`
- `default_generation_depth`: `1`
- `description`: `default admin agent`
- `prompt_template`: `You are my primary autonomous agent.`
- `channel_bindings`: `telegram-main`
- `actor`: `admin-ui`
- `append_prompt`: `true`
- `enabled`: `true`

## 4. “高级 JSON”什么时候用

这些场景才建议用高级 JSON：

- 需要 `default_env` 覆盖环境变量。
- 需要 `cli_args` 或 `command_override`。
- 批量复制已有配置。

否则优先表单，错误率更低。

## 5. 常见报错对照

- `401 missing admin bearer token`：页面没设置 token。
- `401 invalid bootstrap key`：`x-admin-bootstrap-key` 不对。
- `503 secret cipher is disabled`：你填写了 `secret_value`，但没配置 `AUTORESEARCH_ADMIN_SECRET_KEY`。
- `400 duplicate channel key`：`key` 重复了，换一个新的 key。
- `400 Agent config is inactive`：该 Agent 处于停用状态，先点“启用”再启动。

## 6. 推荐操作顺序（最稳）

1. 先配好一个 Channel（`telegram-main`）。
2. 再建一个 Agent（绑定 `telegram-main`）。
3. 在 Agent 行点 `启动`，先不填 override，做一次最小验证。
4. 成功后再调整 prompt、timeout、depth。
