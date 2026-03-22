# Tmux + Claude + Codex 组建Agent团队

**来源**: https://x.com/chenchengpro/status/2033509892909379731
**发现日期**: 2026-03-21
**优先级**: ⭐⭐⭐ 高

## 核心思路

用一个模型、一个对话、一次一个任务 → Tmux组建真实Agent团队，并行干活

## 架构设计

```
Claude（大脑）→ 理解需求、拆解任务
   ↓
├── Codex Coder（写代码）
├── Codex Tester（跑测试）
└── Codex Reviewer（做审查）
```

三个角色各跑在独立的tmux pane里

## 五步上手

### 1. 安装工具
```bash
brew install tmux
npm install -g @anthropic-ai/claude-code @openai/codex
```

### 2. 创建独立工作区
```bash
git worktree add ../project-coder main
git worktree add ../project-tester main
git worktree add ../project-reviewer main
```
解决并行互相踩文件问题

### 3. 开tmux session
```bash
tmux new-session -d -s agent-team
tmux split-window -h && tmux split-window -v
```
Claude占左上，三个Codex各占一格

### 4. 启动agent
```bash
tmux send-keys -t agent-team:0.0 "claude" Enter
tmux send-keys -t agent-team:0.1 "cd ../project-coder && codex" Enter
```

### 5. 分发任务
```bash
tmux send-keys -t agent-team:0.1 "实现登录功能，JWT，带单测" Enter
tmux capture-pane -t agent-team:0.1 -p  # 读取输出
```

## 核心机制

- **send-keys**: 写入指令
- **capture-pane**: 读取输出
- **Tmux**: 消息总线

## 一键安装

```bash
brew install claude-squad
```

## 优势

- 真正的并行执行
- Claude任务拆解自动注入
- 无需手动复制粘贴
- git worktree避免冲突

## 待实践

- [ ] 安装tmux和claude-squad
- [ ] 创建worktree工作区
- [ ] 测试三Agent并行
- [ ] 实战复杂项目
