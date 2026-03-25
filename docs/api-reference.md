# 📚 API 参考

> **Autoresearch API - 5 大核心接口详细说明**

---

## 📋 API 总览

| API | 方法 | 路径 | 状态 | 描述 |
|-----|------|------|------|------|
| **Evaluator API** | POST | `/api/v1/evaluations` | ✅ 已实现 | 创建评估任务 |
| **Evaluator API** | GET | `/api/v1/evaluations/{task_id}` | ✅ 已实现 | 查询评估结果 |
| **Evaluator API** | GET | `/api/v1/evaluations` | ✅ 已实现 | 列出所有评估 |
| **Report API** | GET | `/api/v1/reports/{report_id}` | ✅ 已实现 | 获取报告 |
| **Experiment API** | POST | `/api/v1/experiments` | ✅ 已实现 | 创建实验 |
| **Panel API** | GET | `/api/v1/panel/state` | ✅ 已实现 | Web 面板状态（需 JWT Header） |
| **Panel API** | POST | `/api/v1/panel/agents/{agent_run_id}/cancel` | ✅ 已实现 | Web 手动取消（审计+通知） |
| **Panel API** | POST | `/api/v1/panel/agents/{agent_run_id}/retry` | ✅ 已实现 | Web 手动重试（审计+通知） |
| **Telegram Gateway** | POST | `/api/v1/gateway/telegram/webhook` | ✅ 已实现 | `/status` 返回短效魔法链接 |
| **Orchestration API** | POST | `/api/v1/orchestration/prompt/execute` | ✅ 已实现 | 通过 prompt 创建图并执行 |

---

## 1. Evaluator API

### 1.1 创建评估任务

**端点**: `POST /api/v1/evaluations`

**请求体**:
```json
{
  "task_name": "string",           // 必需：任务名称
  "config_path": "string",         // 必需：配置文件路径
  "description": "string",         // 可选：任务描述
  "evaluator_command": {           // 可选：自定义评估器
    "command": ["python", "evaluate.py"],
    "timeout_seconds": 60,
    "work_dir": ".",
    "env": {"FOO": "bar"}
  },
  "criteria": ["accuracy", "completeness", "readability"]  // 可选：评估标准
}
```

**响应**:
```json
{
  "task_id": "eval_abc123",
  "status": "queued",
  "created_at": "2026-03-25T21:00:00Z"
}
```

**示例**:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/evaluations",
    json={
        "task_name": "my_task",
        "config_path": "task.json",
        "evaluator_command": {
            "command": ["python", "evaluate.py"],
            "timeout_seconds": 60
        }
    }
)

print(response.json())
# {"task_id": "eval_abc123", "status": "queued", "created_at": "2026-03-25T21:00:00Z"}
```

---

### 1.2 查询评估结果

**端点**: `GET /api/v1/evaluations/{task_id}`

**响应**:
```json
{
  "task_id": "eval_abc123",
  "status": "completed",  // queued | running | completed | failed | interrupted
  "result": {
    "status": "pass",     // pass | fail
    "score": 85.5,
    "summary": "任务执行成功",
    "metrics": {
      "accuracy": 0.85,
      "completeness": 0.90,
      "readability": 0.82
    }
  },
  "error": null,
  "metadata": {
    "command_source": "override",
    "returncode": 0,
    "duration_seconds": 12.5,
    "stdout_preview": "开始评估...\n评估完成",
    "stderr_preview": ""
  },
  "created_at": "2026-03-25T21:00:00Z",
  "updated_at": "2026-03-25T21:00:15Z",
  "completed_at": "2026-03-25T21:00:15Z"
}
```

**示例**:
```python
result = requests.get("http://localhost:8000/api/v1/evaluations/eval_abc123")

if result.json()["status"] == "completed":
    print(f"评分: {result.json()['result']['score']}")
else:
    print(f"状态: {result.json()['status']}")
```

---

### 1.3 列出所有评估

**端点**: `GET /api/v1/evaluations`

**查询参数**:
- `status`: 按状态过滤（queued | running | completed | failed | interrupted）
- `limit`: 返回数量（默认 100）

**响应**:
```json
{
  "evaluations": [
    {
      "task_id": "eval_abc123",
      "task_name": "my_task",
      "status": "completed",
      "created_at": "2026-03-25T21:00:00Z"
    },
    ...
  ],
  "total": 10,
  "limit": 100
}
```

**示例**:
```python
# 查询所有已完成的评估
response = requests.get(
    "http://localhost:8000/api/v1/evaluations",
    params={"status": "completed", "limit": 10}
)

for eval in response.json()["evaluations"]:
    print(f"{eval['task_name']}: {eval['status']}")
