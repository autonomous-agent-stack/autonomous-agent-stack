# P3 生态融合手册（OpenViking + MiroFish）

> 目标：在不破坏现有稳定主链的前提下，通过插件化方式接入 OpenViking 分层记忆与 MiroFish 预测旁路，实现“更低 Token 成本 + 更高执行良品率”。

---

## 1. 设计原则

1. 不侵入主链：采用 Sidecar / Adapter，不改核心执行语义。
2. 默认安全：预测闸门默认关闭，需要显式开启。
3. 可回滚：任意阶段可关闭 P3 功能回到 P2 运行模式。
4. 可观测：每次压缩和预测都产出结构化指标。

---

## 2. 架构落点

### OpenViking（Memory Compression Adapter）
- 服务：`OpenVikingMemoryService`
- 作用：
  - 将长会话压缩为“摘要 + 最近窗口”
  - 输出压缩率和 Token 估算，落盘到 session metadata

### MiroFish（Prediction Sidecar）
- 服务：`MiroFishPredictionService`
- 作用：
  - 在执行前评估任务成功置信度
  - 当低于阈值时，直接 Fail Fast 拦截

---

## 3. API 契约（核心）

## 3.1 会话压缩（OpenViking）

### `POST /api/v1/openclaw/sessions/{session_id}/compact`

请求：

```json
{
  "keep_recent_events": 12,
  "summary_max_chars": 1200
}
```

响应（`OpenVikingMemoryProfileRead`）：

```json
{
  "session_id": "oc_xxx",
  "original_event_count": 180,
  "retained_event_count": 13,
  "compressed_event_count": 167,
  "estimated_tokens_before": 9200,
  "estimated_tokens_after": 4100,
  "compression_ratio": 0.5543,
  "summary": "Role distribution: user:70, status:90, tool:20 ...",
  "updated_at": "2026-03-26T02:00:00+00:00"
}
```

### `GET /api/v1/openclaw/sessions/{session_id}/memory-profile`

返回当前会话的压缩画像；如果尚未压缩，`compression_ratio=0`。

---

## 3.2 预测评估（MiroFish）

### `POST /api/v1/openclaw/predictions`

请求：

```json
{
  "task_name": "marketing-copy",
  "prompt": "Generate 10 copies for MARULU with strict brand constraints",
  "metadata": {
    "channel": "telegram"
  }
}
```

响应（`MiroFishPredictionRead`）：

```json
{
  "engine": "mirofish_heuristic_v1",
  "score": 0.83,
  "decision": "allow",
  "reasons": [
    "stable intent signals: analyze, summarize"
  ],
  "created_at": "2026-03-26T02:01:00+00:00",
  "metadata": {
    "prompt_length": 143
  }
}
```

---

## 3.3 执行前闸门（与 Agent Spawn 集成）

接口：`POST /api/v1/openclaw/agents`

当启用闸门后：
- 先调用 MiroFish 预测
- 若 `score < AUTORESEARCH_MIROFISH_MIN_CONFIDENCE` 或 `decision=reject`
- 返回 `422`，并包含预测详情

---

## 4. 环境变量

```bash
# OpenViking 无需额外开关，按接口调用触发

# MiroFish 闸门
export AUTORESEARCH_MIROFISH_ENABLED=true
export AUTORESEARCH_MIROFISH_MIN_CONFIDENCE=0.35
export AUTORESEARCH_MIROFISH_ENGINE=mirofish_heuristic_v1
```

推荐阈值：
- `0.30 ~ 0.40`：平衡拦截与吞吐（默认推荐）
- `> 0.60`：严格模式（适合高风险生产动作）

---

## 5. 运行建议（生产）

1. 白天高峰：阈值略降（例如 `0.30`）保证吞吐。
2. 夜间批处理：阈值略升（例如 `0.45`）提高质量。
3. 每完成一批任务后压缩 session，防止上下文膨胀。
4. 看板固定显示两个指标：
   - `Compression % (OpenViking)`
   - `Prediction Score (MiroFish)`

---

## 6. 回滚策略

1. 发现误拦截偏高：先把 `AUTORESEARCH_MIROFISH_ENABLED=false`
2. 保留压缩功能，不影响执行链路
3. 需要回到完全 P2：
   - 不调用 `/compact`
   - 关闭 MiroFish 闸门

---

## 7. 测试与质量门禁

当前分支已覆盖：
- OpenViking 压缩接口测试
- MiroFish 预测接口测试
- MiroFish 执行前拦截测试

运行命令：

```bash
python -m pytest -q
```

---

## 8. 版本记录

- 2026-03-26：P3 初版，OpenViking + MiroFish 插件化接入完成。
