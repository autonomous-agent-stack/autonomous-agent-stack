"""Docker 沙盒测试运行器 (简化版)

功能：
1. 拉起 Docker 容器
2. 运行玛露业务测试
3. AppleDouble 清理
4. Exit Code 捕获
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class SandboxTestResult:
    """沙盒测试结果"""
    success: bool
    exit_code: int
    logs: str
    test_passed: int
    test_failed: int
    violations: List[str]


class AppleDoubleCleaner:
    """AppleDouble 脏文件清理器"""
    
    @staticmethod
    def clean(directory: str) -> int:
        """清理目录下所有 ._ 开头的文件"""
        cleaned_count = 0
        dir_path = Path(directory)
        
        if not dir_path.exists():
            logger.warning(f"目录不存在: {directory}")
            return 0
        
        for apple_file in dir_path.rglob("._*"):
            try:
                apple_file.unlink()
                cleaned_count += 1
                logger.debug(f"已删除: {apple_file}")
            except Exception as e:
                logger.warning(f"删除失败 {apple_file}: {e}")
        
        logger.info(f"✅ 清理了 {cleaned_count} 个 AppleDouble 文件")
        return cleaned_count


class Sandbox_Test_Runner:
    """Docker 沙盒测试运行器"""
    
    def __init__(
        self,
        docker_image: str = "python:3.11-slim",
        timeout_seconds: int = 300,
        clean_appledouble: bool = True,
    ):
        self.docker_image = docker_image
        self.timeout_seconds = timeout_seconds
        self.clean_appledouble = clean_appledouble
        
        # 玛露业务红线关键词
        self.malu_required_keywords = [
            "6g罐装",
            "挑战游泳级别持妆",
            "不用调色",
            "遮瑕力强",
        ]
        
        # 禁止词汇
        self.forbidden_terms = [
            "平替",
            "代工厂",
            "批发",
            "清仓",
            "甩卖",
            "廉价",
        ]
    
    async def run_tests_in_sandbox(
        self,
        pr_branch: str,
        repo_path: str,
        test_command: str = "pytest tests/ -v --tb=short",
    ) -> SandboxTestResult:
        """在 Docker 沙盒中运行测试"""
        logger.info(f"🚀 启动沙盒测试: {pr_branch}")
        
        # 1. 清理 AppleDouble 文件
        if self.clean_appledouble:
            cleaned = AppleDoubleCleaner.clean(repo_path)
            logger.info(f"🗑️ 清理 AppleDouble: {cleaned} 个文件")
        
        # 2. 执行 Docker 命令
        start_time = time.time()
        try:
            docker_cmd = self._build_docker_command(repo_path, test_command)
            
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            
            exit_code = result.returncode
            logs = result.stdout + result.stderr
            elapsed = time.time() - start_time
            
            logger.info(f"⏱️ 测试耗时: {elapsed:.2f}s")
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ 测试超时 ({self.timeout_seconds}s)")
            return SandboxTestResult(
                success=False,
                exit_code=124,
                logs=f"测试超时 ({self.timeout_seconds}s)",
                test_passed=0,
                test_failed=0,
                violations=["测试超时"],
            )
        except Exception as e:
            logger.error(f"❌ Docker 执行失败: {e}")
            return SandboxTestResult(
                success=False,
                exit_code=1,
                logs=str(e),
                test_passed=0,
                test_failed=0,
                violations=[f"Docker 执行失败: {e}"],
            )
        
        # 3. 解析测试结果
        test_passed, test_failed = self._parse_test_results(logs)
        
        # 4. 玛露业务断言检查
        violations = self._check_malu_business_rules(logs)
        
        # 5. 构建结果
        success = (exit_code == 0) and (test_failed == 0) and (len(violations) == 0)
        
        return SandboxTestResult(
            success=success,
            exit_code=exit_code,
            logs=logs,
            test_passed=test_passed,
            test_failed=test_failed,
            violations=violations,
        )
    
    def _build_docker_command(self, repo_path: str, test_command: str) -> List[str]:
        """构建 Docker 命令"""
        return [
            "docker", "run", "--rm",
            "-v", f"{repo_path}:/app:ro",
            "-w", "/app",
            self.docker_image,
            "sh", "-c",
            f"pip install -q pytest && {test_command}",
        ]
    
    def _parse_test_results(self, logs: str) -> tuple[int, int]:
        """解析测试结果"""
        passed_match = re.search(r"(\d+) passed", logs)
        failed_match = re.search(r"(\d+) failed", logs)
        
        passed = int(passed_match.group(1)) if passed_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0
        
        return passed, failed
    
    def _check_malu_business_rules(self, logs: str) -> List[str]:
        """检查玛露业务红线"""
        violations = []
        
        # 检查必需关键词
        for keyword in self.malu_required_keywords:
            if "玛露" in logs or "文案" in logs:
                if keyword not in logs:
                    violations.append(f"缺少必需关键词: {keyword}")
        
        # 检查禁止词汇
        for term in self.forbidden_terms:
            if term in logs:
                violations.append(f"包含禁止词汇: {term}")
        
        return violations


# 测试
if __name__ == "__main__":
    import asyncio
    
    async def test():
        runner = Sandbox_Test_Runner()
        
        # 测试清理 AppleDouble
        cleaned = AppleDoubleCleaner.clean("/tmp")
        print(f"✅ 清理了 {cleaned} 个 AppleDouble 文件")
    
    asyncio.run(test())
