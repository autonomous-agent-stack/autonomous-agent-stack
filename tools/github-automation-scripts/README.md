# GitHub 自动化脚本集合

这个目录包含 10 个实用的 GitHub Issue 自动化脚本，涵盖日常管理、数据分析、批量操作等场景。

## 脚本列表

### 1. issue-metrics.sh
**用途**: 收集和分析 Issue 指标
- 统计开放/关闭 Issues 数量
- 计算平均关闭时间
- 标签分布统计
- 团队成员工作负载分析

**使用**:
```bash
./issue-metrics.sh owner/repo 2024-01-01
```

### 2. issue-triage-bot.py
**用途**: 自动化 Issue 分类和分配
- 基于关键词自动添加标签
- 智能推荐负责人
- 添加 "needs-triage" 标签
- 提交信息收集表单

**使用**:
```bash
./issue-triage-bot.py owner/repo --token $GITHUB_TOKEN --label
```

### 3. issue-sla-monitor.py
**用途**: SLA 监控和告警
- 监控 Issue 响应时间
- 检测 SLA 违规
- 自动发送告警
- 生成 SLA 报告

**使用**:
```bash
./issue-sla-monitor.py owner/repo --sla-config sla.json
```

### 4. bulk-issue-operations.py
**用途**: 批量 Issue 操作
- 批量关闭 Issues
- 批量添加/移除标签
- 批量分配 Issues
- 批量转移 Issues

**使用**:
```bash
./bulk-issue-operations.py close --owner owner --repo repo --issues-file issues.txt
```

### 5. issue-backup-restore.py
**用途**: Issue 备份和恢复
- 完整备份 Issues 和评论
- 压缩存储节省空间
- 跨仓库恢复
- 增量备份支持

**使用**:
```bash
./issue-backup-restore.py backup owner/repo --output backups/
./issue-backup-restore.py restore owner/repo --input backups/backup.json.gz
```

### 6. issue-template-validator.py
**用途**: Issue 模板验证
- 验证 Issue 是否符合模板
- 检查必填字段
- 自动提示补充信息
- 生成验证报告

**使用**:
```bash
./issue-template-validator.py owner/repo --issue 123 --template bug_report.yml
```

### 7. issue-deduplicator.py
**用途**: 检测重复 Issues
- 基于标题相似度检测
- 内容去重
- 自动合并重复 Issues
- 生成去重报告

**使用**:
```bash
./issue-deduplicator.py owner/repo --similarity 0.8
```

### 8. issue-label-manager.py
**用途**: 标签管理系统
- 标准化标签名称
- 批量创建标签
- 标签颜色统一
- 标签使用统计

**使用**:
```bash
./issue-label-manager.py standardize --owner owner --repo repo --config labels.yml
```

### 9. issue-notifier.py
**用途**: Issue 通知系统
- Slack/Discord 集成
- 邮件通知
- 自定义通知规则
- 汇总日报/周报

**使用**:
```bash
./issue-notifier.py owner/repo --slack-webhook $SLACK_WEBHOOK --daily
```

### 10. issue-workload-balancer.py
**用途**: 工作负载均衡器
- 分析团队成员负载
- 智能分配 Issues
- 考虑技能匹配
- 生成分配报告

**使用**:
```bash
./issue-workload-balancer.py owner/repo --team frontend --auto-assign
```

---

## 依赖安装

```bash
# Python 依赖
pip install PyGithub requests python-dateutil

# 或使用 uv
uv pip install PyGithub requests python-dateutil

# Bash 脚本依赖 (需要 gh CLI)
brew install gh  # macOS
apt install gh   # Linux
```

## 环境配置

```bash
# GitHub Token (需要 repo 权限)
export GITHUB_TOKEN="your_token_here"

# 或创建 .env 文件
echo "GITHUB_TOKEN=your_token_here" > .env
```

## 通用参数

所有 Python 脚本支持以下通用参数:

```
--token TOKEN       GitHub Token (或使用 $GITHUB_TOKEN)
--debug             启用调试输出
--dry-run           模拟运行，不实际执行
--config FILE       配置文件路径
--output FILE       输出文件路径
--format FORMAT     输出格式 (json/table/csv)
```

## 最佳实践

### 1. 定期备份
```bash
# 每周备份所有仓库
./issue-backup-restore.py backup owner/repo --output backups/weekly/
```

### 2. SLA 监控
```bash
# 每小时检查 SLA
./issue-sla-monitor.py owner/repo --cron --interval 3600
```

### 3. 自动分类
```bash
# 每 5 分钟检查新 Issues
./issue-triage-bot.py owner/repo --daemon --interval 300
```

### 4. 指标报告
```bash
# 每周生成指标报告
./issue-metrics.sh owner/repo $(date -v-1w +%Y-%m-%d) > reports/weekly-$(date +%Y%m%d).md
```

## 安全注意事项

⚠️ **重要**:
- 不要将 Token 提交到 Git 仓库
- 使用环境变量或配置文件
- Token 需要最小权限原则
- 定期轮换 Token
- 使用 `.gitignore` 排除敏感文件

## 故障排除

### Rate Limiting
GitHub API 有速率限制:
- 认证用户: 5000 requests/hour
- 未认证: 60 requests/hour

如遇到限制，脚本会自动等待。

### 网络问题
脚本内置重试机制，失败会自动重试 3 次。

### 调试模式
使用 `--debug` 参数查看详细日志。

---

## 贡献

欢迎贡献新的脚本！请遵循以下规范:

1. 添加详细注释
2. 提供 `--help` 文档
3. 支持 `--dry-run` 模式
4. 处理错误和异常
5. 提供使用示例

## 许可证

MIT License
