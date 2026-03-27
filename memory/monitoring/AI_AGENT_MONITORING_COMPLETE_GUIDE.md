# AI Agent 监控与告警完整指南

> **版本**: v1.0
> **更新时间**: 2026-03-27 14:00
> **监控类型**: 40+

---

## 📊 监控架构

```
┌─────────────────────────────────────────────────────────────┐
│                     监控系统架构                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  应用监控   │  │  性能监控   │  │  成本监控   │         │
│  │  - 日志     │  │  - 响应时间 │  │  - Token    │         │
│  │  - 错误     │  │  - 吞吐量   │  │  - API 调用 │         │
│  │  - 事件     │  │  - 资源     │  │  - 预算     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  数据采集层                           │   │
│  │  Prometheus / StatsD / OpenTelemetry                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  存储层     │  │  告警层     │  │  可视化     │         │
│  │  - TSDB     │  │  - 告警规则 │  │  - Grafana  │         │
│  │  - ES       │  │  - 通知     │  │  - Dashboard│         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 核心指标

### 1. 性能指标

```python
from prometheus_client import Counter, Histogram, Gauge

# 请求计数
REQUEST_COUNT = Counter(
    'agent_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

# 请求延迟
REQUEST_LATENCY = Histogram(
    'agent_request_latency_seconds',
    'Request latency',
    ['method', 'endpoint'],
    buckets=[0.1, 0.5, 1, 2, 5, 10]
)

# 活跃请求
ACTIVE_REQUESTS = Gauge(
    'agent_active_requests',
    'Active requests'
)

class PerformanceMonitor:
    """性能监控"""
    
    def __init__(self):
        pass
    
    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """记录请求"""
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        REQUEST_LATENCY.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    @contextmanager
    def track_request(self, method: str, endpoint: str):
        """追踪请求"""
        ACTIVE_REQUESTS.inc()
        
        start = time.time()
        status = 200
        
        try:
            yield
        except Exception as e:
            status = 500
            raise
        finally:
            duration = time.time() - start
            
            self.record_request(method, endpoint, status, duration)
            ACTIVE_REQUESTS.dec()
```

---

### 2. 业务指标

```python
# Agent 调用
AGENT_CALLS = Counter(
    'agent_calls_total',
    'Agent calls',
    ['agent_name', 'model', 'status']
)

# Token 使用
TOKEN_USAGE = Counter(
    'agent_token_usage_total',
    'Token usage',
    ['model', 'type']  # type: input/output
)

# 工具调用
TOOL_CALLS = Counter(
    'agent_tool_calls_total',
    'Tool calls',
    ['tool_name', 'status']
)

class BusinessMonitor:
    """业务监控"""
    
    def record_agent_call(self, agent_name: str, model: str, status: str):
        """记录 Agent 调用"""
        AGENT_CALLS.labels(
            agent_name=agent_name,
            model=model,
            status=status
        ).inc()
    
    def record_token_usage(self, model: str, input_tokens: int, output_tokens: int):
        """记录 Token 使用"""
        TOKEN_USAGE.labels(model=model, type='input').inc(input_tokens)
        TOKEN_USAGE.labels(model=model, type='output').inc(output_tokens)
    
    def record_tool_call(self, tool_name: str, status: str):
        """记录工具调用"""
        TOOL_CALLS.labels(
            tool_name=tool_name,
            status=status
        ).inc()
```

---

### 3. 成本指标

```python
# 成本
COST_TOTAL = Counter(
    'agent_cost_total_dollars',
    'Total cost in dollars',
    ['model', 'category']
)

# 预算
BUDGET_USAGE = Gauge(
    'agent_budget_usage_ratio',
    'Budget usage ratio (0-1)'
)

class CostMonitor:
    """成本监控"""
    
    def __init__(self, daily_budget: float = 100.0):
        self.daily_budget = daily_budget
        self.current_cost = 0.0
    
    def record_cost(self, model: str, cost: float, category: str = "llm"):
        """记录成本"""
        COST_TOTAL.labels(model=model, category=category).inc(cost)
        
        self.current_cost += cost
        
        # 更新预算使用率
        usage_ratio = self.current_cost / self.daily_budget
        BUDGET_USAGE.set(usage_ratio)
        
        # 检查告警
        self._check_budget_alert(usage_ratio)
    
    def _check_budget_alert(self, usage_ratio: float):
        """检查预算告警"""
        if usage_ratio >= 1.0:
            self._send_alert("预算已用完！")
        elif usage_ratio >= 0.8:
            self._send_alert("预算使用 80%！")
        elif usage_ratio >= 0.5:
            self._send_alert("预算使用 50%")
```

---

### 4. 资源指标

```python
# CPU
CPU_USAGE = Gauge(
    'agent_cpu_usage_percent',
    'CPU usage percent'
)

# 内存
MEMORY_USAGE = Gauge(
    'agent_memory_usage_bytes',
    'Memory usage in bytes'
)

# 数据库连接
DB_CONNECTIONS = Gauge(
    'agent_db_connections',
    'Database connections',
    ['pool_name']
)

class ResourceMonitor:
    """资源监控"""
    
    def __init__(self):
        self.process = psutil.Process()
    
    def update_metrics(self):
        """更新指标"""
        # CPU
        cpu_percent = self.process.cpu_percent()
        CPU_USAGE.set(cpu_percent)
        
        # 内存
        memory_info = self.process.memory_info()
        MEMORY_USAGE.set(memory_info.rss)
        
        # 数据库连接
        # DB_CONNECTIONS.labels(pool_name='main').set(get_db_connections())
    
    def start_monitoring(self, interval: int = 60):
        """开始监控"""
        while True:
            self.update_metrics()
            time.sleep(interval)
```

---

## 🚨 告警系统

### 1. 告警规则

```yaml
# alert_rules.yml
groups:
  - name: agent_alerts
    rules:
      # 性能告警
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(agent_request_latency_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "P95 latency is {{ $value }}s"
      
      # 错误率告警
      - alert: HighErrorRate
        expr: rate(agent_requests_total{status="500"}[5m]) / rate(agent_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: error
        annotations:
          summary: "High error rate"
          description: "Error rate is {{ $value | humanizePercentage }}"
      
      # 成本告警
      - alert: BudgetExceeded
        expr: agent_budget_usage_ratio > 1.0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Budget exceeded"
          description: "Daily budget exceeded"
      
      # 资源告警
      - alert: HighCPU
        expr: agent_cpu_usage_percent > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage"
          description: "CPU usage is {{ $value }}%"
```

---

### 2. 告警通知

```python
class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.notifiers = {
            "email": EmailNotifier(),
            "slack": SlackNotifier(),
            "pagerduty": PagerDutyNotifier()
        }
    
    def send_alert(self, alert: Alert):
        """发送告警"""
        # 根据严重级别选择通知渠道
        if alert.severity == "critical":
            channels = ["email", "slack", "pagerduty"]
        elif alert.severity == "error":
            channels = ["email", "slack"]
        else:
            channels = ["slack"]
        
        for channel in channels:
            try:
                self.notifiers[channel].send(alert)
            except Exception as e:
                logger.error(f"Failed to send alert via {channel}: {e}")

class SlackNotifier:
    """Slack 通知"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send(self, alert: Alert):
        """发送到 Slack"""
        color_map = {
            "warning": "#ff9900",
            "error": "#ff0000",
            "critical": "#990000"
        }
        
        payload = {
            "attachments": [{
                "color": color_map.get(alert.severity, "#36a64f"),
                "title": f"Alert: {alert.name}",
                "fields": [
                    {"title": "Severity", "value": alert.severity.upper(), "short": True},
                    {"title": "Value", "value": str(alert.value), "short": True},
                    {"title": "Description", "value": alert.description, "short": False}
                ],
                "footer": f"Fired at {alert.timestamp}"
            }]
        }
        
        requests.post(self.webhook_url, json=payload)
```

---

## 📈 可视化

### 1. Grafana Dashboard

```json
{
  "dashboard": {
    "title": "AI Agent Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(agent_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Latency",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(agent_request_latency_seconds_bucket[5m]))",
            "legendFormat": "P50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(agent_request_latency_seconds_bucket[5m]))",
            "legendFormat": "P95"
          },
          {
            "expr": "histogram_quantile(0.99, rate(agent_request_latency_seconds_bucket[5m]))",
            "legendFormat": "P99"
          }
        ]
      },
      {
        "title": "Cost",
        "type": "stat",
        "targets": [
          {
            "expr": "agent_cost_total_dollars",
            "legendFormat": "Total Cost"
          }
        ]
      }
    ]
  }
}
```

---

## 📊 监控清单

### 必需监控

- [ ] 请求计数
- [ ] 请求延迟（P50/P95/P99）
- [ ] 错误率
- [ ] 成本
- [ ] Token 使用

### 推荐监控

- [ ] CPU/内存
- [ ] 数据库连接
- [ ] 缓存命中率
- [ ] 工具调用统计
- [ ] Agent 调用统计

### 告警配置

- [ ] 高延迟告警
- [ ] 高错误率告警
- [ ] 成本告警
- [ ] 资源告警

---

**生成时间**: 2026-03-27 14:05 GMT+8
