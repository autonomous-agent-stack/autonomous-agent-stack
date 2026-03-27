# AI Agent 监控告警系统

> **版本**: v1.0
> **更新时间**: 2026-03-27
> **告警类型**: 10+

---

## 📊 监控指标

### 核心指标

| 指标类别 | 具体指标 | 阈值 |
|---------|---------|------|
| **性能** | 响应时间 | > 5s 告警 |
| **可用性** | 成功率 | < 95% 告警 |
| **成本** | 日调用成本 | > $10 告警 |
| **错误** | 错误率 | > 5% 告警 |
| **资源** | CPU/内存 | > 80% 告警 |

---

## 🔔 告警系统实现

```python
"""
AI Agent 监控告警系统
"""

import time
import smtplib
from email.mime.text import MIMEText
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import requests

class AlertSeverity(Enum):
    """告警严重级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class Alert:
    """告警"""
    alert_id: str
    severity: AlertSeverity
    metric: str
    current_value: float
    threshold: float
    message: str
    timestamp: float
    resolved: bool = False

class MonitoringSystem:
    """监控系统"""
    
    def __init__(self):
        self.metrics = {}
        self.alerts = []
        self.thresholds = {
            "response_time": 5.0,       # 秒
            "success_rate": 0.95,       # 95%
            "error_rate": 0.05,         # 5%
            "daily_cost": 10.0,         # 美元
            "cpu_usage": 80.0,          # %
            "memory_usage": 80.0        # %
        }
        
        self.notifiers = []
    
    def add_notifier(self, notifier):
        """添加通知器"""
        self.notifiers.append(notifier)
    
    def record_metric(self, metric_name: str, value: float):
        """记录指标"""
        timestamp = time.time()
        
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        
        self.metrics[metric_name].append({
            "value": value,
            "timestamp": timestamp
        })
        
        # 检查告警
        self._check_threshold(metric_name, value)
    
    def _check_threshold(self, metric_name: str, value: float):
        """检查阈值"""
        threshold = self.thresholds.get(metric_name)
        
        if not threshold:
            return
        
        # 判断是否需要告警
        needs_alert = False
        severity = AlertSeverity.WARNING
        
        if metric_name in ["response_time", "error_rate", "daily_cost", "cpu_usage", "memory_usage"]:
            # 这些指标，值越高越危险
            if value > threshold:
                needs_alert = True
                
                if value > threshold * 1.5:
                    severity = AlertSeverity.ERROR
                if value > threshold * 2.0:
                    severity = AlertSeverity.CRITICAL
        
        elif metric_name == "success_rate":
            # 成功率，值越低越危险
            if value < threshold:
                needs_alert = True
                
                if value < threshold * 0.8:
                    severity = AlertSeverity.ERROR
                if value < threshold * 0.5:
                    severity = AlertSeverity.CRITICAL
        
        if needs_alert:
            self._create_alert(metric_name, value, threshold, severity)
    
    def _create_alert(
        self,
        metric_name: str,
        current_value: float,
        threshold: float,
        severity: AlertSeverity
    ):
        """创建告警"""
        alert = Alert(
            alert_id=f"{metric_name}_{int(time.time())}",
            severity=severity,
            metric=metric_name,
            current_value=current_value,
            threshold=threshold,
            message=self._generate_alert_message(metric_name, current_value, threshold),
            timestamp=time.time()
        )
        
        self.alerts.append(alert)
        
        # 发送通知
        self._send_notification(alert)
    
    def _generate_alert_message(
        self,
        metric_name: str,
        current_value: float,
        threshold: float
    ) -> str:
        """生成告警消息"""
        if metric_name == "response_time":
            return f"⚠️ 响应时间过慢: {current_value:.2f}s (阈值: {threshold}s)"
        elif metric_name == "success_rate":
            return f"⚠️ 成功率过低: {current_value*100:.1f}% (阈值: {threshold*100:.1f}%)"
        elif metric_name == "error_rate":
            return f"⚠️ 错误率过高: {current_value*100:.1f}% (阈值: {threshold*100:.1f}%)"
        elif metric_name == "daily_cost":
            return f"⚠️ 日成本超限: ${current_value:.2f} (阈值: ${threshold})"
        elif metric_name == "cpu_usage":
            return f"⚠️ CPU 使用率过高: {current_value:.1f}% (阈值: {threshold}%)"
        elif metric_name == "memory_usage":
            return f"⚠️ 内存使用率过高: {current_value:.1f}% (阈值: {threshold}%)"
        else:
            return f"⚠️ {metric_name} 异常: {current_value} (阈值: {threshold})"
    
    def _send_notification(self, alert: Alert):
        """发送通知"""
        for notifier in self.notifiers:
            try:
                notifier.send(alert)
            except Exception as e:
                print(f"通知发送失败: {e}")
    
    def get_alerts(
        self,
        severity: AlertSeverity = None,
        resolved: bool = None
    ) -> List[Alert]:
        """获取告警"""
        alerts = self.alerts
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]
        
        return alerts
    
    def resolve_alert(self, alert_id: str):
        """解决告警"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                break


class EmailNotifier:
    """邮件通知器"""
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        sender_email: str,
        sender_password: str,
        recipients: List[str]
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipients = recipients
    
    def send(self, alert: Alert):
        """发送邮件"""
        subject = f"[{alert.severity.value.upper()}] Agent Alert: {alert.metric}"
        
        body = f"""
Alert ID: {alert.alert_id}
Severity: {alert.severity.value}
Metric: {alert.metric}
Current Value: {alert.current_value}
Threshold: {alert.threshold}
Message: {alert.message}
Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.timestamp))}

Please investigate and resolve this issue.
"""
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.sender_email
        msg['To'] = ', '.join(self.recipients)
        
        # 发送
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)


class SlackNotifier:
    """Slack 通知器"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send(self, alert: Alert):
        """发送 Slack 消息"""
        # 颜色映射
        color_map = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9900",
            AlertSeverity.ERROR: "#ff0000",
            AlertSeverity.CRITICAL: "#990000"
        }
        
        payload = {
            "attachments": [
                {
                    "color": color_map[alert.severity],
                    "title": f"Agent Alert: {alert.metric}",
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Current Value",
                            "value": str(alert.current_value),
                            "short": True
                        },
                        {
                            "title": "Threshold",
                            "value": str(alert.threshold),
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.timestamp)),
                            "short": True
                        },
                        {
                            "title": "Message",
                            "value": alert.message,
                            "short": False
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(self.webhook_url, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Slack notification failed: {response.text}")


class Dashboard:
    """监控仪表板"""
    
    def __init__(self, monitoring_system: MonitoringSystem):
        self.monitoring = monitoring_system
    
    def generate_html(self) -> str:
        """生成 HTML 仪表板"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Agent Monitoring Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #333; }
        .metric-card {
            background: white;
            padding: 20px;
            margin: 10px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric-name { font-size: 18px; font-weight: bold; color: #555; }
        .metric-value { font-size: 32px; font-weight: bold; margin: 10px 0; }
        .metric-status { padding: 5px 10px; border-radius: 4px; }
        .status-ok { background: #d4edda; color: #155724; }
        .status-warning { background: #fff3cd; color: #856404; }
        .status-error { background: #f8d7da; color: #721c24; }
        .alert-list { margin-top: 20px; }
        .alert-item { padding: 10px; margin: 5px 0; border-left: 4px solid; }
        .alert-info { border-color: #17a2b8; background: #d1ecf1; }
        .alert-warning { border-color: #ffc107; background: #fff3cd; }
        .alert-error { border-color: #dc3545; background: #f8d7da; }
        .alert-critical { border-color: #721c24; background: #f5c6cb; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Agent Monitoring Dashboard</h1>
        <p>Last updated: <span id="timestamp"></span></p>
        
        <div class="metrics">
"""
        
        # 添加指标卡片
        for metric_name, values in self.monitoring.metrics.items():
            if values:
                latest_value = values[-1]["value"]
                threshold = self.monitoring.thresholds.get(metric_name, 0)
                
                # 判断状态
                if metric_name in ["success_rate"]:
                    status = "ok" if latest_value >= threshold else "warning"
                else:
                    status = "ok" if latest_value <= threshold else "warning"
                
                html += f"""
            <div class="metric-card">
                <div class="metric-name">{metric_name}</div>
                <div class="metric-value">{latest_value:.2f}</div>
                <div class="metric-status status-{status}">
                    Threshold: {threshold}
                </div>
            </div>
"""
        
        html += """
        </div>
        
        <div class="alert-list">
            <h2>🚨 Active Alerts</h2>
"""
        
        # 添加告警列表
        active_alerts = self.monitoring.get_alerts(resolved=False)
        
        if active_alerts:
            for alert in active_alerts[-10:]:  # 最近 10 个
                html += f"""
            <div class="alert-item alert-{alert.severity.value}">
                <strong>{alert.severity.value.upper()}</strong>: {alert.message}
                <br>
                <small>{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.timestamp))}</small>
            </div>
"""
        else:
            html += "<p>No active alerts</p>"
        
        html += """
        </div>
    </div>
    
    <script>
        document.getElementById('timestamp').textContent = new Date().toLocaleString();
        
        // 自动刷新
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
"""
        
        return html
    
    def save(self, filename: str = "monitoring_dashboard.html"):
        """保存仪表板"""
        html = self.generate_html()
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ Dashboard saved to {filename}")


# 使用示例
if __name__ == "__main__":
    # 1. 创建监控系统
    monitoring = MonitoringSystem()
    
    # 2. 添加通知器
    # Email
    email_notifier = EmailNotifier(
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        sender_email="your@gmail.com",
        sender_password="your-password",
        recipients=["admin@example.com"]
    )
    monitoring.add_notifier(email_notifier)
    
    # Slack
    slack_notifier = SlackNotifier(
        webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    )
    monitoring.add_notifier(slack_notifier)
    
    # 3. 记录指标（模拟）
    monitoring.record_metric("response_time", 3.2)
    monitoring.record_metric("success_rate", 0.97)
    monitoring.record_metric("error_rate", 0.03)
    monitoring.record_metric("daily_cost", 8.5)
    
    # 触发告警
    monitoring.record_metric("response_time", 6.5)  # 超过阈值
    
    # 4. 生成仪表板
    dashboard = Dashboard(monitoring)
    dashboard.save()
    
    print("\n✅ 监控系统运行中")
```

---

**生成时间**: 2026-03-27 13:25 GMT+8
