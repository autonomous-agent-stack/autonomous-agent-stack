# UI DAG 节点 API

为浅色极简 UI 看板提供 DAG 数据流接口。

---

## GET /api/v1/openclaw/agents/tree

获取完整的 DAG 节点和边数据。

### 请求

```bash
curl http://localhost:8000/api/v1/openclaw/agents/tree
```

### 响应

```json
{
  "nodes": [
    {
      "id": "planner_001",
      "label": "规划节点",
      "status": "success",
      "duration_ms": 1200,
      "progress": 1.0,
      "metadata": {}
    },
    {
      "id": "generator_001",
      "label": "生成节点",
      "status": "running",
      "duration_ms": 1500,
      "progress": 0.7,
      "metadata": {}
    },
    {
      "id": "validator_001",
      "label": "验证节点",
      "status": "pending",
      "duration_ms": 0,
      "progress": 0.0,
      "metadata": {}
    },
    {
      "id": "executor_001",
      "label": "执行节点",
      "status": "pending",
      "duration_ms": 0,
      "progress": 0.0,
      "metadata": {}
    }
  ],
  "edges": [
    {"from": "planner_001", "to": "generator_001", "label": "生成"},
    {"from": "generator_001", "to": "validator_001", "label": "验证"},
    {"from": "validator_001", "to": "executor_001", "label": "执行"}
  ],
  "metadata": {
    "total_nodes": 4,
    "total_edges": 3,
    "timestamp": "2026-03-25T23:35:00",
    "ui_theme": {
      "background": "#F9FAFB",
      "style": "minimal"
    }
  }
}
```

---

## JSON 结构说明

### Node 节点

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | string | 节点唯一标识 |
| `label` | string | 节点显示名称 |
| `status` | string | 状态：`pending` / `running` / `success` / `failed` |
| `duration_ms` | number | 执行耗时（毫秒） |
| `progress` | number | 进度（0.0 - 1.0） |
| `metadata` | object | 额外元数据 |

### Edge 边

| 字段 | 类型 | 描述 |
|------|------|------|
| `from` | string | 源节点 ID |
| `to` | string | 目标节点 ID |
| `label` | string | 边标签（可选） |

---

## GET /api/v1/openclaw/agents/status

获取系统整体状态摘要。

### 请求

```bash
curl http://localhost:8000/api/v1/openclaw/agents/status
```

### 响应

```json
{
  "total_nodes": 4,
  "status_breakdown": {
    "pending": 2,
    "running": 1,
    "success": 1,
    "failed": 0
  },
  "total_duration_ms": 2700,
  "average_progress": 0.42,
  "is_running": true,
  "timestamp": "2026-03-25T23:35:00"
}
```

---

## 浅色极简 UI 渲染指南

### CSS 变量

```css
:root {
  --background: #F9FAFB;
  --node-border: #E5E7EB;
  --text-primary: #1F2937;
  --text-secondary: #6B7280;
  
  --status-running: #3B82F6;
  --status-success: #10B981;
  --status-failed: #EF4444;
  --status-pending: #9CA3AF;
}
```

### 状态颜色映射

| 状态 | 颜色 | 用途 |
|------|------|------|
| `pending` | `#9CA3AF` | 灰色，等待中 |
| `running` | `#3B82F6` | 蓝色，执行中 |
| `success` | `#10B981` | 绿色，成功 |
| `failed` | `#EF4444` | 红色，失败 |

### 无视觉干扰原则

```css
.dag-node {
  box-shadow: none !important;
  background: var(--background) !important;
  transition: none !important;
}

.dag-node:hover {
  border-color: var(--text-primary);
}
```

### 前端集成示例

```javascript
async function loadDAG() {
  const res = await fetch('/api/v1/openclaw/agents/tree');
  const { nodes, edges, metadata } = await res.json();
  
  nodes.forEach(node => {
    const color = {
      pending: '#9CA3AF',
      running: '#3B82F6',
      success: '#10B981',
      failed: '#EF4444'
    }[node.status];
    
    renderNode({
      id: node.id,
      label: node.label,
      color,
      progress: node.progress,
      duration: formatDuration(node.duration_ms)
    });
  });
  
  edges.forEach(edge => {
    renderEdge(edge.from, edge.to, edge.label);
  });
}

function formatDuration(ms) {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}
```

---

## 其他端点

### GET /api/v1/openclaw/agents/nodes/{node_id}

获取单个节点详情及其连接关系。

```bash
curl http://localhost:8000/api/v1/openclaw/agents/nodes/planner_001
```
