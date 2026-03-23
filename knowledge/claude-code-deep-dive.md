# Claude Code 深度学习笔记 - 官网核心内容提炼

**整理时间**: 2026-03-23  
**来源**: Anthropic 官方 + 36.4k stars 社区资源  
**状态**: 🔥 一直在路上，持续更新

---

## 📖 目录

1. [核心概念](#核心概念)
2. [实战技巧](#实战技巧)
3. [高级功能](#高级功能)
4. [最佳实践](#最佳实践)
5. [常见问题](#常见问题)

---

## 核心概念

### 1. Claude Code 是什么？

**定义**: AI 编程助手，理解整个代码库，跨多文件工作

**核心能力**:
- ✅ 自动化重复性工作
- ✅ 构建功能和修复 bug
- ✅ 创建 commits 和 PR
- ✅ 连接工具（MCP）
- ✅ 自定义指令、技能、钩子
- ✅ 运行代理团队
- ✅ 脚本和自动化

**支持平台**:
- Terminal（终端）
- VS Code
- JetBrains IDEs
- Desktop App
- Web (claude.ai/code)
- Chrome Extension

---

### 2. 工作原理

#### 2.1 上下文理解
- **代码库扫描**: 自动理解项目结构
- **依赖分析**: 识别模块关系
- **上下文窗口**: 200K tokens（Claude 3.5 Sonnet）

#### 2.2 工具调用
- **Bash Tool**: 执行命令
- **Text Editor Tool**: 编辑文件
- **Memory Tool**: 存储记忆
- **Code Execution Tool**: 运行代码
- **Web Search Tool**: 网络搜索
- **Computer Use Tool**: 操作电脑

#### 2.3 工作流程
```
用户请求 → 上下文分析 → 工具选择 → 执行操作 → 结果验证 → 输出响应
```

---

### 3. Memory 系统

#### 3.1 CLAUDE.md 文件
**位置**: 项目根目录  
**作用**: 存储项目特定的指令和上下文

**模板**:
```markdown
# 项目说明

## 技术栈
- Node.js 18+
- TypeScript 5.0
- React 18

## 项目结构
- /src - 源代码
- /tests - 测试文件
- /docs - 文档

## 编码规范
- 使用 ESLint
- 单元测试覆盖率 > 80%
- 遵循 Airbnb 风格指南

## 常用命令
- npm run dev - 开发服务器
- npm run build - 构建项目
- npm run test - 运行测试

## 注意事项
- 不要修改 /config 目录
- 提交前运行 lint
- PR 需要 2 个 approve
```

#### 3.2 自动记忆
**位置**: `~/.claude/memory/`  
**作用**: Claude 自动记住重要上下文

**示例**:
```json
{
  "projectPreferences": {
    "testFramework": "jest",
    "styleGuide": "airbnb",
    "branchNaming": "feature/*"
  },
  "userPreferences": {
    "editor": "vscode",
    "commitFormat": "conventional"
  }
}
```

---

## 实战技巧

### 1. 高效指令编写

#### 1.1 明确的目标
✅ **好**: "将这个 React 组件重构为 TypeScript，使用 hooks，保持功能不变"
❌ **差**: "改一下这个组件"

#### 1.2 提供上下文
✅ **好**: "在 /src/components 目录下，找到所有使用 class 组件的文件，转换为函数组件"
❌ **差**: "转换组件"

#### 1.3 分步执行
✅ **好**:
```
1. 先分析这个函数的性能瓶颈
2. 提出优化方案
3. 实施优化
4. 运行测试验证
```
❌ **差**: "优化这个函数"

---

### 2. 常用场景示例

#### 2.1 代码重构
```
场景: 重构大型组件

指令:
"重构 /src/components/Dashboard.tsx
1. 拆分为多个子组件
2. 提取自定义 hooks
3. 添加 TypeScript 类型
4. 保持所有功能不变
5. 运行测试确保无回归"
```

#### 2.2 Bug 修复
```
场景: 修复生产环境 bug

指令:
"分析这个错误日志：
[粘贴错误日志]

1. 定位问题根源
2. 提供修复方案
3. 实施修复
4. 添加测试用例防止回归
5. 更新相关文档"
```

#### 2.3 功能开发
```
场景: 添加新功能

指令:
"为用户管理模块添加批量导入功能

需求：
1. 支持 CSV/Excel 文件上传
2. 数据验证和错误处理
3. 进度显示
4. 导入结果报告

遵循：
- 项目编码规范（见 CLAUDE.md）
- 使用现有的 UI 组件库
- 添加单元测试和集成测试"
```

---

### 3. Git 集成

#### 3.1 智能提交
```bash
# Claude 自动分析变更并生成提交信息
claude "创建一个 commit，描述本次变更"

# 示例输出：
# feat(user-management): add batch import feature
# 
# - Add CSV/Excel file upload support
# - Implement data validation and error handling
# - Add progress indicator and import report
# - Add unit tests and integration tests
```

#### 3.2 PR 创建
```bash
# 自动生成 PR 描述
claude "创建一个 PR，标题：添加批量导入功能"

# Claude 会：
# 1. 分析所有 commits
# 2. 生成详细的 PR 描述
# 3. 列出变更文件
# 4. 添加测试计划
# 5. 提供截图（如果需要）
```

---

## 高级功能

### 1. MCP (Model Context Protocol)

#### 1.1 什么是 MCP？
**定义**: 连接 Claude 与外部工具的协议

**常见 MCP 服务器**:
- **Filesystem**: 文件系统操作
- **PostgreSQL**: 数据库查询
- **GitHub**: GitHub API 集成
- **Slack**: Slack 消息发送
- **Google Drive**: 文件管理

#### 1.2 配置 MCP
**文件**: `~/.claude/mcp_settings.json`

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "mcp-filesystem",
      "args": ["/path/to/project"]
    },
    "github": {
      "command": "mcp-github",
      "env": {
        "GITHUB_TOKEN": "your_token"
      }
    }
  }
}
```

---

### 2. Skills（技能）

#### 2.1 什么是 Skills？
**定义**: 可重用的任务模板

**示例 Skill**:
```json
{
  "name": "code-review",
  "description": "自动代码审查",
  "prompt": "审查以下代码变更，检查：
1. 代码质量
2. 潜在 bug
3. 性能问题
4. 安全隐患
5. 最佳实践

提供具体的改进建议。",
  "tools": ["text-editor", "bash"]
}
```

#### 2.2 使用 Skills
```bash
# 调用 skill
claude --skill code-review

# Claude 会自动执行：
# 1. 获取代码变更
# 2. 运行代码审查
# 3. 生成报告
```

---

### 3. Hooks（钩子）

#### 3.1 什么是 Hooks？
**定义**: 在特定事件触发时自动执行的操作

**示例 Hook**:
```json
{
  "name": "auto-test",
  "trigger": "after-file-save",
  "condition": "*.test.ts",
  "action": "run-tests"
}
```

#### 3.2 配置 Hooks
**文件**: `~/.claude/hooks.json`

```json
{
  "hooks": [
    {
      "name": "lint-on-save",
      "trigger": "after-file-save",
      "condition": "*.ts",
      "action": "npm run lint"
    },
    {
      "name": "test-on-commit",
      "trigger": "before-git-commit",
      "action": "npm run test"
    }
  ]
}
```

---

## 最佳实践

### 1. 项目设置

#### 1.1 初始化 CLAUDE.md
```bash
# 在项目根目录创建
touch CLAUDE.md

# Claude 会自动读取并应用
```

#### 1.2 配置 .claudeignore
```
# 类似 .gitignore
node_modules/
.env
*.log
dist/
build/
```

---

### 2. 性能优化

#### 2.1 Token 节省技巧
1. **使用 CLAUDE.md**: 避免重复说明
2. **精准指令**: 减少不必要的对话
3. **分步执行**: 避免一次性大任务
4. **使用缓存**: 启用自动记忆

#### 2.2 提高响应速度
1. **缩小上下文**: 只包含相关文件
2. **使用缓存**: 启用 Prompt Caching
3. **优化模型**: 选择合适的模型
4. **并行任务**: 使用 sub-agents

---

### 3. 团队协作

#### 3.1 共享 CLAUDE.md
```bash
# 提交到版本控制
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md for team"
```

#### 3.2 统一 Skills
```bash
# 创建团队共享的 skills
mkdir .claude/skills
echo '{"name": "team-code-review", ...}' > .claude/skills/review.json
```

---

## 常见问题

### 1. 费用相关

**Q**: Claude Code 如何收费？  
**A**: 
- 需要 Claude 订阅或 API key
- Terminal CLI 和 VS Code 支持第三方提供商
- 按使用量计费（token 数量）

**Q**: 如何控制成本？  
**A**:
- 使用 CLAUDE.md 减少 token
- 启用 Prompt Caching
- 选择合适的模型
- 避免重复请求

---

### 2. 数据安全

**Q**: 代码会上传到服务器吗？  
**A**: 是的，代码会上传到 Anthropic 服务器处理

**Q**: 如何保护敏感信息？  
**A**:
- 使用 `.claudeignore` 排除敏感文件
- 不要提交 `.env` 文件
- 审查 CLAUDE.md 中的信息

---

### 3. 功能限制

**Q**: 支持哪些编程语言？  
**A**: 支持所有主流编程语言

**Q**: 文件大小限制？  
**A**: 单个文件 < 10MB，总上下文 < 200K tokens

**Q**: 支持离线使用吗？  
**A**: 不支持，需要联网

---

## 进阶资源

### 1. 官方文档
- **产品页**: https://code.claude.com/
- **文档**: https://docs.anthropic.com/en/docs/overview
- **API**: https://docs.anthropic.com/en/api/overview

### 2. 社区资源 ⭐
- **learn-claude-code**: https://github.com/shareAI-lab/learn-claude-code (36.4k stars)
- **文档技能**: https://github.com/pranavred/claude-code-documentation-skill

### 3. 学习路径
- **Day 1**: 基础（安装 + Quickstart + CLAUDE.md）
- **Day 2**: 工作流（Common Workflows + Git + 多文件）
- **Day 3**: 高级（MCP + Skills + 性能优化）

---

## 实战项目

### 项目 1: 自动化文档生成
**目标**: 为现有项目生成完整文档  
**时间**: 1 天  
**技能**: pranavred/claude-code-documentation-skill

### 项目 2: 代理开发
**目标**: 构建自定义代理  
**时间**: 3 天  
**参考**: shareAI-lab/learn-claude-code/agents/

### 项目 3: CI/CD 集成
**目标**: GitHub Actions 自动 review  
**时间**: 2 天  
**文档**: https://docs.anthropic.com/en/docs/github-actions

---

**更新时间**: 2026-03-23 16:05  
**版本**: 1.0  
**状态**: 🔥 一直在路上，持续更新中

---

## 附录

### A. 环境变量
```bash
# API Key
export ANTHROPIC_API_KEY=your_key

# 默认模型
export CLAUDE_MODEL=claude-3-5-sonnet-20241022

# 调试模式
export CLAUDE_DEBUG=true

# 最大 tokens
export CLAUDE_MAX_TOKENS=4096
```

### B. 配置文件
```json
// ~/.claude/settings.json
{
  "defaultModel": "claude-3-5-sonnet-20241022",
  "maxTokens": 4096,
  "temperature": 0.7,
  "enableCaching": true,
  "autoSave": true
}
```

### C. 命令速查
```bash
# 基础命令
claude                          # 启动
claude --help                   # 帮助
claude --version                # 版本

# 高级命令
claude --skill <name>           # 使用技能
claude --model <model>          # 指定模型
claude --print "task"           # 非交互模式
claude --config <file>          # 指定配置文件
```

---

**备注**: 本文档基于官方文档和社区资源整理，持续更新中。如有疑问，请参考官方文档或社区资源。
