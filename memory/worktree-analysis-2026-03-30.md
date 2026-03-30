# Git Worktree 分析（2026-03-30 00:02）

## 🔍 发现
3 个非 Git 目录实际上是 `autonomous-agent-stack` 的 **Git Worktree**！

## 📊 Worktree 清单

### 1. autonomous-agent-stack-autoresearch-worker
- **分支**: `codex/autoresearch-worker-strict`
- **提交**: d2f1c68
- **用途**: AutoResearch Worker 严格模式
- **状态**: 活跃工作分支

### 2. autonomous-agent-stack-orchestration
- **分支**: `codex/worker-orchestration-e2e`
- **提交**: 2694322
- **用途**: Worker 编排 E2E 测试
- **状态**: 活跃工作分支

### 3. autonomous-agent-stack-pr1-chat-spine
- **分支**: `codex/pr1-chat-spine-repair`
- **提交**: 2fe2646
- **用途**: PR1 Chat Spine 修复
- **状态**: 活跃工作分支

## 🎯 修正后的统计

### 本地仓库（实际 27 个 Git 仓库）
- **主仓库**: autonomous-agent-stack（有 3 个 worktree）
- **其他 Git 仓库**: 26 个

### Git Worktree 分布
- **主仓库**: autonomous-agent-stack
- **本地 Worktree**: 3 个（在 /Volumes/AI_LAB/Github/）
- **临时 Worktree**: 10 个（在 /tmp/ 和其他位置）
- **Codex Worktree**: 2 个（在 .codex-worktrees/）

## 💡 建议

### ✅ 保留
- 3 个本地 worktree 都是活跃开发分支
- 与主仓库关联，不需要独立管理

### 🧹 清理
- 临时 worktree 可以清理（/tmp/ 下的 4 个）
- 其他位置的 worktree 根据需要决定保留

### 📝 更新文档
- 修正本地仓库统计：27 个 Git 仓库
- 说明 worktree 关系

## 🔧 Worktree 管理命令

### 查看所有 worktree
```bash
cd autonomous-agent-stack
git worktree list
```

### 清理临时 worktree
```bash
# 清理 /tmp/ 下的 worktree
git worktree remove /private/tmp/autonomous-agent-stack-pr10
git worktree remove /private/tmp/autonomous-agent-stack-pr11
git worktree remove /private/tmp/autonomous-agent-stack-pr14
```

### 创建新 worktree
```bash
git worktree add ../new-feature-branch feature-branch
```

---

**时间**: 2026-03-30 00:02
**状态**: 🟢 Worktree 理解完成
