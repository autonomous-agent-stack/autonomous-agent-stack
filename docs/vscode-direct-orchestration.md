# VS 直连编排指南

本指南用于在 VS Code 中直接驱动本仓库运行时，不依赖第三方插件协议。

## 目标

- 用 prompt 快速构建并运行图编排
- 在 VS Code 内一键执行（Task / Debug）
- 可选通过本仓库 API 远程触发执行

## 已提供能力

- CLI：`scripts/vscode_orchestrate.py`
- API：`POST /api/v1/orchestration/prompt/execute`
- VS Code 任务：`.vscode/tasks.json`
- VS Code 调试配置：`.vscode/launch.json`

## Prompt 格式

```text
goal: 优化代码性能
nodes: planner -> generator -> executor -> evaluator
retry: evaluator -> generator when decision == 'retry'
max_steps: 16
max_concurrency: 3
```

支持自然语言兜底，不写结构化字段也能执行默认链路。

## 方式 1：VS Code Task 直接跑 CLI

1. 打开一个包含编排 prompt 的文件
2. 运行任务：`Orchestration: Run Prompt File`
3. 在终端中查看 JSON 结果

CLI 示例：

```bash
.venv/bin/python scripts/vscode_orchestrate.py \
  --prompt-file examples/orchestration.prompt.md \
  --pretty \
  --include-graph
```

## 方式 2：VS Code Task 走 API

1. 运行任务：`API: Start Local Server`
2. 打开 prompt 文件
3. 运行任务：`Orchestration API: Execute Prompt File`

也可以手工调用：

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/v1/orchestration/prompt/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "goal: 优化代码性能\nnodes: planner -> generator -> executor -> evaluator\nretry: evaluator -> generator when decision == '\''retry'\''\nmax_steps: 16\nmax_concurrency: 3",
    "include_graph": true
  }'
```

## API 请求与响应

请求字段：

- `prompt`：必填，编排 prompt
- `goal`：可选，兜底目标
- `graph_id`：可选，图 ID
- `max_steps`：可选，最大步数
- `max_concurrency`：可选，最大并发
- `context`：可选，执行上下文注入
- `include_graph`：可选，是否返回拓扑

响应字段：

- `status`：`completed` 或 `failed`
- `results`：节点结果
- `graph`：拓扑结构（可选）
- `error`：失败原因（仅失败时）

## 注意事项

- 运行 API 任务时建议使用：`PYTHONPATH=src`
- 若本地未安装依赖，请先执行：`pip install -r requirements.txt`
