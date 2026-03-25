# 玛露营销实战手册（P3）

> 目标：基于 Autonomous Agent Stack（P3），稳定产出“专业、去工厂化”的玛露 6g 罐装遮瑕膏营销内容，并实现低成本、可回滚、可观测运行。

---

## 1. 适用范围

- 内容方向：小红书、朋友圈、分销商私信、短视频脚本
- 业务硬约束：
  - 6g 罐装
  - 挑战游泳级别持妆 / 不脱妆
  - 不用调色
  - 遮瑕力强
- 风险要求：
  - 禁止医疗功效暗示
  - 禁止虚假绝对化承诺

---

## 2. 最小启动配置

```bash
export AUTORESEARCH_API_DB_PATH=/absolute/path/to/evaluations.sqlite3
export AUTORESEARCH_AGENT_MAX_CONCURRENCY=20
export AUTORESEARCH_AGENT_MAX_DEPTH=3

export AUTORESEARCH_TOOL_SANDBOX_BACKEND=docker
export AUTORESEARCH_TOOL_SANDBOX_IMAGE=python:3.12-alpine
export AUTORESEARCH_TOOL_SANDBOX_CPUS=1.0
export AUTORESEARCH_TOOL_SANDBOX_MEMORY=512m
export AUTORESEARCH_TOOL_SANDBOX_PIDS_LIMIT=128

export AUTORESEARCH_CLAUDE_COMMAND="claude"

# P3: 预测闸门
export AUTORESEARCH_MIROFISH_ENABLED=true
export AUTORESEARCH_MIROFISH_MIN_CONFIDENCE=0.35
```

```bash
uvicorn autoresearch.api.main:app --host 127.0.0.1 --port 8000
```

---

## 3. 推荐系统提示词

```text
你是“资深文案龙虾”，服务于玛露品牌。输出必须专业、克制、去工厂化。

硬约束：
1) 每条内容必须覆盖至少 2 个核心卖点：
   - 6g 罐装
   - 挑战游泳级别持妆 / 不脱妆
   - 不用调色
   - 遮瑕力强
2) 禁止医疗功效或虚假绝对化承诺。
3) 输出结构：标题 / 核心文案 / 风险检查备注。

风格要求：
- 避免套路化营销口号
- 信息密度高，句式简洁
- 面向真实用户决策，不写“流水线感”文案
```

---

## 4. 标准执行流（生产建议）

1. 创建会话（OpenClawCompat）
2. 先跑 MiroFish 预测，低分直接打回重写（Fail Fast）
3. 通过后再创建 Agent 执行
4. 任务结束后查询任务树和执行摘要
5. 调用 OpenViking 压缩会话，降低下一轮 Token 成本

### 4.1 创建会话

```bash
curl -X POST http://127.0.0.1:8000/api/v1/openclaw/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "产出 10 条玛露遮瑕膏专业短文案",
    "channel": "telegram"
  }'
```

### 4.2 执行前预测

```bash
curl -X POST http://127.0.0.1:8000/api/v1/openclaw/predictions \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "marlu-copy-batch",
    "prompt": "生成 10 条专业、去工厂化的玛露遮瑕文案",
    "metadata": {"campaign": "marlu-6g-q2"}
  }'
```

### 4.3 创建 Agent（通过闸门后）

```bash
curl -X POST http://127.0.0.1:8000/api/v1/openclaw/agents \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "oc_xxx",
    "task": "按模板输出 10 条，需附风险检查备注"
  }'
```

### 4.4 任务树可视化与治理

```bash
# 查询父子任务树
curl http://127.0.0.1:8000/api/v1/openclaw/sessions/oc_xxx/task-tree

# 取消异常任务
curl -X POST http://127.0.0.1:8000/api/v1/openclaw/agents/agent_xxx/cancel

# 重试失败任务
curl -X POST http://127.0.0.1:8000/api/v1/openclaw/agents/agent_xxx/retry
```

### 4.5 会话压缩（OpenViking）

```bash
curl -X POST http://127.0.0.1:8000/api/v1/openclaw/sessions/oc_xxx/compact \
  -H "Content-Type: application/json" \
  -d '{
    "keep_recent_events": 12,
    "summary_max_chars": 1200
  }'
```

---

## 5. 监控指标（看板建议）

- 质量指标：`MiroFish score`（阈值默认 `0.35`）
- 成本指标：`OpenViking compression_ratio`
- 稳定性指标：
  - `running -> interrupted` 恢复数量
  - 取消/重试次数
  - 子任务树最大深度

---

## 6. 常见异常与处理

1. 预测误拦截偏高
   - 临时下调阈值到 `0.30`
   - 或关闭闸门：`AUTORESEARCH_MIROFISH_ENABLED=false`
2. 输出偏“工厂化”
   - 强化系统提示词中的负面约束
   - 对失败样例做 few-shot 反例注入
3. 上下文膨胀导致费用上涨
   - 每批次执行后调用 `/compact`
   - 降低 `keep_recent_events`
4. 本地执行不稳定
   - 检查 Docker 可用性与资源限制
   - 保持 AppleDouble 清理脚本启用

---

## 7. 回滚方案

1. 关闭 MiroFish：`AUTORESEARCH_MIROFISH_ENABLED=false`
2. 暂停 OpenViking 压缩：不调用 `/compact`
3. 保留 OpenClawCompat 与 P1 控制接口（cancel/retry/task-tree）

以上回滚不影响主链可运行性，可在分钟级恢复到 P2 稳态。

---

## 8. 验收标准（替代 OpenClaw）

- 运行链路可用：
  - 会话创建、Agent 执行、取消/重试、任务树查询全部正常
- 成本控制可用：
  - 会话压缩率稳定为正（`compression_ratio > 0`）
- 质量闸门可用：
  - 低分任务被拦截，高分任务可放行
- 结果可追溯：
  - SQLite 中可追踪 session / agent / memory profile
