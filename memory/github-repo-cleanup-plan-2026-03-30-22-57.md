# GitHub 仓库清理计划

> **执行时间**: 2026-03-30 22:57
> **模式**: 火力全开
> **限制**: 不能使用 glm-5, glm-4.7, glm-5-* 模型

---

## 🎯 清理目标

### GitHub 仓库（100 个）
需要清理到 **5 个核心仓库**

### 本地仓库（26 个）
需要清理到 **5 个核心仓库**

---

## 📊 保留列表（待确认）

### 可能保留的仓库
- openclaw-memory（核心记忆）
- autonomous-agent-stack（Agent 开发栈）
- claude_cli（Claude CLI）
- claude-cookbooks-zh（Claude 教程）
- ClawX（桌面应用）

### 需要删除的仓库
- BettaFish_copy（需要权限）
- game_local_web
- 其他 90+ 个仓库

---

## 🔧 执行步骤

### 阶段 1: 本地清理
```bash
# 1. 删除本地仓库
cd ~/github_GZ
rm -rf [不需要的仓库]
```

### 阶段 2: GitHub 清理
```bash
# 需要先获取 delete_repo 权限
gh auth refresh -h github.com -s delete_repo

# 然后批量删除
gh repo delete [repo-name] --yes
```

---

## ⚠️ 注意事项

1. **权限问题**: 删除仓库需要 `delete_repo` scope
2. **备份重要数据**: 删除前确保重要数据已备份
3. **确认保留列表**: 先确认要保留哪些仓库

---

**状态**: 🔄 等待确认
