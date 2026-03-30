# 重复文件处理方案（2026-03-31 00:10）

## 🔍 重复文件详情

### 1. 2026-03-25.md（2 个）
- **memory/2026-03-25.md**: 227 行（简化版）
- **memory/daily-logs/2026-03-25.md**: 743 行（完整版）

**处理方案**:
- 保留: memory/daily-logs/2026-03-25.md（完整版）
- 删除: memory/2026-03-25.md（简化版）
- 原因: 完整版更有价值

### 2. claude-cookbooks-translation-progress.md（2 个）
**待检查**: 确定位置和内容

### 3. repo-health-check.md（2 个）
**待检查**: 确定位置和内容

## 🎯 执行计划

### 阶段 1：删除 memory/2026-03-25.md
```bash
# 确认后删除
rm /Users/iCloud_GZ/github_GZ/openclaw-memory/memory/2026-03-25.md
```

### 阶段 2：检查其他重复文件
```bash
# 查找位置
find /Users/iCloud_GZ/github_GZ/openclaw-memory -name "claude-cookbooks-translation-progress.md"
find /Users/iCloud_GZ/github_GZ/openclaw-memory -name "repo-health-check.md"
```

### 阶段 3：合并或删除重复

## 📋 其他重复文件

### INDEX.md（多个）
- 可能是不同模块的索引
- **建议**: 保留，但需要主索引

### SUMMARY.md（多个）
- 可能是不同项目的总结
- **建议**: 保留，但需要主总结

### PROJECT_SUMMARY.md（2 个）
- 可能是项目总结
- **建议**: 合并或删除旧版本

---

**时间**: 2026-03-31 00:10
**状态**: 🟡 开始处理重复文件
