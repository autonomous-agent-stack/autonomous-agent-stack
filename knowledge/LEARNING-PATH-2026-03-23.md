# Claude Code 学习路径 - 2026-03-23

## 📚 学习资源整理

### 官方文档
- **链接**: https://docs.anthropic.com/en/docs/overview
- **状态**: ✅ 已深度分析（2 部分，- **仓库**: `claude-code-learning` (公开)

### 社区资源 ⭐
- **shareAI-lab/learn-claude-code**: https://github.com/shareAI-lab/learn-claude-code
- **Stars**: 36.4k ⭐⭐⭐
- **状态**: ✅ 已 Fork
- **多语言**: en, ja, zh

### 本地整理
- **位置**: `knowledge/claude-code-*.md`
- **状态**: ✅ 已完成（7 个文件
- **大小**: ~35 KB

---

## 🎯 模型选择策略

### 决策树
```
任务复杂度?
├─ 最高智能?
│  ├─ 是 → Opus 4.6 ($5/$25)
│  └─ 否 → 需要平衡?
│       ├─ 是 → Sonnet 4.6 ($3/$15) ⭐ 推荐
│       └─ 否 → Haiku 4.5 ($1/$5)
└─ 简单任务?
    └─ Haiku 4.5 ($1/$5)
```

### 价格对比
| 模型 | Input | Output | 上下文 | 最大输出 | 延迟 |
|------|-------|--------|--------|---------|------|
| Opus 4.6 | $5 | $25 | 1M | 128K | 中等 |
| Sonnet 4.6 | $3 | $15 | 1M | 64K | 快速 |
| Haiku 4.5 | $1 | $5 | 200K | 64K | 最快 |

---

## 📖 学习路径

### Week 1: 基础（3 天）
- [x] **Day 1**: 安装 + Quickstart + 基本命令
- [ ] **Day 2**: Memory 系统 + CLAUDE.md
- [ ] **Day 3**: Git 集成 + 基础工作流

### Week 2: 核心（4 天）
- [ ] **Day 4**: Skills + Hooks
- [ ] **Day 5**: MCP 基础
- [ ] **Day 6**: Tools 使用
- [ ] **Day 7**: 综合实践

### Week 3: 进阶（7 天）
- [ ] **Day 8-10**: Agent SDK
- [ ] **Day 11-12**: CI/CD 集成
- [ ] **Day 13-14**: 性能优化

---

## 🔥 核心概念

### 1. Memory 系统
**CLAUDE.md**: 项目根目录的指令文件
```markdown
# 项目说明

## 技术栈
- Node.js 18+
- TypeScript

## 编码规范
- ESLint
- 测试覆盖率 > 80%
```

**自动记忆**: `~/.claude/memory/`

### 2. 工具使用
**Server-side**: Code execution, Web search/fetch
**Client-side**: Bash, Computer use, Memory

### 3. 上下文管理
- **Prompt Caching**: 节省 50%+ 成本
- **Compaction**: 自动压缩长上下文
- **1M Context**: Beta 功能

---

## 💡 最佳实践

### 成本优化
1. ✅ 使用 Prompt Caching
2. ✅ 选择合适模型
3. ✅ 控制输出长度
4. ✅ 批量处理

### 性能优化
1. ✅ 精准指令
2. ✅ 分步执行
3. ✅ 并发请求
4. ✅ 流式响应

### 开发技巧
1. ✅ CLAUDE.md 优化
2. ✅ Git 集成
3. ✅ 错误处理
4. ✅ 降级策略

---

## 📊 进度统计

### 已完成
- ✅ 官方文档深度分析（2 部分）
- ✅ 社区资源调研（36.4k stars）
- ✅ 模型选择策略
- ✅ 学习路径规划
- ✅ 中文文档分析

### 进行中
- ⏳ 系统学习（Week 1）
- ⏳ 实践项目

### 待完成
- ⏳ Agent SDK 开发
- ⏳ CI/CD 集成
- ⏳ 贡献社区

---

## 🔗 重要链接

### 公开仓库
- **claude-code-learning**: https://github.com/srxly888-creator/claude-code-learning
- **状态**: 公开
- **内容**: 官方文档深度分析

### 私有仓库
- **openclaw-memory**: 当前仓库
- **内容**: 学习笔记 + 进度追踪

### 官方资源
- **产品**: https://code.claude.com/
- **文档**: https://docs.anthropic.com/
- **Console**: https://console.anthropic.com/

### 社区资源
- **shareAI-lab**: https://github.com/shareAI-lab/learn-claude-code (36.4k stars)

---

## 📝 备注

- **学习策略**: 官方 + 社区结合
- **优先级**: 基础 → 核心 → 进阶
- **时间投入**: 2-3 周
- **目标**: 熟练使用 Claude Code

---

**更新时间**: 2026-03-23  
**状态**: 🔥 持续学习中  
**下一步**: 完成 Week 1 学习任务
