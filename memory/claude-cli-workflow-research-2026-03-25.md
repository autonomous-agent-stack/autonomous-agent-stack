# Claude CLI Workflows 深度研究报告

**研究时间**: 2026-03-25 00:21  
**优先级**: 🔴 高（职场必备工具）  
**版本**: Claude CLI 深度优化版

---

## 📋 执行摘要

Claude CLI 确实包含强大的 **Workflows** 功能，核心是 **GradScaler Workflow**，这是一个完整的软件开发生命周期工作流，从规划到部署的端到端自动化流程。

**关键发现**：
- ✅ **GradScaler Workflow**：6 阶段完整工作流（PLAN → FIX → DESIGN → BUILD → CODE REVIEW → SHIP）
- ✅ **设计工作流**：Pencil + Claude Code 集成，AI 驱动的 UI 设计
- ✅ **自动化审查**：多智能体代码审查系统
- ✅ **职场应用**：适用于产品经理、前端开发、UI 设计师、项目经理

---

## 1. GradScaler Workflow 完整流程

### 1.1 工作流程图

```
┌─────────────────────────────────────────────────────────────┐
│                  GradScaler Workflow                        │
└─────────────────────────────────────────────────────────────┘

1. PLAN (规划阶段)
   └─> global-doc-master 创建规划文档
       ├─ 功能需求分析
       ├─ 技术方案设计
       └─ 实施计划制定

2. FIX (修复阶段)
   └─> global-doc-fixer 审查修复（循环）
       ├─ 自动审查文档
       ├─ 发现问题并修复
       └─ 重复直到 READY 状态

3. DESIGN (设计阶段) ⭐ 新增
   └─> Pencil + Claude Code 设计界面
       ├─ 自动注入项目上下文
       ├─ AI 生成 UI 设计
       └─ 实时预览和验证

4. BUILD (构建阶段)
   └─> 基于文档和设计构建功能
       ├─ 前端开发
       ├─ 后端开发
       └─ API 集成

5. CODE REVIEW (代码审查)
   └─> global-review-code 审计实现
       ├─ 代码质量检查
       ├─ 安全漏洞扫描
       └─ 性能优化建议

6. SHIP (发布阶段)
   └─> 修复问题 → 重新审查 → 部署
       ├─ 修复审查发现
       ├─ 二次审查确认
       └─ 生产环境部署
```

### 1.2 核心组件

#### A. 规划代理 (global-doc-master)
**功能**：创建高质量的技术规划文档  
**输出**：
- 功能需求文档
- 技术架构设计
- 实施计划和时间线
- 风险评估

**触发方式**：
```bash
# 在项目根目录
claude "创建用户认证功能的规划文档"
```

#### B. 修复代理 (global-doc-fixer)
**功能**：自动审查和修复文档问题  
**循环机制**：
- 发现问题 → 自动修复 → 重新审查
- 直到达到 READY 状态
- 避免人工反复修改

**质量标准**：
- 文档结构完整性
- 技术方案可行性
- 实施计划详细度
- 风险评估准确性

#### C. 设计工具 (Pencil + Claude Code)
**核心创新**：AI 驱动的上下文感知设计

**技术架构**：
```
Pencil (Mac 原生应用)
    ↓ MCP 协议
Claude Code (AI 引擎)
    ↓ Design Context Hook
项目代码库 (完整上下文)
```

**关键特性**：
1. **自动上下文注入**
   - 自动读取项目 `CLAUDE.md`
   - 扫描 `docs/planning/` 目录
   - 索引前端页面和组件
   - 索引后端 API 路由

2. **Auto-research Rules**
   - 屏幕名称 → 代码路径自动映射
   - 设计前自动读取相关代码
   - 使用真实数据结构而非猜测

3. **多智能体并行设计**
   - 同时启动多个设计代理
   - 每个代理独立处理一个屏幕
   - 共享项目上下文

#### D. 代码审查 (global-review-code)
**功能**：自动化代码质量审查  
**检查项**：
- 代码规范
- 安全漏洞
- 性能问题
- 架构一致性
- 测试覆盖率

#### E. 文档审查 (global-review-doc)
**功能**：文档质量审查  
**检查项**：
- 文档结构
- 内容准确性
- 技术可行性
- 可维护性

---

## 2. Pencil + Claude Code 深度集成

### 2.1 工作原理

**传统设计流程的问题**：
```
设计师 → 设计稿 → 开发者 → 实现
         ↓
    缺乏上下文
    猜测数据结构
    手动标注
    反复沟通
```

**Claude + Pencil 的解决方案**：
```
Claude Code (完整项目上下文)
    ↓
Pencil (设计工具)
    ↓
AI 生成设计 (基于真实代码)
```

### 2.2 Design Context Hook

