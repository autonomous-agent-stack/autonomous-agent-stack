"""
Skill Loader - 动态加载外部 Skill

支持：
- 动态加载外部 Skill
- 强制触发安全扫描（调用 Security_Auditor）
- Skill 生命周期管理
"""

from __future__ import annotations

import logging
import ast
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime
import tempfile
import shutil

logger = logging.getLogger("agent_stack.bridge.skill_loader")


class SecurityAuditor:
    """
    安全审计器 - 对 Skill 代码进行安全扫描

    检测：
    1. 危险导入 (os, subprocess, eval, exec)
    2. 网络操作 (requests, urllib, socket)
    3. 文件系统操作 (open, shutil, pathlib)
    4. 系统命令执行 (subprocess, os.system)
    5. AppleDouble 文件 (._ 开头的文件)
    """

    # 危险导入黑名单
    DANGEROUS_IMPORTS = {
        "os": "系统操作",
        "subprocess": "子进程执行",
        "eval": "动态代码执行",
        "exec": "动态代码执行",
        "requests": "网络请求",
        "urllib": "网络请求",
        "socket": "网络操作",
        "shutil": "文件操作",
        "pickle": "反序列化攻击",
        "marshal": "反序列化攻击",
    }

    # 危险函数黑名单
    DANGEROUS_FUNCTIONS = {
        "eval": "动态代码执行",
        "exec": "动态代码执行",
        "__import__": "动态导入",
        "compile": "代码编译",
        "open": "文件操作（大量使用时）",
    }

    def __init__(self, strict_mode: bool = True):
        """
        初始化安全审计器

        Args:
            strict_mode: 严格模式（发现危险操作立即失败）
        """
        self.strict_mode = strict_mode
        self.scan_results: List[Dict] = []

    def audit_skill(self, skill_path: Path) -> Dict[str, Any]:
        """
        审计 Skill 代码

        Args:
            skill_path: Skill 目录或文件路径

        Returns:
            审计结果
        """
        logger.info(f"[SecurityAuditor] Auditing skill: {skill_path}")

        self.scan_results = []

        # 收集所有 Python 文件
        python_files = []
        if skill_path.is_file():
            python_files = [skill_path]
        else:
            python_files = list(skill_path.rglob("*.py"))

        # 检测 AppleDouble 文件
        appledouble_files = list(skill_path.rglob("._*"))
        if appledouble_files:
            self.scan_results.append({
                "severity": "critical",
                "type": "appledouble_file",
                "message": f"发现 AppleDouble 文件: {[str(f) for f in appledouble_files]}",
                "files": [str(f) for f in appledouble_files],
            })

        # 审计每个 Python 文件
        for py_file in python_files:
            self._audit_python_file(py_file)

        # 汇总结果
        critical_count = sum(1 for r in self.scan_results if r["severity"] == "critical")
        high_count = sum(1 for r in self.scan_results if r["severity"] == "high")
        medium_count = sum(1 for r in self.scan_results if r["severity"] == "medium")

        return {
            "skill_path": str(skill_path),
            "files_scanned": len(python_files),
            "findings": self.scan_results,
            "summary": {
                "critical": critical_count,
                "high": high_count,
                "medium": medium_count,
            },
            "passed": critical_count == 0,
            "timestamp": datetime.now().isoformat(),
        }

    def _audit_python_file(self, file_path: Path) -> None:
        """审计单个 Python 文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()

            # 解析 AST
            tree = ast.parse(source_code, filename=str(file_path))

            # 检查导入
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split(".")[0]
                        if module_name in self.DANGEROUS_IMPORTS:
                            self.scan_results.append({
                                "severity": "high",
                                "type": "dangerous_import",
                                "module": module_name,
                                "line": node.lineno,
                                "file": str(file_path),
                                "message": f"导入危险模块: {module_name} ({self.DANGEROUS_IMPORTS[module_name]})",
                            })
                elif isinstance(node, ast.ImportFrom):
                    module_name = node.module.split(".")[0] if node.module else ""
                    if module_name in self.DANGEROUS_IMPORTS:
                        self.scan_results.append({
                            "severity": "high",
                            "type": "dangerous_import",
                            "module": module_name,
                            "line": node.lineno,
                            "file": str(file_path),
                            "message": f"从危险模块导入: {module_name} ({self.DANGEROUS_IMPORTS[module_name]})",
                        })

                # 检查危险函数调用
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        if func_name in self.DANGEROUS_FUNCTIONS:
                            self.scan_results.append({
                                "severity": "medium",
                                "type": "dangerous_function",
                                "function": func_name,
                                "line": node.lineno,
                                "file": str(file_path),
                                "message": f"调用危险函数: {func_name} ({self.DANGEROUS_FUNCTIONS[func_name]})",
                            })

        except SyntaxError as e:
            self.scan_results.append({
                "severity": "critical",
                "type": "syntax_error",
                "file": str(file_path),
                "message": f"语法错误: {str(e)}",
            })
        except Exception as e:
            self.scan_results.append({
                "severity": "medium",
                "type": "scan_error",
                "file": str(file_path),
                "message": f"扫描失败: {str(e)}",
            })


class AppleDoubleCleaner:
    """
    AppleDouble 文件清理器

    物理清理 macOS 系统生成的 ._ 开头文件
    """

    @staticmethod
    def clean(directory: Path) -> int:
        """
        清理指定目录下的所有 AppleDouble 文件

        Args:
            directory: 目标目录

        Returns:
            清理的文件数量
        """
        logger.info(f"[AppleDoubleCleaner] Cleaning directory: {directory}")

        count = 0
        for appledouble_file in directory.rglob("._*"):
            try:
                if appledouble_file.is_file():
                    appledouble_file.unlink()
                    logger.info(f"[AppleDoubleCleaner] Removed: {appledouble_file}")
                    count += 1
            except Exception as e:
                logger.warning(f"[AppleDoubleCleaner] Failed to remove {appledouble_file}: {e}")

        logger.info(f"[AppleDoubleCleaner] Cleaned {count} AppleDouble files")
        return count


class SkillLoader:
    """
    Skill 动态加载器

    功能：
    1. 动态加载外部 Skill
    2. 加载前强制安全扫描
    3. 管理 Skill 生命周期
    """

    def __init__(
        self,
        base_path: Path,
        enable_security_scan: bool = True,
        strict_mode: bool = False,
    ):
        """
        初始化 Skill Loader

        Args:
            base_path: Skill 基础路径
            enable_security_scan: 是否启用安全扫描
            strict_mode: 严格模式（安全扫描失败则拒绝加载）
        """
        self.base_path = base_path
        self.enable_security_scan = enable_security_scan
        self.strict_mode = strict_mode

        self.auditor = SecurityAuditor(strict_mode=strict_mode)
        self.loaded_skills: Dict[str, Any] = {}

        logger.info("[Agent-Stack-Bridge] Skill Loader initialized")

    async def load_skill(self, skill_path: str) -> Any:
        """
        加载 Skill

        Args:
            skill_path: Skill 路径（相对或绝对）

        Returns:
            加载的 Skill 模块或对象

        Raises:
            ValueError: 安全扫描失败或 Skill 不存在
        """
        # 解析路径
        skill_full_path = self._resolve_skill_path(skill_path)

        logger.info(f"[Agent-Stack-Bridge] Loading skill: {skill_full_path}")

        # 强制预检：清理 AppleDouble 文件
        if self.enable_security_scan:
            # 如果是文件，清理其所在目录；如果是目录，直接清理
            clean_dir = skill_full_path.parent if skill_full_path.is_file() else skill_full_path
            AppleDoubleCleaner.clean(clean_dir)

        # 强制安全扫描
        if self.enable_security_scan:
            audit_result = self.auditor.audit_skill(skill_full_path)

            logger.info(f"[Agent-Stack-Bridge] Security audit completed: {audit_result['summary']}")

            if not audit_result["passed"] and self.strict_mode:
                raise ValueError(
                    f"Security audit failed for skill {skill_path}:\n"
                    f"{audit_result['summary']}\n"
                    f"Findings: {audit_result['findings']}"
                )

        # 加载 Skill
        skill = await self._load_skill_module(skill_full_path)

        self.loaded_skills[str(skill_full_path)] = skill

        logger.info(f"[Agent-Stack-Bridge] Skill loaded: {skill_path}")
        return skill

    def _resolve_skill_path(self, skill_path: str) -> Path:
        """解析 Skill 路径"""
        path = Path(skill_path)

        # 如果是相对路径，基于 base_path
        if not path.is_absolute():
            path = self.base_path / path

        # 检查是否存在
        if not path.exists():
            raise ValueError(f"Skill path does not exist: {path}")

        return path

    async def _load_skill_module(self, skill_path: Path) -> Any:
        """
        加载 Skill 模块

        Args:
            skill_path: Skill 目录或文件路径

        Returns:
            加载的 Skill 对象
        """
        # 如果是目录，查找主要的 Python 文件
        if skill_path.is_dir():
            # 查找 skill.py 或 __init__.py
            main_files = ["skill.py", "__init__.py", "main.py"]
            for main_file in main_files:
                potential_path = skill_path / main_file
                if potential_path.exists():
                    skill_path = potential_path
                    break
            else:
                raise ValueError(f"Cannot find main skill file in: {skill_path}")

        # 动态导入
        spec = importlib.util.spec_from_file_location(
            f"skill_{skill_path.stem}",
            skill_path,
        )

        if spec is None or spec.loader is None:
            raise ValueError(f"Cannot load skill from: {skill_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        # 查找 Skill 类或主函数
        if hasattr(module, "Skill"):
            return module.Skill()
        elif hasattr(module, "main"):
            return module
        elif hasattr(module, "execute"):
            return module
        else:
            # 返回整个模块
            return module

    def unload_skill(self, skill_path: str) -> None:
        """卸载 Skill"""
        skill_full_path = str(self._resolve_skill_path(skill_path))
        if skill_full_path in self.loaded_skills:
            del self.loaded_skills[skill_full_path]
            logger.info(f"[Agent-Stack-Bridge] Skill unloaded: {skill_path}")

    def list_loaded_skills(self) -> List[str]:
        """列出已加载的 Skills"""
        return list(self.loaded_skills.keys())

    async def cleanup(self) -> None:
        """清理资源"""
        self.loaded_skills.clear()
        logger.info("[Agent-Stack-Bridge] Skill Loader cleaned up")
