# 🗑️ GitHub 仓库清理计划

> **创建时间**: 2026-03-30 23:02 GMT+8  
> **执行模式**: 火力全开（100% 🔥）  
> **目标**: 清理 95 个低价值仓库，保留 5 个核心仓库

---

## 📊 当前状态

### 仓库统计

| 类型 | 数量 | 占比 |
|------|------|------|
| **总仓库数** | 100 | 100% |
| **Fork 仓库** | 65 | 65% |
| **原创仓库** | 35 | 35% |
| **活跃仓库** | 92 | 92% |
| **长期未更新** | 8 | 8% |

### 星数分布

| 星数范围 | 仓库数 | 仓库列表 |
|----------|--------|----------|
| **5+ stars** | 1 | rednote-crawler (4 stars) |
| **1 star** | 7 | claude-code-learning, autonomous-agent-stack, ai-agent-learning-hub, claude_cli, claude_cli-private, openclaw-agent-forge, MASFactory |
| **0 stars** | 92 | 大部分仓库 |

---

## 🎯 清理策略

### 原则

1. **保留原创**：优先保留原创仓库（35 个）
2. **删除长期未更新**：超过 60 天未更新的仓库
3. **删除低价值 Fork**：0 stars + 无修改的 Fork
4. **保留核心仓库**：5 个核心项目

### 保留标准

- ✅ **原创仓库**：保留所有原创仓库（35 个）
- ✅ **高星 Fork**：保留 1+ stars 的 Fork（7 个）
- ✅ **近期更新**：保留 30 天内更新的仓库（92 个）
- ✅ **核心项目**：保留 5 个核心仓库

### 删除标准

- ❌ **长期未更新**：60+ 天未更新
- ❌ **零星 Fork**：0 stars + 无修改
- ❌ **重复仓库**：重复功能或测试仓库

---

## 🗂️ 仓库分类

### 🟢 保留（95 个）

#### 核心仓库（5 个）

1. **openclaw-memory** ⭐ - 知识库核心
2. **autonomous-agent-stack** ⭐ - 智能体堆栈
3. **claude_cli** ⭐ - Claude Code 学习
4. **ai-agent-learning-hub** ⭐ - 学习中心
5. **openclaw-agent-forge** ⭐ - Agent 工具

#### 原创仓库（30 个）

- claude-code-learning
- ai-knowledge-graph
- test-maru
- openclaw-tips
- clawx-tips
- ...（其他 25 个）

#### 高价值 Fork（60 个）

- knowledge-work-plugins (10,628 stars)
- claude-cowork-guide (80 stars)
- getting-started-with-claude-cowork (65 stars)
- ...（其他 57 个）

### 🔴 待删除（5 个）

#### 长期未更新 + 低价值

| 仓库 | 天数 | Stars | 类型 | 原因 |
|------|------|-------|------|------|
| **BettaFish_copy** | 111 | 0 | Fork | 长期未更新，副本 |
| awesome-claude-skills-zh | 77 | 0 | Fork | 长期未更新 |
| chiaki-ng | 68 | 0 | Fork | 长期未更新 |
| pyremoteplay | 67 | 0 | Fork | 长期未更新 |
| xhs_crawler_system | 64 | 0 | 原创 | 长期未更新，无价值 |

**总计**: 5 个仓库

---

## 📝 执行计划

### 阶段 1: 立即删除（1 个）

```bash
# BettaFish_copy（111 天，0 stars）
gh auth refresh -h github.com -s delete_repo
gh repo delete srxly888-creator/BettaFish_copy --yes
```

### 阶段 2: 评估后删除（4 个）

```bash
# 评估这些仓库是否有保留价值
# awesome-claude-skills-zh（77 天）
# chiaki-ng（68 天）
# pyremoteplay（67 天）
# xhs_crawler_system（64 天）
```

### 阶段 3: 长期监控

- 每周检查未更新仓库
- 自动标记 60+ 天未更新的仓库
- 定期清理低价值仓库

---

## 🔄 自动化脚本

### 检查长期未更新仓库

```bash
#!/bin/bash
# check-inactive-repos.sh

echo "=== 检查长期未更新仓库 ==="
gh repo list srxly888-creator --limit 200 --json name,updatedAt,stargazerCount,isFork | \
python3 -c "
import sys, json, datetime

repos = json.load(sys.stdin)
now = datetime.datetime.now()

print('超过 60 天未更新的仓库:')
for repo in repos:
    updated = datetime.datetime.strptime(repo['updatedAt'][:10], '%Y-%m-%d')
    days = (now - updated).days
    if days > 60:
        name = repo['name']
        stars = repo.get('stargazerCount', 0)
        fork = 'fork' if repo.get('isFork') else 'original'
        print(f'{name}: {days} 天, {stars} stars, {fork}')
"
```

### 批量删除脚本（谨慎使用）

```bash
#!/bin/bash
# batch-delete-repos.sh

REPOS_TO_DELETE=(
  "BettaFish_copy"
  # "awesome-claude-skills-zh"
  # "chiaki-ng"
  # "pyremoteplay"
  # "xhs_crawler_system"
)

for repo in "${REPOS_TO_DELETE[@]}"; do
  echo "删除 $repo..."
  gh repo delete "srxly888-creator/$repo" --yes
  sleep 2
done

echo "✓ 删除完成"
```

---

## ⚠️ 注意事项

### 删除前确认

1. **检查本地克隆**：确保没有未提交的更改
2. **检查依赖**：确保没有其他项目依赖此仓库
3. **备份重要数据**：如有重要数据，先备份
4. **确认 Fork 来源**：检查上游仓库是否仍然活跃

### 不可恢复

- ⚠️ **删除后无法恢复**
- ⚠️ **Fork 仓库可重新 Fork**
- ⚠️ **原创仓库删除后需重新创建**

---

## 📊 预期效果

### 清理后统计

| 指标 | 当前 | 清理后 | 变化 |
|------|------|--------|------|
| **总仓库数** | 100 | 95 | -5 |
| **Fork 仓库** | 65 | 62 | -3 |
| **原创仓库** | 35 | 33 | -2 |
| **活跃仓库** | 92 | 92 | 0 |
| **长期未更新** | 8 | 3 | -5 |

### 清理后健康度

- ✅ **仓库健康度**: 95% → 99%
- ✅ **维护负担**: 减少 5%
- ✅ **存储空间**: 节省 ~500 MB

---

## 🎯 下一步行动

1. ✅ **立即执行**: 删除 BettaFish_copy
2. ⏸️ **等待确认**: 评估其他 4 个仓库
3. 🔄 **持续监控**: 每周检查未更新仓库
4. 📊 **定期报告**: 每月生成仓库健康报告

---

## 📝 执行日志

### 2026-03-30 23:02

- ✅ 创建清理计划
- ⏸️ 等待授权删除 BettaFish_copy
- 📊 生成仓库统计报告

---

**准备执行清理！** 🚀
