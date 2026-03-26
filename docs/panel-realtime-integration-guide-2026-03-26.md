# 面板实时数据集成指南

> **集成时间**：2026-03-26 10:10 GMT+8
> **目标**：让面板显示实时数据

---

## ✅ 已完成

### 1. 后端 API 接口

**文件**：`src/bridge/api.py`

**端点**：`GET /api/v1/system/health`

**响应**：
```json
{
  "cleanup_count": 82,
  "ast_blocks": 14,
  "uptime": "18h 42m",
  "memory_usage": "1.2GB",
  "agents": [
    {
      "id": "architect",
      "name": "架构领航员",
      "status": "idle",
      "color": "blue",
      "work": "等待指令"
    },
    ...
  ],
  "recent_logs": [
    {
      "id": 1,
      "type": "security",
      "msg": "[环境防御] 物理清理了 82 个 ._ 缓存文件",
      "time": "1m ago"
    },
    ...
  ]
}
```

---

### 2. 前端实时更新

**文件**：`panel/components/SuperAgentDashboard.tsx`

**功能**：
- ✅ 每 30 秒自动刷新数据
- ✅ 调用 `/api/v1/system/health` 接口
- ✅ 更新 Agent 状态
- ✅ 更新审计日志

---

## 🔧 集成到 OpenClaw Web UI

### 步骤 1：挂载面板路由

```python
# src/autoresearch/api/main.py

from fastapi.staticfiles import StaticFiles

# 挂载面板静态文件
app.mount("/panel", StaticFiles(directory="panel/out", html=True), name="panel")
```

---

### 步骤 2：修改 /status 指令路由

```python
# src/autoresearch/api/routers/gateway_telegram.py

@router.get("/status")
async def status_redirect():
    """重定向到面板"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/panel")
```

---

### 步骤 3：构建前端

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack/panel

# 安装依赖
npm install

# 构建生产版本
npm run build

# 输出到 panel/out 目录
```

---

## 🚀 测试验证

### 测试 1：API 接口

```bash
curl http://127.0.0.1:8001/api/v1/system/health | jq .

# 期望响应：
{
  "cleanup_count": 82,
  "ast_blocks": 14,
  "uptime": "18h 42m",
  "memory_usage": "1.2GB",
  "agents": [...],
  "recent_logs": [...]
}
```

---

### 测试 2：面板访问

```bash
# 在浏览器访问
http://127.0.0.1:8001/panel

# 期望结果：
# - 看到实时更新的 Agent 状态
# - 看到物理防御层统计
# - 看到审计日志流
```

---

### 测试 3：实时更新

```bash
# 1. 打开面板
# 2. 等待 30 秒
# 3. 观察数据是否自动刷新
```

---

## 📊 数据流

```
┌─────────────────────────────────────┐
│  SuperAgentDashboard.tsx            │
│  - useEffect(() => { ... }, [])     │
│  - 每 30 秒调用 API                  │
└─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────┐
│  GET /api/v1/system/health          │
│  - 返回实时统计数据                  │
└─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────┐
│  后端统计模块                        │
│  - AppleDoubleCleaner._cleanup_count│
│  - SecurityAuditor._block_count     │
│  - psutil（内存/运行时间）           │
└─────────────────────────────────────┘
```

---

## 🔧 扩展建议

### 1. WebSocket 实时推送

```typescript
// 使用 WebSocket 实现真正的实时更新
useEffect(() => {
  const ws = new WebSocket('ws://127.0.0.1:8001/ws/system');
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    setStats(data.stats);
    setAgents(data.agents);
    setRecentLogs(data.logs);
  };
  
  return () => ws.close();
}, []);
```

---

### 2. 真实 Agent 状态

```python
# 从 ClaudeAgentService 获取真实状态
from autoresearch.api.dependencies import get_claude_agent_service

@router.get("/api/v1/system/health")
async def get_system_health(
    agent_service: ClaudeAgentService = Depends(get_claude_agent_service)
):
    # 获取真实 Agent 状态
    runs = agent_service.list()
    active_agents = [run for run in runs if run.status in ['running', 'queued']]
    
    agents = [
        {
            "id": run.agent_run_id,
            "name": run.task_name,
            "status": run.status.value,
            "work": run.prompt[:50] + "..."
        }
        for run in active_agents
    ]
    
    return {...}
```

---

## 📁 文件变更

```
修改文件（2 个）：
├── src/bridge/api.py（新增 /api/v1/system/health 接口）
└── panel/components/SuperAgentDashboard.tsx（实时数据更新）

新增功能：
- ✅ 实时数据 API
- ✅ 每 30 秒自动刷新
- ✅ 物理防御层统计
- ✅ Agent 状态更新
```

---

**集成时间**：2026-03-26 10:10 GMT+8
**状态**：✅ 后端 API 已完成，前端已集成
**下一步**：构建前端并测试
