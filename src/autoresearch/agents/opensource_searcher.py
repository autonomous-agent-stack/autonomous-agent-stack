"""开源库搜索与评估模块

功能：
1. GitHub 搜索高星评项目
2. 评估项目安全性和成熟度
3. 检查依赖漏洞
4. 返回推荐的开源库
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class OpenSourceLibrary:
    """开源库"""
    name: str
    full_name: str  # owner/repo
    stars: int
    last_update: datetime
    license: str
    language: str
    description: str
    url: str
    security_score: float  # 0-100
    maturity_score: float  # 0-100


@dataclass
class SearchResult:
    """搜索结果"""
    libraries: List[OpenSourceLibrary]
    total_count: int
    query: str


class GitHubSearcher:
    """GitHub 搜索器"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
    
    async def search_libraries(
        self,
        query: str,
        min_stars: int = 100,
        max_age_days: int = 365,
        language: Optional[str] = "python",
        limit: int = 10,
    ) -> SearchResult:
        """搜索开源库
        
        Args:
            query: 搜索关键词
            min_stars: 最小星数
            max_age_days: 最近更新时间（天）
            language: 编程语言
            limit: 返回数量限制
            
        Returns:
            SearchResult
        """
        logger.info(f"🔍 搜索开源库: {query}")
        
        # 构建搜索查询
        search_query = f"{query} stars:>={min_stars}"
        if language:
            search_query += f" language:{language}"
        since = (datetime.utcnow() - timedelta(days=max_age_days)).strftime("%Y-%m-%d")
        search_query += f" pushed:>={since}"

        libraries: list[OpenSourceLibrary] = []
        try:
            payload = await self._github_get(
                "/search/repositories",
                params={
                    "q": search_query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": min(max(limit, 1), 50),
                },
            )
            for item in payload.get("items", []):
                pushed_at = item.get("pushed_at") or item.get("updated_at") or datetime.utcnow().isoformat()
                last_update = datetime.fromisoformat(pushed_at.replace("Z", "+00:00")).replace(tzinfo=None)
                libraries.append(
                    OpenSourceLibrary(
                        name=item.get("name", ""),
                        full_name=item.get("full_name", ""),
                        stars=int(item.get("stargazers_count", 0)),
                        last_update=last_update,
                        license=((item.get("license") or {}).get("spdx_id") or "Unknown"),
                        language=item.get("language") or (language or "Unknown"),
                        description=item.get("description") or "",
                        url=item.get("html_url") or "",
                        security_score=85.0,
                        maturity_score=85.0,
                    )
                )
        except Exception as exc:
            logger.warning("⚠️ GitHub API 调用失败，回退本地候选: %s", exc)
            libraries = self._fallback_libraries(query, language)
        
        logger.info(f"✅ 找到 {len(libraries)} 个开源库")
        
        return SearchResult(
            libraries=libraries,
            total_count=len(libraries),
            query=query,
        )

    async def _github_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(f"{self.base_url}{path}", params=params, headers=headers)
            response.raise_for_status()
        return response.json()

    def _fallback_libraries(self, query: str, language: Optional[str]) -> List[OpenSourceLibrary]:
        now = datetime.utcnow()
        candidates = [
            OpenSourceLibrary(
                name="requests",
                full_name="psf/requests",
                stars=52000,
                last_update=now - timedelta(days=30),
                license="Apache-2.0",
                language="Python",
                description="HTTP for Humans",
                url="https://github.com/psf/requests",
                security_score=92.0,
                maturity_score=97.0,
            ),
            OpenSourceLibrary(
                name="pydantic",
                full_name="pydantic/pydantic",
                stars=18000,
                last_update=now - timedelta(days=7),
                license="MIT",
                language="Python",
                description="Data validation using Python type hints",
                url="https://github.com/pydantic/pydantic",
                security_score=95.0,
                maturity_score=95.0,
            ),
        ]
        query_lower = query.lower()
        lang_lower = (language or "").lower()
        filtered = [
            item for item in candidates
            if (query_lower in item.description.lower() or query_lower in item.name.lower() or not query_lower)
            and (lang_lower in item.language.lower() or not lang_lower)
        ]
        return filtered or candidates


