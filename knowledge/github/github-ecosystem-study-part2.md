
  # Issue 转换为 PR
  convert_to_pr:
    if: github.event.action == 'opened'
    runs-on: ubuntu-latest
    steps:
      - name: Check if issue should be PR
        uses: actions/github-script@v7
        with:
          script: |
            const issue = context.payload.issue;
            const title = issue.title.toLowerCase();

            // 如果标题包含 "[PR]"，提示创建 PR
            if (title.includes('[pr]')) {
              await github.rest.issues.createComment({
                issue_number: context.issue.number,
                owner: context.repo.owner,
                repo: context.repo.repo,
                body: `@${issue.user.login} 这看起来像是一个 Pull Request，请使用 PR 而不是 Issue。`
              });
            }

  # SLA 监控
  sla_monitor:
    if: github.event.action == 'opened'
    runs-on: ubuntu-latest
    steps:
      - name: Set SLA reminder
        uses: actions/github-script@v7
        with:
          script: |
            const issue = context.payload.issue;

            // 高优先级 Issue - 24小时响应
            if (issue.labels.some(l => l.name === 'priority:high' || l.name === 'priority:critical')) {
              // 24小时后检查
              const delay = 24 * 60 * 60 * 1000;

              setTimeout(async () => {
                const { data: issueData } = await github.rest.issues.get({
                  issue_number: context.issue.number,
                  owner: context.repo.owner,
                  repo: context.repo.repo
                });

                // 如果仍未分配，提醒
                if (!issueData.assignees || issueData.assignees.length === 0) {
                  await github.rest.issues.createComment({
                    issue_number: context.issue.number,
                    owner: context.repo.owner,
                    repo: context.repo.repo,
                    body: '⚠️ **SLA 警告**: 高优先级 Issue 已超过 24 小时未分配。'
                  });
                }
              }, delay);
            }

  # 过时 Issue 清理
  stale_issues:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/stale@v9
        with:
          repo-token: ${{ secrets.GITHUB_TOKEN }}
          days-before-stale: 30
          days-before-close: 14
          stale-issue-label: 'stale'
          stale-issue-message: |
            此 Issue 已 30 天无活动，标记为 stale。
            如果问题仍然存在，请评论确认，我们会重新处理。
            14 天内无确认将自动关闭。
          exempt-issue-labels: 'priority:critical,status:in-progress,status:blocked'
          operations-per-run: 100

  # 指标收集
  collect_metrics:
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

            // 评论周期时间
            await github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `📊 **周期时间**: ${cycleTimeDays.toFixed(1)} 天`
            });

            // 记录到数据存储（可选）
            // 这里可以发送到外部分析系统
```

---

## 大型项目案例分析

### 1. Kubernetes Issues 管理

#### 特点
- 📊 **海量 Issues** - 数万个开放 Issues
- 🏷️ **复杂标签系统** - SIG、组件、优先级
- 🤖 **自动化机器人** - k8s-triage-bot、needs-rebase
- 👥 **SIG 机制** - 特别兴趣小组管理
- 📋 **Milestone 管理** - 按版本追踪

#### Issue 分类系统

```yaml
# Kubernetes 标签体系
sig:
  - api-machinery
  - apps
  - auth
  - autoscaling
  - cli
  - cloud-provider
  - cluster-lifecycle
  - instrumentation
  - network
  - node
  - scalability
  - scheduling
  - storage
  - testing
  - ui
  - windows

kind:
  - bug
  - feature
  - documentation
  - failing-test
  - flake

priority:
  - critical
  - high
  - medium
  - low

triage:
  - needs-triage
  - needs-information
  - needs-sig
  - needs-rebase

area:
  - kube-apiserver
  - kube-controller-manager
  - kube-scheduler
  - kubelet
  - proxy
```

#### Triage 流程

```python
# Kubernetes 风格的 Issue Triage 机器人

