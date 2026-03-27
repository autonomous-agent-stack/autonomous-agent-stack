# AI Agent 数据可视化完整指南

> **版本**: v1.0
> **更新时间**: 2026-03-27 14:10
> **可视化类型**: 30+

---

## 📊 数据可视化架构

```
┌─────────────────────────────────────────────────────────────┐
│                   数据可视化系统架构                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  数据源     │  │  处理层     │  │  可视化     │         │
│  │  - 监控     │  │  - 清洗     │  │  - Grafana  │         │
│  │  - 日志     │  │  - 聚合     │  │  - Kibana  │         │
│  │  - 业务     │  │  - 转换     │  │  - 自定义   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  数据存储层                           │   │
│  │  Prometheus / Elasticsearch / PostgreSQL             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 核心图表

### 1. 性能监控面板

```python
import plotly.graph_objects as go
from datetime import datetime

class PerformanceDashboard:
    """性能监控面板"""
    
    def __init__(self, data_source):
        self.data = data_source
    
    def create_dashboard(self) -> go.Figure:
        """创建仪表板"""
        fig = go.Figure()
        
        # 1. 请求速率
        fig.add_trace(go.Scatter(
            x=self.data["timestamp"],
            y=self.data["request_rate"],
            name="Request Rate (RPS)",
            line=dict(color="blue")
        ))
        
        # 2. 响应时间
        fig.add_trace(go.Scatter(
            x=self.data["timestamp"],
            y=self.data["latency_p95"],
            name="P95 Latency (s)",
            line=dict(color="red"),
            yaxis="y2"
        ))
        
        # 布局
        fig.update_layout(
            title="AI Agent Performance",
            xaxis_title="Time",
            yaxis_title="RPS",
            yaxis2=dict(
                title="Latency (s)",
                overlaying="y",
                side="right"
            ),
            height=600,
            hovermode="x unified"
        )
        
        return fig
    
    def save(self, filename: str):
        """保存图表"""
        fig = self.create_dashboard()
        fig.write_html(filename)
```

---

### 2. 成本分析面板

```python
class CostDashboard:
    """成本分析面板"""
    
    def __init__(self, cost_data):
        self.data = cost_data
    
    def create_dashboard(self) -> go.Figure:
        """创建仪表板"""
        fig = make_subplots(
            rows=2,
            cols=2,
            specs=[
                [{"type": "pie"}, {"type": "bar"}],
                [{"type": "scatter"}, {"type": "indicator"}]
            ],
            subplot_titles=[
                "Cost by Model",
                "Daily Cost",
                "Cost Trend",
                "Budget Usage"
            ]
        )
        
        # 1. 成本分布（饼图）
        fig.add_trace(
            go.Pie(
                labels=list(self.data["by_model"].keys()),
                values=list(self.data["by_model"].values()),
                name="Cost by Model"
            ),
            row=1, col=1
        )
        
        # 2. 日成本（柱状图）
        fig.add_trace(
            go.Bar(
                x=self.data["daily"]["date"],
                y=self.data["daily"]["cost"],
                name="Daily Cost"
            ),
            row=1, col=2
        )
        
        # 3. 成本趋势（折线图）
        fig.update_layout(height=800, showlegend=False)
        
        return fig
