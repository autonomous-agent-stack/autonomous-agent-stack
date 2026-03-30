# DevOps - 开发运维

> **最后更新**: 2026-03-30

---

## 📚 核心概念

DevOps = Development + Operations，强调开发与运维的协作与自动化。

### 关键原则
- 🔄 **持续集成/持续部署（CI/CD）**
- 🤖 **基础设施即代码（IaC）**
- 📊 **监控与可观测性**
- 🚀 **自动化优先**
- 🤝 **协作文化**

---

## 🛠️ 工具生态

### CI/CD
- **GitHub Actions** - GitHub 原生
- **GitLab CI** - GitLab 集成
- **Jenkins** - 老牌工具
- **CircleCI** - 云原生

### 容器化
- **Docker** - 容器标准
- **Kubernetes** - 容器编排
- **Podman** - 无守护进程
- **containerd** - 轻量级运行时

### IaC
- **Terraform** - 多云支持
- **Pulumi** - 编程式
- **Ansible** - 配置管理
- **CloudFormation** - AWS 专用

### 监控
- **Prometheus** - 指标收集
- **Grafana** - 可视化
- **ELK Stack** - 日志分析
- **Jaeger** - 分布式追踪

---

## 🚀 最佳实践

### 1. CI/CD 流水线
```yaml
# GitHub Actions 示例
name: CI/CD Pipeline
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: pytest tests/

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: ./deploy.sh
```

### 2. 容器化部署
```dockerfile
# Dockerfile 最佳实践
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000
CMD ["uvicorn", "app:main", "--host", "0.0.0.0"]
```

### 3. 监控告警
```yaml
# Prometheus 告警规则
groups:
  - name: app-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status="500"}[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"
```

---

## 📊 监控指标

### 四大黄金信号
1. **延迟（Latency）** - 响应时间
2. **流量（Traffic）** - 请求速率
3. **错误（Errors）** - 错误率
4. **饱和度（Saturation）** - 资源使用率

### RED 方法
- **Rate** - 请求速率
- **Errors** - 错误率
- **Duration** - 响应时间

### USE 方法
- **Utilization** - 资源使用率
- **Saturation** - 饱和度
- **Errors** - 错误数

---

## 🔧 实战案例

### 案例 1：零停机部署
**技术**：蓝绿部署 + 健康检查
**效果**：
- 部署时间：5 分钟
- 停机时间：0 秒
- 回滚时间：30 秒

### 案例 2：自动扩缩容
**技术**：Kubernetes HPA + 自定义指标
**效果**：
- 峰值处理能力：+300%
- 成本节省：40%
- 响应时间：<100ms

### 案例 3：日志聚合
**技术**：ELK Stack + Filebeat
**效果**：
- 日志查询时间：5 分钟 → 5 秒
- 问题定位效率：+80%

---

## 📚 学习路径

### 入门（1-2 周）
- [ ] 学习 Linux 基础
- [ ] 掌握 Git 工作流
- [ ] 理解 Docker 基础
- [ ] 了解 CI/CD 概念

### 进阶（1-2 月）
- [ ] Kubernetes 部署
- [ ] Terraform 基础
- [ ] 监控系统搭建
- [ ] 安全最佳实践

### 高级（3-6 月）
- [ ] 多集群管理
- [ ] GitOps 实践
- [ ] 混沌工程
- [ ] SRE 方法论

---

## 🔗 相关主题

- [[Cloud Native]] - 云原生架构
- [[SRE]] - 站点可靠性工程
- [[Security]] - 安全运维
- [[Performance]] - 性能优化

---

**维护者**: OpenClaw Memory Team
**最后更新**: 2026-03-30