class KubernetesTriageBot:
    """Kubernetes Issue Triage 机器人"""

    def __init__(self, gh_client):
        self.gh = gh_client

    def triage_new_issue(self, owner: str, repo: str, issue_number: int):
        """Triage 新 Issue"""
        issue = self.gh.get_issue(owner, repo, issue_number)

        # 1. 检查是否需要 triage
        if not self._needs_triage(issue):
            return

        # 2. 添加 needs-triage 标签
        self.gh.add_labels(owner, repo, issue_number, ["needs-triage"])

        # 3. 提交信息收集表单
        self._post_template_comment(owner, repo, issue_number)

        # 4. 尝试自动分类
        self._auto_classify(owner, repo, issue_number, issue)

    def _needs_triage(self, issue: Dict) -> bool:
        """检查是否需要 triage"""
        # 已有 triaged 标签
        if any(l["name"] == "triaged" for l in issue["labels"]):
            return False

        # 已有 SIG 标签
        sig_labels = [l for l in issue["labels"] if l["name"].startswith("sig/")]
        if sig_labels:
            return False

        return True

    def _post_template_comment(self, owner: str, repo: str, issue_number: int):
        """提交信息收集评论"""
        template = """
@{author} 感谢提交 Issue！为了帮助我们快速处理，请提供以下信息：

**Issue Template**:

### 问题描述
<!-- 清晰描述问题 -->

### 复现步骤
1.
2.
3.

### 期望行为
<!-- 你期望发生什么 -->

### 实际行为
<!-- 实际发生了什么 -->

### 环境
- Kubernetes 版本:
- 云提供商:
- OS:

### 额外信息
<!-- 日志、截图等 -->
        """.format(author=issue["user"]["login"])

        self.gh.create_comment(owner, repo, issue_number, template)

    def _auto_classify(self, owner: str, repo: str, issue_number: int, issue: Dict):
        """自动分类"""
        title = issue["title"].lower()
        body = issue["body"].lower() if issue["body"] else ""

        # SIG 关键词映射
        sig_keywords = {
            "sig/api-machinery": ["api", "apiserver", "crd", "custom resource"],
            "sig/apps": ["deployment", "statefulset", "daemonset", "replicaset"],
            "sig/auth": ["auth", "rbac", "service account", "certificate"],
            "sig/network": ["network", "service", "ingress", "cni", "kube-proxy"],
            "sig/node": ["kubelet", "node", "kube-proxy"],
            "sig/scheduling": ["schedule", "scheduler", "pod", "node"],
            "sig/storage": ["volume", "storage", "pv", "pvc", "csi"],
        }

        # 匹配 SIG
        matched_sigs = []
        for sig, keywords in sig_keywords.items():
            if any(kw in title or kw in body for kw in keywords):
                matched_sigs.append(sig)

        if matched_sigs:
            self.gh.add_labels(owner, repo, issue_number, matched_sigs)
            self.gh.remove_label(owner, repo, issue_number, "needs-triage")
            self.gh.add_labels(owner, repo, issue_number, ["triaged"])
```

### 2. Linux 内核 Issue 流程

#### 特点
- 📝 **邮件列表工作流** - 主要通过邮件讨论
- 🔍 **严格的提交规范** - 遵循 Documentation/process/submitting-patches.rst
- 👨‍💼 **维护者层级** - Maintainers → Sub-maintainers → Contributors
- 🌳 **分支策略** - 每个子系统有独立的分支
- 📅 **发布周期** - 约 2-3 个月一个大版本

#### 提交规范

```bash
#!/bin/bash
# Linux 内核风格的提交脚本

