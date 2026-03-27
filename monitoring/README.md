# 监控系统

> OpenClaw 运行监控、性能分析和告警系统

---

## 📋 目录

- [快速开始](#快速开始)
- [监控指标](#监控指标)
- [告警配置](#告警配置)
- [可视化仪表板](#可视化仪表板)

---

## 🚀 快速开始

### 1. 安装监控工具

```bash
# 安装 Prometheus
brew install prometheus

# 安装 Grafana
brew install grafana

# 安装 Node Exporter
brew install node_exporter
```

### 2. 配置 Prometheus

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'openclaw'
    static_configs:
      - targets: ['localhost:9090']
  
  - job_name: 'node_exporter'
    static_configs:
      - targets: ['localhost:9100']
```

### 3. 启动监控

```bash
# 启动 Prometheus
prometheus --config.file=prometheus.yml

# 启动 Grafana
brew services start grafana

# 访问仪表板
open http://localhost:3000
```

---

## 📊 监控指标

### 1. 系统指标

| 指标 | 描述 | 阈值 |
|------|------|------|
| **CPU 使用率** | CPU 使用百分比 | < 80% |
| **内存使用率** | 内存使用百分比 | < 80% |
| **磁盘使用率** | 磁盘使用百分比 | < 90% |
| **网络流量** | 入站/出站流量 | - |

### 2. 应用指标

| 指标 | 描述 | 阈值 |
|------|------|------|
| **请求成功率** | API 请求成功率 | > 99% |
| **响应时间** | API 响应时间 | < 500ms |
| **错误率** | 错误请求比例 | < 1% |
| **并发连接数** | 活跃连接数 | < 1000 |

### 3. Agent 指标

| 指标 | 描述 | 阈值 |
|------|------|------|
| **任务成功率** | Agent 任务成功率 | > 95% |
| **平均执行时间** | 任务执行时间 | < 60s |
| **Token 使用量** | Token 消耗量 | - |
| **重试次数** | 任务重试次数 | < 3 |

---

## 🔔 告警配置

### 1. 告警规则

```yaml
# alert.rules.yml
groups:
  - name: openclaw_alerts
    rules:
      # CPU 告警
      - alert: HighCPUUsage
        expr: cpu_usage > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "CPU 使用率过高"
          description: "CPU 使用率超过 80% 已持续 5 分钟"
      
      # 内存告警
      - alert: HighMemoryUsage
        expr: memory_usage > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "内存使用率过高"
          description: "内存使用率超过 80% 已持续 5 分钟"
      
      # 错误率告警
      - alert: HighErrorRate
        expr: error_rate > 0.01
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "错误率过高"
          description: "错误率超过 1% 已持续 2 分钟"
```

### 2. 告警通知

```yaml
# alertmanager.yml
global:
  slack_api_url: 'https://hooks.slack.com/services/xxx'

route:
  receiver: 'team-notifications'
  
receivers:
  - name: 'team-notifications'
    slack_configs:
      - channel: '#alerts'
        send_resolved: true
```

---

## 📈 可视化仪表板

### 1. Grafana 仪表板

**导入仪表板**:
```bash
# 导入官方仪表板
grafana-cli admin data-migration /path/to/dashboard.json

# 或通过 UI 导入
# Dashboard → Import → Upload JSON file
```

**推荐仪表板**:
- **Node Exporter Full** (ID: 1860)
- **Prometheus Stats** (ID: 3662)
- **OpenClaw Overview** (自定义)

### 2. 自定义仪表板

```json
{
  "dashboard": {
    "title": "OpenClaw Monitoring",
    "panels": [
      {
        "title": "CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "cpu_usage",
            "legendFormat": "CPU"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "memory_usage",
            "legendFormat": "Memory"
          }
        ]
      },
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "Requests"
          }
        ]
      }
    ]
  }
}
```

---

## 🔧 监控脚本

### 1. 健康检查脚本

```bash
#!/bin/bash
# health_check.sh

# 检查服务状态
check_service() {
  local service=$1
  if systemctl is-active --quiet $service; then
    echo "✅ $service is running"
  else
    echo "❌ $service is not running"
    # 发送告警
    send_alert "$service is down"
  fi
}

# 发送告警
send_alert() {
  local message=$1
  curl -X POST -H 'Content-type: application/json' \
    --data "{\"text\":\"$message\"}" \
    $SLACK_WEBHOOK_URL
}

# 执行检查
check_service prometheus
check_service grafana
check_service node_exporter
```

### 2. 性能分析脚本

```bash
#!/bin/bash
# performance_analysis.sh

# CPU 分析
analyze_cpu() {
  echo "CPU 分析:"
  top -bn1 | head -20
}

# 内存分析
analyze_memory() {
  echo "内存分析:"
  free -h
}

# 磁盘分析
analyze_disk() {
  echo "磁盘分析:"
  df -h
}

# 网络分析
analyze_network() {
  echo "网络分析:"
  netstat -an | grep ESTABLISHED | wc -l
}

# 执行分析
analyze_cpu
analyze_memory
analyze_disk
analyze_network
```

---

## 📚 相关资源

### 官方文档

- [Prometheus 文档](https://prometheus.io/docs/)
- [Grafana 文档](https://grafana.com/docs/)
- [Node Exporter 文档](https://github.com/prometheus/node_exporter)

### 推荐阅读

- [监控最佳实践](https://prometheus.io/docs/practices/)
- [告警设计指南](https://sre.google/sre-book/practical-alerting/)
- [性能优化指南](https://grafana.com/blog/2022/10/20/how-to-optimize-prometheus-performance/)

---

<div align="center">
  <p>📊 监控一切，掌控全局！</p>
</div>
