"""Docker 沙盒测试运行器 (S1, QA1)

功能：
1. 拉起挂载新代码的 Docker 容器
2. 执行前清理 AppleDouble 脏文件
3. 运行玛露业务断言测试
4. 捕获 Exit Code 决定放行/打回
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class SandboxTestResult:
    """沙盒测试结果"""
    success: bool
    exit_code: int
    logs: str
    test_passed: int
    test_failed: int
    malu_business_check: bool
    violations: List[str]


class AppleDoubleCleaner:
    """AppleDouble 脏文件清理器"""
    
    @staticmethod
    def clean(directory: str) -> int:
        """清理目录下所有 ._ 开头的文件
        
        Args:
            directory: 要清理的目录
            
        Returns:
            清理的文件数量
        """
        cleaned_count = 0
        dir_path = Path(directory)
        
        if not dir_path.exists():
            logger.warning(f"目录不存在: {directory}")
            return 0
        
        # 查找所有 ._ 开头的文件
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
        
        # 禁止词汇（工厂化）
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
        """在 Docker 沙盒中运行测试
        
        Args:
            pr_branch: PR 分支名
            repo_path: 仓库路径
            test_command: 测试命令
            
        Returns:
            SandboxTestResult
        """
        logger.info(f"🚀 启动沙盒测试: {pr_branch}")
        
        # 1. 清理 AppleDouble 文件（红线：必须在测试前执行）
        if self.clean_appledouble:
            cleaned = AppleDoubleCleaner.clean(repo_path)
            logger.info(f"🗑️ 清理 AppleDouble: {cleaned} 个文件")
        
        # 2. 创建临时目录用于测试结果
        with tempfile.TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir) / "test_results"
            results_dir.mkdir()
            
            # 3. 构建 Docker 命令
            docker_cmd = self._build_docker_command(
                repo_path=repo_path,
                test_command=test_command,
                results_dir=str(results_dir),
            )
            
            # 4. 执行 Docker 容器
            start_time = time.time()
            try:
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
                    exit_code=124,  # Timeout exit code
                    logs=f"测试超时 ({self.timeout_seconds}s)",
                    test_passed=0,
                    test_failed=0,
                    malu_business_check=False,
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
                    malu_business_check=False,
                    violations=[f"Docker 执行失败: {e}"],
                )
        
        # 5. 解析测试结果
        test_passed, test_failed = self._parse_test_results(logs)
        
        # 6. 玛露业务断言检查
        malu_check, violations = self._check_malu_business_rules(logs)
        
        # 7. 构建结果
        success = (exit_code == 0) and malu_check and (test_failed == 0)
        
        return SandboxTestResult(
            success=success,
            exit_code=exit_code,
            logs=logs,
            test_passed=test_passed,
            test_failed=test_failed,
            malu_business_check=malu_check,
            violations=violations,
        )
    
    def _build_docker_command(
        self,
        repo_path: str,
        test_command: str,
        results_dir: str,
    ) -> List[str]:
        """构建 Docker 命令"""
        return [
            "docker", "run", "--rm",
            "-v", f"{repo_path}:/app:ro",
            "-v", f"{results_dir}:/results",
            "-w", "/app",
            self.docker_image,
            "sh", "-c",
            f"pip install -q pytest && {test_command}",
        ]
    
    def _parse_test_results(self, logs: str) -> tuple[int, int]:
        """解析测试结果"""
        # 提取 passed 和 failed 数量
        passed_match = re.search(r"(\d+) passed", logs)
        failed_match = re.search(r"(\d+) failed", logs)
        
        passed = int(passed_match.group(1)) if passed_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0
        
        return passed, failed
    
    def _check_malu_business_rules(self, logs: str) -> tuple[bool, List[str]]:
        """检查玛露业务红线"""
        violations = []
        
        # 检查必需关键词（如果有文案相关测试）
        for keyword in self.malu_required_keywords:
            # 仅检查包含 "玛露" 或 "文案" 的测试输出
            if "玛露" in logs or "文案" in logs:
                if keyword not in logs:
                    violations.append(f"缺少必需关键词: {keyword}")
        
        # 检查禁止词汇
        for term in self.forbidden_terms:
            if term in logs:
                violations.append(f"包含禁止词汇: {term}")
        
        malu_check = len(violations) == 0
        return malu_check, violations


# ========================================================================
# 测试
# ========================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        runner = Sandbox_Test_Runner()
        
        # 测试清理 AppleDouble
        cleaned = AppleDoubleCleaner.clean("/tmp")
        print(f"✅ 清理了 {cleaned} 个 AppleDouble 文件")
        
        # 测试沙盒运行（需要 Docker）
        # result = await runner.run_tests_in_sandbox(
        #     pr_branch="feature/test",
        #     repo_path="/path/to/repo",
        # )
        # print(f"测试结果: {result.success}")
    
    asyncio.run(test())