```

---

## 2. Report API

### 2.1 获取报告

**端点**: `GET /api/v1/reports/{report_id}`

**响应**:
```json
{
  "report_id": "report_xyz789",
  "task_id": "eval_abc123",
  "content": "# 评估报告\n\n## 摘要\n任务执行成功...",
  "format": "markdown",
  "created_at": "2026-03-25T21:00:20Z"
}
```

**示例**:
```python
report = requests.get("http://localhost:8000/api/v1/reports/report_xyz789")
print(report.json()["content"])
```

---

## 3. Experiment API

### 3.1 创建实验

**端点**: `POST /api/v1/experiments`

**请求体**:
```json
{
  "experiment_name": "my_experiment",
  "task_ids": ["eval_abc123", "eval_def456"],
  "config": {
    "optimization_goal": "maximize",
    "max_iterations": 100
  }
}
```

**响应**:
```json
{
  "experiment_id": "exp_ghi012",
  "status": "created",
  "created_at": "2026-03-25T21:01:00Z"
}
```

**示例**:
```python
experiment = requests.post(
    "http://localhost:8000/api/v1/experiments",
    json={
        "experiment_name": "optimization_test",
        "task_ids": ["eval_abc123"],
        "config": {"max_iterations": 10}
    }
)

print(experiment.json()["experiment_id"])
```

---

## 4. Variant API（待实现）

### 4.1 生成变体

**端点**: `POST /api/v1/variants`

**请求体**:
```json
{
  "source_task_id": "eval_abc123",
  "mutation_type": "hyperparameter",
  "config": {
    "learning_rate": [0.001, 0.01, 0.1]
  }
}
```

**响应**:
```json
{
  "variant_id": "var_jkl345",
  "status": "created",
  "created_at": "2026-03-25T21:02:00Z"
}
```

---

## 5. Loop Control API（待实现）

### 5.1 启动优化循环

**端点**: `POST /api/v1/loops`

**请求体**:
```json
{
  "experiment_id": "exp_ghi012",
  "strategy": "hill_climbing",
  "max_iterations": 100,
  "convergence_threshold": 0.01
}
```

---

## 6. Orchestration API

### 6.1 Prompt 直接编排并执行

**端点**: `POST /api/v1/orchestration/prompt/execute`

**请求体**:
```json
{
  "prompt": "goal: 优化代码性能\nnodes: planner -> generator -> executor -> evaluator\nretry: evaluator -> generator when decision == 'retry'\nmax_steps: 16\nmax_concurrency: 3",
  "goal": "可选兜底目标",
  "max_steps": 16,
  "max_concurrency": 3,
  "context": {"timestamp": "2026-03-26T00:00:00Z"},
  "include_graph": true
}
```

**响应（成功）**:
```json
{
  "graph_id": "graph_xxx",
  "status": "completed",
  "goal": "优化代码性能",
  "max_steps": 16,
  "max_concurrency": 3,
  "duration_seconds": 0.12,
  "results": {
    "planner": {},
    "generator": {},
    "executor": {},
    "evaluator": {}
  },
  "graph": {
    "graph_id": "graph_xxx",
    "nodes": [],
    "edges": []
  },
  "error": null
}
```

**响应**:
```json
{
  "loop_id": "loop_mno678",
  "status": "running",
  "created_at": "2026-03-25T21:03:00Z"
}
```

---

## 🚨 错误处理

### 错误响应格式

```json
{
  "error": {
    "code": "EVALUATION_NOT_FOUND",
    "message": "评估任务不存在",
    "details": {
      "task_id": "eval_invalid"
    }
  }
}
```

### 常见错误码

| 错误码 | HTTP 状态码 | 描述 |
|--------|-----------|------|
| `EVALUATION_NOT_FOUND` | 404 | 评估任务不存在 |
| `INVALID_REQUEST` | 400 | 请求参数无效 |
| `TIMEOUT_EXCEEDED` | 408 | 执行超时 |
| `INTERNAL_ERROR` | 500 | 内部服务器错误 |

---

## 📊 状态机

### Evaluation 状态流转

```
queued → running → completed
                 → failed
                 → interrupted（重启时恢复）
```

### Experiment 状态流转

```
created → running → completed
                 → failed
                 → paused
