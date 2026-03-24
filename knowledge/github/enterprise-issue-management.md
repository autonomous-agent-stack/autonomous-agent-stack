# 企业级 Issue 管理方案

## 目录

1. [多仓库协调](#多仓库协调)
2. [团队协作](#团队协作)
3. [合规和审计](#合规和审计)
4. [性能优化](#性能优化)
5. [监控和报告](#监控和报告)
6. [灾难恢复](#灾难恢复)

---

## 多仓库协调

### 跨仓库 Issue 追踪

#### 主-从仓库模式

```python
class MultiRepoIssueManager:
    """多仓库 Issue 管理器"""

    def __init__(self, gh_client, main_repo: str):
        self.gh = gh_client
        self.main_repo = main_repo
        self.repos = []

    def add_repo(self, repo: str):
        """添加管理的仓库"""
        self.repos.append(repo)

    def create_cross_repo_issue(
        self,
        title: str,
        body: str,
        labels: List[str] = None,
        assignees: List[str] = None
    ) -> Dict:
        """创建跨仓库 Issue"""
        # 在主仓库创建主 Issue
        main_issue = self.gh.create_issue(
            *self.main_repo.split("/"),
            title=f"[Cross-Repo] {title}",
            body=body,
            labels=labels or [],
            assignees=assignees or []
        )

        # 在所有子仓库创建链接 Issue
        child_issues = []
        for repo in self.repos:
            child_body = f"""
**主 Issue**: {main_issue['html_url']}

{body}

---
*此 Issue 跟踪主仓库 Issue #{main_issue['number']} 的进度*
"""
            child_issue = self.gh.create_issue(
                *repo.split("/"),
                title=title,
                body=child_body,
                labels=["cross-repo"] + (labels or [])
            )

            child_issues.append({
                "repo": repo,
                "issue_number": child_issue["number"]
            })

        # 在主 Issue 添加子 Issue 链接
        links = "\n".join([
            f"- [{repo}#{issue['issue_number']}](https://github.com/{repo}/issues/{issue['issue_number']})"
            for repo, issue in zip(self.repos, child_issues)
        ])

        self.gh.create_comment(
            *self.main_repo.split("/"),
            main_issue["number"],
            f"## 子仓库 Issues\n\n{links}"
        )

        return {
            "main_issue": main_issue,
            "child_issues": child_issues
        }

    def sync_issue_status(
        self,
        source_repo: str,
        issue_number: int,
        status: str
    ):
        """同步 Issue 状态到其他仓库"""
        issue = self.gh.get_issue(*source_repo.split("/"), issue_number)

        # 检查是否为跨仓库 Issue
        if not self._is_cross_repo_issue(issue):
            return

        # 获取所有相关的跨仓库 Issues
        related_issues = self._get_related_issues(issue)

        # 同步状态
        for related in related_issues:
            if status == "closed":
                self.gh.close_issue(
                    *related["repo"].split("/"),
                    related["number"]
                )
            elif status == "open":
                # GitHub API 不直接支持 reopen，使用 update
                self.gh.update_issue(
                    *related["repo"].split("/"),
                    related["number"],
                    state="open"
                )

    def _is_cross_repo_issue(self, issue: Dict) -> bool:
        """检查是否为跨仓库 Issue"""
        body = issue.get("body", "").lower()
        return "cross-repo" in body or "主 issue" in body

    def _get_related_issues(self, issue: Dict) -> List[Dict]:
        """获取相关的跨仓库 Issues"""
        # 从 Issue 评论中提取链接
        comments = self.gh.list_comments(
            *issue["repository_url"].split("/")[-2:],
            issue["number"]
        )

        related = []
        for comment in comments:
            # 解析评论中的 Issue 链接
            # (实际实现需要更复杂的解析)
            pass

        return related
```

#### 统一分类标准

```yaml
# .github/labels-standard.yml
# 企业级统一标签标准

# 所有仓库必须使用的核心标签
core_labels:
  kind:
    - name: kind:bug
      color: "d73a4a"
      description: Bug 修复
    - name: kind:feature
      color: "a2eeef"
      description: 新功能
    - name: kind:documentation
      color: "0075ca"
      description: 文档改进
    - name: kind:performance
      color: "fbca04"
      description: 性能优化
    - name: kind:security
      color: "02f0bd"
      description: 安全问题

  priority:
    - name: priority:critical
      color: "b60205"
      description: 阻塞性问题，立即处理
    - name: priority:high
      color: "ff6b00"
      description: 高优先级，本周处理
    - name: priority:medium
      color: "ffd700"
      description: 中优先级，本迭代处理
    - name: priority:low
      color: "cfd3d7"
      description: 低优先级，有空再处理

  status:
    - name: status:needs-triage
      color: "eeeeee"
      description: 待分类
    - name: status:confirmed
      color: "bfd4f2"
      description: 已确认
    - name: status:in-progress
      color: "7057ff"
      description: 处理中
    - name: status:in-review
      color: "5319e7"
      description: 审查中
    - name: status:blocked
      color: "d4c5f9"
      description: 被阻塞
    - name: status:ready-to-merge
      color: "0e8a16"
      description: 待合并

# 可选的扩展标签（根据项目需求）
extension_labels:
  team:
    - name: team:frontend
      color: "ff7b72"
    - name: team:backend
      color: "79c0ff"
    - name: team:infra
      color: "ffa657"
    - name: team:data
      color: "7ee787"

  component:
    - name: component:auth
      color: "d2a8ff"
    - name: component:api
      color: "a5d6ff"
    - name: component:database
      color: "c5def5"
    - name: component:ui
      color: "f0f6fc"

  complexity:
    - name: complexity:small
      color: "c2e0c6"
      description: "< 2 小时"
    - name: complexity:medium
      color: "9be9a8"
      description: "2-8 小时"
    - name: complexity:large
      color: "40c463"
      description: "1-3 天"
    - name: complexity:x-large
      color: "2ea043"
      description: "> 3 天"
```

#### 全局搜索和过滤

```python
class EnterpriseSearch:
    """企业级 Issue 搜索"""

    def __init__(self, gh_client, org: str):
        self.gh = gh_client
        self.org = org

    def search_all_repos(
        self,
        query: str,
        state: str = "open",
        sort: str = "created",
        order: str = "desc"
    ) -> List[Dict]:
        """搜索所有仓库的 Issues"""
        search_query = f"org:{self.org} {query} state:{state}"

        results = self.gh.search_issues(
            query=search_query,
            sort=sort,
            order=order
        )

        return results["items"]

    def get_org_metrics(self) -> Dict:
        """获取组织级指标"""
        # 搜索所有开放 Issues
        open_issues = self.search_all_repos("", state="open")
        closed_issues = self.search_all_repos("", state="closed")

        # 按仓库分组
        by_repo = {}
        for issue in open_issues:
            repo_name = issue["repository_url"].split("/")[-1]
            if repo_name not in by_repo:
                by_repo[repo_name] = {"open": 0, "closed": 0}
            by_repo[repo_name]["open"] += 1

        for issue in closed_issues:
            repo_name = issue["repository_url"].split("/")[-1]
            if repo_name not in by_repo:
                by_repo[repo_name] = {"open": 0, "closed": 0}
            by_repo[repo_name]["closed"] += 1

        return {
            "total_open": len(open_issues),
            "total_closed": len(closed_issues),
            "by_repo": by_repo
        }

    def find_duplicate_issues(self, similarity_threshold: float = 0.8):
        """查找重复 Issues（跨仓库）"""
        # 获取最近的所有 Issues
        recent_issues = self.search_all_repos(
            "created:>2024-01-01",
            state="all"
        )

        # 计算相似度（简化版）
        duplicates = []
        for i, issue1 in enumerate(recent_issues):
            for issue2 in recent_issues[i+1:]:
                similarity = self._calculate_similarity(
                    issue1["title"],
                    issue2["title"]
                )

                if similarity >= similarity_threshold:
                    duplicates.append({
                        "issue1": issue1,
                        "issue2": issue2,
                        "similarity": similarity
                    })

        return duplicates

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（简化实现）"""
        # 实际应用应使用更复杂的算法（如 TF-IDF、word2vec 等）
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0
```

---

## 团队协作

### 权限隔离

```python
class TeamAccessManager:
    """团队权限管理器"""

    def __init__(self, gh_client, org: str):
        self.gh = gh_client
        self.org = org

    def setup_team_permissions(self, teams_config: Dict):
        """设置团队权限"""
        for team_name, config in teams_config.items():
            # 创建团队
            team = self._create_team(team_name, config["description"])

            # 设置仓库权限
            for repo_config in config["repos"]:
                self._set_team_repo_permission(
                    team["id"],
                    repo_config["name"],
                    repo_config["permission"]
                )

            # 添加成员
            for member in config["members"]:
                self._add_team_member(team["slug"], member)

    def _create_team(self, name: str, description: str) -> Dict:
        """创建团队"""
        return self.gh.create_team(
            self.org,
            name,
            description=description
        )

    def _set_team_repo_permission(
        self,
        team_id: str,
        repo: str,
        permission: str
    ):
        """设置团队仓库权限"""
        # permission: pull, triage, push, maintain, admin
        self.gh.set_team_repo_permission(
            team_id,
            f"{self.org}/{repo}",
            permission
        )

    def _add_team_member(self, team_slug: str, username: str):
        """添加团队成员"""
        self.gh.add_team_member(
            self.org,
            team_slug,
            username
        )
```

#### 权限矩阵示例

| 团队 | Repo A | Repo B | Repo C | 描述 |
|------|--------|--------|--------|------|
| **frontend** | Admin | Push | Pull | 前端团队 |
| **backend** | Pull | Admin | Push | 后端团队 |
| **infra** | Pull | Pull | Admin | 基础设施团队 |
| **qa** | Triage | Triage | Triage | 测试团队 |
| **managers** | Admin | Admin | Admin | 管理层 |

### 审批流程

```python
class ApprovalWorkflow:
    """审批工作流"""

    def __init__(self, gh_client):
        self.gh = gh_client

    def require_approval(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        required_approvers: List[str],
        min_approvals: int
    ):
        """要求审批"""
        # 添加 "needs-approval" 标签
        self.gh.add_labels(
            owner, repo, issue_number,
            ["needs-approval"]
        )

        # 提交审批请求
        approvers = " ".join([f"@{u}" for u in required_approvers])
        comment = f"""
## 🔒 需要审批

此 Issue 需要至少 {min_approvals} 位以下成员审批：

{approvers}

请审批者回复 `/approve` 批准，或 `/reject` 拒绝。

---
*当前审批进度: 0/{min_approvals}*
"""
        self.gh.create_comment(owner, repo, issue_number, comment)

    def process_approval_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        commenter: str,
        comment_body: str
    ):
        """处理审批评论"""
        issue = self.gh.get_issue(owner, repo, issue_number)

        # 检查是否需要审批
        if not self._needs_approval(issue):
            return

        # 处理命令
        if comment_body.strip() == "/approve":
            self._add_approval(owner, repo, issue_number, commenter)
        elif comment_body.strip() == "/reject":
            self._reject_approval(owner, repo, issue_number, commenter)

    def _add_approval(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        approver: str
    ):
        """添加审批"""
        # 添加 "approved-by-{username}" 标签
        self.gh.add_labels(
            owner, repo, issue_number,
            [f"approved-by-{approver}"]
        )

        # 检查是否达到最低审批数
        issue = self.gh.get_issue(owner, repo, issue_number)
        approval_labels = [
            l for l in issue["labels"]
            if l["name"].startswith("approved-by-")
        ]

        if len(approval_labels) >= self._get_min_approvals(issue):
            # 移除 needs-approval 标签
            self.gh.remove_label(owner, repo, issue_number, "needs-approval")

            # 添加 approved 标签
            self.gh.add_labels(owner, repo, issue_number, ["approved"])

            # 通知
            self.gh.create_comment(
                owner, repo, issue_number,
                "✅ 审批通过！此 Issue 已获准继续。"
            )

    def _reject_approval(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        rejecter: str
    ):
        """拒绝审批"""
        # 添加 rejected 标签
        self.gh.add_labels(owner, repo, issue_number, ["rejected"])

        # 通知
        self.gh.create_comment(
            owner, repo, issue_number,
            f"❌ 审批被 @{rejecter} 拒绝。请重新评估此 Issue。"
        )

    def _needs_approval(self, issue: Dict) -> bool:
        """检查是否需要审批"""
        return any(
            l["name"] == "needs-approval"
            for l in issue["labels"]
        )

    def _get_min_approvals(self, issue: Dict) -> int:
        """获取最低审批数（从 Issue body 或评论中解析）"""
        # 简化实现，实际应解析 Issue 内容
        return 2
```

### 工作分配

```python
class WorkAssignmentManager:
    """工作分配管理器"""

    def __init__(self, gh_client):
        self.gh = gh_client

    def auto_assign_by_workload(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        team_members: List[str]
    ):
        """根据工作负载自动分配"""
        # 计算每个成员的当前负载
        workloads = {}
        for member in team_members:
            open_issues = self.gh.search_issues(
                f"repo:{owner}/{repo} assignee:{member} state:open"
            )
            workloads[member] = len(open_issues)

        # 选择负载最轻的成员
        assignee = min(workloads.items(), key=lambda x: x[1])[0]

        # 分配
        self.gh.update_issue(
            owner, repo, issue_number,
            assignees=[assignee]
        )

        # 评论
        self.gh.create_comment(
            owner, repo, issue_number,
            f"👤 自动分配给 @{assignee}（当前负载: {workloads[assignee]} 个开放 Issues）"
        )

    def assign_by_skill_match(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        skill_tree: Dict
    ):
        """根据技能匹配分配"""
        issue = self.gh.get_issue(owner, repo, issue_number)

        # 提取关键词
        keywords = self._extract_keywords(issue)

        # 匹配技能
        scores = {}
        for member, skills in skill_tree.items():
            score = 0
            for keyword in keywords:
                if keyword in skills:
                    score += skills[keyword]
            scores[member] = score

        # 选择得分最高的成员
        if scores:
            assignee = max(scores.items(), key=lambda x: x[1])[0]

            self.gh.update_issue(
                owner, repo, issue_number,
                assignees=[assignee]
            )

    def _extract_keywords(self, issue: Dict) -> List[str]:
        """从 Issue 提取关键词"""
        # 简化实现：从标题和标签提取
        keywords = []

        # 从标签
        for label in issue["labels"]:
            if label["name"].startswith("component:"):
                component = label["name"].split(":")[1]
                keywords.append(component)

        # 从标题
        title_words = issue["title"].lower().split()
        keywords.extend(title_words)

        return keywords
```

---

## 合规和审计

### 审计日志

```python
class IssueAuditLogger:
    """Issue 审计日志记录器"""

    def __init__(self, gh_client, storage_backend):
        self.gh = gh_client
        self.storage = storage_backend

    def log_issue_event(
        self,
        event_type: str,
        owner: str,
        repo: str,
        issue_number: int,
        actor: str,
        details: Dict = None
    ):
        """记录 Issue 事件"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "repository": f"{owner}/{repo}",
            "issue_number": issue_number,
            "actor": actor,
            "details": details or {}
        }

        # 存储到审计日志
        self.storage.write("issue_audit", event)

    def audit_all_events(self, owner: str, repo: str):
        """审计仓库的所有 Issue 事件"""
        # 获取所有 Issues
        issues = self.gh.list_issues(owner, repo, state="all")

        for issue in issues:
            # 记录创建事件
            self.log_issue_event(
                "created",
                owner, repo, issue["number"],
                issue["user"]["login"],
                {"title": issue["title"]}
            )

            # 获取 Issue 时间线
            timeline = self.gh.get_issue_timeline(owner, repo, issue["number"])

            for event in timeline:
                self.log_issue_event(
                    event["event"],
                    owner, repo, issue["number"],
                    event["actor"]["login"] if event.get("actor") else "system",
                    event
                )

    def generate_audit_report(
        self,
        owner: str,
        repo: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """生成审计报告"""
        # 查询审计日志
        events = self.storage.query(
            "issue_audit",
            filters={
                "repository": f"{owner}/{repo}",
                "timestamp": {
                    "$gte": start_date.isoformat(),
                    "$lte": end_date.isoformat()
                }
            }
        )

        # 统计
        report = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_events": len(events),
            "by_event_type": {},
            "by_actor": {},
            "by_issue": {}
        }

        for event in events:
            # 按事件类型统计
            event_type = event["event_type"]
            report["by_event_type"][event_type] = \
                report["by_event_type"].get(event_type, 0) + 1

            # 按操作者统计
            actor = event["actor"]
            report["by_actor"][actor] = \
                report["by_actor"].get(actor, 0) + 1

            # 按 Issue 统计
            issue_key = f"{event['issue_number']}"
            report["by_issue"][issue_key] = \
                report["by_issue"].get(issue_key, 0) + 1

        return report
```

### 数据保留策略

```python
class DataRetentionPolicy:
    """数据保留策略管理器"""

    def __init__(self, gh_client, storage_backend):
        self.gh = gh_client
        self.storage = storage_backend

    def enforce_retention_policy(self, policy: Dict):
        """执行保留策略"""
        # 策略示例:
        # {
        #     "closed_issues": {
        #         "retention_days": 365,
        #         "action": "archive"  # or "delete"
        #     },
        #     "comments": {
        #         "retention_days": 180,
        #         "action": "delete"
        #     }
        # }

        for repo in policy["repositories"]:
            owner, repo_name = repo.split("/")

            # 处理已关闭的 Issues
            if "closed_issues" in policy:
                self._handle_closed_issues(
                    owner, repo_name,
                    policy["closed_issues"]
                )

            # 处理评论
            if "comments" in policy:
                self._handle_old_comments(
                    owner, repo_name,
                    policy["comments"]
                )

    def _handle_closed_issues(
        self,
        owner: str,
        repo: str,
        policy: Dict
    ):
        """处理已关闭的 Issues"""
        retention_days = policy["retention_days"]
        action = policy["action"]

        # 查找超过保留期的已关闭 Issues
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        issues = self.gh.search_issues(
            f"repo:{owner}/{repo} state:closed closed:<{cutoff_date.isoformat()}"
        )

        for issue in issues:
            if action == "archive":
                # 锁定并标记为已归档
                self.gh.lock_issue(owner, repo, issue["number"])
                self.gh.add_labels(
                    owner, repo, issue["number"],
                    ["archived"]
                )

            elif action == "delete":
                # 删除 Issue（谨慎操作）
                self.gh.delete_issue(owner, repo, issue["number"])

            # 记录审计日志
            self.storage.write("retention_actions", {
                "action": action,
                "issue_number": issue["number"],
                "repository": f"{owner}/{repo}",
                "timestamp": datetime.now().isoformat()
            })

    def _handle_old_comments(
        self,
        owner: str,
        repo: str,
        policy: Dict
    ):
        """处理旧评论"""
        # (实现类似)
        pass
```

---

## 性能优化

### 批量操作优化

```python
class BulkIssueOperations:
    """批量 Issue 操作优化器"""

    def __init__(self, gh_client):
        self.gh = gh_client

    def bulk_update_labels(
        self,
        owner: str,
        repo: str,
        issue_numbers: List[int],
        add_labels: List[str] = None,
        remove_labels: List[str] = None
    ):
        """批量更新标签"""
        # 使用 GraphQL 批量更新（比 REST API 快）
        mutation = """
        mutation($input: UpdateIssuesInput!) {
          updateIssues(input: $input) {
            issues {
              number
              labels(first: 20) {
                nodes {
                  name
                }
              }
            }
          }
        }
        """

        # GitHub GraphQL API 有批量限制
        batch_size = 10

        for i in range(0, len(issue_numbers), batch_size):
            batch = issue_numbers[i:i+batch_size]

            # 执行批量更新
            # (实际实现需要构建正确的 GraphQL mutation)
            pass

    def bulk_close_issues(
        self,
        owner: str,
        repo: str,
        issue_numbers: List[int],
        comment: str = None
    ):
        """批量关闭 Issues"""
        for issue_number in issue_numbers:
            self.gh.close_issue(owner, repo, issue_number)

            if comment:
                self.gh.create_comment(
                    owner, repo, issue_number, comment
                )

            # 避免 rate limiting
            time.sleep(0.5)

    def bulk_transfer_issues(
        self,
        source_owner: str,
        source_repo: str,
        target_owner: str,
        target_repo: str,
        issue_numbers: List[int]
    ):
        """批量转移 Issues 到其他仓库"""
        for issue_number in issue_numbers:
            issue = self.gh.get_issue(source_owner, source_repo, issue_number)

            # 在目标仓库创建新 Issue
            new_issue = self.gh.create_issue(
                target_owner, target_repo,
                title=issue["title"],
                body=f"""
**转移自**: {issue['html_url']}

{issue.get('body', '')}

---
*此 Issue 从 {source_owner}/{source_repo} 转移*
""",
                labels=[l["name"] for l in issue["labels"]],
                assignees=[a["login"] for a in issue.get("assignees", [])]
            )

            # 在原 Issue 添加链接
            self.gh.create_comment(
                source_owner, source_repo, issue_number,
                f"此 Issue 已转移到: {new_issue['html_url']}"
            )

            # 关闭原 Issue
            self.gh.close_issue(source_owner, source_repo, issue_number)
```

---

## 监控和报告

### 实时监控仪表板

```python
from flask import Flask, jsonify, render_template

app = Flask(__name__)

class IssueMonitoringDashboard:
    """Issue 监控仪表板"""

    def __init__(self, gh_client):
        self.gh = gh_client

    def get_dashboard_data(self, org: str) -> Dict:
        """获取仪表板数据"""
        return {
            "metrics": self._get_metrics(org),
            "sla_status": self._check_sla_status(org),
            "team_workload": self._get_team_workload(org),
            "recent_activity": self._get_recent_activity(org)
        }

    def _get_metrics(self, org: str) -> Dict:
        """获取关键指标"""
        # 搜索所有仓库的 Issues
        open_issues = self.gh.search_issues(f"org:{org} state:open")
        closed_today = self.gh.search_issues(
            f"org:{org} state:closed closed:>today"
        )

        return {
            "total_open": len(open_issues),
            "closed_today": len(closed_today),
            "avg_close_time": self._calculate_avg_close_time(org),
            "by_priority": self._group_by_priority(open_issues),
            "by_kind": self._group_by_kind(open_issues)
        }

    def _check_sla_status(self, org: str) -> Dict:
        """检查 SLA 状态"""
        # 查找 SLA 违规的 Issues
        sla_violations = self.gh.search_issues(
            f"org:{org} state:open label:sla-violation"
        )

        return {
            "violations": len(sla_violations),
            "issues": sla_violations[:10]  # 最近的 10 个
        }

    def _get_team_workload(self, org: str) -> Dict:
        """获取团队工作负载"""
        # 按团队成员分组
        members = self._get_org_members(org)

        workloads = {}
        for member in members:
            open_issues = self.gh.search_issues(
                f"org:{org} assignee:{member} state:open"
            )
            workloads[member] = len(open_issues)

        return {
            "by_member": workloads,
            "avg_workload": sum(workloads.values()) / len(workloads) if workloads else 0
        }

    def _get_recent_activity(self, org: str, limit: int = 50) -> List[Dict]:
        """获取最近活动"""
        # 使用 GraphQL API 获取最近事件
        query = """
        query($org: String!, $limit: Int!) {
          organization(login: $org) {
            repositories(first: 20) {
              nodes {
                name
                issues(first: $limit, states: [OPEN], orderBy: {field: CREATED_AT, direction: DESC}) {
                  nodes {
                    number
                    title
                    createdAt
                    author {
                      login
                    }
                  }
                }
              }
            }
          }
        }
        """

        # 执行查询
        # (实际实现)
        return []
```

---

## 灾难恢复

### Issue 备份和恢复

```python
import json
import gzip

class IssueBackupManager:
    """Issue 备份管理器"""

    def __init__(self, gh_client, backup_storage):
        self.gh = gh_client
        self.storage = backup_storage

    def backup_repo(self, owner: str, repo: str):
        """备份仓库的所有 Issues"""
        # 获取所有 Issues
        issues = self.gh.list_issues(owner, repo, state="all", per_page=100)

        backup_data = {
            "repository": f"{owner}/{repo}",
            "backup_date": datetime.now().isoformat(),
            "issues": []
        }

        for issue in issues:
            # 获取完整 Issue 数据
            full_issue = self.gh.get_issue(owner, repo, issue["number"])

            # 获取评论
            comments = self.gh.list_comments(owner, repo, issue["number"])

            # 获取时间线
            timeline = self.gh.get_issue_timeline(owner, repo, issue["number"])

            backup_data["issues"].append({
                "issue": full_issue,
                "comments": comments,
                "timeline": timeline
            })

        # 压缩并存储
        backup_json = json.dumps(backup_data)
        compressed = gzip.compress(backup_json.encode())

        backup_path = f"backups/{owner}/{repo}/{datetime.now().strftime('%Y%m%d')}.json.gz"
        self.storage.write(backup_path, compressed)

        return backup_path

    def restore_repo(
        self,
        owner: str,
        repo: str,
        backup_path: str
    ):
        """恢复仓库 Issues"""
        # 读取备份
        compressed = self.storage.read(backup_path)
        backup_json = gzip.decompress(compressed).decode()
        backup_data = json.loads(backup_json)

        # 恢复 Issues
        for item in backup_data["issues"]:
            issue = item["issue"]

            # 创建新 Issue
            new_issue = self.gh.create_issue(
                owner, repo,
                title=issue["title"],
                body=issue.get("body", ""),
                labels=[l["name"] for l in issue["labels"]],
                assignees=[a["login"] for a in issue.get("assignees", [])]
            )

            # 恢复评论
            for comment in item["comments"]:
                self.gh.create_comment(
                    owner, repo,
                    new_issue["number"],
                    comment["body"]
                )

            # 如果原 Issue 已关闭，关闭新 Issue
            if issue["state"] == "closed":
                self.gh.close_issue(owner, repo, new_issue["number"])

        print(f"恢复完成: {len(backup_data['issues'])} 个 Issues")
```

---

## 总结

企业级 Issue 管理需要考虑:

✅ **多仓库协调** - 统一标准、全局搜索、跨仓库追踪
✅ **权限管理** - 细粒度权限、团队隔离、审批流程
✅ **合规审计** - 审计日志、数据保留、风险控制
✅ **性能优化** - 批量操作、缓存策略、API 优化
✅ **监控报告** - 实时监控、SLA 追踪、定期报告
✅ **灾难恢复** - 定期备份、快速恢复、业务连续性

通过系统化的企业级 Issue 管理，可以提升团队协作效率，降低风险，确保业务连续性。