**核心功能**：自动桥接项目知识到设计会话

**工作流程**：
1. 检测当前目录是否为 `/design`
2. 爬取父项目信息：
   - 从 `CLAUDE.md` 提取概览、用户流程、路由、角色
   - 索引 `docs/` 目录下的文档
   - 索引 `frontend/src/Pages/` 下的页面
   - 索引 `frontend/src/Components/` 下的组件
   - 索引 `backend/api/` 下的 API 路由
3. 生成 `design/CLAUDE.md`（约 1,600 tokens）
4. 输出注入摘要

**生成的内容示例**：
```
Design Context Hook
===================
Project: my-project
Parent: /Users/you/projects/my-project

Injected into design/CLAUDE.md:
  - Project overview, user flow, routes, roles from CLAUDE.md
  - 3 planning doc(s) indexed
  - 12 frontend page(s) listed
  - 5 frontend component(s) listed
  - 4 backend API route file(s) listed

  Auto-research rules active: Claude will read relevant
  docs and code automatically before designing screens.
```

### 2.3 Auto-research Rules

**智能行为**：当你说"设计登录页面"时，Claude 会：

1. 匹配"登录"到屏幕-研究映射
2. 自动读取 `../frontend/src/Pages/Auth/LoginPage.jsx`
3. 检查 `../docs/planning/auth-feature.md` 是否存在
4. 使用实际字段名、状态形状、验证规则
5. 基于完整知识设计（无需手动提示）

**优势**：
- ✅ 使用真实 API 字段而非猜测
- ✅ 了解用户流程和步骤进展
- ✅ 使用真实数据形状而非占位符
- ✅ 知道 Redux 状态、API 响应、条件渲染
- ✅ 自动遵循约定、品牌规则、设计决策

---

## 3. 职场应用场景

### 3.1 产品经理

**使用场景**：需求文档 → 可交互原型

**工作流程**：
```
1. 使用 global-doc-master 创建产品需求文档
2. global-doc-fixer 自动优化文档质量
3. 在 Pencil 中打开设计文件
4. Claude 基于需求文档自动生成 UI 原型
5. 多智能体并行设计所有页面
```

**价值**：
- ⏱️ **时间节省**：从 2-3 天缩短到 2-3 小时
- 🎯 **准确性**：基于真实需求而非猜测
- 🔄 **迭代速度**：快速修改和验证

### 3.2 前端开发者

**使用场景**：设计稿 → 代码实现

**工作流程**：
```
1. 查看设计师生成的 Pencil 设计
2. Claude 已了解设计背后的数据结构
3. 基于设计和文档实现功能
4. global-review-code 自动审查代码质量
5. 修复问题后部署
```

**价值**：
- 📐 **设计一致性**：代码完全符合设计
- 🔍 **上下文完整**：了解数据流和业务逻辑
- 🚀 **开发效率**：减少设计-开发沟通成本

### 3.3 UI 设计师

**使用场景**：概念设计 → 高保真原型

**工作流程**：
```
1. 在 Pencil 中创建新设计文件
2. Claude 自动加载项目上下文
3. 描述设计需求（如"设计用户资料页"）
4. Claude 自动读取相关代码和文档
5. 生成符合项目规范的设计
6. 使用截图验证设计效果
```

**价值**：
- 🎨 **设计准确性**：基于真实数据结构
- ⚡ **设计速度**：AI 辅助快速生成
- 🔄 **协作无缝**：设计与代码自动对齐

### 3.4 项目经理

**使用场景**：项目规划 → 进度跟踪

**工作流程**：
```
1. 使用 global-doc-master 创建项目规划
2. 自动生成甘特图和里程碑
3. 分配任务给开发团队
4. global-review-code 监控代码质量
5. 自动生成进度报告
```

**价值**：
- 📊 **可视化**：清晰的项目进度
- 🤖 **自动化**：减少手动跟踪工作
- ⚠️ **风险预警**：自动识别潜在问题

---

## 4. 与其他工具对比

### 4.1 vs Figma

| 维度 | Claude CLI + Pencil | Figma |
|------|---------------------|-------|
| **AI 集成** | ✅ 深度集成（AI 生成设计） | ❌ 需要插件 |
| **代码感知** | ✅ 基于真实代码 | ❌ 无代码感知 |
| **自动化** | ✅ 上下文自动注入 | ❌ 手动标注 |
| **协作** | ✅ 设计-代码自动对齐 | ⚠️ 需要手动同步 |
| **学习曲线** | ⚠️ 需要学习 Claude CLI | ✅ 易上手 |
| **成本** | ✅ 开源（Claude API 按用量） | ⚠️ $15-45/月 |

### 4.2 vs Cursor