create_kernel_style_patch() {
    local branch=$1
    local issue_number=$2

    # 检查是否有未提交的更改
    if [ -n "$(git status --porcelain)" ]; then
        echo "错误: 有未提交的更改"
        exit 1
    fi

    # 创建 Issue 分支
    git checkout -b "issue-$issue_number"

    # ... 进行修改 ...

    # 创建提交
    git commit -s -F- <<EOF
subsystem: fix issue in component (#$issue_number)

Detailed description of the fix.

Explain the problem and the solution.

The issue was: <link to issue or mailing list discussion>

Fixes: #$issue_number
Signed-off-by: Your Name <your.email@example.com>
EOF

    # 生成 patch
    git format-patch -1 --stdout > "issue-$issue_number.patch"

    echo "Patch created: issue-$issue_number.patch"
    echo "Send to: subsystem-maintainer@vger.kernel.org"
}
```

### 3. VS Code Issues 生态

#### 特点
- 🔌 **Extensions 生态** - 大量第三方扩展 Issues
- 📊 **API-first** - Issues 驱动的 API 开发
- 🧪 **自动化测试集成** - Issue 包含测试用例
- 👥 **社区驱动** - 高度社区参与
- 🚀 **快速迭代** - 月度发布周期

#### Issue 模板系统

```yaml
# .github/ISSUE_TEMPLATE/bug_report.yml
name: Bug Report
title: "[Bug] "
labels: ["bug", "needs-triage"]
body:
  - type: markdown
    attributes:
      value: |
        感谢报告 Bug！请提供尽可能多的信息。

  - type: textarea
    id: reproduction
    attributes:
      label: Steps to Reproduce
      description: 如何重现 Bug
      placeholder: |
        1. Create a file 'test.js'
        2. Paste content...
        3. Press...
        4. Bug happens
    validations:
      required: true

  - type: textarea
    id: expected
    attributes:
      label: Expected Behavior
      description: 期望行为

  - type: textarea
    id: actual
    attributes:
      label: Actual Behavior
      description: 实际行为
      validations:
        required: true

  - type: textarea
    id: code
    attributes:
      label: Reproducible Code
      description: 最小可复现代码
      render: typescript
      validations:
        required: true

  - type: input
    id: vscode_version
    attributes:
      label: VS Code Version
      placeholder: 1.85.0
      validations:
        required: true

  - type: input
    id: os_version
    attributes:
      label: OS Version
      placeholder: Windows 11, macOS 14, Ubuntu 22.04
      validations:
        required: true

  - type: dropdown
    id: area
    attributes:
      label: Area
      options:
        - Editor
        - Workbench
        - Extension API
        - Terminal
        - Debug
        - Language Features
        - SCM
        - Other
      default: 0
```

### 4. TensorFlow Issues 管理

#### 特点
- 📜 **RFC 机制** - 重大变更需要 RFC 讨论
- 🧠 **Google 内部使用** - 内部和外部双轨开发
- 🔄 **TFX 集成** - 生产级机器学习管道
- 📊 **大规模协作** - 数千贡献者
- 🎯 **RFC 流程**
  1. 提交 RFC Issue
  2. 社区讨论
  3. 达成共识
  4. 实现 PR
  5. 合并后关闭 RFC

```yaml
# TensorFlow RFC Issue 模板
name: RFC (Request for Comments)
title: "[RFC] "
labels: ["RFC", "type:process"]
body:
  - type: markdown
    attributes:
      value: |
        RFC 用于重大变更和技术决策讨论。

  - type: textarea
    id: summary
    attributes:
      label: Summary
      description: RFC 简要总结
      validations:
        required: true

  - type: textarea
    id: motivation
    attributes:
      label: Motivation
      description: 为什么需要这个变更？
      validations:
        required: true

  - type: textarea
    id: goals
    attributes:
      label: Goals
      description: 这个 RFC 的目标

  - type: textarea
    id: non_goals
    attributes:
      label: Non-Goals
      description: 这个 RFC 不涵盖什么

  - type: textarea
    id: proposed_solution
    attributes:
      label: Proposed Solution
      description: 详细的解决方案
      validations:
        required: true

  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives Considered
      description: 考虑过哪些替代方案？

  - type: textarea
    id: impact
    attributes:
      label: Impact
      description: 这个变更的影响范围
      placeholder: |
        - Breaking changes: ...
        - Backward compatibility: ...
        - Performance: ...
        - Documentation: ...

  - type: textarea
    id: implementation_plan
    attributes:
      label: Implementation Plan
      description: 如何实施

  - type: textarea
    id: unresolved_questions
    attributes:
      label: Unresolved Questions
      description: 还有哪些问题需要讨论
```

### 5. Rust 社区治理

#### 特点
- 🗳️ **民主决策** - RFC 投票机制
- 📋 **FCP (Final Comment Period)** - 最后意见征询期
- 🤝 **MCP (Major Change Proposal)** - 重大变更提案
- 👥 **团队管理** - 各个团队独立决策
- 🎯 **治理最佳实践**

#### RFC 流程

```python
class RustRFCBot:
    """Rust 风格的 RFC 机器人"""

    def __init__(self, gh_client, teams_client):
        self.gh = gh_client
        self.teams = teams_client

    def process_rfc(self, owner: str, repo: str, issue_number: int):
        """处理 RFC"""
        issue = self.gh.get_issue(owner, repo, issue_number)

        # 检查是否为 RFC
        if not self._is_rfc(issue):
            return

        # 添加 RFC 标签
        self.gh.add_labels(owner, repo, issue_number, ["RFC", "T-compiler"])

        # 请求相关团队审查
        self._request_team_review(owner, repo, issue_number, issue)

        # 设置 FCP 计时器
        self._schedule_fcp(owner, repo, issue_number)

    def _is_rfc(self, issue: Dict) -> bool:
        """检查是否为 RFC"""
        title = issue["title"].lower()
        return title.startswith("[rfc") or "rfc:" in title

    def _request_team_review(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        issue: Dict
    ):
        """请求团队审查"""
        # 根据关键词确定团队
        title = issue["title"].lower()
        body = issue["body"].lower() if issue["body"] else ""

        team_keywords = {
            "T-compiler": ["compiler", "llvm", "mir", "codegen"],
            "T-lang": ["language", "syntax", "macro", "trait"],
            "T-libs": ["library", "std", "collection"],
            "T-rustdoc": ["doc", "rustdoc"],
        }

        teams = []
        for team, keywords in team_keywords.items():
            if any(kw in title or kw in body for kw in keywords):
                teams.append(team)

        if teams:
            comment = "@"
            for team in teams:
                comment += f"{team} "
            comment += "\n\n这是一个 RFC，请团队审查。"

            self.gh.create_comment(owner, repo, issue_number, comment)

    def _schedule_fcp(self, owner: str, repo: str, issue_number: int):
        """安排 FCP"""
        # 10 天后进入 FCP
        fcp_date = datetime.now() + timedelta(days=10)

        # 提交 FCP 安排任务（实际实现需要外部调度系统）
        pass
```

---

## 自动化机器人

### 深度学习分类机器人

```python
import openai
from typing import List, Dict

class AIssueBot:
    """AI 驱动的 Issue 分类机器人"""

    def __init__(self, gh_client, openai_api_key: str):
        self.gh = gh_client
        openai.api_key = openai_api_key

    def classify_and_label(self, owner: str, repo: str, issue_number: int):
        """分类并标签 Issue"""
        issue = self.gh.get_issue(owner, repo, issue_number)

        # 准备分类文本
        text = f"Title: {issue['title']}\n\nBody: {issue.get('body', '')}"

        # AI 分类
        classification = self._classify_issue(text)

        # 应用标签
        self._apply_labels(owner, repo, issue_number, classification)

        # 自动分配
        self._auto_assign(owner, repo, issue_number, classification)

        # 提供总结
        self._post_summary(owner, repo, issue_number, classification)

    def _classify_issue(self, text: str) -> Dict:
        """使用 AI 分类 Issue"""
        prompt = f"""
分类以下 GitHub Issue，返回 JSON 格式：

{text}

返回格式：
{{
  "kind": "bug|feature|documentation|performance|security",
  "priority": "critical|high|medium|low",
  "component": "auth|api|ui|database|infra|other",
  "complexity": "small|medium|large|x-large",
  "estimated_hours": 数字,
  "summary": "简要总结"
}}
"""

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是 GitHub Issue 分类专家"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        result = response.choices[0].message.content

        # 解析 JSON
        import json
        return json.loads(result)

    def _apply_labels(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        classification: Dict
    ):
        """应用标签"""
        labels = [
            f"kind:{classification['kind']}",
            f"priority:{classification['priority']}",
            f"component:{classification['component']}",
            f"complexity:{classification['complexity']}"
        ]

        self.gh.add_labels(owner, repo, issue_number, labels)

    def _auto_assign(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        classification: Dict
    ):
        """自动分配"""
        # 组件负责人映射
        component_assignees = {
            "auth": ["alice"],
            "api": ["bob", "charlie"],
            "ui": ["david"],
            "database": ["eve"],
            "infra": ["frank"]
        }

        component = classification["component"]
        if component in component_assignees:
            assignees = component_assignees[component]
            # 选择负载最轻的成员（需要额外的负载跟踪）
            assignee = self._select_least_loaded(assignees)

            self.gh.update_issue(
                owner, repo, issue_number,
                assignees=[assignee]
            )

    def _select_least_loaded(self, assignees: List[str]) -> str:
        """选择负载最轻的成员"""
        # 简化版本：随机选择
        # 实际实现需要查询每个成员的开放 Issue 数量
        return assignees[0]

    def _post_summary(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        classification: Dict
    ):
        """发布 AI 总结"""
        summary = f"""
## 🤖 AI 分类结果

- **类型**: {classification['kind']}
- **优先级**: {classification['priority']}
- **组件**: {classification['component']}
- **复杂度**: {classification['complexity']}
- **预估时间**: {classification['estimated_hours']} 小时

### 总结
{classification['summary']}

---
*由 AIssueBot 自动分类*
"""

        self.gh.create_comment(owner, repo, issue_number, summary)
```

### SLA 监控机器人

```python
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler

class SLAMonitorBot:
    """SLA 监控机器人"""

    def __init__(self, gh_client):
        self.gh = gh_client
        self.scheduler = BlockingScheduler()

        # SLA 配置（小时）
        self.sla_config = {
            "priority:critical": {"response": 4, "resolution": 24},
            "priority:high": {"response": 8, "resolution": 72},
            "priority:medium": {"response": 24, "resolution": 168},
            "priority:low": {"response": 72, "resolution": 336}
        }

    def start(self):
        """启动监控"""
        # 每 5 分钟检查一次
        self.scheduler.add_job(
            self.check_sla,
            'interval',
            minutes=5,
            id='sla_check'
        )

        self.scheduler.start()

    def check_sla(self):
        """检查 SLA"""
        # 获取所有仓库
        repos = self._get_monitored_repos()

        for repo in repos:
            owner, name = repo.split("/")

            # 获取开放 Issues
            issues = self.gh.list_issues(owner, name, state="open")

            for issue in issues:
                self._check_issue_sla(owner, name, issue)

    def _check_issue_sla(self, owner: str, repo: str, issue: Dict):
        """检查单个 Issue 的 SLA"""
        # 提取优先级标签
        priority_label = self._get_priority_label(issue)

        if not priority_label:
            return

        # 获取 SLA 配置
        sla = self.sla_config.get(priority_label)
        if not sla:
            return

        # 计算已用时间
        created = datetime.fromisoformat(issue["created_at"].replace("Z", ""))
        now = datetime.now()
        hours_since_creation = (now - created).total_seconds() / 3600

        # 检查响应 SLA
        if not issue["assignees"] or len(issue["assignees"]) == 0:
            if hours_since_creation > sla["response"]:
                self._send_sla_alert(
                    owner, repo, issue["number"],
                    "response", sla["response"], hours_since_creation
                )

        # 检查解决 SLA
        if issue["state"] == "open":
            if hours_since_creation > sla["resolution"]:
                self._send_sla_alert(
                    owner, repo, issue["number"],
                    "resolution", sla["resolution"], hours_since_creation
                )

    def _get_priority_label(self, issue: Dict) -> str:
        """获取优先级标签"""
        for label in issue["labels"]:
            if label["name"].startswith("priority:"):
                return label["name"]
        return None

    def _send_sla_alert(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        sla_type: str,
        sla_hours: int,
        actual_hours: float
    ):
        """发送 SLA 警报"""
        sla_name = "响应" if sla_type == "response" else "解决"

        comment = f"""
## ⚠️ SLA 警报

**{sla_name} SLA 已超时**

- **SLA**: {sla_hours} 小时
- **实际**: {actual_hours:.1f} 小时
- **超时**: {actual_hours - sla_hours:.1f} 小时

@maintainers 请立即处理此 Issue！
"""

        self.gh.create_comment(owner, repo, issue_number, comment)

        # 添加 SLA 违规标签
        self.gh.add_labels(owner, repo, issue_number, ["sla-violation"])

    def _get_monitored_repos(self) -> List[str]:
        """获取监控的仓库列表"""
        # 从配置文件或数据库读取
        return ["owner/repo1", "owner/repo2"]
```

---

## 最佳实践总结

### Issue 创建最佳实践

#### ✅ 标题编写

```markdown
好的标题:
- [BUG] 登录页面在 Safari 14 中崩溃
- [Feature] 添加深色模式支持
- [Performance] 数据库查询优化 - 减少 API 响应时间
- [Security] 修复 XSS 漏洞在用户输入处

不好的标题:
- 有问题 ❌
- Help me ❌
- Bug ❌
- ？？？ ❌
```

#### ✅ 描述编写

```markdown
## 结构化的 Issue 描述

### 问题描述
清晰、简洁地描述问题。

### 复现步骤
1. 第一步
2. 第二步
3. 第三步

### 期望行为
期望发生什么

### 实际行为
实际发生了什么

### 环境信息
- OS: [例如 macOS 14.0]
- Browser: [例如 Chrome 120]
- Version: [例如 v2.1.0]

### 日志信息
<details>
<summary>点击展开日志</summary>

```
日志内容
```
</details>
```

### Issue 管理最佳实践

#### 定期维护

```bash
# 每周维护脚本

# 1. 标记过时的 Issues
gh issue list --repo owner/repo --state open \
  --search "updated:<30-days-ago" \
  --json number \
  --jq '.[].number' | \
  xargs -I {} gh issue edit {} --add-label "stale"

# 2. 清理重复 Issues
# 使用 GitHub Actions 或手动审查

# 3. 更新 Milestone
gh issue list --repo owner/repo --state open \
  --json number,milestone \
  --jq '.[] | select(.milestone == null) | .number'

# 4. 生成周报
gh issue list --repo owner/repo \
  --search "created:2024-03-18..2024-03-25"
```

### 社区参与最佳实践

#### 贡献者培养

```yaml
新贡献者入门:
  1. 标记 "good first issue"
  2. 提供详细指导
  3. 指定 Mentor
  4. 快速反馈
  5. 公开认可

成为维护者:
  1. 持续贡献（3+ 月）
  2. 高质量 PR（10+）
  3. 审查他人 PR
  4. 参与 RFC 讨论
  5. 提议并投票
```

#### 冲突处理

```
1. 保持尊重
2. 聚焦问题，不针对个人
3. 寻求共同点
4. 必要时引入第三方调解
5. 遵循行为准则
```

---

## 总结

GitHub Issues 生态系统提供了丰富的工具和最佳实践：

**核心工具**:
- ✅ GitHub CLI - 强大的命令行工具
- ✅ GraphQL/REST API - 完整的编程接口
- ✅ GitHub Actions - 自动化工作流

**第三方集成**:
- ✅ ZenHub - 敏捷项目管理
- ✅ Jira - 企业级项目管理
- ✅ Linear - 现代 Issue 追踪

**大型项目经验**:
- ✅ Kubernetes - SIG 机制和自动化
- ✅ Linux 内核 - 邮件列表工作流
- ✅ VS Code - API 驱动开发
- ✅ TensorFlow - RFC 机制
- ✅ Rust - 民主决策

**自动化**:
- ✅ AI 分类
- ✅ SLA 监控
- ✅ 自动分配
- ✅ 智能推荐

通过学习这些最佳实践，可以构建高效的 Issue 管理系统，提升团队协作效率和代码质量。
