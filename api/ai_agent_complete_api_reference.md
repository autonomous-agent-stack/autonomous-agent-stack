# AI Agent 完整 API 参考

> **版本**: v1.0
> **端点数**: 15+

---

## 📡 API 端点

### 1. 基础对话

```http
POST /api/v1/chat
Content-Type: application/json

{
  "message": "Hello, how are you?",
  "context": {
    "user_id": "user123"
  }
}

Response:
{
  "response": "Hello! I'm doing well, thank you!",
  "status": "success",
  "timestamp": "2026-03-27T14:50:00Z"
}
```

---

### 2. 工具调用

```http
POST /api/v1/tools/execute
Content-Type: application/json

{
  "tool_name": "search",
  "parameters": {
    "query": "AI news",
    "limit": 5
  }
}

Response:
{
  "result": [...],
  "status": "success",
  "execution_time": 0.5
}
```

---

### 3. 批量处理

```http
POST /api/v1/batch
Content-Type: application/json

{
  "tasks": [
    "What is AI?",
    "What is ML?",
    "What is DL?"
  ]
}

Response:
{
  "results": [...],
  "status": "success",
  "total_time": 1.2
}
```

---

### 4. 健康检查

```http
GET /health

Response:
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 3600
}
```

---

### 5. 性能指标

```http
GET /api/v1/metrics

Response:
{
  "requests_total": 1000,
  "requests_success": 995,
  "avg_latency": 1.2,
  "p95_latency": 2.5,
  "p99_latency": 3.8
}
```

---

### 6. 配置更新

```http
PUT /api/v1/config
Content-Type: application/json

{
  "model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 4000
}

Response:
{
  "status": "success",
  "message": "Configuration updated"
}
```

---

### 7. 记忆管理

```http
POST /api/v1/memory/add
Content-Type: application/json

{
  "user_id": "user123",
  "content": "User likes Python"
}

Response:
{
  "status": "success",
  "memory_id": "mem_123"
}
```

---

### 8. 记忆检索

```http
GET /api/v1/memory/search?user_id=user123&query=Python

Response:
{
  "results": [
    {
      "content": "User likes Python",
      "timestamp": "2026-03-27T14:50:00Z"
    }
  ]
}
```

---

### 9. 清空记忆

```http
DELETE /api/v1/memory/clear?user_id=user123

Response:
{
  "status": "success",
  "deleted_count": 10
}
```

---

### 10. 工具列表

```http
GET /api/v1/tools/list

Response:
{
  "tools": [
    {
      "name": "search",
      "description": "Search the web",
      "parameters": {...}
    },
    ...
  ]
}
```

---

### 11. 添加工具

```http
POST /api/v1/tools/add
Content-Type: application/json

{
  "name": "calculate",
  "description": "Calculate expressions",
  "function": "lambda x: eval(x)"
}

Response:
{
  "status": "success",
  "tool_id": "tool_123"
}
```

---

### 12. 删除工具

```http
DELETE /api/v1/tools/tool_123

Response:
{
  "status": "success",
  "message": "Tool deleted"
}
```

---

### 13. 日志查询

```http
GET /api/v1/logs?level=ERROR&limit=10

Response:
{
  "logs": [
    {
      "timestamp": "2026-03-27T14:50:00Z",
      "level": "ERROR",
      "message": "API timeout"
    }
  ]
}
```

---

### 14. 成本报告

```http
GET /api/v1/costs?period=daily

Response:
{
  "total_cost": 45.20,
  "by_model": {
    "gpt-4": 30.00,
    "gpt-3.5-turbo": 15.20
  }
}
```

---

### 15. 限流配置

```http
PUT /api/v1/rate_limit
Content-Type: application/json

{
  "requests_per_minute": 60,
  "tokens_per_minute": 100000
}

Response:
{
  "status": "success",
  "message": "Rate limit updated"
}
```

---

## 📊 响应码

| 状态码 | 说明 |
|--------|------|
| **200** | 成功 |
| **400** | 参数错误 |
| **401** | 认证失败 |
| **403** | 权限不足 |
| **404** | 资源不存在 |
| **429** | 请求过多 |
| **500** | 服务器错误 |
| **503** | 服务不可用 |

---

**生成时间**: 2026-03-27 14:51 GMT+8
