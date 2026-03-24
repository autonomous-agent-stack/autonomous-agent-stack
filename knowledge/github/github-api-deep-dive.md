# GitHub API 完全指南：REST + GraphQL

## 目录

1. [API 概览](#api-概览)
2. [REST API 深度应用](#rest-api-深度应用)
3. [GraphQL API 深度应用](#graphql-api-深度应用)
4. [实战案例](#实战案例)
5. [性能优化](#性能优化)
6. [安全最佳实践](#安全最佳实践)

---

## API 概览

### API 类型对比

| 特性 | REST API | GraphQL API |
|------|----------|-------------|
| **数据获取** | 固定结构 | 按需查询 |
| **请求次数** | 多次请求 | 单次请求 |
| **缓存** | 易于缓存 | 难以缓存 |
| **学习曲线** | 平缓 | 陡峭 |
| **适用场景** | 简单操作 | 复杂查询 |
| **版本管理** | 有版本控制 | 无版本（向后兼容） |

### 选择建议

**使用 REST API 当**:
- 简单的 CRUD 操作
- 需要 HTTP 缓存
- 快速集成
- 标准化操作

**使用 GraphQL API 当**:
- 需要复杂关联查询
- 减少网络请求
- 灵活的数据结构
- 批量操作

---

## REST API 深度应用

### 核心端点

#### Issue 管理

```python
import requests
from typing import List, Dict, Optional

class GitHubIssuesAPI:
    """GitHub Issues REST API 封装"""

    def __init__(self, token: str):
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Issues-Manager/1.0"
        })

    def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        labels: List[str] = None,
        since: str = None,
        per_page: int = 100,
        page: int = 1
    ) -> Dict:
        """
        列出 Issues

        Args:
            owner: 仓库所有者
            repo: 仓库名称
            state: open/closed/all
            labels: 标签过滤
            since: ISO 8601 时间戳
            per_page: 每页数量 (1-100)
            page: 页码

        Returns:
            Dict with issues list and pagination info
        """
        params = {
            "state": state,
            "per_page": per_page,
            "page": page
        }

        if labels:
            params["labels"] = ",".join(labels)
        if since:
            params["since"] = since

        response = self.session.get(
            f"{self.base_url}/repos/{owner}/{repo}/issues",
            params=params
        )

        response.raise_for_status()

        data = response.json()

        # 返回数据和分页信息
        return {
            "issues": data,
            "page": page,
            "per_page": per_page,
            "total_count": self._get_total_count(response)
        }

    def get_issue(self, owner: str, repo: str, number: int) -> Dict:
        """获取单个 Issue 详情"""
        response = self.session.get(
            f"{self.base_url}/repos/{owner}/{repo}/issues/{number}"
        )
        response.raise_for_status()
        return response.json()

    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = None,
        labels: List[str] = None,
        assignees: List[str] = None,
        milestone: int = None
    ) -> Dict:
        """
        创建 Issue

        Args:
            owner: 仓库所有者
            repo: 仓库名称
            title: Issue 标题
            body: Issue 内容
            labels: 标签列表
            assignees: 负责人列表
            milestone: Milestone 编号

        Returns:
            创建的 Issue 对象
        """
        data = {"title": title}

        if body:
            data["body"] = body
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees
        if milestone:
            data["milestone"] = milestone

        response = self.session.post(
            f"{self.base_url}/repos/{owner}/{repo}/issues",
            json=data
        )

        response.raise_for_status()
        return response.json()

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

        response = self.session.patch(
            f"{self.base_url}/repos/{owner}/{repo}/issues/{number}",
            json=data
        )

        response.raise_for_status()
        return response.json()

    def close_issue(self, owner: str, repo: str, number: int) -> Dict:
        """关闭 Issue"""
        return self.update_issue(owner, repo, number, state="closed")

    def lock_issue(
        self,
        owner: str,
        repo: str,
        number: int,
        reason: str = "off-topic"
    ):
        """锁定 Issue"""
        response = self.session.put(
            f"{self.base_url}/repos/{owner}/{repo}/issues/{number}/lock",
            json={"lock_reason": reason},
            headers={"Accept": "application/vnd.github.v3+json"}
        )
        response.raise_for_status()

    def unlock_issue(self, owner: str, repo: str, number: int):
        """解锁 Issue"""
        response = self.session.delete(
            f"{self.base_url}/repos/{owner}/{repo}/issues/{number}/lock"
        )
        response.raise_for_status()

    def _get_total_count(self, response) -> int:
        """从 Link header 获取总数"""
        link_header = response.headers.get("Link", "")
        if not link_header:
            return len(response.json())

        # 解析 Link header
        # <https://api.github.com/...?page=2>; rel="next",
        # <https://api.github.com/...?page=10>; rel="last"
        import re
        last_page_match = re.search(r'page=(\d+)>; rel="last"', link_header)
        if last_page_match:
            last_page = int(last_page_match.group(1))
            per_page = len(response.json())
            return last_page * per_page

        return len(response.json())


class IssueCommentsAPI:
    """Issue 评论 API"""

    def __init__(self, token: str):
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        })

    def list_comments(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        since: str = None
    ) -> List[Dict]:
        """列出评论"""
        params = {}
        if since:
            params["since"] = since

        response = self.session.get(
            f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments",
            params=params
        )

        response.raise_for_status()
        return response.json()

    def create_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str
    ) -> Dict:
        """创建评论"""
        response = self.session.post(
            f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments",
            json={"body": body}
        )

        response.raise_for_status()
        return response.json()

    def update_comment(
        self,
        owner: str,
        repo: str,
        comment_id: int,
        body: str
    ) -> Dict:
        """更新评论"""
        response = self.session.patch(
            f"{self.base_url}/repos/{owner}/{repo}/issues/comments/{comment_id}",
            json={"body": body}
        )

        response.raise_for_status()
        return response.json()

    def delete_comment(self, owner: str, repo: str, comment_id: int):
        """删除评论"""
        response = self.session.delete(
            f"{self.base_url}/repos/{owner}/{repo}/issues/comments/{comment_id}"
        )
        response.raise_for_status()


class IssueLabelsAPI:
    """Issue 标签 API"""

    def __init__(self, token: str):
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        })

    def list_labels(self, owner: str, repo: str) -> List[Dict]:
        """列出所有标签"""
        response = self.session.get(
            f"{self.base_url}/repos/{owner}/{repo}/labels"
        )
        response.raise_for_status()
        return response.json()

    def get_label(self, owner: str, repo: str, name: str) -> Dict:
        """获取单个标签"""
        response = self.session.get(
            f"{self.base_url}/repos/{owner}/{repo}/labels/{name}"
        )
        response.raise_for_status()
        return response.json()

    def create_label(
        self,
        owner: str,
        repo: str,
        name: str,
        color: str,
        description: str = None
    ) -> Dict:
        """创建标签"""
        data = {
            "name": name,
            "color": color.lstrip("#")
        }

        if description:
            data["description"] = description

        response = self.session.post(
            f"{self.base_url}/repos/{owner}/{repo}/labels",
            json=data
        )

        response.raise_for_status()
        return response.json()

    def update_label(
        self,
        owner: str,
        repo: str,
        name: str,
        color: str = None,
        description: str = None
    ) -> Dict:
        """更新标签"""
        data = {}

        if color:
            data["color"] = color.lstrip("#")
        if description:
            data["description"] = description

        response = self.session.patch(
            f"{self.base_url}/repos/{owner}/{repo}/labels/{name}",
            json=data
        )

        response.raise_for_status()
        return response.json()

    def delete_label(self, owner: str, repo: str, name: str):
        """删除标签"""
        response = self.session.delete(
            f"{self.base_url}/repos/{owner}/{repo}/labels/{name}"
        )
        response.raise_for_status()

    def add_labels(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        labels: List[str]
    ) -> List[Dict]:
        """为 Issue 添加标签"""
        response = self.session.post(
            f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/labels",
            json=labels
        )

        response.raise_for_status()
        return response.json()

    def remove_label(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        label: str
    ):
        """移除 Issue 的标签"""
        response = self.session.delete(
            f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/labels/{label}"
        )
        response.raise_for_status()

    def replace_labels(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        labels: List[str]
    ) -> List[Dict]:
        """替换 Issue 的所有标签"""
        response = self.session.put(
            f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/labels",
            json=labels
        )

        response.raise_for_status()
        return response.json()
```

### 高级搜索

```python
class GitHubSearchAPI:
    """GitHub 搜索 API"""

    def __init__(self, token: str):
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        })

    def search_issues(
        self,
        query: str,
        sort: str = "created",
        order: str = "desc",
        per_page: int = 100
    ) -> Dict:
        """
        搜索 Issues

        查询语法:
            repo:owner/repo           - 限定仓库
            org:organization          - 限定组织
            author:username           - 限定作者
            assignee:username         - 限定负责人
            mentions:username         - 限定提及
            state:open/closed         - 限定状态
            is:issue/pr               - 限定类型
            label:bug                 - 限定标签
            no:label                  - 排除标签
            language:python           - 限定语言
            created:>2024-01-01       - 创建时间
            updated:<2024-01-01       - 更新时间
            comments:>10              - 评论数
            in:title                  - 在标题中搜索
            in:body                   - 在正文中搜索
        """
        params = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": per_page
        }

        response = self.session.get(
            f"{self.base_url}/search/issues",
            params=params
        )

        response.raise_for_status()

        data = response.json()

        return {
            "total_count": data["total_count"],
            "items": data["items"],
            "incomplete_results": data.get("incomplete_results", False)
        }

    def advanced_search(
        self,
        repos: List[str] = None,
        orgs: List[str] = None,
        labels: List[str] = None,
        exclude_labels: List[str] = None,
        state: str = "open",
        author: str = None,
        assignee: str = None,
        created_after: str = None,
        created_before: str = None,
        updated_after: str = None,
        comments_min: int = None,
        comments_max: int = None,
        search_in: str = None,  # title/body
        per_page: int = 100
    ) -> Dict:
        """高级搜索（构建查询）"""
        query_parts = []

        # 仓库/组织过滤
        if repos:
            for repo in repos:
                query_parts.append(f"repo:{repo}")
        if orgs:
            for org in orgs:
                query_parts.append(f"org:{org}")

        # 标签过滤
        if labels:
            for label in labels:
                query_parts.append(f"label:\"{label}\"")
        if exclude_labels:
            for label in exclude_labels:
                query_parts.append(f"-label:\"{label}\"")

        # 状态过滤
        query_parts.append(f"state:{state}")

        # 用户过滤
        if author:
            query_parts.append(f"author:{author}")
        if assignee:
            query_parts.append(f"assignee:{assignee}")

        # 时间过滤
        if created_after:
            query_parts.append(f"created:>{created_after}")
        if created_before:
            query_parts.append(f"created:<{created_before}")
        if updated_after:
            query_parts.append(f"updated:>{updated_after}")

        # 评论数过滤
        if comments_min:
            query_parts.append(f"comments:>{comments_min}")
        if comments_max:
            query_parts.append(f"comments:<{comments_max}")

        # 搜索位置
        if search_in:
            query_parts.append(f"in:{search_in}")

        # 组合查询
        query = " ".join(query_parts)

        return self.search_issues(query, per_page=per_page)
```

---

## GraphQL API 深度应用

### 查询构建器

```python
import requests
import json
from typing import Dict, List, Optional, Any

class GraphQLClient:
    """GitHub GraphQL API 客户端"""

    def __init__(self, token: str):
        self.endpoint = "https://api.github.com/graphql"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        })

    def query(
        self,
        query: str,
        variables: Dict = None,
        operation_name: str = None
    ) -> Dict:
        """
        执行 GraphQL 查询

        Args:
            query: GraphQL 查询字符串
            variables: 查询变量
            operation_name: 操作名称（用于多个操作时）

        Returns:
            查询结果

        Raises:
            Exception: 查询失败时
        """
        payload = {"query": query}

        if variables:
            payload["variables"] = variables
        if operation_name:
            payload["operationName"] = operation_name

        response = self.session.post(self.endpoint, json=payload)
        response.raise_for_status()

        data = response.json()

        # 检查错误
        if "errors" in data:
            errors = data["errors"]
            error_msg = "\n".join([e.get("message", "Unknown error") for e in errors])
            raise Exception(f"GraphQL Error:\n{error_msg}")

        return data

    def mutate(
        self,
        mutation: str,
        variables: Dict = None
    ) -> Dict:
        """执行 GraphQL 变更"""
        return self.query(mutation, variables)


class IssuesGraphQL:
    """Issues GraphQL 查询"""

    def __init__(self, client: GraphQLClient):
        self.client = client

    def get_issue(
        self,
        owner: str,
        repo: str,
        number: int,
        include_comments: bool = True,
        include_timeline: bool = True,
        comments_limit: int = 50,
        timeline_limit: int = 100
    ) -> Dict:
        """
        获取 Issue 详情（含评论和时间线）

        使用 GraphQL 可以一次性获取所有数据，减少网络请求
        """
        query = """
        query GetIssue(
            $owner: String!,
            $repo: String!,
            $number: Int!,
            $commentsLimit: Int!,
            $timelineLimit: Int!
        ) {
            repository(owner: $owner, name: $repo) {
                issue(number: $number) {
                    id
                    number
                    title
                    body
                    state
                    createdAt
                    closedAt
                    url
                    author {
                        login
                        avatarUrl
                        url
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
                            url
                        }
                    }
                    milestone {
                        id
                        title
                        state
                        dueOn
                    }
                    participants(first: 20) {
                        nodes {
                            login
                        }
                    }
                    comments(first: $commentsLimit) {
                        totalCount
                        nodes {
                            id
                            body
                            createdAt
                            updatedAt
                            author {
                                login
                                avatarUrl
                            }
                            authorAssociation
                            reactions(first: 20) {
                                nodes {
                                    content
                                    user {
                                        login
                                    }
                                }
                            }
                        }
                    }
                    timelineItems(first: $timelineLimit, itemTypes: [LABELED_EVENT, UNLABELED_EVENT, ASSIGNED_EVENT, CLOSED_EVENT, REFERENCED_EVENT, CROSS_REFERENCED_EVENT, RENAMED_TITLE_EVENT, MILESTONED_EVENT, DEMILESTONED_EVENT]) {
                        totalCount
                        nodes {
                            __typename
                            ... on LabeledEvent {
                                label {
                                    name
                                    color
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
        """

        variables = {
            "owner": owner,
            "repo": repo,
            "number": number,
            "commentsLimit": comments_limit,
            "timelineLimit": timeline_limit
        }

        result = self.client.query(query, variables)
        return result["data"]["repository"]["issue"]

    def search_issues(
        self,
        query: str,
        limit: int = 100,
        sort: str = "CREATED_AT",
        order: str = "DESC"
    ) -> List[Dict]:
        """
        搜索 Issues

        使用 GraphQL API 进行更灵活的搜索
        """
        q = """
        query SearchIssues($query: String!, $limit: Int!, $sort: IssueOrderField!, $order: OrderDirection!) {
            search(query: $query, type: ISSUE, first: $limit) {
                issueCount
                nodes {
                    ... on Issue {
                        id
                        number
                        title
                        state
                        createdAt
                        closedAt
                        url
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
                        assignees(first: 5) {
                            nodes {
                                login
                            }
                        }
                        author {
                            login
                        }
                    }
                }
            }
        }
        """

        variables = {
            "query": f"{query} sort:{sort.lower()}-{order.lower()}",
            "limit": limit,
            "sort": sort,
            "order": order
        }

        result = self.client.query(q, variables)
        return result["data"]["search"]["nodes"]

    def get_repository_issues(
        self,
        owner: str,
        repo: str,
        states: List[str] = None,
        labels: List[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取仓库的 Issues（支持复杂过滤）

        GraphQL 相比 REST 的优势：
        - 一次请求获取所有数据
        - 支持复杂的嵌套查询
        - 按需获取字段，减少数据传输
        """
        query = """
        query GetRepoIssues(
            $owner: String!,
            $repo: String!,
            $states: [IssueState!],
            $labels: [String!],
            $limit: Int!
        ) {
            repository(owner: $owner, name: $repo) {
                issues(first: $limit, states: $states, labels: $labels) {
                    nodes {
                        id
                        number
                        title
                        state
                        createdAt
                        closedAt
                        author {
                            login
                        }
                        labels(first: 10) {
                            nodes {
                                name
                                color
                            }
                        }
                        assignees(first: 5) {
                            nodes {
                                login
                            }
                        }
                        comments(first: 100) {
                            totalCount
                        }
                        reactions(first: 20) {
                            totalCount
                        }
                    }
                    totalCount
                }
            }
        }
        """

        variables = {
            "owner": owner,
            "repo": repo,
            "states": states or ["OPEN", "CLOSED"],
            "labels": labels or [],
            "limit": limit
        }

        result = self.client.query(query, variables)
        return result["data"]["repository"]["issues"]["nodes"]

    def get_issue_metrics(
        self,
        owner: str,
        repo: str,
        since: str
    ) -> Dict:
        """
        获取 Issue 指标

        使用 GraphQL 一次性获取所有指标数据
        """
        query = """
        query IssueMetrics($owner: String!, $repo: String!, $since: GitTimestamp!) {
            repository(owner: $owner, name: $repo) {
                issues(
                    first: 100,
                    states: [OPEN, CLOSED],
                    filterBy: { createdSince: $since },
                    orderBy: { field: CREATED_AT, direction: DESC }
                ) {
                    totalCount
                    nodes {
                        number
                        state
                        createdAt
                        closedAt
                        labels(first: 20) {
                            nodes {
                                name
                            }
                        }
                        assignees(first: 10) {
                            totalCount
                            nodes {
                                login
                            }
                        }
                        comments(first: 100) {
                            totalCount
                        }
                        reactions(first: 50) {
                            totalCount
                        }
                    }
                }
            }
        }
        """

        result = self.client.query(query, {
            "owner": owner,
            "repo": repo,
            "since": since
        })

        issues = result["data"]["repository"]["issues"]["nodes"]

        # 计算指标
        from datetime import datetime

        metrics = {
            "total": len(issues),
            "open": len([i for i in issues if i["state"] == "OPEN"]),
            "closed": len([i for i in issues if i["state"] == "CLOSED"]),
        }

        # 平均关闭时间
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
```

### GraphQL 变更（Mutations）

```python
class IssuesMutations:
    """Issues GraphQL 变更操作"""

    def __init__(self, client: GraphQLClient):
        self.client = client

    def create_issue(
        self,
        repo_id: str,
        title: str,
        body: str = None,
        label_ids: List[str] = None,
        assignee_ids: List[str] = None
    ) -> Dict:
        """
        创建 Issue

        需要先获取 repository ID
        """
        mutation = """
        mutation CreateIssue(
            $repoId: ID!,
            $title: String!,
            $body: String
        ) {
            createIssue(input: {
                repositoryId: $repoId
                title: $title
                body: $body
            }) {
                issue {
                    id
                    number
                    title
                    url
                }
            }
        }
        """

        variables = {
            "repoId": repo_id,
            "title": title,
            "body": body
        }

        result = self.client.mutate(mutation, variables)
        return result["data"]["createIssue"]["issue"]

    def update_issue(
        self,
        issue_id: str,
        title: str = None,
        body: str = None,
        state: str = None
    ) -> Dict:
        """更新 Issue"""
        mutation = """
        mutation UpdateIssue(
            $issueId: ID!,
            $title: String,
            $body: String,
            $state: IssueState
        ) {
            updateIssue(input: {
                id: $issueId
                title: $title
                body: $body
                state: $state
            }) {
                issue {
                    id
                    number
                    title
                    state
                }
            }
        }
        """

        variables = {"issueId": issue_id}

        if title:
            variables["title"] = title
        if body:
            variables["body"] = body
        if state:
            variables["state"] = state.upper()

        result = self.client.mutate(mutation, variables)
        return result["data"]["updateIssue"]["issue"]

    def close_issue(self, issue_id: str) -> Dict:
        """关闭 Issue"""
        return self.update_issue(issue_id, state="CLOSED")

    def add_labels(self, issue_id: str, label_ids: List[str]) -> Dict:
        """添加标签"""
        mutation = """
        mutation AddLabels($issueId: ID!, $labelIds: [ID!]!) {
            addLabelsToLabelable(input: {
                labelableId: $issueId
                labelIds: $labelIds
            }) {
                labelable {
                    ... on Issue {
                        id
                        number
                        labels(first: 20) {
                            nodes {
                                name
                            }
                        }
                    }
                }
            }
        }
        """

        result = self.client.mutate(mutation, {
            "issueId": issue_id,
            "labelIds": label_ids
        })

        return result["data"]["addLabelsToLabelable"]["labelable"]

    def remove_labels(self, issue_id: str, label_ids: List[str]) -> Dict:
        """移除标签"""
        mutation = """
        mutation RemoveLabels($issueId: ID!, $labelIds: [ID!]!) {
            removeLabelsFromLabelable(input: {
                labelableId: $issueId
                labelIds: $labelIds
            }) {
                labelable {
                    ... on Issue {
                        id
                        number
                        labels(first: 20) {
                            nodes {
                                name
                            }
                        }
                    }
                }
            }
        }
        """

        result = self.client.mutate(mutation, {
            "issueId": issue_id,
            "labelIds": label_ids
        })

        return result["data"]["removeLabelsFromLabelable"]["labelable"]

    def add_comment(
        self,
        subject_id: str,
        body: str
    ) -> Dict:
        """添加评论"""
        mutation = """
        mutation AddComment($subjectId: ID!, $body: String!) {
            addComment(input: {
                subjectId: $subjectId
                body: $body
            }) {
                commentEdge {
                    node {
                        id
                        body
                        createdAt
                    }
                }
            }
        }
        """

        result = self.client.mutate(mutation, {
            "subjectId": subject_id,
            "body": body
        })

        return result["data"]["addComment"]["commentEdge"]["node"]

    def get_repository_id(self, owner: str, name: str) -> str:
        """获取仓库 ID"""
        query = """
        query($owner: String!, $name: String!) {
            repository(owner: $owner, name: $name) {
                id
            }
        }
        """

        result = self.client.query(query, {
            "owner": owner,
            "name": name
        })

        return result["data"]["repository"]["id"]

    def get_label_ids(
        self,
        owner: str,
        repo: str,
        label_names: List[str]
    ) -> Dict[str, str]:
        """获取标签 ID"""
        query = """
        query($owner: String!, $repo: String!, $names: [String!]!) {
            repository(owner: $owner, name: $repo) {
                labels(first: 100, query: $names) {
                    nodes {
                        id
                        name
                    }
                }
            }
        }
        """

        # 构建查询字符串
        query_str = " ".join([f'"{name}"' for name in label_names])

        result = self.client.query(query, {
            "owner": owner,
            "repo": repo,
            "names": query_str
        })

        labels = result["data"]["repository"]["labels"]["nodes"]
        return {label["name"]: label["id"] for label in labels}
```

---

## 实战案例

### 案例 1: 批量创建 Issues

```python
from typing import List, Dict

class BulkIssueCreator:
    """批量 Issue 创建器"""

    def __init__(self, token: str, owner: str, repo: str):
        self.gh = GitHub(token)
        self.owner = owner
        self.repo = repo
        self.repo_id = None

    def prepare(self):
        """准备（获取仓库 ID）"""
        # 如果使用 GraphQL
        from IssuesMutations import IssuesMutations
        from GraphQLClient import GraphQLClient

        client = GraphQLClient(token)
        mutations = IssuesMutations(client)
        self.repo_id = mutations.get_repository_id(self.owner, self.repo)

    def create_from_csv(self, csv_file: str) -> List[Dict]:
        """从 CSV 文件批量创建 Issues"""
        import csv

        results = []

        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    issue = self.gh.create_issue(
                        self.owner, self.repo,
                        title=row["title"],
                        body=row.get("body", ""),
                        labels=row.get("labels", "").split(",") if row.get("labels") else None
                    )

                    results.append({
                        "success": True,
                        "row": row,
                        "issue": issue
                    })

                    print(f"✅ Created: {issue['number']} - {issue['title']}")

                except Exception as e:
                    results.append({
                        "success": False,
                        "row": row,
                        "error": str(e)
                    })

                    print(f"❌ Failed: {row['title']} - {e}")

        # 生成报告
        self._generate_report(results)

        return results

    def create_from_json(self, json_file: str) -> List[Dict]:
        """从 JSON 文件批量创建 Issues"""
        import json

        with open(json_file, 'r') as f:
            issues_data = json.load(f)

        results = []

        for issue_data in issues_data:
            try:
                issue = self.gh.create_issue(
                    self.owner, self.repo,
                    **issue_data
                )

                results.append({
                    "success": True,
                    "data": issue_data,
                    "issue": issue
                })

            except Exception as e:
                results.append({
                    "success": False,
                    "data": issue_data,
                    "error": str(e)
                })

        return results

    def _generate_report(self, results: List[Dict]):
        """生成报告"""
        total = len(results)
        success = len([r for r in results if r["success"]])
        failed = total - success

        report = f"""
# Bulk Issue Creation Report

**Repository**: {self.owner}/{self.repo}
**Total**: {total}
**Success**: {success}
**Failed**: {failed}

## Failed Issues

"""

        for result in results:
            if not result["success"]:
                report += f"- {result['row'].get('title', 'Unknown')}: {result['error']}\n"

        print(report)
```

### 案例 2: Issue 迁移工具

```python
class IssueMigrator:
    """Issue 迁移工具（跨仓库或跨平台）"""

    def __init__(self, source_token: str, target_token: str):
        self.source_gh = GitHub(source_token)
        self.target_gh = GitHub(target_token)
        self.mapping = {}

    def migrate_repo_to_repo(
        self,
        source_repo: str,
        target_repo: str,
        migrate_comments: bool = True,
        preserve_labels: bool = True,
        close_source: bool = False
    ) -> Dict:
        """迁移仓库的所有 Issues 到另一个仓库"""
        source_owner, source_name = source_repo.split("/")
        target_owner, target_name = target_repo.split("/")

        # 获取所有 Issues
        print(f"📥 获取源仓库 Issues: {source_repo}")
        issues = self.source_gh.list_issues(
            source_owner, source_name,
            state="all",
            per_page=100
        )["issues"]

        results = {
            "total": len(issues),
            "migrated": 0,
            "failed": 0,
            "errors": []
        }

        for issue in issues:
            if issue.get("pull_request"):
                continue  # 跳过 PR

            try:
                # 迁移 Issue
                new_issue = self._migrate_issue(
                    source_owner, source_name,
                    target_owner, target_name,
                    issue,
                    migrate_comments,
                    preserve_labels
                )

                results["migrated"] += 1

                # 保存映射
                self.mapping[issue["number"]] = new_issue["number"]

                print(f"✅ Migrated: #{issue['number']} -> #{new_issue['number']}")

                # 如果需要，关闭源 Issue
                if close_source:
                    self.source_gh.close_issue(
                        source_owner, source_name,
                        issue["number"]
                    )

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "source_issue": issue["number"],
                    "error": str(e)
                })

                print(f"❌ Failed: #{issue['number']} - {e}")

        # 生成报告
        self._generate_migration_report(results)

