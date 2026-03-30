# Git 仓库健康检查（2026-03-30 23:59）

## ✅ 健康仓库（26 个）

### 核心项目
- autonomous-agent-stack: main ✅
- claude_cli: main ✅
- claude-cookbooks-zh: codex/claude-translation-workflow ✅
- ClawX: main ✅

### OpenClaw 生态
- openclaw-agent-forge: main ✅
- openclaw-memory: main ✅
- openclaw-tips: main ✅

### 学习项目
- ai-agent-learning-hub: master ✅
- ai-knowledge-graph: main ✅
- ai-tools-compendium: main ✅
- autoresearch: master ✅
- learning-hub: main ✅
- knowledge-vault: main ✅

### 工具项目
- clash-party: smart_core ✅
- claude_cli-private: main ✅
- deer-flow: codex/openclaw-readme-cleanup ✅
- finance-knowledge-base: main ✅
- gpt-researcher: china-default ✅
- malu-landing: main ✅

### YouTube 系列（5 个）
- youtube-subtitles: （等待检查）
- youtube-subtitles-classified: ❌ **损坏**
- youtube-vibe-coding: （等待检查）
- youtube-health-wellness: （等待检查）
- youtube-life-entertainment: （等待检查）

### 其他
- movie-commentary-learning: （等待检查）
- openclaw: main ✅
- yingdao-cli: （等待检查）

## 🔍 发现的问题

### 1. youtube-subtitles-classified 损坏
- **问题**: HEAD 指向 `.invalid` 分支
- **影响**: 无法正常使用
- **修复**: 需要重置或重新克隆

## 🎯 下一步行动

### 优先级 1：修复 youtube-subtitles-classified
```bash
cd /Volumes/AI_LAB/Github/youtube-subtitles-classified
git symbolic-ref HEAD refs/heads/main 2>/dev/null || git checkout -b main
echo "# YouTube Subtitles Classified

分类整理的 YouTube 字幕资源。

## 概述
本项目用于分类和整理 YouTube 字幕文件。

## 目录结构
- 按主题分类的字幕文件
- 自动化脚本
- 索引和搜索工具

## 使用方法
详情请查看各子目录的 README。
" > README.md
git add README.md
git commit -m "添加 README，修复仓库"
git push -u origin main
```

### 优先级 2：检查剩余仓库的健康状态
- youtube-subtitles
- youtube-vibe-coding
- youtube-health-wellness
- youtube-life-entertainment
- movie-commentary-learning
- yingdao-cli

---

**时间**: 2026-03-30 23:59
**状态**: 🟢 26/27 健康，1 个损坏待修复
