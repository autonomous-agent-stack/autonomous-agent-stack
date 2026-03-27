# AI Agent 完整监控看板配置

> **版本**: v1.0
> **更新时间**: 2026-03-27 21:27
> **看板数**: 10+

---

## 📊 Grafana 看板

### 1. 概览看板

```json
{
  "dashboard": {
    "title": "AI Agent Overview",
    "panels": [
      {
        "title": "Total Requests",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(agent_requests_total[5m]))"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "gauge",
        "targets": [
          {
            "expr": "rate(agent_errors_total[5m]) / rate(agent_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Latency P95",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, agent_request_latency_seconds)"
          }
        ]
      }
    ]
  }
}
```

---

### 2. 性能看板

```json
{
  "dashboard": {
    "title": "Performance Dashboard",
    "panels": [
      {
        "title": "Request Latency",
        "type": "heatmap",
        "targets": [
          {
            "expr": "agent_request_latency_seconds"
          }
        ]
      },
      {
        "title": "Throughput",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(agent_requests_total[1m])"
          }
        ]
      },
      {
        "title": "Active Agents",
        "type": "gauge",
        "targets": [
          {
            "expr": "agent_active_count"
          }
        ]
      }
    ]
  }
}
```

---

### 3. 成本看板

```json
{
  "dashboard": {
    "title": "Cost Dashboard",
    "panels": [
      {
        "title": "Daily Cost",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(increase(agent_cost_total[1d]))"
          }
        ]
      },
      {
        "title": "Token Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(agent_tokens_total[1h])"
          }
        ]
      },
      {
        "title": "Cost by Model",
        "type": "piechart",
        "targets": [
          {
            "expr": "sum by (model) (agent_cost_total)"
          }
        ]
      }
    ]
  }
}
```

---

## 📈 Prometheus 指标

### 核心指标

```yaml
# 请求指标
- agent_requests_total
- agent_errors_total
- agent_request_latency_seconds
- agent_active_count

# Token 指标
- agent_tokens_total
- agent_tokens_input_total
- agent_tokens_output_total

# 成本指标
- agent_cost_total
- agent_cost_by_model_total

# 系统指标
- agent_memory_usage_bytes
- agent_cpu_usage_percent
- agent_connections_active
```

---

## 🔔 告警规则

### 关键告警

```yaml
groups:
  - name: agent-critical
    rules:
      - alert: AgentDown
        expr: up{job="agent"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Agent is down"
      
      - alert: HighErrorRate
        expr: rate(agent_errors_total[5m]) / rate(agent_requests_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
      
      - alert: HighLatency
        expr: histogram_quantile(0.95, agent_request_latency_seconds) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
```

---

## 🎨 看板布局

### 主页面

```
+------------------+------------------+
|  Total Requests  |    Error Rate    |
+------------------+------------------+
|                                      |
|        Request Latency Heatmap       |
|                                      |
+------------------+------------------+
|  Throughput      |  Active Agents   |
+------------------+------------------+
```

### 性能页面

```
+------------------+------------------+
|   P50 Latency    |    P99 Latency   |
+------------------+------------------+
|                                      |
|          Throughput Graph            |
|                                      |
+------------------+------------------+
|  Memory Usage    |   CPU Usage      |
+------------------+------------------+
```

### 成本页面

```
+------------------+------------------+
|   Daily Cost     |   Monthly Cost   |
+------------------+------------------+
|                                      |
|           Token Usage Graph          |
|                                      |
+------------------+------------------+
|  Cost by Model   |  Cost by Agent   |
+------------------+------------------+
```

---

## 📱 移动端看板

### 响应式设计

```css
.dashboard {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.panel {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

@media (max-width: 768px) {
  .dashboard {
    grid-template-columns: 1fr;
  }
}
```

---

## 🔄 实时更新

### WebSocket 集成

```javascript
const ws = new WebSocket('wss://agent.example.com/metrics');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  // 更新看板
  updateDashboard(data);
};

function updateDashboard(metrics) {
  // 更新请求计数
  document.getElementById('requests').textContent = metrics.requests;
  
  // 更新错误率
  document.getElementById('errors').textContent = metrics.errors;
  
  // 更新延迟
  document.getElementById('latency').textContent = metrics.latency;
}
```

---

**生成时间**: 2026-03-27 21:30 GMT+8
