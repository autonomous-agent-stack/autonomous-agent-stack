# GitHub Actions 优化建议

**分析日期**: 2026-03-25

---

## 📊 当前状况

已有工作流:
- update-stars.yml (每天 2:00 UTC)

---

## 🎯 优化建议

### 1. 新增工作流

#### 知识库健康检查
```yaml
name: Knowledge Base Health Check
on:
  schedule:
    - cron: '0 23 * * *'  # 每天 23:00 CST
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check links
        run: |
          # 检查 README 链接
          # 检查仓库健康
```

---

**优先级**: 低
