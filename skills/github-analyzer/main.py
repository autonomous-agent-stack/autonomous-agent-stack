"""
Skill Name: Universal GitHub Repo Analyzer
Version: 1.0.0
Description: 通用代码库审查工具，提取语言分布与提交活跃度。
Security Level: Safe (No dangerous OS calls)
"""

import json
import os
from urllib.error import HTTPError, URLError
import urllib.request
from typing import Dict, Any


class SkillEntry:
    """标准技能入口类，OpenSage 将动态加载此模块"""

    def __init__(self):
        self.api_base = "https://api.github.com/repos"
        self.headers = {"User-Agent": "Autonomous-Agent-Stack-v2.0"}
        token = os.getenv("GITHUB_TOKEN", "").strip()
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
            self.headers["X-GitHub-Api-Version"] = "2022-11-28"

    def execute(self, params: Dict[str, Any]) -> str:
        """
        执行入口
        :param params: {"repo": "owner/repo_name"}
        """
        repo_name = params.get("repo")
        if not repo_name:
            return json.dumps({"status": "error", "message": "Missing 'repo' parameter."})

        try:
            # 1. 获取基础信息
            req = urllib.request.Request(f"{self.api_base}/{repo_name}", headers=self.headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                repo_data = json.loads(response.read().decode())

            # 2. 获取语言分布
            lang_req = urllib.request.Request(f"{self.api_base}/{repo_name}/languages", headers=self.headers)
            with urllib.request.urlopen(lang_req, timeout=5) as lang_response:
                languages = json.loads(lang_response.read().decode())

            # 3. 结构化组装
            result = {
                "status": "success",
                "repo": repo_name,
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "open_issues": repo_data.get("open_issues_count", 0),
                "language_distribution": languages,
                "analysis": "代码库活跃度扫描完成，建议送入下游 JSON Distiller 进行深度特征提取。"
            }
            return json.dumps(result, ensure_ascii=False, indent=2)

        except HTTPError as exc:
            return json.dumps(
                self._build_http_error_result(repo=repo_name, status_code=exc.code, reason=str(exc.reason)),
                ensure_ascii=False,
                indent=2,
            )
        except URLError as exc:
            return json.dumps(
                {
                    "status": "error",
                    "error_type": "network_error",
                    "repo": repo_name,
                    "message": "GitHub API network error",
                    "details": str(exc.reason),
                    "retryable": True,
                },
                ensure_ascii=False,
                indent=2,
            )
        except json.JSONDecodeError as exc:
            return json.dumps(
                {
                    "status": "error",
                    "error_type": "invalid_json",
                    "repo": repo_name,
                    "message": "GitHub API returned invalid JSON",
                    "details": str(exc),
                    "retryable": True,
                },
                ensure_ascii=False,
                indent=2,
            )
        except Exception as exc:
            return json.dumps(
                {
                    "status": "error",
                    "error_type": "unexpected_error",
                    "repo": repo_name,
                    "message": str(exc),
                    "retryable": False,
                },
                ensure_ascii=False,
                indent=2,
            )

    def _build_http_error_result(self, repo: str, status_code: int, reason: str) -> Dict[str, Any]:
        is_rate_limited = status_code == 403 and "rate limit" in reason.lower()
        return {
            "status": "error",
            "error_type": "rate_limit" if is_rate_limited else "http_error",
            "repo": repo,
            "http_status": status_code,
            "message": "GitHub API rate limit exceeded" if is_rate_limited else "GitHub API request failed",
            "details": reason,
            "retryable": is_rate_limited or status_code >= 500,
            "suggestion": (
                "Set GITHUB_TOKEN to increase API quota and retry."
                if is_rate_limited
                else "Verify repository path and network connectivity."
            ),
        }


# 供动态挂载器调用的工厂函数
def get_skill():
    return SkillEntry()