```

---

## 🔧 配置选项

### 环境变量

| 变量 | 默认值 | 描述 |
|------|--------|------|
| `AUTORESEARCH_API_DB_PATH` | `artifacts/api/evaluations.sqlite3` | SQLite 数据库路径 |
| `AUTORESEARCH_API_HOST` | `127.0.0.1` | API 服务主机（建议 localhost / Tailscale IP） |
| `AUTORESEARCH_API_PORT` | `8000` | API 服务端口 |
| `AUTORESEARCH_API_ALLOW_UNSAFE_BIND` | `false` | 是否允许绑定公网 IP（不推荐） |
| `AUTORESEARCH_PANEL_JWT_SECRET` | _空_ | 面板 JWT 签名密钥（启用魔法链接必填） |
| `AUTORESEARCH_PANEL_BASE_URL` | `http://127.0.0.1:8000/api/v1/panel/view` | Telegram 返回的面板链接前缀 |
| `AUTORESEARCH_TELEGRAM_MINI_APP_URL` | _空_ | `/status` 消息里附带 Telegram Mini App 按钮时使用的 URL |
| `AUTORESEARCH_PANEL_MAGIC_LINK_TTL_SECONDS` | `300` | 魔法链接有效期（秒） |
| `AUTORESEARCH_PANEL_TELEGRAM_INITDATA_MAX_AGE_SECONDS` | `900` | Telegram Mini App initData 最大有效时长（秒） |
| `AUTORESEARCH_TELEGRAM_ALLOWED_UIDS` | _空_ | 允许访问面板的 Telegram UID 白名单（逗号分隔） |
| `AUTORESEARCH_TELEGRAM_BOT_TOKEN` | _空_ | Telegram 实时通知 Bot Token |
| `AUTORESEARCH_TELEGRAM_SECRET_TOKEN` | _空_ | Telegram webhook Header 校验 token |
| `CLOUDFLARE_TUNNEL_PUBLIC_BASE_URL` | _空_ | Cloudflare Tunnel 对外域名（例如 `https://panel.example.com`） |

### 示例配置

```bash
# .env 文件
AUTORESEARCH_API_DB_PATH=/data/evaluations.sqlite3
AUTORESEARCH_API_HOST=127.0.0.1
AUTORESEARCH_API_PORT=8000
AUTORESEARCH_PANEL_JWT_SECRET=replace-with-random-secret
AUTORESEARCH_PANEL_BASE_URL=http://100.88.1.9:8000/api/v1/panel/view
AUTORESEARCH_PANEL_MAGIC_LINK_TTL_SECONDS=300
AUTORESEARCH_PANEL_TELEGRAM_INITDATA_MAX_AGE_SECONDS=900
AUTORESEARCH_TELEGRAM_ALLOWED_UIDS=9527
AUTORESEARCH_TELEGRAM_BOT_TOKEN=123456:ABCDEF
AUTORESEARCH_TELEGRAM_SECRET_TOKEN=webhook-secret-token
```

### 零信任访问建议（双方案）

1. 方案一（Tailscale）：
   `AUTORESEARCH_API_HOST` 绑定为 `127.0.0.1` 或 Tailscale IP（`100.64.0.0/10`），通过 `/status` 使用 JWT 魔法链接访问面板。
2. 方案二（Cloudflare Tunnel + TWA）：
   API 仍绑定 `127.0.0.1`，Tunnel 仅转发私有域名；Telegram Mini App 请求携带 `x-telegram-init-data`，后端验签并校验 UID 白名单。
3. 面板后端同时支持两种访问头：
   `Authorization: Bearer <jwt>` / `x-autoresearch-panel-token` / `x-telegram-init-data`。
4. 所有面板 `cancel/retry` 自动写入 SQLite 审计并推送 Telegram。

---

## 🧪 测试示例

### 单元测试

```python
# tests/test_evaluator_api.py
from fastapi.testclient import TestClient
from src.autoresearch.api.main import app

client = TestClient(app)

def test_create_evaluation():
    response = client.post(
        "/api/v1/evaluations",
        json={
            "task_name": "test_task",
            "config_path": "test.json"
        }
    )
    assert response.status_code == 200
    assert "task_id" in response.json()

def test_get_evaluation():
    # 先创建任务
    create_response = client.post(
        "/api/v1/evaluations",
        json={
            "task_name": "test_task",
            "config_path": "test.json"
        }
    )
    task_id = create_response.json()["task_id"]
    
    # 查询任务
    response = client.get(f"/api/v1/evaluations/{task_id}")
    assert response.status_code == 200
    assert response.json()["task_id"] == task_id
```

---

## 📖 最佳实践

### 1. 超时设置

```python
# 根据任务复杂度设置合理的超时时间
{
    "evaluator_command": {
        "command": ["python", "evaluate.py"],
        "timeout_seconds": 300  # 5 分钟
    }
}
```

### 2. 错误处理

```python
try:
    result = requests.post("/api/v1/evaluations", json=data, timeout=10)
    result.raise_for_status()
except requests.exceptions.Timeout:
    print("请求超时")
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 404:
        print("任务不存在")
    else:
        print(f"HTTP 错误: {e.response.status_code}")
```

### 3. 批量操作

```python
# 批量创建任务
tasks = [
    {"task_name": f"task_{i}", "config_path": "task.json"}
    for i in range(10)
]

results = []
for task in tasks:
    result = requests.post("/api/v1/evaluations", json=task)
    results.append(result.json())
```

---

## 🔗 相关资源

- **主文档**: [README.md](../README.md)
- **架构文档**: [architecture.md](architecture.md)
- **集成指南**: [integration-guide.md](integration-guide.md)
- **路线图**: [roadmap.md](roadmap.md)

---

**API 使用愉快！** 🚀
