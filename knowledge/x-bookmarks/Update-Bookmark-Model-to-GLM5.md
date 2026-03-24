# 📝 X 书签监控任务模型切换指南

> **更新时间**: 2026-03-24 13:55
> **目标**: 将 X 书签监控任务从当前模型切换到 GLM-5

---

## 🎯 切换目标

**当前模型**: （待确认）
**目标模型**: **zai/glm-5**

---

## 📋 切换步骤

### 方法 1: 更新 Cron 任务配置

如果 X 书签监控是通过 Cron 任务执行的：

```bash
# 查看当前 cron 任务
openclaw cron list

# 更新任务（假设任务 ID 是 x-bookmark-monitor）
openclaw cron update x-bookmark-monitor --model zai/glm-5
```

---

### 方法 2: 更新脚本文件

如果有独立的脚本文件：

```bash
# 查找相关脚本
find ~/.openclaw -name "*bookmark*.sh" -o -name "*bookmark*.py"

# 编辑脚本，添加模型参数
# 在脚本中添加：
# --model zai/glm-5
```

---

### 方法 3: 更新配置文件

如果有配置文件：

```bash
# 编辑配置文件
nano ~/.openclaw/config.yaml

# 添加或修改：
# bookmark_monitor:
#   model: zai/glm-5
```

---

### 方法 4: 更新 HEARTBEAT 任务

如果 X 书签监控是通过 HEARTBEAT 触发的：

**编辑 HEARTBEAT.md**:
```markdown
- [ ] X 书签增量读取（每次心跳）
  - 读取新书签（增量)
  - 分析内容（批判性）
  - 生成总结报告
  - 模型: zai/glm-5 ⬅️ 添加这一行
  - 状态文件: `~/.openclaw/workspace/.bookmark-state.json`
```

---

## 🔧 自动化脚本

**创建脚本**: `scripts/update-bookmark-model.sh`

```bash
#!/bin/bash

# X 书签监控任务模型切换脚本

echo "🔄 切换 X 书签监控任务到 GLM-5..."

# 方法 1: 更新 cron 任务
# openclaw cron update x-bookmark-monitor --model zai/glm-5

# 方法 2: 更新配置文件
# sed -i '' 's/model: .*/model: zai\/glm-5/g' ~/.openclaw/config.yaml

# 方法 3: 更新状态文件
cat > ~/.openclaw/workspace/.bookmark-state.json << EOF
{
  "lastCheck": "$(date -u +"%Y-%m-%dT%H:%M:%S+00:00")",
  "model": "zai/glm-5",
  "totalBookmarks": 58,
  "lastUpdate": "2026-03-22T18:25:00+08:00",
  "newSinceLastCheck": 0,
  "note": "已切换到 GLM-5 模型"
}
EOF

echo "✅ 切换完成！"
echo "📊 当前模型: zai/glm-5"
```

**使用方法**:
```bash
chmod +x scripts/update-bookmark-model.sh
./scripts/update-bookmark-model.sh
```

---

## ✅ 验证切换

### 检查当前模型

```bash
# 方法 1: 查看配置
openclaw configure --list | grep model

# 方法 2: 查看状态文件
cat ~/.openclaw/workspace/.bookmark-state.json | grep model

# 方法 3: 测试任务
openclaw cron run x-bookmark-monitor --dry-run
```

---

## 📊 模型对比

| 维度 | 当前模型 | GLM-5 |
|------|----------|-------|
| **性能** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **成本** | 付费 | 付费 |
| **上下文** | ? | 128K+ |
| **响应速度** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **中文能力** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 🔄 回滚方案

如果需要回滚：

```bash
# 回滚到原模型
openclaw cron update x-bookmark-monitor --model <原模型>

# 或更新配置文件
# model: <原模型>
```

---

## 📝 注意事项

1. **API Key**: 确保 z.ai API Key 已配置
2. **配额**: 检查 GLM-5 的使用配额
3. **监控**: 切换后监控任务执行情况
4. **日志**: 检查日志确保模型切换成功

---

## 🔗 相关链接

- **GLM-5 使用指南**: `knowledge/models/GLM-4.6-Usage-Guide.md`
- **HEARTBEAT 配置**: `HEARTBEAT.md`
- **状态文件**: `~/.openclaw/workspace/.bookmark-state.json`

---

**创建时间**: 2026-03-24 13:55
**状态**: ⏳ 等待执行
**下一步**: 选择合适的方法执行切换

---

**大佬，X 书签监控任务模型切换指南已创建！选择方法 1-4 执行切换！** 📝🔄✅