class LibraryEvaluator:
    """开源库评估器"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.min_security_score = 80.0
        self.min_maturity_score = 70.0
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
    
    async def evaluate_library(
        self,
        library: OpenSourceLibrary,
    ) -> Dict[str, Any]:
        """评估开源库
        
        Args:
            library: 开源库
            
        Returns:
            评估结果
        """
        logger.info(f"📊 评估开源库: {library.name}")
        
        # 1. 安全性评估
        security_result = await self._check_security(library)
        
        # 2. 成熟度评估
        maturity_result = await self._check_maturity(library)
        
        # 3. 依赖检查
        dependency_result = await self._check_dependencies(library)
        
        # 4. 综合评分
        overall_score = (
            security_result["score"] * 0.4 +
            maturity_result["score"] * 0.3 +
            dependency_result["score"] * 0.3
        )
        
        return {
            "library": library,
            "security": security_result,
            "maturity": maturity_result,
            "dependency": dependency_result,
            "overall_score": overall_score,
            "recommended": overall_score >= self.min_security_score,
        }
    
    async def _check_security(
        self,
        library: OpenSourceLibrary,
    ) -> Dict[str, Any]:
        """检查安全性"""
        score = float(library.security_score)
        vulnerabilities: list[str] = []

        repo_meta = await self._github_get_optional(f"/repos/{library.full_name}")
        if repo_meta:
            open_issues = int(repo_meta.get("open_issues_count", 0))
            score -= min(open_issues * 0.2, 12.0)
            security_analysis = repo_meta.get("security_and_analysis") or {}
            if security_analysis:
                score += 4.0

        alerts = await self._github_get_optional(f"/repos/{library.full_name}/dependabot/alerts")
        if isinstance(alerts, list):
            vulnerabilities = [str(item.get("security_advisory", {}).get("summary", "unknown")) for item in alerts[:10]]
            score -= len(vulnerabilities) * 6.0

        score = max(0.0, min(100.0, score))
        return {
            "score": score,
            "vulnerabilities": vulnerabilities,
            "last_audit": datetime.utcnow().isoformat(),
        }
    
    async def _check_maturity(
        self,
        library: OpenSourceLibrary,
    ) -> Dict[str, Any]:
        """检查成熟度"""
        days_since_update = (datetime.utcnow() - library.last_update).days
        score = float(library.maturity_score)
        if days_since_update > 365:
            score -= 25.0
        elif days_since_update > 180:
            score -= 12.0
        elif days_since_update < 30:
            score += 5.0

        if library.stars > 50000:
            score += 8.0
        elif library.stars > 10000:
            score += 5.0
        elif library.stars < 100:
            score -= 10.0
        score = max(0.0, min(100.0, score))
        
        return {
            "score": score,
            "days_since_update": days_since_update,
            "is_active": days_since_update < 365,
        }
    
    async def _check_dependencies(
        self,
        library: OpenSourceLibrary,
    ) -> Dict[str, Any]:
        """检查依赖"""
        score = 90.0
        dependencies: list[str] = []
        vulnerabilities: list[str] = []

        requirements = await self._get_repo_file_text(library.full_name, "requirements.txt")
        pyproject = await self._get_repo_file_text(library.full_name, "pyproject.toml")

        if requirements:
            for line in requirements.splitlines():
                normalized = line.strip()
                if normalized and not normalized.startswith("#"):
                    dependencies.append(normalized)
            pinned = [dep for dep in dependencies if any(token in dep for token in ("==", "~=", ">="))]
            if dependencies:
                pin_ratio = len(pinned) / len(dependencies)
                score += (pin_ratio - 0.5) * 20
                if pin_ratio < 0.3:
                    vulnerabilities.append("依赖版本固定率过低")
        elif pyproject:
            score += 3.0
            if "poetry.lock" not in pyproject and "uv.lock" not in pyproject:
                vulnerabilities.append("未检测到 lockfile 线索")
                score -= 5.0
        else:
            vulnerabilities.append("未发现依赖清单")
            score -= 12.0

        score = max(0.0, min(100.0, score))
        return {
            "score": score,
            "dependencies": dependencies[:80],
            "vulnerabilities": vulnerabilities,
        }

    async def _github_get_optional(self, path: str) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(f"{self.base_url}{path}", headers=headers)
            if response.status_code >= 400:
                return None
            return response.json()
        except (httpx.HTTPError, json.JSONDecodeError):
            return None

    async def _get_repo_file_text(self, full_name: str, filename: str) -> str:
        payload = await self._github_get_optional(f"/repos/{full_name}/contents/{filename}")
        if not isinstance(payload, dict):
            return ""
        content = payload.get("content")
        if not isinstance(content, str):
            return ""
        try:
            import base64

            decoded = base64.b64decode(content)
            return decoded.decode("utf-8", errors="ignore")
        except Exception:
            return ""


class OpenSourceSearcher:
    """开源库搜索与评估"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_searcher = GitHubSearcher(github_token)
        self.evaluator = LibraryEvaluator(github_token)
    
    async def find_best_library(
        self,
        requirement: str,
        min_stars: int = 100,
        max_age_days: int = 365,
    ) -> Optional[OpenSourceLibrary]:
        """找到最佳开源库
        
        Args:
            requirement: 需求描述
            min_stars: 最小星数
            max_age_days: 最近更新时间（天）
            
        Returns:
            OpenSourceLibrary or None
        """
        logger.info(f"🎯 寻找最佳开源库: {requirement}")
        
        # 1. 搜索开源库
        search_result = await self.github_searcher.search_libraries(
            query=requirement,
            min_stars=min_stars,
            max_age_days=max_age_days,
        )
        
        if not search_result.libraries:
            logger.warning(f"❌ 未找到合适的开源库: {requirement}")
            return None
        
        # 2. 评估所有库
        evaluations = []
        for library in search_result.libraries:
            evaluation = await self.evaluator.evaluate_library(library)
            evaluations.append(evaluation)
        
        # 3. 排序（按综合评分）
        evaluations.sort(key=lambda x: x["overall_score"], reverse=True)
        
        # 4. 返回最佳库
        best = evaluations[0]
        
        if best["recommended"]:
            logger.info(f"✅ 推荐开源库: {best['library'].name} (评分: {best['overall_score']:.1f})")
            return best["library"]
        else:
            logger.warning(f"⚠️ 未找到足够安全的开源库（最高评分: {best['overall_score']:.1f}）")
            return None


# 全局实例
opensource_searcher = OpenSourceSearcher()


# ========================================================================
# 测试
# ========================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        searcher = OpenSourceSearcher()
        
        # 测试搜索
        library = await searcher.find_best_library(
            requirement="http client",
            min_stars=100,
        )
        
        if library:
            print(f"最佳库: {library.name}")
            print(f"星数: {library.stars}")
            print(f"安全评分: {library.security_score}")
        else:
            print("未找到合适的开源库")
    
    asyncio.run(test())
