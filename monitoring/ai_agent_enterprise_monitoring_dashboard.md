# AI Agent 企业级监控看板

> **版本**: v1.0
> **更新时间**: 2026-03-27 16:34
> **监控维度**: 8+

---

## 📊 监控看板架构

### 1. 实时监控面板

```python
from fastapi import FastAPI
from prometheus_client import Counter, Histogram, Gauge
import asyncio

app = FastAPI()

# Prometheus 指标
REQUEST_COUNT = Counter('agent_requests_total', 'Total requests')
REQUEST_LATENCY = Histogram('agent_request_latency_seconds', 'Request latency')
ACTIVE_AGENTS = Gauge('agent_active_count', 'Active agents')
TOKEN_USAGE = Counter('agent_tokens_total', 'Total tokens used')

@app.get("/api/v1/metrics/dashboard")
async def get_dashboard_metrics():
    """获取看板指标"""
    return {
        "requests": {
            "total": REQUEST_COUNT._value.get(),
            "rate_per_minute": calculate_rate(),
        },
        "latency": {
            "p50": REQUEST_LATENCY._quantiles[0.5],
            "p95": REQUEST_LATENCY._quantiles[0.95],
            "p99": REQUEST_LATENCY._quantiles[0.99],
        },
        "agents": {
            "active": ACTIVE_AGENTS._value.get(),
            "idle": get_idle_agents(),
        },
        "tokens": {
            "total": TOKEN_USAGE._value.get(),
            "cost_usd": calculate_cost(),
        }
    }
```

---

## 🎯 8 大监控维度

### 1. 请求监控

```python
class RequestMonitor:
    """请求监控"""
    
    def __init__(self):
        self.requests = []
    
    async def track_request(self, request_id: str, duration: float):
        """追踪请求"""
        self.requests.append({
            "id": request_id,
            "duration": duration,
            "timestamp": time.time()
        })
        
        # 计算统计
        durations = [r["duration"] for r in self.requests[-100:]]
        
        return {
            "count": len(self.requests),
            "avg_duration": np.mean(durations),
            "p95_duration": np.percentile(durations, 95)
        }
```

---

### 2. Agent 状态监控

```python
class AgentMonitor:
    """Agent 状态监控"""
    
    def __init__(self):
        self.agents = {}
    
    async def get_status(self):
        """获取所有 Agent 状态"""
        return {
            "total": len(self.agents),
            "active": len([a for a in self.agents.values() if a["status"] == "active"]),
            "idle": len([a for a in self.agents.values() if a["status"] == "idle"]),
            "error": len([a for a in self.agents.values() if a["status"] == "error"]),
        }
```

---

### 3. Token 使用监控

```python
class TokenMonitor:
    """Token 使用监控"""
    
    def __init__(self):
        self.usage = []
    
    async def track_usage(self, model: str, tokens: int, cost: float):
        """追踪 Token 使用"""
        self.usage.append({
            "model": model,
            "tokens": tokens,
            "cost": cost,
            "timestamp": time.time()
        })
        
        # 计算总成本
        total_cost = sum(u["cost"] for u in self.usage)
        
        return {
            "total_tokens": sum(u["tokens"] for u in self.usage),
            "total_cost": total_cost,
            "by_model": self._group_by_model()
        }
```

---

### 4. 性能监控

```python
class PerformanceMonitor:
    """性能监控"""
    
    async def get_metrics(self):
        """获取性能指标"""
        return {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "network_io": psutil.net_io_counters()._asdict()
        }
```

---

### 5. 错误监控

```python
class ErrorMonitor:
    """错误监控"""
    
    def __init__(self):
        self.errors = []
    
    async def track_error(self, error: Exception, context: dict):
        """追踪错误"""
        self.errors.append({
            "type": type(error).__name__,
            "message": str(error),
            "context": context,
            "timestamp": time.time()
        })
        
        return {
            "total_errors": len(self.errors),
            "error_rate": len(self.errors) / max(len(self.requests), 1),
            "by_type": self._group_by_type()
        }
```

---

### 6. 缓存监控

