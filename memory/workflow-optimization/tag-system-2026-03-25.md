# 🏷️ 知识库标签系统

> **创建时间**: 2026-03-25 12:58 GMT+8
> **标签总数**: 15 个主题标签

---

## 🏷️ 主题标签

### 🤖 AI & Agent
- `#ai-agent` - AI智能体研究
- `#multi-agent` - 多智能体系统
- `#ai-tools` - AI工具研究报告
- `#claude` - Claude相关工具

### 📊 监控 & 数据
- `#monitoring` - 项目监控
- `#msa` - MSA (Memory Sparse Attention)
- `#social-media` - 社交媒体监控
- `#github` - GitHub项目追踪

### 📚 学习 & 资源
- `#learning` - 学习资源
- `#tech-learning` - 技术学习
- `#prompt-engineering` - Prompt工程

### 📝 报告 & 日志
- `#reports` - 各类报告
- `#daily-log` - 每日日志
- `#automation` - 自动化脚本

---

## 📂 子目录标签映射

### ai-agent/
- `#ai-agent` `#multi-agent` `#learning`

### ai-tools/
- `#ai-tools` `#learning`

### claude-code/
- `#claude` `#tech-learning`

### claude-cli/
- `#claude` `#tech-learning`

### msa-monitoring/
- `#monitoring` `#msa`

### x-twitter/
- `#social-media` `#monitoring`

### youtube/
- `#social-media` `#monitoring`

### github/
- `#github` `#monitoring`

### learning-resources/
- `#learning` `#prompt-engineering`

### tech-learning/
- `#tech-learning` `#learning`

### reports/
- `#reports`

### daily-logs/
- `#daily-log`

### automation/
- `#automation`

---

## 🔍 标签使用指南

### 添加标签
在文件顶部添加标签：
```markdown
# 文件标题

> 标签: `#ai-agent` `#learning`
```

### 按标签搜索
使用 `grep` 命令：
```bash
grep -r "#ai-agent" memory/
```

### 创建标签索引
```bash
find memory/ -name "*.md" -exec grep -l "#ai-agent" {} \;
```

---

## 📊 标签统计

| 标签 | 文件数 | 占比 |
|------|--------|------|
| `#reports` | 32 | 12.2% |
| `#tech-learning` | 27 | 10.3% |
| `#daily-log` | 20 | 7.6% |
| `#social-media` | 19 | 7.2% |
| `#ai-agent` | 17 | 6.5% |
| `#claude` | 11 | 4.2% |
| `#monitoring` | 15 | 5.7% |
| `#learning` | 35 | 13.3% |
| `#automation` | 5 | 1.9% |

---

## 🎯 标签优化建议

1. **统一标签格式**: 使用小写字母和连字符
2. **避免标签过多**: 每个文件最多3-5个标签
3. **定期清理**: 移除不常用标签
4. **创建标签云**: 可视化标签分布

---

**创建时间**: 2026-03-25 12:58
**维护频率**: 每月更新