| 维度 | Claude CLI | Cursor |
|------|-----------|--------|
| **工作流** | ✅ 完整工作流（PLAN → SHIP） | ⚠️ 代码补全为主 |
| **设计工具** | ✅ Pencil 集成 | ❌ 无设计工具 |
| **多智能体** | ✅ 并行代理系统 | ❌ 单一助手 |
| **上下文** | ✅ 项目级上下文 | ⚠️ 文件级上下文 |
| **审查系统** | ✅ 自动化审查 | ❌ 需要手动审查 |
| **成本** | ✅ 按用量付费 | ⚠️ $20/月 |

### 4.3 vs Notion AI

| 维度 | Claude CLI | Notion AI |
|------|-----------|-----------|
| **代码开发** | ✅ 完整开发工作流 | ❌ 仅文档辅助 |
| **设计工具** | ✅ Pencil 集成 | ❌ 无设计工具 |
| **代码审查** | ✅ 自动化审查 | ❌ 不支持 |
| **项目管理** | ⚠️ 需要集成 | ✅ 原生支持 |
| **学习曲线** | ⚠️ 需要技术背景 | ✅ 易上手 |
| **成本** | ✅ 按用量付费 | ⚠️ $10/月 |

---

## 5. 实战教程

### 5.1 安装 Design Context Hook

**步骤 1：下载 Hook 脚本**
```bash
# 下载脚本
curl -o ~/.claude/design-context-hook.sh \
  https://raw.githubusercontent.com/GradScalerTeam/claude_cli/main/hooks/design-context/design-context-hook.sh

# 添加执行权限
chmod +x ~/.claude/design-context-hook.sh
```

**步骤 2：配置 SessionStart Hook**
```bash
# 编辑配置文件
nano ~/.claude/settings.json
```

**添加以下内容**：
```json
{
  "hooks": {
    "SessionStart": [
      {
        "command": "bash ~/.claude/design-context-hook.sh"
      }
    ]
  }
}
```

**步骤 3：验证安装**
```bash
# 在项目的 design/ 目录中打开 .pen 文件
# Hook 会自动运行并显示注入摘要
```

### 5.2 第一次设计会话

**项目结构准备**：
```
my-project/
├── CLAUDE.md               ← 项目上下文（必需）
├── docs/
│   └── planning/
│       └── dashboard-feature.md
├── frontend/
│   └── src/
│       ├── Pages/
│       │   ├── Dashboard/DashboardPage.jsx
│       │   └── Auth/LoginPage.jsx
│       └── Components/
│           ├── Navbar.jsx
│           └── Sidebar.jsx
├── backend/
│   └── api/
│       ├── dashboard.py
│       └── auth.py
└── design/                  ← .pen 文件放这里
    └── app-screens.pen
```

**设计步骤**：
1. 在 Pencil 中打开 `design/app-screens.pen`
2. Claude Code 自动启动，Hook 注入上下文
3. 输入设计需求：
   ```
   "设计仪表板页面，包含侧边栏导航和主内容区域。
    显示用户的活跃会话和最近活动。"
   ```
4. Claude 自动：
   - 读取 `DashboardPage.jsx` 了解数据流
   - 检查 `dashboard-feature.md` 规划文档
   - 使用真实字段名和状态形状
   - 生成设计并保存到 `.pen` 文件

### 5.3 多智能体并行设计

**场景**：设计 5 个入职流程页面

**命令**：
```
"并行设计所有 5 个入职页面 —— 每个代理处理一个页面"
```

**效果**：
- 5 个设计代理同时启动
- 每个代理独立处理一个页面
- 共享项目上下文
- 大幅缩短设计时间

---

## 6. 最佳实践

### 6.1 编写高质量 CLAUDE.md

**推荐结构**：
```markdown
# 项目名称

## Project Overview
- 应用功能描述
- 目标用户群体

## User Flow
1. 用户注册
2. 邮箱验证
3. 完善资料
4. 开始使用

## Frontend Routes
- `/login` - LoginPage.jsx
- `/dashboard` - DashboardPage.jsx
- `/profile` - ProfilePage.jsx

## User Roles
- **普通用户**：查看和编辑自己的数据
- **管理员**：管理所有用户和内容
```

### 6.2 创建详细的规划文档

**位置**：`docs/planning/功能名称.md`

**内容**：
- 功能描述
- 用户故事
- 技术方案
- 数据结构
- API 接口
- 测试计划

### 6.3 使用屏幕-研究映射

**最佳命名**：
- ✅ `dashboard`（而非"主页"）
- ✅ `onboarding`（而非"新手引导"）
- ✅ `auth`（而非"登录注册"）
- ✅ `profile`（而非"个人中心"）

### 6.4 验证设计