```python
class CacheMonitor:
    """缓存监控"""
    
    def __init__(self, cache_client):
        self.cache = cache_client
    
    async def get_stats(self):
        """获取缓存统计"""
        info = await self.cache.info()
        
        return {
            "hit_rate": info["keyspace_hits"] / (info["keyspace_hits"] + info["keyspace_misses"]),
            "memory_usage": info["used_memory"],
            "keys": info["db0"]["keys"]
        }
```

---

### 7. 数据库监控

```python
class DatabaseMonitor:
    """数据库监控"""
    
    async def get_metrics(self):
        """获取数据库指标"""
        return {
            "connections": await self._get_connections(),
            "queries_per_second": await self._get_qps(),
            "slow_queries": await self._get_slow_queries(),
            "replication_lag": await self._get_replication_lag()
        }
```

---

### 8. 业务监控

```python
class BusinessMonitor:
    """业务监控"""
    
    async def get_metrics(self):
        """获取业务指标"""
        return {
            "daily_active_users": await self._get_dau(),
            "tasks_completed": await self._get_completed_tasks(),
            "success_rate": await self._get_success_rate(),
            "revenue": await self._get_revenue()
        }
```

---

## 📊 Grafana 看板配置

```yaml
# grafana-dashboard.yaml
apiVersion: 1
providers:
  - name: 'AI Agent Dashboard'
    folder: 'AI'
    type: file
    options:
      path: /var/lib/grafana/dashboards

dashboards:
  - uid: ai-agent-main
    title: AI Agent Overview
    panels:
      - title: Request Rate
        type: graph
        targets:
          - expr: rate(agent_requests_total[5m])
        
      - title: Latency
        type: heatmap
        targets:
          - expr: agent_request_latency_seconds
        
      - title: Active Agents
        type: gauge
        targets:
          - expr: agent_active_count
        
      - title: Token Usage
        type: stat
        targets:
          - expr: sum(agent_tokens_total)
```

---

## 🔔 告警规则

```yaml
# alert-rules.yaml
groups:
  - name: ai-agent-alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(agent_errors_total[5m]) > 0.1
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
      
      - alert: TokenBudgetExceeded
        expr: agent_tokens_total > 1000000
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Token budget exceeded"
```

---

## 📱 移动端看板

```html
<!DOCTYPE html>
<html>
<head>
    <title>AI Agent Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="dashboard">
        <div class="metric-card">
            <h3>请求速率</h3>
            <div id="request-rate">0</div>
        </div>
        
        <div class="metric-card">
            <h3>活跃 Agent</h3>
            <div id="active-agents">0</div>
        </div>
        
        <div class="metric-card">
            <h3>Token 使用</h3>
            <div id="token-usage">0</div>
        </div>
        
        <div class="metric-card">
            <h3>错误率</h3>
            <div id="error-rate">0%</div>
        </div>
    </div>
    
    <canvas id="latency-chart"></canvas>
    
    <script>
        // 实时更新
        setInterval(async () => {
            const response = await fetch('/api/v1/metrics/dashboard');
            const data = await response.json();
            
            document.getElementById('request-rate').textContent = data.requests.rate_per_minute;
            document.getElementById('active-agents').textContent = data.agents.active;
            document.getElementById('token-usage').textContent = data.tokens.total;
            document.getElementById('error-rate').textContent = data.errors.rate + '%';
        }, 5000);
    </script>
</body>
</html>
```

---

## 🔧 部署配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    volumes:
      - ./dashboards:/var/lib/grafana/dashboards
  
  alertmanager:
    image: prom/alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
```

---

## 📊 监控指标汇总

| 维度 | 指标 | 频率 |
|------|------|------|
| **请求** | QPS, 延迟, 成功率 | 实时 |
| **Agent** | 活跃数, 状态, 任务数 | 实时 |
| **Token** | 使用量, 成本, 模型分布 | 实时 |
| **性能** | CPU, 内存, 磁盘, 网络 | 实时 |
| **错误** | 错误率, 错误类型, 堆栈 | 实时 |
| **缓存** | 命中率, 内存, 键数 | 实时 |
| **数据库** | 连接数, QPS, 慢查询 | 实时 |
| **业务** | DAU, 完成任务, 收入 | 每小时 |

---

**生成时间**: 2026-03-27 16:35 GMT+8
