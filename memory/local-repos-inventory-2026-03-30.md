# 本地仓库清单（2026-03-30）

## 📊 统计
- **总目录数**: 30 个
- **Git 仓库**: 27 个
- **非 Git 目录**: 3 个

## ✅ Git 仓库（27 个）

### 核心项目（5 个）
- autonomous-agent-stack
- claude_cli
- claude-cookbooks-zh
- ClawX
- openclaw-agent-forge

### OpenClaw 生态（3 个）
- openclaw
- openclaw-memory
- openclaw-tips

### 学习项目（8 个）
- ai-agent-learning-hub
- ai-knowledge-graph
- ai-tools-compendium
- claude_cli-private
- learning-hub
- movie-commentary-learning
- knowledge-vault
- malu-landing

### 工具项目（3 个）
- autoresearch
- clash-party
- yingdao-cli

### AI 项目（8 个）
- deer-flow
- gpt-researcher
- finance-knowledge-base

### ❌ 非 Git 目录（3 个）
- autonomous-agent-stack-autoresearch-worker（子目录）
- autonomous-agent-stack-orchestration（子目录）
- autonomous-agent-stack-pr1-chat-spine（子目录）

## 🔍 关键发现

### 1. 本地有 GitHub Fork 的仓库
以下仓库在本地存在，GitHub 上是 Fork（可以删除 GitHub 上的）：
- openclaw ✅
- ClawX ✅
- claude-cookbooks-zh ✅
- autoresearch ✅
- gpt-researcher ✅

### 2. 本地独有的仓库
以下仓库只在本地，GitHub 上没有：
- autonomous-agent-stack-autoresearch-worker（子目录）
- autonomous-agent-stack-orchestration（子目录）
- autonomous-agent-stack-pr1-chat-spine（子目录）

### 3. 子目录清理建议
`autonomous-agent-stack-*` 的 3 个子目录：
- **autoresearch-worker**: 可能是临时工作目录
- **orchestration**: 可能是编排实验
- **pr1-chat-spine**: PR 相关的实验分支

建议：确认后删除或移到其他位置

## 🎯 下一步行动

### 优先级 1：子目录清理
```bash
# 检查这些子目录的内容
ls -la autonomous-agent-stack-*/ | head -20
```

### 优先级 2：README 补充
为缺少 README 的仓库创建说明文档

### 优先级 3：等待 GitHub 授权
完成 Fork 删除任务

---

**时间**: 2026-03-30 23:59
**状态**: 🟢 清单完成