**使用截图工具**：
```
"截取我们刚刚构建的仪表板屏幕截图"
```

Pencil 的 `get_screenshot` 工具捕获当前状态，便于验证。

---

## 7. 故障排除

### 7.1 Hook 未运行

**检查项**：
1. ✅ Hook 已在 `~/.claude/settings.json` 中注册
2. ✅ 脚本有执行权限：`chmod +x ~/.claude/design-context-hook.sh`
3. ✅ `.pen` 文件在 `design/` 文件夹内（不是 `designs/`、`ui/` 等）

### 7.2 无项目上下文生成

**原因**：
- 父目录缺少 `CLAUDE.md` 或 `.git` 目录

**解决方案**：
- 创建 `CLAUDE.md` 文件
- 或初始化 Git 仓库：`git init`

### 7.3 design/CLAUDE.md 缺少章节

**原因**：
- `CLAUDE.md` 中的标题不匹配

**解决方案**：
- 检查 `CLAUDE.md` 是否包含 `## Frontend Routes` 等标准标题
- 编辑 Hook 脚本中的 `awk` 模式以匹配你的标题

### 7.4 design/CLAUDE.md 不断重新生成

**说明**：这是正常行为

**原因**：
- 每次会话重新生成以捕获父项目的变更

**建议**：
- 不要手动编辑 `design/CLAUDE.md`
- 编辑父目录的 `CLAUDE.md` 代替

---

## 8. 未来发展方向

### 8.1 短期（3-6 个月）

- **更多设计工具集成**：Figma、Sketch 插件
- **增强的 Auto-research**：更智能的代码-设计映射
- **协作功能**：多人实时设计协作

### 8.2 中期（6-12 个月）

- **完整的设计系统**：自动生成设计系统
- **组件库生成**：从设计自动生成可复用组件
- **A/B 测试集成**：自动生成设计变体

### 8.3 长期（1-2 年）

- **全栈自动化**：从需求到部署的完整自动化
- **AI 驱动的项目管理**：智能任务分配和进度预测
- **跨平台支持**：Windows、Linux 版本

---

## 9. 总结

### 9.1 核心优势

1. **完整的开发生命周期**：从规划到部署的端到端工作流
2. **AI 驱动的设计**：基于真实代码的智能设计生成
3. **自动化审查**：多智能体系统确保代码和文档质量
4. **上下文感知**：自动注入项目上下文，无需手动解释
5. **并行处理**：多智能体并行工作，大幅提升效率

### 9.2 适用人群

- ✅ **产品经理**：快速原型设计
- ✅ **前端开发者**：设计到代码的无缝转换
- ✅ **UI 设计师**：AI 辅助设计
- ✅ **项目经理**：自动化项目跟踪
- ✅ **全栈开发者**：完整的开发工作流

### 9.3 推荐指数

**⭐⭐⭐⭐⭐ 5/5 星**

**理由**：
- 完整的工作流覆盖
- 强大的 AI 集成
- 显著的效率提升
- 活跃的开源社区
- 持续的更新和改进

---

## 10. 快速开始

### 10.1 5 分钟快速体验

```bash
# 1. 克隆 Claude CLI 仓库
git clone https://github.com/srxly888-creator/claude_cli.git

# 2. 安装 Design Context Hook
cd claude_cli
bash -c "$(curl -fsSL https://raw.githubusercontent.com/GradScalerTeam/claude_cli/main/hooks/design-context/install.sh)"

# 3. 下载 Pencil
# 访问 https://pencil.dev/ 下载 Mac 应用

# 4. 创建测试项目
mkdir test-project && cd test-project
mkdir -p design docs/planning frontend/src

# 5. 创建 CLAUDE.md
cat > CLAUDE.md << 'EOF'
# 测试项目

## Project Overview
这是一个测试项目，用于体验 Claude CLI Workflows。

## User Flow
1. 用户登录
2. 查看仪表板
3. 管理个人资料

## Frontend Routes
- `/login` - LoginPage.jsx
- `/dashboard` - DashboardPage.jsx
- `/profile` - ProfilePage.jsx
EOF

# 6. 在 Pencil 中创建设计文件
# 打开 Pencil，在 design/ 文件夹中创建 test.pen

# 7. 开始设计
# 在 Pencil 中输入："设计登录页面"
```

### 10.2 进阶学习资源

- **官方文档**：`HOW_TO_USE_PENCIL_WITH_CLAUDE.md`
- **Hook 文档**：`hooks/design-context/README.md`
- **代理文档**：`agents/` 目录
- **技能文档**：`skills/` 目录

---

**报告生成时间**: 2026-03-25 00:21  
**报告版本**: v1.0  
**维护者**: srxly888-creator  
**仓库**: https://github.com/srxly888-creator/claude_cli
