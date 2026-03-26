"""P4 自我进化协议：触发与解析模块

功能：
1. 接收外部 GitHub 链接
2. 分配专用研发 Agent
3. 拉取源码
4. 解析核心协议
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProtocolSpec:
    """协议规范"""
    name: str
    version: str
    api_endpoints: List[Dict[str, str]]
    data_formats: List[Dict[str, str]]
    auth_methods: List[str]
    dependencies: List[str]
    test_cases: List[Dict[str, Any]]


class IntegrationAgent:
    """集成 Agent"""
    
    def __init__(
        self,
        model: str = "claude-3-opus",
        workspace: str = "/tmp/integration",
    ):
        self.model = model
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
    
    async def execute(self, command: str) -> str:
        """执行命令"""
        logger.info(f"🔧 执行命令: {command}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self.workspace,
            )
            
            if result.returncode != 0:
                logger.error(f"❌ 命令失败: {result.stderr}")
                raise RuntimeError(f"命令执行失败: {result.stderr}")
            
            return result.stdout
        
        except subprocess.TimeoutExpired:
            logger.error("⏰ 命令超时")
            raise RuntimeError("命令执行超时")
    
    async def clone_repo(self, repo_url: str) -> Path:
        """克隆仓库"""
        logger.info(f"📥 克隆仓库: {repo_url}")
        
        # 提取仓库名
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        repo_path = self.workspace / repo_name
        
        # 克隆仓库
        await self.execute(f"git clone {repo_url} {repo_path}")
        
        logger.info(f"✅ 仓库已克隆: {repo_path}")
        return repo_path
    
    async def analyze_protocol(self, repo_path: Path) -> ProtocolSpec:
        """分析协议"""
        logger.info(f"🔍 分析协议: {repo_path}")

        py_files = [path for path in repo_path.rglob("*.py") if ".git" not in path.parts]
        text_files = [path for path in repo_path.rglob("*") if path.is_file()]

        version = "0.1.0"
        pyproject_file = repo_path / "pyproject.toml"
        if pyproject_file.exists():
            text = pyproject_file.read_text(encoding="utf-8", errors="ignore")
            match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', text)
            if match:
                version = match.group(1)

        endpoint_patterns = [
            re.compile(r'@[\w\.]+\.get\(["\']([^"\']+)["\']'),
            re.compile(r'@[\w\.]+\.post\(["\']([^"\']+)["\']'),
            re.compile(r'@[\w\.]+\.put\(["\']([^"\']+)["\']'),
            re.compile(r'@[\w\.]+\.delete\(["\']([^"\']+)["\']'),
        ]
        api_endpoints: list[dict[str, str]] = []
        seen_endpoints: set[tuple[str, str]] = set()
        for path in py_files:
            source = path.read_text(encoding="utf-8", errors="ignore")
            for method, pattern in zip(["GET", "POST", "PUT", "DELETE"], endpoint_patterns):
                for match in pattern.finditer(source):
                    endpoint = match.group(1).strip()
                    key = (method, endpoint)
                    if key in seen_endpoints:
                        continue
                    seen_endpoints.add(key)
                    api_endpoints.append({"method": method, "path": endpoint})

        dependency_candidates: set[str] = set()
        requirements_txt = repo_path / "requirements.txt"
        if requirements_txt.exists():
            for line in requirements_txt.read_text(encoding="utf-8", errors="ignore").splitlines():
                normalized = line.strip()
                if normalized and not normalized.startswith("#"):
                    dependency_candidates.add(re.split(r"[<>=~!]", normalized)[0].strip())
        if pyproject_file.exists():
            text = pyproject_file.read_text(encoding="utf-8", errors="ignore")
            for match in re.finditer(r'["\']([a-zA-Z0-9_\-]+(?:\[[a-zA-Z0-9_,\-]+\])?)', text):
                token = match.group(1)
                if token and token[0].isalpha():
                    dependency_candidates.add(token.split("[", 1)[0])

        text_blob = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")[:6000]
            for path in text_files[:30]
        ).lower()
        data_formats: list[dict[str, str]] = []
        if "json" in text_blob:
            data_formats.append({"type": "json", "schema": "dynamic"})
        if "yaml" in text_blob or ".yml" in text_blob:
            data_formats.append({"type": "yaml", "schema": "dynamic"})
        if "xml" in text_blob:
            data_formats.append({"type": "xml", "schema": "dynamic"})
        if not data_formats:
            data_formats.append({"type": "text", "schema": "unknown"})

        auth_methods: list[str] = []
        auth_keywords = {
            "bearer": "bearer",
            "jwt": "jwt",
            "oauth": "oauth2",
            "apikey": "api_key",
            "api-key": "api_key",
            "basic auth": "basic",
        }
        for keyword, method in auth_keywords.items():
            if keyword in text_blob and method not in auth_methods:
                auth_methods.append(method)
        if not auth_methods:
            auth_methods.append("none")

        test_cases: list[dict[str, Any]] = []
        if any(endpoint["path"].endswith("/health") or "health" in endpoint["path"] for endpoint in api_endpoints):
            test_cases.append({"name": "test_health_endpoint", "expected": "200"})
        if api_endpoints:
            test_cases.append({"name": "test_api_schema", "expected": "valid_response"})
        if auth_methods and auth_methods != ["none"]:
            test_cases.append({"name": "test_auth_flow", "expected": "authorized"})
        if not test_cases:
            test_cases.append({"name": "test_import_module", "expected": "success"})

        protocol_name = repo_path.name.replace("_", "-")

        return ProtocolSpec(
            name=protocol_name,
            version=version,
            api_endpoints=api_endpoints or [{"method": "GET", "path": "/"}],
            data_formats=data_formats,
            auth_methods=auth_methods,
            dependencies=sorted(item for item in dependency_candidates if item)[:50],
            test_cases=test_cases,
        )


class TriggerAndParse:
    """触发与解析模块"""
    
    def __init__(self):
        self.agent = IntegrationAgent()
    
    async def parse_github_repo(self, repo_url: str) -> ProtocolSpec:
        """解析 GitHub 仓库协议
        
        Args:
            repo_url: GitHub 仓库 URL
            
        Returns:
            ProtocolSpec
        """
        logger.info(f"🚀 开始解析: {repo_url}")
        
        # 1. 克隆仓库
        repo_path = await self.agent.clone_repo(repo_url)
        
        # 2. 分析协议
        spec = await self.agent.analyze_protocol(repo_path)
        
        logger.info(f"✅ 协议解析完成: {spec.name}")
        return spec


# 全局实例
trigger_and_parse = TriggerAndParse()


# ========================================================================
# 测试
# ========================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        tap = TriggerAndParse()
        
        # 测试解析 GitHub 仓库
        spec = await tap.parse_github_repo(
            "https://github.com/example/example.git"
        )
        
        print(f"协议名称: {spec.name}")
        print(f"版本: {spec.version}")
        print(f"API 端点: {spec.api_endpoints}")
    
    asyncio.run(test())
