# GitHub Issues 完全指南

## 目录

1. [核心概念](#核心概念)
2. [Issue 生命周期](#issue-生命周期)
3. [协作机制](#协作机制)
4. [权限与安全](#权限与安全)
5. [工具链概览](#工具链概览)
6. [最佳实践](#最佳实践)

---

## 核心概念

### 什么是 GitHub Issues?

GitHub Issues 是 GitHub 提供的**问题跟踪系统**，用于:
- **Bug 跟踪**: 报告和修复软件缺陷
- **功能请求**: 提出新功能建议
- **任务管理**: 跟踪开发任务和进度
- **讨论平台**: 团队协作和技术讨论
- **项目规划**: 通过项目板和里程碑进行规划

### Issue vs Pull Request

| 特性 | Issue | Pull Request |
|------|-------|--------------|
| **用途** | 问题、任务、讨论 | 代码变更、合并 |
| **代码** | 可选代码片段 | 必须包含代码 diff |
| **关联** | 可引用 PR | 可关闭 Issue |
| **审查** | 评论讨论 | 完整代码审查流程 |
| **合并** | 无合并操作 | 可合并到分支 |

---

## Issue 生命周期

### 1. 创建阶段

#### 创建方式

```bash
# Web UI
访问 GitHub 仓库 → Issues → New Issue

# GitHub CLI
gh issue create --repo owner/repo \
  --title "Bug: 登录失败" \
  --body "详细描述..."

# GitHub REST API
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/owner/repo/issues \
  -d '{"title":"Bug","body":"描述"}'

# GitHub GraphQL API
curl -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -d '{"query":
    "mutation {
      createIssue(input:{
        repositoryId:\"REPO_ID\",
        title:\"Bug\",
        body:\"描述\"
      }) { issue { number } }
    }"
  }'
```

#### Issue 模板系统

**YAML 前置元数据**:
```yaml
---
name: Bug 报告
about: 报告问题帮助我们改进
title: '[BUG] '
labels: bug
assignees: ''
---
```

**表单语法** (新式表单):
```markdown
---
name: Bug 报告
description: 报告一个 Bug
title: "[BUG] <简短描述>"
labels: ["bug", "needs-triage"]
assignees: []
body:
  - type: markdown
    attributes:
      value: "感谢提交 Bug 报告!"
  - type: textarea
    id: reproduction
    attributes:
      label: 复现步骤
      description: 如何重现这个问题
      placeholder: |
        1. 打开...
        2. 点击...
        3. 看到错误...
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: 期望行为
      description: 你期望发生什么
  - type: textarea
    id: actual
    attributes:
      label: 实际行为
      description: 实际发生了什么
  - type: textarea
    id: logs
    attributes:
      label: 日志/截图
      description: 粘贴日志或上传截图
  - type: dropdown
    id: version
    attributes:
      label: 版本
      description: 你使用的是哪个版本?
      options:
        - v1.0.0
        - v1.1.0
        - v2.0.0
      default: 0
    validations:
      required: true
  - type: checkboxes
    id: terms
    attributes:
      label: 确认
      description: 请确认以下事项
      options:
        - label: 我已搜索过现有 Issues
          required: true
        - label: 我已阅读贡献指南
          required: false
```

### 2. 分类阶段

#### 标签系统 (Labels)

**标签命名最佳实践**:

```yaml
# 优先级标签
priority: critical   # 阻塞性问题，立即处理
priority: high       # 高优先级，本周处理
priority: medium     # 中优先级，本迭代处理
priority: low        # 低优先级，有空再处理

# 类型标签
kind: bug            # Bug 修复
kind: feature        # 新功能
kind: documentation  # 文档改进
kind: performance    # 性能优化
kind: security       # 安全问题

# 状态标签
status: needs-triage    # 待分类
status: confirmed       # 已确认
status: in-progress     # 处理中
status: in-review       # 审查中
status: blocked         # 被阻塞
status: ready-to-merge  # 待合并

# 团队标签
team: frontend      # 前端团队
team: backend       # 后端团队
team: infra         # 基础设施
team: design        # 设计团队

# 组件标签
component: auth     # 认证模块
component: api      # API
component: ui       # UI 组件
component: database # 数据库

# 复杂度标签
complexity: small    # < 2 小时
complexity: medium   # 2-8 小时
complexity: large    # 1-3 天
complexity: x-large  # > 3 天

# 版本标签
version: v1.0    # 影响版本
version: v2.0
```

#### 自动分类策略

**基于关键词的标签**:
```yaml
# .github/labeler.yml
# 自动标签配置文件
Bug:
  - bug
  - crash
  - error
  - not working
  - broken

Feature Request:
  - enhancement
  - feature request
  - add support for
  - wishlist

Documentation:
  - documentation
  - typo
  - grammar
  - unclear

Performance:
  - slow
  - performance
  - optimization
  - latency

Security:
  - security
  - vulnerability
  - exploit
  - xss
  - csrf
```

**基于文件的路径标签**:
```yaml
# .github/labeler-code.yml
frontend:
  - changed_files:
    - "src/**/*.js"
    - "src/**/*.jsx"
    - "src/**/*.ts"
    - "src/**/*.tsx"

backend:
  - changed_files:
    - "server/**/*.py"
    - "api/**/*.go"

infrastructure:
  - changed_files:
    - "docker/**"
    - "k8s/**"
    - "terraform/**"
```

### 3. 分配阶段

#### 负责人分配策略

```javascript
// 自动分配算法示例
function autoAssignIssue(issue, teamMembers) {
  // 1. 基于标签的分配
  const teamMap = {
    'frontend': ['alice', 'bob'],
    'backend': ['charlie', 'david'],
    'infra': ['eve']
  };

  // 2. 基于组件的分配
  const componentMap = {
    'auth': ['alice'],
    'api': ['charlie', 'david'],
    'ui': ['bob']
  };

  // 3. 基于负载均衡
  const assignee = assignByWorkload(teamMembers);

  // 4. 考虑时区和假期
  if (isOnVacation(assignee)) {
    return assignByWorkload(teamMembers.filter(m => !isOnVacation(m)));
  }

  return assignee;
}
```

#### 分配最佳实践

**✅ 推荐做法**:
- 一次分配给 1-2 人（避免责任分散）
- 明确期望和截止日期
- 提供 Context 和相关资源
- 考虑技能匹配和负载

**❌ 避免做法**:
- 分配给所有人（无责任感）
- 不说明原因和期望
- 忽略时区和假期
- 重复分配同一人

### 4. 处理阶段

#### Milestone 管理

```bash
# 创建 Milestone
gh api \
  repos/owner/repo/milestones \
  -f title="v1.2.0 Release" \
  -f description="Q2 Feature Release" \
  -f due_on="2024-06-30T23:59:59Z"

# 为 Issue 添加 Milestone
gh issue edit 42 \
  --repo owner/repo \
  --milestone "v1.2.0 Release"

# 查看 Milestone 进度
gh milestone view \
  "v1.2.0 Release" \
  --repo owner/repo \
  --json title,dueOn,progress,issues
```

#### 项目板 (Project Boards)

**自动化工作流**:
```yaml
# .github/workflows/project-automation.yml
name: Issue Project Automation

on:
  issues:
    types: [opened, edited, closed, reopened]

jobs:
  project-automation:
    runs-on: ubuntu-latest
    steps:
      - name: Move to To Do
        if: github.event.action == 'opened'
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.projects.createCard({
              column_id: COLUMN_ID_TODO,
              content_id: context.payload.issue.id,
              content_type: 'Issue'
            });

      - name: Move to In Progress
        if: |
          contains(github.event.issue.labels.*.name, 'status:in-progress')
        uses: actions/github-script@v7
        with:
          script: |
            // Move card to In Progress column
```

### 5. 关闭阶段

#### 关闭策略

```bash
# 基于关键词自动关闭
# 当 PR 包含 "closes #42" 或 "fixes #42" 时自动关闭 Issue

# 手动关闭
gh issue close 42 --repo owner/repo \
  --comment "已通过 PR #123 修复"

# 批量关闭
gh issue list \
  --repo owner/repo \
  --label "status:stale" \
  --json number \
  --jq '.[].number' | \
  xargs -I {} gh issue close {} --repo owner/repo \
  --comment "因长期未活动自动关闭"

# 锁定 Issue（禁止评论）
gh issue lock 42 --repo owner/repo \
  --reason "off-topic"
```

#### 关闭前检查清单

```markdown
## 关闭 Issue 前的检查清单

### 功能相关
- [ ] 功能已实现并测试
- [ ] 文档已更新
- [ ] 测试覆盖充分
- [ ] 向后兼容性检查

### Bug 相关
- [ ] Bug 已复现并修复
- [ ] 回归测试已添加
- [ ] 根因已分析
- [ ] 防止措施已实施

### 通用检查
- [ ] 关联的 PR 已合并
- [ ] 所有评论已回复
- [ ] 相关文档已更新
- [ ] 发布说明已更新
```

---

## 协作机制

### 评论和讨论

#### 评论语法

```markdown
# Markdown 支持

## 标题
### 子标题

**粗体** *斜体* ~~删除线~~

- 列表项 1
- 列表项 2
  - 子列表项

1. 编号列表
2. 第二项

`inline code`

```javascript
// 代码块
function hello() {
  console.log("world");
}
```

> 引用文本

[链接](https://example.com)

![图片](image-url)

| 表头 1 | 表头 2 |
|--------|--------|
| 内容 1 | 内容 2 |

---

@mention 用户
#issue-number 引用 Issue
#PR-number 引用 PR
commit:sha 引用提交
```

#### 任务列表 (Task Lists)

```markdown
## 实现计划

- [ ] 需求分析
- [x] 设计方案
- [x] 开发实现
- [ ] 测试验证
- [ ] 文档编写
- [ ] 代码审查
- [ ] 部署上线

### 子任务

#### 前端部分
- [ ] 页面设计
- [ ] 组件开发
- [ ] 接口对接

#### 后端部分
- [ ] API 设计
- [ ] 数据库设计
- [ ] 业务逻辑
```

**自动跟踪功能**:
- 当 Issue 中有任务列表时，Issue 描述会显示进度（如: `3/10 tasks completed`）
- 可以将任务列表复制到 PR，自动同步状态

#### 建议评论 (Suggested Changes)

在代码审查中可以直接建议代码修改:

```diff
- const name = "World";
+ const name = "GitHub";
```

审查者可以一键应用建议。

### @提及系统

#### 提及类型

```markdown
# 用户提及
@username  # 直接通知用户

# 团队提及
@org/team-name  # 通知整个团队（需要团队权限）

# Issue/PR 引用
#42  # 引用同仓库的 Issue #42
owner/repo#42  # 引用其他仓库的 Issue

# Commit 引用
abc123def  # 引用 commit SHA

# 讨论引用
#conversation-url  # 引用团队讨论
```

#### 提及最佳实践

**✅ 适当使用**:
- 需要某人输入或审查时
- 指派任务或请求帮助
- 通知相关人员变更

**❌ 过度使用**:
- @所有人（仅在紧急情况）
- 无缘无故提及（制造噪音）
- 重复提及同一人

### 代码审查集成

#### 从 Issue 创建 PR

```bash
# 1. 从 Issue 创建分支
gh issue develop 42 --repo owner/repo --branch "fix/bug-42"

# 或手动
git checkout -b fix/issue-42

# 2. 开发并提交
git commit -m "fix: resolve issue #42"

# 3. 创建 PR 并关联 Issue
gh pr create \
  --repo owner/repo \
  --title "Fix: 解决登录问题 (#42)" \
  --body "Closes #42" \
  --base main \
  --head fix/issue-42
```

**自动关闭机制**:
在 PR 描述或提交信息中使用以下关键词会自动关闭关联的 Issue:
- `close #42`
- `closes #42`
- `closed #42`
- `fix #42`
- `fixes #42`
- `fixed #42`
- `resolve #42`
- `resolves #42`
- `resolved #42`

#### 审查流程

```bash
# 请求审查
gh pr review-request 123 \
  --repo owner/repo \
  --reviewer alice,bob

# 提交审查
gh pr review 123 \
  --repo owner/repo \
  --body "Looks good!" \
  --approve

# 或评论（不批准）
gh pr review 123 \
  --repo owner/repo \
  --body "需要修改以下问题..." \
  --comment

# 请求变更
gh pr review 123 \
  --repo owner/repo \
  --body "请修复以下问题" \
  --request-changes
```

### Milestone 管理

#### Milestone 最佳实践

**命名规范**:
```
v1.0.0 Release
v1.1.0 Release
v2.0.0 Beta
Q1 2024 Roadmap
Sprint 23
```

**时间规划**:
```python
# Milestone 时间规划示例
milestones = [
    {
        "name": "v1.0.0",
        "due_date": "2024-03-31",
        "description": "Initial release",
        "issues": [
            {"title": "Core features", "estimate": 10},
            {"title": "Documentation", "estimate": 3}
        ]
    },
    {
        "name": "v1.1.0",
        "due_date": "2024-06-30",
        "description": "Feature enhancements",
        "backlog": True
    }
]
```

#### 进度跟踪

```bash
# Milestone 进度报告
gh milestone view "v1.0.0" \
  --repo owner/repo \
  --json title,dueOn,progress,issues \
  --jq '
    "Milestone: \(.title)\n" +
    "Due: \(.dueOn)\n" +
    "Progress: \(.progress)\% closed\n" +
    "Open Issues: \([.issues[] | select(.state == "open")] | length)\n" +
    "Closed Issues: \([.issues[] | select(.state == "closed")] | length)"
  '
```

### 项目板使用

#### Board 类型

**1. Basic Board**:
```
To Do → In Progress → Done
```

**2. Kanban Board**:
```
Backlog → To Do → In Progress → In Review → Done → Archived
```

**3. Review Board**:
```
Needs Review → Approved → Changes Requested → Merged
```

**4. Bug Board**:
```
New → Triage → Confirmed → In Progress → In QA → Verified → Closed
```

#### 自动化规则

```javascript
// 使用 GitHub Actions 自动化项目板
// .github/workflows/project-board-automation.yml

const automations = [
  {
    trigger: 'labeled',
    label: 'status:in-progress',
    action: 'move',
    column: 'In Progress'
  },
  {
    trigger: 'closed',
    action: 'move',
    column: 'Done'
  },
  {
    trigger: 'reopened',
    action: 'move',
    column: 'In Progress'
  },
  {
    trigger: 'assign',
    action: 'move',
    column: 'In Progress'
  }
];
```

---

## 权限与安全

### 仓库权限模型

#### 权限级别

```yaml
# Read (读取)
- 查看 Issues
- 评论 Issues
- 不能创建、编辑、关闭

# Triage (分类) - 仅组织仓库
- 所有 Read 权限
- 创建和编辑标签
- 管理 Milestone
- 管理项目板
- 关闭自己创建的 Issue

# Write (写入)
- 所有 Triage 权限
- 创建和编辑 Issues
- 分配和取消分配 Issues
- 关闭任何 Issue
- 添加协作者

# Maintain (维护)
- 所有 Write 权限
- 删除 Issue 评论
- 锁定/解锁 Issues
- 管理所有标签
- 编辑 Issue 内容（包括他人的）

# Admin (管理)
- 所有 Maintain 权限
- 删除 Issues
- 修改仓库设置
- 管理协作者和团队
```

#### 权限矩阵

| 操作 | Read | Triage | Write | Maintain | Admin |
|------|------|--------|-------|----------|-------|
| 查看 Issues | ✅ | ✅ | ✅ | ✅ | ✅ |
| 创建 Issues | ❌ | ❌ | ✅ | ✅ | ✅ |
| 编辑自己 Issue | ✅ | ✅ | ✅ | ✅ | ✅ |
| 编辑他人 Issue | ❌ | ❌ | ❌ | ✅ | ✅ |
| 删除 Issue | ❌ | ❌ | ❌ | ❌ | ✅ |
| 关闭 Issue | ❌ | ⚠️* | ✅ | ✅ | ✅ |
| 锁定 Issue | ❌ | ❌ | ❌ | ✅ | ✅ |
| 管理标签 | ❌ | ✅ | ✅ | ✅ | ✅ |
| 管理 Milestone | ❌ | ✅ | ✅ | ✅ | ✅ |
| 分配 Issue | ❌ | ❌ | ✅ | ✅ | ✅ |

*仅能关闭自己创建的

### Issue 安全策略

#### 敏感信息处理

**自动化扫描**:
```yaml
# .github/workflows/security-scan.yml
name: Security Scan

on:
  issues:
    types: [opened, edited]

jobs:
  scan-for-secrets:
    runs-on: ubuntu-latest
    steps:
      - name: Scan Issue Body
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.issue.body }}
          extra_args: --only-verified
```

**手动审查清单**:
- [ ] 无密码、token、密钥
- [ ] 无 IP 地址、内网信息
- [ ] 无个人信息、PII
- [ ] 无机密文档链接
- [ ] 无生产环境配置

#### 私有仓库 Issues

**特点**:
- 仅仓库成员可见
- 搜索引擎不可索引
- 不公开显示在用户 profile
- 可以转换为公开仓库（需谨慎）

**转换到公开前的检查**:
```bash
#!/bin/bash
# 检查私有仓库转为公开前的安全问题

REPO="owner/repo"
TOKEN="$GITHUB_TOKEN"

# 扫描所有 Issues 敏感信息
gh issue list \
  --repo $REPO \
  --state all \
  --limit 1000 \
  --json number,body \
  --jq '.[] | select(.body | test("password|token|secret|api_key"; "i")) | .number'
```

### 企业级权限

#### 团队权限管理

```bash
# 创建团队
gh api \
  orgs/YOUR_ORG/teams \
  -f name="backend-team" \
  -f description="Backend developers" \
  -f permission="pull"

# 添加仓库权限
gh api \
  orgs/YOUR_ORG/teams/backend-team/repos/owner/repo \
  -f permission="triage"

# 添加团队成员
gh api \
  orgs/YOUR_ORG/teams/backend-team/memberships/username \
  -f role="member"
```

#### 外部协作者管理

```bash
# 添加外部协作者
gh api \
  repos/owner/repo/collaborators/external-user \
  -f permission="write"

# 查看所有协作者
gh api \
  repos/owner/repo/collaborators \
  --jq '.[] | "\(.login): \(.permission)"'
```

---

## 工具链概览

### GitHub CLI (gh)

#### 安装与配置

```bash
# 安装
brew install gh  # macOS
apt install gh   # Linux
winget install gh # Windows

# 认证
gh auth login
# 选择 GitHub.com
# 选择 HTTPS
# 粘贴 token (需要 repo 权限)

# 验证
gh auth status

# 配置
gh config set editor vim
gh config set git_protocol ssh
gh config set prompt disabled
```

#### 核心 Issue 命令

```bash
# 列出 Issues
gh issue list \
  --repo owner/repo \
  --state open \
  --limit 20 \
  --search "label:bug"

# 创建 Issue
gh issue create \
  --repo owner/repo \
  --title "Bug title" \
  --body "Description" \
  --label "bug,high-priority"

# 查看 Issue
gh issue view 42 \
  --repo owner/repo \
  --json title,body,labels,assignees,comments

# 更新 Issue
gh issue edit 42 \
  --repo owner/repo \
  --add-label "in-progress" \
  --remove-label "needs-triage" \
  --assignee "@me"

# 关闭 Issue
gh issue close 42 \
  --repo owner/repo \
  --comment "Fixed via PR #123"

# 转换为 Issue
gh issue convert 42 \
  --repo owner/repo

# 锁定 Issue
gh issue lock 42 \
  --repo owner/repo \
  --reason "spam"
```

#### 高级查询

```bash
# 复杂搜索
gh issue list \
  --search "repo:owner/repo state:open label:bug -label:duplicate created:>2024-01-01" \
  --json number,title,labels,createdAt,assignees \
  --jq '.[] | select(.labels[].name == "priority:high")'

# 统计数据
gh issue list \
  --state all \
  --json state \
  --jq 'group_by(.state) | map({state: .[0].state, count: length})'

# 按标签分组
gh issue list \
  --state all \
  --json labels \
  --jq '[.[].labels[].name] | group_by(.) | map({label: .[0], count: length})'
```

### GitHub GraphQL API

#### 基础查询

```graphql
# 获取 Issue 详情
query {
  repository(owner: "owner", name: "repo") {
    issue(number: 42) {
      id
      title
      body
      state
      author {
        login
      }
      labels(first: 10) {
        nodes {
          name
          color
        }
      }
      assignees(first: 10) {
        nodes {
          login
        }
      }
      comments(first: 10) {
        nodes {
          body
          author {
            login
          }
          createdAt
        }
      }
      timelineItems(first: 20) {
        nodes {
          __typename
          ... on LabeledEvent {
            label {
              name
            }
            actor {
              login
            }
            createdAt
          }
        }
      }
    }
  }
}
```

#### 批量查询

```graphql
# 获取多个 Issue
query {
  repository(owner: "owner", name: "repo") {
    issues(first: 100, states: OPEN) {
      nodes {
        number
        title
        labels(first: 5) {
          nodes {
            name
          }
        }
        assignees(first: 5) {
          nodes {
            login
          }
        }
      }
    }
  }
}
```

#### 自动化脚本

```python
import requests
import json

# GitHub GraphQL API 客户端
class GitHubGraphQL:
    def __init__(self, token):
        self.token = token
        self.endpoint = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def query(self, query, variables=None):
        response = requests.post(
            self.endpoint,
            headers=self.headers,
            json={"query": query, "variables": variables}
        )
        response.raise_for_status()
        return response.json()

    def get_issue_metrics(self, owner, repo, months=6):
        """获取 Issue 指标"""
        query = """
        query($owner: String!, $repo: String!, $since: GitTimestamp!) {
          repository(owner: $owner, name: $repo) {
            issues(
              first: 100
              states: [OPEN, CLOSED]
              filterBy: {createdSince: $since}
            ) {
              nodes {
                number
                title
                state
                createdAt
                closedAt
                labels(first: 10) {
                  nodes {
                    name
                  }
                }
                comments(first: 50) {
                  totalCount
                }
              }
            }
          }
        }
        """
        from datetime import datetime, timedelta
        since = (datetime.now() - timedelta(days=months*30)).isoformat() + "Z"

        result = self.query(query, {
            "owner": owner,
            "repo": repo,
            "since": since
        })

        issues = result["data"]["repository"]["issues"]["nodes"]

        # 计算指标
        metrics = {
            "total": len(issues),
            "open": len([i for i in issues if i["state"] == "OPEN"]),
            "closed": len([i for i in issues if i["state"] == "CLOSED"]),
            "avg_comments": sum(i["comments"]["totalCount"] for i in issues) / len(issues),
            "label_distribution": {}
        }

        # 标签分布
        for issue in issues:
            for label in issue["labels"]["nodes"]:
                name = label["name"]
                metrics["label_distribution"][name] = \
                    metrics["label_distribution"].get(name, 0) + 1

        return metrics
```

### GitHub Actions 自动化

#### Issue 自动化工作流

```yaml
# .github/workflows/issue-automation.yml

name: Issue Automation

on:
  issues:
    types: [opened, edited, labeled, unlabeled, assigned, closed]

jobs:
  auto-label:
    if: github.event.action == 'opened'
    runs-on: ubuntu-latest
    steps:
      - name: Auto-label based on title
        uses: actions/github-script@v7
        with:
          script: |
            const issue = context.payload.issue;
            const title = issue.title.toLowerCase();
            const body = issue.body.toLowerCase();

            let labels = [];

            // 基于关键词添加标签
            if (title.includes('bug') || body.includes('crash') || body.includes('error')) {
              labels.push('kind:bug');
            }
            if (title.includes('feature') || title.includes('enhancement')) {
              labels.push('kind:feature');
            }
            if (body.includes('slow') || body.includes('performance')) {
              labels.push('kind:performance');
            }

            // 添加标签
            if (labels.length > 0) {
              github.rest.issues.addLabels({
                issue_number: context.issue.number,
                owner: context.repo.owner,
                repo: context.repo.repo,
                labels: labels
              });
            }

  auto-assign:
    if: github.event.action == 'labeled'
    runs-on: ubuntu-latest
    steps:
      - name: Auto-assign based on component label
        uses: actions/github-script@v7
        with:
          script: |
            const issue = context.payload.issue;
            const label = context.payload.label.name;

            const componentMap = {
              'component:auth': ['alice'],
              'component:api': ['bob', 'charlie'],
              'component:ui': ['david'],
              'component:database': ['eve']
            };

            if (label in componentMap) {
              const assignees = componentMap[label];
              github.rest.issues.addAssignees({
                issue_number: context.issue.number,
                owner: context.repo.owner,
                repo: context.repo.repo,
                assignees: assignees
              });
            }

  move-project-card:
    if: github.event.action == 'labeled'
    runs-on: ubuntu-latest
    steps:
      - name: Move project card
        uses: actions/github-script@v7
        with:
          script: |
            // 根据标签移动项目板卡片
            const labelToColumn = {
              'status:in-progress': 2,
              'status:in-review': 3,
              'status:done': 4
            };

            const label = context.payload.label.name;
            if (label in labelToColumn) {
              const columnId = labelToColumn[label];

              // 获取项目板卡片
              const cards = await github.rest.projects.listCards({
                column_id: 1 // TODO 列
              });

              // 移动到对应列
              for (const card of cards.data) {
                if (card.content_url.includes(`issues/${context.issue.number}`)) {
                  await github.rest.projects.moveCard({
                    card_id: card.id,
                    position: 'top',
                    column_id: columnId
                  });
                  break;
                }
              }
            }

  stale-issues:
    runs-on: ubuntu-latest
    steps:
      - name: Mark stale issues
        uses: actions/stale@v9
        with:
          repo-token: ${{ secrets.GITHUB_TOKEN }}
          days-before-stale: 30
          days-before-close: 14
          stale-issue-label: 'stale'
          stale-issue-message: |
            这个 Issue 已经 30 天没有活动了，标记为 stale。
            如果问题仍然存在，请评论确认，我们会重新处理。
            如果 14 天内没有确认，Issue 将被自动关闭。
          exempt-issue-labels: 'priority:critical,status:in-progress'

  issue-metrics:
    if: github.event.action == 'closed'
    runs-on: ubuntu-latest
    steps:
      - name: Calculate cycle time
        uses: actions/github-script@v7
        with:
          script: |
            const issue = context.payload.issue;
            const created = new Date(issue.created_at);
            const closed = new Date(issue.closed_at);
            const cycleTimeDays = (closed - created) / (1000 * 60 * 60 * 24);

            // 添加评论显示周期时间
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: `📊 **周期时间**: ${cycleTimeDays.toFixed(1)} 天`
            });
```

---

## 最佳实践

### Issue 标题最佳实践

#### 好的标题

```
✅ [BUG] 登录页面在 Safari 14 中崩溃
✅ [Feature] 添加深色模式支持
✅ [Performance] 数据库查询优化 - 减少 API 响应时间
✅ [Security] 修复 XSS 漏洞在用户输入处
✅ [Docs] 更新 API 文档关于认证部分
```

#### 不好的标题

```
❌ 有问题
❌ Help me
❌ Bug
❌ 东西坏了
❌ ???
```

#### 标题模板

```
[类型] 简短描述 (影响范围)

类型:
- [BUG] - Bug 报告
- [Feature] - 功能请求
- [Performance] - 性能问题
- [Security] - 安全问题
- [Docs] - 文档问题
- [Tech Debt] - 技术债务

影响范围 (可选):
- (Admin Panel)
- (API v2)
- (Mobile App)
```

### Issue 描述最佳实践

#### Bug 报告模板

```markdown
## Bug 描述
清晰简洁地描述 Bug。

## 复现步骤
1. 访问 '...'
2. 点击 '....'
3. 滚动到 '....'
4. 看到错误

## 期望行为
应该发生什么。

## 实际行为
实际发生了什么。

## 截图
如果适用，添加截图。

## 环境信息
- OS: [e.g. macOS 14.0]
- Browser: [e.g. Chrome 120]
- Version: [e.g. v1.2.3]

## 额外信息
其他相关信息、日志、stack traces 等。

<details>
<summary>日志详情</summary>

```
粘贴详细日志
```
</details>
```

#### 功能请求模板

```markdown
## 功能描述
清晰简洁地描述新功能。

## 问题背景
这个功能解决什么问题？为什么需要？

## 建议方案
你期望这个功能如何工作？

## 替代方案
考虑过其他实现方式吗？

## 优先级
- [ ] 高优先级
- [ ] 中优先级
- [ ] 低优先级

## 实现复杂度评估
- [ ] 简单 (< 2 小时)
- [ ] 中等 (2-8 小时)
- [ ] 复杂 (1-3 天)
- [ ] 非常复杂 (> 3 天)

## 附加信息
其他相关信息、参考链接、mockup 等。
```

### Issue 管理最佳实践

#### 定期维护

```bash
# 每周维护脚本
#!/bin/bash

# 1. 标记过时的 Issues
gh issue list \
  --repo owner/repo \
  --state open \
  --search "updated:<2024-02-01" \
  --json number \
  --jq '.[].number' | \
  xargs -I {} gh issue edit {} \
    --add-label "stale" \
    --comment "此 Issue 已长时间未更新，请确认是否仍然相关。"

# 2. 清理重复 Issues
# 使用 GitHub Actions 或手动审查

# 3. 更新 Milestone
gh issue list \
  --repo owner/repo \
  --state open \
  --json number,milestone \
  --jq '.[] | select(.milestone == null) | .number' | \
  # 提醒用户添加 Milestone

# 4. 生成周报
echo "# Issue 周报 - $(date +%Y-%m-%d)"
echo ""
echo "## 本周新增"
gh issue list \
  --repo owner/repo \
  --search "created:$(date -v-1w +%Y-%m-%d)..$(date +%Y-%m-%d)" \
  --state all
echo ""
echo "## 本周关闭"
gh issue list