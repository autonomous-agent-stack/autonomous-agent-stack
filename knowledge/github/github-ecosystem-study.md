# GitHub 工具链生态完整研究

## 目录

1. [官方工具生态](#官方工具生态)
2. [第三方集成工具](#第三方集成工具)
3. [浏览器扩展生态](#浏览器扩展生态)
4. [CI/CD 集成](#cicd-集成)
5. [大型项目案例分析](#大型项目案例分析)
6. [自动化机器人](#自动化机器人)
7. [最佳实践总结](#最佳实践总结)

---

## 官方工具生态

### GitHub CLI (gh)

#### 完整命令参考

```bash
# ========== 认证 ==========
gh auth login                    # 登录
gh auth status                   # 查看认证状态
gh auth logout                   # 登出
gh auth token                    # 获取 token
gh auth refresh                  # 刷新 token
gh auth git-credential           # 配置 git 凭据

# ========== Issue 管理 ==========
gh issue list                    # 列出 Issues
gh issue list --state open       # 仅开放的 Issues
gh issue list --state closed     # 已关闭的 Issues
gh issue list --limit 100        # 限制数量
gh issue list --search "label:bug"  # 搜索

gh issue view 42                 # 查看 Issue
gh issue view 42 --json title,body,labels  # JSON 输出
gh issue view 42 --jq '.title'   # JSON 查询

gh issue create                  # 创建 Issue（交互式）
gh issue create --title "Bug" --body "Details"  # 直接创建
gh issue create --label bug,high  # 添加标签

gh issue edit 42                 # 编辑 Issue
gh issue edit 42 --add-label "in-progress"
gh issue edit 42 --remove-label "needs-triage"
gh issue edit 42 --assignee "@me"
gh issue edit 42 --milestone "v1.0"

gh issue close 42                # 关闭 Issue
gh issue close 42 --comment "Fixed"
gh issue reopen 42               # 重新打开

gh issue lock 42                 # 锁定 Issue
gh issue lock 42 --reason "spam"  # spam/off-topic/resolved/too heated
gh issue unlock 42               # 解锁

gh issue delete 42               # 删除 Issue（仅管理员）

gh issue convert 42              # 转换为 Issue

# ========== PR 管理 ==========
gh pr list                       # 列出 PRs
gh pr list --state open          # 开放的 PRs
gh pr list --search "label:review-required"  # 搜索

gh pr view 123                   # 查看 PR
gh pr view 123 --json title,body,author,additions,deletions

gh pr diff 123                   # 查看 diff
gh pr diff 123 --color never     # 无颜色

gh pr create                     # 创建 PR（交互式）
gh pr create --title "Feature" --body "Description"
gh pr create --base main --head feature-branch

gh pr checkout 123               # 检出 PR 分支
gh pr merge 123                  # 合并 PR
gh pr merge 123 --squash         # squash merge
gh pr merge 123 --rebase         # rebase merge
gh pr merge 123 --merge          # merge commit
gh pr merge 123 --delete-branch  # 合并后删除分支

gh pr close 123                  # 关闭 PR
gh pr reopen 123                 # 重新打开

gh pr checks 123                 # 查看 CI 状态
gh pr checks 123 --watch         # 监控 CI 状态

gh pr review 123                 # 审查 PR
gh pr review 123 --approve       # 批准
gh pr review 123 --request-changes  # 请求变更
gh pr review 123 --comment       # 评论

gh pr diff 123                   # 查看变更

# ========== Runner 和 Workflow ==========
gh run list                      # 列出 workflow runs
gh run list --limit 10

gh run view 456                  # 查看 run 详情
gh run view 456 --log            # 查看日志
gh run view 456 --log-failed     # 仅失败日志

gh run watch 456                 # 监控 run
gh run watch 456 --interval 5    # 5 秒刷新

gh run rerun 456                 # 重新运行
gh run rerun 456 --failed        # 仅重新运行失败的 job

gh run cancel 456                # 取消运行

# ========== Repository 管理 ==========
gh repo view                     # 查看仓库信息
gh repo view owner/repo

gh repo create                   # 创建仓库
gh repo create my-repo --public
gh repo create my-repo --private --source=.

gh repo clone owner/repo         # 克隆仓库
gh repo clone owner/repo --clone-with-ssh

gh repo fork                     # Fork 仓库
gh repo fork owner/repo

# ========== Release 管理 ==========
gh release list                  # 列出 releases
gh release view latest           # 查看最新 release

gh release create v1.0.0         # 创建 release
gh release create v1.0.0 \
  --title "Version 1.0.0" \
  --notes "Release notes" \
  --assets ./artifact.tar.gz

gh release delete v1.0.0         # 删除 release

# ========== API 查询 ==========
gh api /user                     # REST API 查询
gh api /repos/owner/repo/issues
gh api /repos/owner/repo/issues --jq '.[] | .title'

gh api graphql -f query='query { viewer { login } }'

# ========== 配置 ==========
gh config set editor vim         # 设置编辑器
gh config set git_protocol ssh   # 设置 git 协议
gh config set prompt disabled    # 禁用交互式提示
gh config list                   # 列出配置

# ========== 扩展 ==========
gh extension install <owner>/<repo>  # 安装扩展
gh extension list                # 列出扩展
gh extension upgrade <name>      # 升级扩展
gh extension remove <name>       # 删除扩展
```

#### 高级用法

```bash
# ========== JSON 处理 ==========
# 使用 jq 进行复杂数据处理
gh issue list --json number,title,labels,assignees \
  --jq '.[] | select(.labels[].name == "bug") | "\(.number): \(.title)"'

# 批量操作
for issue in $(gh issue list --json number --jq '.[].number'); do
  gh issue edit $issue --add-label "triaged"
done

# 统计数据
gh issue list --json state \
  --jq 'group_by(.state) | map({state: .[0].state, count: length})'

# ========== 脚本编写 ==========
#!/bin/bash
# issue-metrics.sh - Issue 指标统计

REPO="${1:-owner/repo}"
SINCE="${2:-2024-01-01}"

echo "# Issue Metrics for $REPO"
echo "Since: $SINCE"
echo ""

echo "## Total Issues"
gh issue list \
  --repo $REPO \
  --search "created:>$SINCE" \
  --json number \
  --jq 'length'

echo "## Open Issues"
gh issue list \
  --repo $REPO \
  --search "created:>$SINCE state:open" \
  --json number \
  --jq 'length'

echo "## Closed Issues"
gh issue list \
  --repo $REPO \
  --search "created:>$SINCE state:closed" \
  --json number \
  --jq 'length'

echo "## Average Time to Close"
gh issue list \
  --repo $REPO \
  --search "created:>$SINCE state:closed" \
  --json createdAt,closedAt \
  --jq '
    map(
      ((.closedAt | fromdateiso8601) - (.createdAt | fromdateiso8601)) / 86400
    ) | add / length
  ' | xargs -I {} echo "{} days"

echo "## Top Labels"
gh issue list \
  --repo $REPO \
  --search "created:>$SINCE" \
  --json labels \
  --jq '[.[].labels[].name] | group_by(.) | map({label: .[0], count: length}) | sort_by(.count) | reverse'
```

#### gh 扩展开发

```bash
#!/bin/bash
# gh-assignee-roulette - 随机分配 Issue
# 扩展路径: ~/.local/share/gh/extensions/assignee-roulette/assignee-roulette.sh

REPO="$(git config --get remote.origin.url | sed 's/.*:\(.*\)\.git/\1/')"
TEAM_MEMBERS=("alice" "bob" "charlie" "david")

ISSUE_NUMBER=$1
if [ -z "$ISSUE_NUMBER" ]; then
  echo "Usage: gh assignee-roulette <issue-number>"
  exit 1
fi

# 随机选择
ASSIGNEE=${TEAM_MEMBERS[$RANDOM % ${#TEAM_MEMBERS[@]}]}

# 分配
gh issue edit $ISSUE_NUMBER --repo $REPO --add-assignee $ASSIGNEE

echo "✅ Assigned issue #$ISSUE_NUMBER to @$ASSIGNEE"
```

### GitHub GraphQL API

#### 完整查询示例

```graphql
# ========== 获取仓库信息 ==========
query GetRepoInfo($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    id
    name
    description
    createdAt
    updatedAt
    stargazerCount
    watcherCount
    forkCount
    licenseInfo {
      key
      name
    }
    defaultBranchRef {
      name
      target {
        ... on Commit {
          history(first: 1) {
            nodes {
              oid
              message
              author {
                name
                email
              }
            }
          }
        }
      }
    }
  }
}

# ========== 获取 Issue 详情（含时间线） ==========
query GetIssueTimeline($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      id
      number
      title
      body
      state
      createdAt
      closedAt
      author {
        login
        avatarUrl
      }
      labels(first: 20) {
        nodes {
          id
          name
          color
          description
        }
      }
      assignees(first: 10) {
        nodes {
          login
          avatarUrl
        }
      }
      milestone {
        id
        title
        state
        dueOn
      }
      comments(first: 50) {
        nodes {
          id
          body
          createdAt
          updatedAt
          author {
            login
          }
          authorAssociation
        }
      }
      timelineItems(first: 100, itemTypes: [LABELED_EVENT, UNLABELED_EVENT, ASSIGNED_EVENT, CLOSED_EVENT, REFERENCED_EVENT, CROSS_REFERENCED_EVENT, RENAMED_TITLE_EVENT]) {
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
          ... on UnlabeledEvent {
            label {
              name
            }
            actor {
              login
            }
            createdAt
          }
          ... on AssignedEvent {
            actor {
              login
            }
            assignee {
              login
            }
            createdAt
          }
          ... on ClosedEvent {
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

# ========== 搜索和过滤 ==========
query SearchIssues($query: String!) {
  search(query: $query, type: ISSUE, first: 50) {
    issueCount
    nodes {
      ... on Issue {
        id
        number
        title
        state
        createdAt
        repository {
          name
          owner {
            login
          }
        }
        labels(first: 10) {
          nodes {
            name
          }
        }
      }
    }
  }
}

# ========== 批量操作 ==========
mutation CloseIssue($issueId: ID!) {
  closeIssue(input: { issueId: $issueId }) {
    issue {
      number
      state
    }
  }
}

mutation AddLabels($labelableId: ID!, $labelIds: [ID!]!) {
  addLabelsToLabelable(input: { labelableId: $labelableId, labelIds: $labelIds }) {
    labelable {
      ... on Issue {
        number
      }
    }
  }
}

# ========== 创建 Issue ==========
mutation CreateIssue($repositoryId: ID!, $title: String!, $body: String!) {
  createIssue(input: {
    repositoryId: $repositoryId
    title: $title
    body: $body
  }) {
    issue {
      id
      number
      title
    }
  }
}

# ========== 复杂统计查询 ==========
query IssueMetrics($owner: String!, $name: String!, $since: GitTimestamp!) {
  repository(owner: $owner, name: $name) {
    issues(
      first: 100
      states: [OPEN, CLOSED]
      filterBy: { createdSince: $since }
      orderBy: { field: CREATED_AT, direction: DESC }
    ) {
      totalCount
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
        assignees(first: 5) {
          totalCount
        }
        comments(first: 100) {
          totalCount
        }
        reactions(first: 20) {
          totalCount
        }
      }
    }
  }
}
```

#### Python 客户端封装

```python
import requests
import json
from typing import List, Dict, Optional
from datetime import datetime

class GitHubGraphQLClient:
    """GitHub GraphQL API 客户端"""

    def __init__(self, token: str):
        self.endpoint = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }

    def query(self, query: str, variables: Dict = None) -> Dict:
        """执行 GraphQL 查询"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = requests.post(
            self.endpoint,
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()

        data = response.json()

        # 检查错误
        if "errors" in data:
            raise Exception(f"GraphQL Error: {data['errors']}")

        return data

    def get_issue_metrics(
        self,
        owner: str,
        repo: str,
        since: datetime
    ) -> Dict:
        """获取 Issue 指标"""
        query = """
        query($owner: String!, $name: String!, $since: GitTimestamp!) {
          repository(owner: $owner, name: $name) {
            issues(
              first: 100
              states: [OPEN, CLOSED]
              filterBy: { createdSince: $since }
              orderBy: { field: CREATED_AT, direction: DESC }
            ) {
              totalCount
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
                assignees(first: 5) {
                  totalCount
                }
                comments(first: 100) {
                  totalCount
                }
                reactions(first: 20) {
                  totalCount
                }
              }
            }
          }
        }
        """

        variables = {
            "owner": owner,
            "name": repo,
            "since": since.isoformat() + "Z"
        }

        data = self.query(query, variables)
        issues = data["data"]["repository"]["issues"]["nodes"]

        # 计算指标
        metrics = {
            "total": len(issues),
            "open": len([i for i in issues if i["state"] == "OPEN"]),
            "closed": len([i for i in issues if i["state"] == "CLOSED"]),
            "avg_assignees": sum(i["assignees"]["totalCount"] for i in issues) / len(issues),
            "avg_comments": sum(i["comments"]["totalCount"] for i in issues) / len(issues),
            "avg_reactions": sum(i["reactions"]["totalCount"] for i in issues) / len(issues),
        }

        # 计算平均关闭时间
        closed_issues = [i for i in issues if i["state"] == "CLOSED"]
        if closed_issues:
            close_times = []
            for issue in closed_issues:
                created = datetime.fromisoformat(issue["createdAt"].replace("Z", ""))
                closed = datetime.fromisoformat(issue["closedAt"].replace("Z", ""))
                close_times.append((closed - created).days)
            metrics["avg_close_time_days"] = sum(close_times) / len(close_times)

        # 标签分布
        label_counts = {}
        for issue in issues:
            for label in issue["labels"]["nodes"]:
                name = label["name"]
                label_counts[name] = label_counts.get(name, 0) + 1
        metrics["label_distribution"] = dict(sorted(
            label_counts.items(),
            key=lambda x: x[1],
            reverse=True
        ))

        return metrics

    def create_issue(
        self,
        repo_id: str,
        title: str,
        body: str,
        label_ids: List[str] = None
    ) -> Dict:
        """创建 Issue"""
        mutation = """
        mutation($repoId: ID!, $title: String!, $body: String!) {
          createIssue(input: {
            repositoryId: $repoId
            title: $title
            body: $body
          }) {
            issue {
              id
              number
              title
            }
          }
        }
        """

        variables = {
            "repoId": repo_id,
            "title": title,
            "body": body
        }

        return self.query(mutation, variables)

    def batch_create_issues(
        self,
        repo_id: str,
        issues: List[Dict]
    ) -> List[Dict]:
        """批量创建 Issues"""
        results = []
        for issue_data in issues:
            try:
                result = self.create_issue(
                    repo_id=repo_id,
                    title=issue_data["title"],
                    body=issue_data.get("body", "")
                )
                results.append({
                    "success": True,
                    "issue": result["data"]["createIssue"]["issue"]
                })
            except Exception as e:
                results.append({
                    "success": False,
                    "error": str(e)
                })
        return results

    def get_repository_id(self, owner: str, name: str) -> str:
        """获取仓库 ID"""
        query = """
        query($owner: String!, $name: String!) {
          repository(owner: $owner, name: $name) {
            id
          }
        }
        """

        data = self.query(query, {"owner": owner, "name": name})
        return data["data"]["repository"]["id"]

# 使用示例
if __name__ == "__main__":
    import os
    from datetime import timedelta

    client = GitHubGraphQLClient(os.getenv("GITHUB_TOKEN"))

    # 获取仓库 ID
    repo_id = client.get_repository_id("owner", "repo")

    # 批量创建 Issues
    issues = [
        {"title": "Bug 1", "body": "Description 1"},
        {"title": "Bug 2", "body": "Description 2"},
        {"title": "Feature 1", "body": "Description 3"},
    ]

    results = client.batch_create_issues(repo_id, issues)
    for result in results:
        if result["success"]:
            print(f"✅ Created issue #{result['issue']['number']}")
        else:
            print(f"❌ Failed: {result['error']}")
```

### GitHub REST API

#### 核心端点

```python
import requests
import base64
import json

class GitHubRESTClient:
    """GitHub REST API 客户端"""

    def __init__(self, token: str):
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def get(self, endpoint: str, params: Dict = None) -> Dict:
        """GET 请求"""
        response = requests.get(
            f"{self.base_url}{endpoint}",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: Dict) -> Dict:
        """POST 请求"""
        response = requests.post(
            f"{self.base_url}{endpoint}",
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()

    def put(self, endpoint: str, data: Dict = None) -> Dict:
        """PUT 请求"""
        response = requests.put(
            f"{self.base_url}{endpoint}",
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()

    def delete(self, endpoint: str) -> Dict:
        """DELETE 请求"""
        response = requests.delete(
            f"{self.base_url}{endpoint}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    # ========== Issue 操作 ==========

    def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        labels: List[str] = None,
        since: str = None,
        per_page: int = 100
    ) -> List[Dict]:
        """列出 Issues"""
        params = {"state": state, "per_page": per_page}
        if labels:
            params["labels"] = ",".join(labels)
        if since:
            params["since"] = since

        return self.get(f"/repos/{owner}/{repo}/issues", params)

    def get_issue(self, owner: str, repo: str, number: int) -> Dict:
        """获取 Issue 详情"""
        return self.get(f"/repos/{owner}/{repo}/issues/{number}")

    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = None,
        labels: List[str] = None,
        assignees: List[str] = None
    ) -> Dict:
        """创建 Issue"""
        data = {"title": title}
        if body:
            data["body"] = body
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees

        return self.post(f"/repos/{owner}/{repo}/issues", data)

    def update_issue(
        self,
        owner: str,
        repo: str,
        number: int,
        title: str = None,
        body: str = None,
        state: str = None,
        labels: List[str] = None,
        assignees: List[str] = None
    ) -> Dict:
        """更新 Issue"""
        data = {}
        if title:
            data["title"] = title
        if body:
            data["body"] = body
        if state:
            data["state"] = state
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees

        return self.put(f"/repos/{owner}/{repo}/issues/{number}", data)

    def close_issue(self, owner: str, repo: str, number: int) -> Dict:
        """关闭 Issue"""
        return self.update_issue(owner, repo, number, state="closed")

    # ========== 评论操作 ==========

    def list_comments(
        self,
        owner: str,
        repo: str,
        issue_number: int
    ) -> List[Dict]:
        """列出评论"""
        return self.get(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
        )

    def create_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str
    ) -> Dict:
        """创建评论"""
        return self.post(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            {"body": body}
        )

    # ========== 标签操作 ==========

    def list_labels(self, owner: str, repo: str) -> List[Dict]:
        """列出标签"""
        return self.get(f"/repos/{owner}/{repo}/labels")

    def create_label(
        self,
        owner: str,
        repo: str,
        name: str,
        color: str,
        description: str = None
    ) -> Dict:
        """创建标签"""
        data = {"name": name, "color": color}
        if description:
            data["description"] = description

        return self.post(f"/repos/{owner}/{repo}/labels", data)

    # ========== Milestone 操作 ==========

    def list_milestones(
        self,
        owner: str,
        repo: str,
        state: str = "open"
    ) -> List[Dict]:
        """列出 Milestones"""
        return self.get(
            f"/repos/{owner}/{repo}/milestones",
            {"state": state}
        )

    def create_milestone(
        self,
        owner: str,
        repo: str,
        title: str,
        description: str = None,
        due_on: str = None
    ) -> Dict:
        """创建 Milestone"""
        data = {"title": title}
        if description:
            data["description"] = description
        if due_on:
            data["due_on"] = due_on

        return self.post(f"/repos/{owner}/{repo}/milestones", data)

    # ========== 搜索操作 ==========

    def search_issues(
        self,
        query: str,
        sort: str = "created",
        order: str = "desc",
        per_page: int = 100
    ) -> Dict:
        """搜索 Issues"""
        params = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": per_page
        }
        return self.get("/search/issues", params)
```

---

## 第三方集成工具

### ZenHub

#### 功能概述

ZenHub 是专为 GitHub 设计的敏捷项目管理工具。

**核心功能**:
- 📊 **看板视图** - 拖拽式 Issue 管理
- 🔥 **燃尽图** - Sprint 进度跟踪
- ⚡ **自动同步** - 与 GitHub Issues 实时同步
- 📈 **报告** - 团队速度、Cycle time 等指标
- 🔗 **Epic** - 大型功能分解和跟踪

#### API 使用

```python
import requests

class ZenHubClient:
    """ZenHub API 客户端"""

    def __init__(self, token: str):
        self.base_url = "https://api.zenhub.com"
        self.headers = {
            "X-Authentication-Token": token,
            "Accept": "application/json"
        }

    def get_board_data(self, repo_id: str) -> Dict:
        """获取看板数据"""
        response = requests.get(
            f"{self.base_url}/p1/repositories/{repo_id}/board",
            headers=self.headers
        )
        return response.json()

    def get_epic(self, repo_id: str, epic_id: str) -> Dict:
        """获取 Epic 详情"""
        response = requests.get(
            f"{self.base_url}/p1/repositories/{repo_id}/epics/{epic_id}",
            headers=self.headers
        )
        return response.json()

    def add_issue_to_epic(
        self,
        repo_id: str,
        epic_id: str,
        issue_id: str
    ) -> Dict:
        """添加 Issue 到 Epic"""
        response = requests.put(
            f"{self.base_url}/p1/repositories/{repo_id}/epics/{epic_id}/issues/{issue_id}",
            headers=self.headers
        )
        return response.json()

    def move_issue(
        self,
        repo_id: str,
        issue_id: str,
        pipeline_id: str,
        position: str = "top"
    ) -> Dict:
        """移动 Issue 到不同列"""
        response = requests.post(
            f"{self.base_url}/p1/repositories/{repo_id}/issues/{issue_id}/moves",
            headers=self.headers,
            json={
                "pipeline_id": pipeline_id,
                "position": position
            }
        )
        return response.json()
```

### Jira Integration

#### 双向同步

```python
class JiraGitHubSync:
    """Jira - GitHub 双向同步"""

    def __init__(self, jira_client, gh_client):
        self.jira = jira_client
        self.gh = gh_client

    def sync_issue_to_jira(self, gh_issue: Dict) -> str:
        """同步 GitHub Issue 到 Jira"""
        # 查找或创建 Jira Issue
        jira_key = self.find_jira_issue(gh_issue["number"])

        if not jira_key:
            # 创建新的 Jira Issue
            issue = self.jira.create_issue({
                "project": {"key": "PROJ"},
                "summary": gh_issue["title"],
                "description": gh_issue["body"] + "\n\n" +
                              f"GitHub Issue: {gh_issue['html_url']}",
                "issuetype": {"name": "Bug"}
            })
            jira_key = issue.key

            # 添加链接到 GitHub Issue
            self.jira.add_remote_link(
                jira_key,
                {
                    "url": gh_issue["html_url"],
                    "title": f"GitHub Issue #{gh_issue['number']}"
                }
            )

        return jira_key

    def sync_status_to_github(self, jira_key: str, gh_owner: str, gh_repo: str):
        """同步 Jira 状态到 GitHub"""
        # 获取 Jira Issue 状态
        issue = self.jira.issue(jira_key)
        status = issue.fields.status.name

        # 映射状态到 GitHub 标签
        label_map = {
            "To Do": "status:todo",
            "In Progress": "status:in-progress",
            "In Review": "status:in-review",
            "Done": "status:done"
        }

        if status in label_map:
            # 更新 GitHub Issue 标签
            # (需要找到对应的 GitHub issue number)
            pass

    def find_jira_issue(self, gh_issue_number: int) -> Optional[str]:
        """查找关联的 Jira Issue"""
        # 通过 JQL 查询
        jql = f'description ~ "GitHub Issue #{gh_issue_number}"'
        issues = self.jira.search_issues(jql)

        if issues:
            return issues[0].key
        return None
```

### Linear

#### 现代 Issue 追踪

```python
class LinearClient:
    """Linear API 客户端"""

    def __init__(self, api_key: str):
        self.base_url = "https://api.linear.app/graphql"
        self.headers = {
            "Authorization": api_key,
            "Content-Type": "application/json"
        }

    def create_issue(
        self,
        team_id: str,
        title: str,
        description: str = None,
        status: str = "Backlog",
        priority: int = 0,
        labels: List[str] = None
    ) -> Dict:
        """创建 Issue"""
        query = """
        mutation createIssue(
          $teamId: String!
          $title: String!
          $description: String
          $status: String
          $priority: Int
        ) {
          issueCreate(
            input: {
              teamId: $teamId
              title: $title
              description: $description
              statusId: $status
              priority: $priority
            }
          ) {
            issue {
              id
              title
              identifier
            }
          }
        }
        """

        variables = {
            "teamId": team_id,
            "title": title,
            "description": description,
            "status": status,
            "priority": priority
        }

        response = requests.post(
            self.base_url,
            headers=self.headers,
            json={"query": query, "variables": variables}
        )

        return response.json()

    def sync_from_github(self, gh_issue: Dict, team_id: str):
        """从 GitHub 同步到 Linear"""
        # 创建 Linear Issue
        linear_issue = self.create_issue(
            team_id=team_id,
            title=gh_issue["title"],
            description=gh_issue["body"] + "\n\n" +
                         f"GitHub: {gh_issue['html_url']}"
        )

        # 在 GitHub Issue 添加链接
        # (使用 GitHub API)
```

---

## 浏览器扩展生态

### Refined GitHub

**核心功能**:
- 🎨 **界面优化** - 更清晰的布局和设计
- ⚡ **快捷操作** - 一键关闭、合并 PR
- 📊 **额外信息** - 显示 Issue 大小、复杂度
- 🔍 **搜索增强** - 更强大的过滤和搜索

**自定义配置**:

```javascript
// 在扩展设置中添加自定义脚本

// 1. 自动隐藏已读的评论
document.addEventListener('turbo:load', () => {
  const comments = document.querySelectorAll('.timeline-comment');
  comments.forEach(comment => {
    if (comment.classList.contains('read')) {
      comment.style.opacity = '0.6';
    }
  });
});

// 2. 添加 Issue 优先级标签
const priorityColors = {
  'critical': '#ff0000',
  'high': '#ff6b00',
  'medium': '#ffd700',
  'low': '#00ff00'
};

// 3. 自定义快捷键
document.addEventListener('keydown', (e) => {
  // Ctrl + Enter: 提交评论
  if (e.ctrlKey && e.key === 'Enter') {
    document.querySelector('.btn-primary').click();
  }

  // Esc: 取消编辑
  if (e.key === 'Escape') {
    document.querySelector('.js-hide-inline-comment-form')?.click();
  }
});
```

### Octotree

**代码树增强**:
- 📁 **侧边栏文件树** - 快速导航
- 🔍 **文件搜索** - 快速定位文件
- 🎨 **主题定制** - 自定义外观

### Enhance GitHub

**额外功能**:
- 📊 **Issue 统计** - 显示 Issue 数量、趋势
- 🏷️ **标签管理** - 快速添加/删除标签
- 👥 **协作者信息** - 显示活跃贡献者

---

## CI/CD 集成

### GitHub Actions 自动化

#### Issue 自动化工作流

```yaml
# .github/workflows/issue-automation.yml

name: Issue Automation

on:
  issues:
    types: [opened, edited, labeled, unlabeled, closed]

# 权限配置
permissions:
  issues: write
  contents: read

jobs:
  # 自动标签
  auto-label:
    if: github.event.action == 'opened'
    runs-on: ubuntu-latest
    steps:
      - name: Auto-label based on content
        uses: actions/github-script@v7
        with:
          script: |
            const issue = context.payload.issue;
            const title = issue.title.toLowerCase();
            const body = issue.body.toLowerCase();

            let labels = [];

            // 标题关键词检测
            if (title.includes('bug') || title.includes('crash') || title.includes('error')) {
              labels.push('kind:bug');
            } else if (title.includes('feature') || title.includes('enhancement')) {
              labels.push('kind:feature');
            } else if (title.includes('performance') || title.includes('slow')) {
              labels.push('kind:performance');
            } else if (title.includes('docs') || title.includes('documentation')) {
              labels.push('kind:documentation');
            }

            // 内容关键词检测
            if (body.includes('security') || body.includes('vulnerability')) {
              labels.push('security');
            }

            // 添加标签
            if (labels.length > 0) {
              await github.rest.issues.addLabels({
                issue_number: context.issue.number,
                owner: context.repo.owner,
                repo: context.repo.repo,
                labels: labels
              });
            }

  # 自动分配
  auto-assign:
    if: github.event.action == 'labeled'
    runs-on: ubuntu-latest
    steps:
      - name: Auto-assign based on component
        uses: actions/github-script@v7
        with:
          script: |
            const label = context.payload.label.name;

            // 组件负责人映射
            const componentMap = {
              'component:auth': ['alice'],
              'component:api': ['bob', 'charlie'],
              'component:database': ['david'],
              'component:ui': ['eve'],
              'component:frontend': ['frank']
            };

            // 优先级分配
            const priorityMap = {
              'priority:critical': ['alice', 'bob'], // Senior devs
              'priority:high': ['charlie', 'david'],
              'priority:medium': ['eve', 'frank