```

---

### 3. 用户行为面板

```python
class UserBehaviorDashboard:
    """用户行为面板"""
    
    def __init__(self, user_data):
        self.data = user_data
    
    def create_dashboard(self) -> go.Figure:
        """创建仪表板"""
        fig = go.Figure()
        
        # 1. 活跃用户
        fig.add_trace(go.Scatter(
            x=self.data["date"],
            y=self.data["active_users"],
            name="Active Users",
            line=dict(color="green")
        ))
        
        # 2. 请求次数
        fig.add_trace(go.Scatter(
            x=self.data["date"],
            y=self.data["total_requests"],
            name="Total Requests",
            line=dict(color="blue")
        )
        
        fig.update_layout(
            title="User Behavior Analysis",
            xaxis_title="Date",
            yaxis_title="Count",
            height=600
        )
        
        return fig
```

---

### 4. 错误分析面板

```python
class ErrorDashboard:
    """错误分析面板"""
    
    def __init__(self, error_data):
        self.data = error_data
    
    def create_dashboard(self) -> go.Figure:
        """创建仪表板"""
        fig = make_subplots(
            rows=2,
            cols=2,
            specs=[
                [{"type": "pie"}, {"type": "bar"}],
                [{"type": "scatter"}, {"type": "heatmap"}]
            ],
            subplot_titles=[
                "Error by Type",
                "Error by Hour",
                "Error Trend",
                "Error Heatmap"
            ]
        )
        
        # 1. 错误类型分布
        fig.add_trace(
            go.Pie(
                labels=list(self.data["by_type"].keys()),
                values=list(self.data["by_type"].values())
            ),
            row=1, col=1
        )
        
        # 2. 每小时错误
        fig.add_trace(
            go.Bar(
                x=list(range(24)),
                y=self.data["by_hour"]
            ),
            row=1, col=2
        )
        
        # 3. 错误趋势
        fig.add_trace(
            go.Scatter(
                x=self.data["trend"]["timestamp"],
                y=self.data["trend"]["count"]
            ),
            row=2, col=1
        )
        
        # 4. 错误热力图
        # ...
        
        fig.update_layout(height=800, showlegend=False)
        
        return fig
```

---

### 5. 工具使用面板

```python
class ToolUsageDashboard:
    """工具使用面板"""
    
    def __init__(self, tool_data):
        self.data = tool_data
    
    def create_dashboard(self) -> go.Figure:
        """创建仪表板"""
        fig = go.Figure()
        
        # 1. 工具调用次数
        fig.add_trace(go.Bar(
            x=list(self.data["usage_count"].keys()),
            y=list(self.data["usage_count"].values()),
            name="Usage Count"
        ))
        
        # 2. 工具成功率
        fig.add_trace(go.Bar(
            x=list(self.data["success_rate"].keys()),
            y=[r * 100 for r in self.data["success_rate"].values()],
            name="Success Rate (%)"
        ))
        
        fig.update_layout(
            title="Tool Usage Analysis",
            barmode="group",
            height=600
        )
        
        return fig
```

---

## 📈 Grafana 集成

### 1. Prometheus 数据源

```yaml
# grafana/datasources/prometheus.yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

### 2. Dashboard 配置

```json
{
  "dashboard": {
    "title": "AI Agent Dashboard",
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
            "fig.update_layout(title="Latency Distribution", xaxis_title="Latency (s)", yaxis_title="Count", height=400)
            return fig
        
        def main():
            # 生成示例数据
            data = {
                "timestamps": pd.date_range(start="2026-03-27 14:00:00", periods=100, freq="1min"),
                "latencies": np.random.exponential(2, 100)
            }
            
            # 创建可视化
            viz = LatencyVisualization(data)
            fig = viz.plot_latency_distribution()
            fig.show()

    if __name__ == "__main__":
        main()
        ```
        
        **效果**:
        - 可视化延迟分布
        - 识别性能瓶颈
        - 优化用户体验

---

## 📊 可视化最佳实践

### 1. 选择合适的图表类型

| 数据类型 | 推荐图表 | 用途 |
|---------|---------|------|
| **时间序列** | 折线图 | 趋势分析 |
| **分布** | 直方图 | 数据分布 |
| **对比** | 柱状图 | 多组对比 |
| **占比** | 饼图 | 比例展示 |
| **关系** | 散点图 | 相关性分析 |
| **热力图** | 热力图 | 密度分析 |

### 2. 颜色方案

```python
# 1. 性能监控配色
colors_performance = {
    "good": "#28a745",  # 绿色
    "warning": "#ffc107",  # 黄色
    "critical": "#dc3545"  # 红色
}

# 2. 成本分析配色
colors_cost = {
    "cheap": "#28a745",
    "moderate": "#17a2b8",
    "expensive": "#dc3545"
}

# 3. 错误类型配色
colors_error = {
    "error": "#dc3545",
    "warning": "#ffc107",
    "info": "#17a2b8"
}
```

### 3. 响应式设计

```css
/* 响应式布局 */
.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
}

.chart-container {
    width: 100%;
    height: 400px;
}

@media (max-width: 768px) {
    .chart-container {
        height: 300px;
    }
}
```

---

## 🎯 可视化清单

### 必需可视化

- [ ] 性能监控面板
- [ ] 成本分析面板
- [ ] 错误分析面板
- [ ] 资源使用面板

### 推荐可视化

- [ ] 用户行为面板
- [ ] 工具使用面板
- [ ] 数据库性能面板
- [ ] API 调用面板

### 高级可视化

- [ ] 预测分析面板
- [ ] 异常检测面板
- [ ] 容量规划面板
- **趋势分析面板**

---

**生成时间**: 2026-03-27 14:15 GMT+8
