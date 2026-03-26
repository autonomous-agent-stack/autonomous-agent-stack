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
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

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
        self.github_token = github_token
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
        
        # TODO: 实现真实的 GitHub API 调用
        # 目前返回模拟结果
        
        libraries = [
            OpenSourceLibrary(
                name="requests",
                full_name="psf/requests",
                stars=52000,
                last_update=datetime.utcnow() - timedelta(days=30),
                license="Apache-2.0",
                language="Python",
                description="HTTP for Humans",
                url="https://github.com/psf/requests",
                security_score=95.0,
                maturity_score=98.0,
            ),
            OpenSourceLibrary(
                name="pydantic",
                full_name="pydantic/pydantic",
                stars=18000,
                last_update=datetime.utcnow() - timedelta(days=7),
                license="MIT",
                language="Python",
                description="Data validation using Python type hints",
                url="https://github.com/pydantic/pydantic",
                security_score=98.0,
                maturity_score=95.0,
            ),
        ]
        
        logger.info(f"✅ 找到 {len(libraries)} 个开源库")
        
        return SearchResult(
            libraries=libraries,
            total_count=len(libraries),
            query=query,
        )


class LibraryEvaluator:
    """开源库评估器"""
    
    def __init__(self):
        self.min_security_score = 80.0
        self.min_maturity_score = 70.0
    
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
        # TODO: 实现真实的安全检查
        # 目前返回模拟结果
        
        return {
            "score": library.security_score,
            "vulnerabilities": [],
            "last_audit": datetime.utcnow().isoformat(),
        }
    
    async def _check_maturity(
        self,
        library: OpenSourceLibrary,
    ) -> Dict[str, Any]:
        """检查成熟度"""
        # TODO: 实现真实的成熟度检查
        # 目前返回模拟结果
        
        days_since_update = (datetime.utcnow() - library.last_update).days
        
        return {
            "score": library.maturity_score,
            "days_since_update": days_since_update,
            "is_active": days_since_update < 365,
        }
    
    async def _check_dependencies(
        self,
        library: OpenSourceLibrary,
    ) -> Dict[str, Any]:
        """检查依赖"""
        # TODO: 实现真实的依赖检查
        # 目前返回模拟结果
        
        return {
            "score": 90.0,
            "dependencies": [],
            "vulnerabilities": [],
        }


class OpenSourceSearcher:
    """开源库搜索与评估"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_searcher = GitHubSearcher(github_token)
        self.evaluator = LibraryEvaluator()
    
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
