# Claude Code 快速参考卡片

## 🚀 一分钟上手

### 安装
```bash
# macOS/Linux/WSL
curl -fsSL https://claude.ai/install.sh | bash

# Windows PowerShell
irm https://claude.ai/install.ps1 | iex
```

### 启动
```bash
cd your-project
claude
```

### 常用命令
```bash
claude                          # 启动交互模式
claude --help                   # 查看帮助
claude --version                # 查看版本
claude --print "your task"      # 非交互模式
claude /path/to/project         # 指定工作目录
```

---

## 📚 核心概念

### 1. CLAUDE.md 文件
**位置**: 项目根目录
**作用**: 存储项目指令和上下文

```markdown
# 项目说明

## 技术栈
- Node.js 18+
- TypeScript

## 编码规范
- ESLint
- 测试覆盖率 > 80%
```

### 2. 自动记忆
**位置**: `~/.claude/memory/`
**作用**: Claude 自动记住重要上下文

### 3. 多文件操作
- Claude 理解整个代码库
- 可以跨多个文件重构

---

## 🎯 常用场景

### 1. 代码重构
```
"重构这个函数，提高性能"
"将这个类拆分为多个模块"
"优化这个 SQL 查询"
```

### 2. Bug 修复
```
"修复这个 bug"
"分析这个错误日志"
"找出性能瓶颈"
```

### 3. Git 操作
```
"创建一个 commit"
"生成 PR 描述"
"审查这个 PR"
```

### 4. 文档生成
```
"为这个项目生成 README"
"添加 API 文档"
"创建架构图"
```

---

## 🔧 配置技巧

### 环境变量
```bash
# API Key
export ANTHROPIC_API_KEY=your_key

# 默认模型
export CLAUDE_MODEL=claude-3-5-sonnet-20241022

# 调试模式
export CLAUDE_DEBUG=true
```

### Settings
**位置**: `~/.claude/settings.json`

```json
{
  "defaultModel": "claude-3-5-sonnet-20241022",
  "maxTokens": 4096,
  "temperature": 0.7
}
```

---

## 🌟 最佳实践

### 1. 清晰的指令
✅ **好**: "将这个 React 组件重构为 TypeScript，使用 hooks"
❌ **差**: "改一下这个组件"

### 2. 提供上下文
✅ **好**: "在 CLAUDE.md 中说明技术栈和规范"
❌ **差**: 让 Claude 猜测项目结构

### 3. 分步执行
✅ **好**: "先分析，再重构，最后测试"
❌ **差**: 一次要求太多

### 4. 验证结果
✅ **好**: "运行测试确保功能正常"
❌ **差**: 盲目信任输出

---

## 🔗 重要链接

### 官方
- **产品**: https://code.claude.com/
- **文档**: https://docs.anthropic.com/en/docs/overview
- **API**: https://docs.anthropic.com/en/api/overview

### 社区 ⭐
- **learn-claude-code**: https://github.com/shareAI-lab/learn-claude-code (36.4k stars)
- **文档技能**: https://github.com/pranavred/claude-code-documentation-skill

---

## 💡 性能优化

### Token 节省技巧
1. **使用 CLAUDE.md**: 避免重复说明
2. **精准指令**: 减少不必要的对话
3. **分步执行**: 避免一次性大任务
4. **使用 claude-token-optimizer**: 节省 90% token

### 提高响应速度
1. **缩小上下文**: 只包含相关文件
2. **使用缓存**: 启用自动记忆
3. **优化模型**: 选择合适的模型
4. **并行任务**: 使用 sub-agents

---

## ⚠️ 注意事项

### 1. 数据安全
- ❗ 代码会上传到服务器
- ❗ 注意敏感信息保护
- ❗ 使用 `.claudeignore` 排除敏感文件

### 2. 费用控制
- 💰 需要 Claude 订阅或 API key
- 💰 大型任务消耗更多 token
- 💰 监控使用量

### 3. 质量保证
- ✅ 总是验证输出
- ✅ 运行测试
- ✅ 代码审查

---

## 📖 学习路径

### Day 1: 基础
1. 安装 Claude Code
2. 完成 Quickstart
3. 尝试基本命令
4. 创建 CLAUDE.md

### Day 2: 工作流
1. 学习 Common Workflows
2. 自动化任务
3. Git 集成
4. 多文件操作

### Day 3: 高级
1. MCP 集成
2. 自定义 Skills
3. 性能优化
4. CI/CD

---

## 🎓 进阶资源

### 必读
1. **官方文档**: https://docs.anthropic.com/en/docs/overview
2. **shareAI-lab 学习资源**: https://github.com/shareAI-lab/learn-claude-code
3. **最佳实践**: https://docs.anthropic.com/en/docs/best-practices

### 必做项目
1. 文档生成项目
2. 代理开发项目
3. CI/CD 集成项目

---

**更新时间**: 2026-03-23  
**版本**: 1.0  
**状态**: 🔥 持续更新中
