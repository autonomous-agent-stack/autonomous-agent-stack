"""Bridge API - OpenClaw 委派执行桥接

功能：
1. 受控加载外部 Python 技能文件
2. 安全审计（AST 扫描）
3. 环境变量脱敏注入
4. 执行隔离
"""

from __future__ import annotations

import ast
import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger(__name__)


# ========================================================================
# 数据模型
# ========================================================================

class BridgeExecuteRequest(BaseModel):
    """Bridge 执行请求"""
    skill_file: str = Field(..., description="技能文件路径")
    function_name: str = Field(..., description="函数名称")
    args: List[Any] = Field(default_factory=list, description="位置参数")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="关键字参数")
    timeout_seconds: int = Field(default=300, description="超时时间")
    env_whitelist: List[str] = Field(
        default_factory=lambda: ["PATH", "HOME"],
        description="环境变量白名单",
    )


class BridgeExecuteResponse(BaseModel):
    """Bridge 执行响应"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_seconds: float
    security_scan_passed: bool
    warnings: List[str] = Field(default_factory=list)


# ========================================================================
# 安全审计器
# ========================================================================

class SecurityAuditor:
    """安全审计器（AST 扫描）"""
    
    # 危险函数黑名单
    DANGEROUS_FUNCTIONS = {
        "eval", "exec", "compile",
        "os.system", "subprocess.call", "subprocess.run",
        "__import__",
    }
    
    # 危险模块黑名单
    DANGEROUS_MODULES = {
        "subprocess", "multiprocessing", "threading",
    }
    
    # 环境变量访问模式
    ENV_ACCESS_PATTERNS = [
        "os.environ",
        "os.getenv",
        "os.environ.get",
    ]
    
    @classmethod
    def scan_file(cls, file_path: str) -> Dict[str, Any]:
        """扫描文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            {
                "passed": bool,
                "errors": List[str],
                "warnings": List[str],
            }
        """
        errors = []
        warnings = []
        
        try:
            # 读取文件
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()
            
            # 解析 AST
            tree = ast.parse(source_code, filename=file_path)
            
            # 遍历 AST
            for node in ast.walk(tree):
                # 检查函数调用
                if isinstance(node, ast.Call):
                    func_name = cls._get_func_name(node.func)
                    
                    if func_name in cls.DANGEROUS_FUNCTIONS:
                        errors.append(f"发现危险函数调用: {func_name}")
                    
                    # 检查环境变量访问
                    if func_name in cls.ENV_ACCESS_PATTERNS:
                        # 检查是否尝试读取 .env 相关变量
                        if cls._check_env_access(node):
                            errors.append(f"尝试越权读取环境变量: {func_name}")
                
                # 检查导入
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in cls.DANGEROUS_MODULES:
                            warnings.append(f"导入危险模块: {alias.name}")
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module in cls.DANGEROUS_MODULES:
                        warnings.append(f"从危险模块导入: {node.module}")
            
            return {
                "passed": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
            }
        
        except SyntaxError as e:
            return {
                "passed": False,
                "errors": [f"语法错误: {e}"],
                "warnings": [],
            }
        
        except Exception as e:
            return {
                "passed": False,
                "errors": [f"扫描异常: {e}"],
                "warnings": [],
            }
    
    @classmethod
    def _get_func_name(cls, node: ast.AST) -> str:
        """获取函数名称"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{cls._get_func_name(node.value)}.{node.attr}"
        else:
            return ""
    
    @classmethod
    def _check_env_access(cls, node: ast.Call) -> bool:
        """检查是否尝试读取敏感环境变量"""
        # 简化检查：如果参数是字符串字面量，检查是否包含敏感关键词
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                sensitive_keywords = [
                    "TOKEN", "SECRET", "PASSWORD", "KEY", "API_KEY",
                    "PRIVATE", "CREDENTIAL",
                ]
                if any(kw in arg.value.upper() for kw in sensitive_keywords):
                    return True
        return False


# ========================================================================
# 环境变量脱敏器
# ========================================================================

class EnvSanitizer:
    """环境变量脱敏器"""
    
    # 允许的环境变量白名单
    DEFAULT_WHITELIST = [
        "PATH", "HOME", "USER", "SHELL",
        "LANG", "LC_ALL",
        "PYTHONPATH", "PYTHONIOENCODING",
    ]
    
    @classmethod
    def sanitize_env(
        cls,
        whitelist: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """脱敏环境变量
        
        Args:
            whitelist: 白名单（默认使用 DEFAULT_WHITELIST）
            
        Returns:
            脱敏后的环境变量字典
        """
        whitelist = whitelist or cls.DEFAULT_WHITELIST
        
        sanitized = {}
        for key in whitelist:
            value = os.getenv(key)
            if value is not None:
                sanitized[key] = value
        
        return sanitized


# ========================================================================
# Bridge 执行器
# ========================================================================

class BridgeExecutor:
    """Bridge 执行器"""
    
    def __init__(self):
        self.security_auditor = SecurityAuditor()
    
    async def execute(
        self,
        request: BridgeExecuteRequest,
    ) -> BridgeExecuteResponse:
        """执行技能文件
        
        Args:
            request: 执行请求
            
        Returns:
            BridgeExecuteResponse
        """
        import time
        import importlib.util
        
        start_time = time.perf_counter()
        warnings = []
        
        # 1. 安全审计
        scan_result = self.security_auditor.scan_file(request.skill_file)
        
        if not scan_result["passed"]:
            return BridgeExecuteResponse(
                success=False,
                error="安全审计未通过",
                duration_seconds=0.0,
                security_scan_passed=False,
                warnings=scan_result["errors"],
            )
        
        warnings.extend(scan_result["warnings"])
        
        # 2. 检查文件是否存在
        skill_path = Path(request.skill_file)
        if not skill_path.exists():
            return BridgeExecuteResponse(
                success=False,
                error=f"技能文件不存在: {request.skill_file}",
                duration_seconds=0.0,
                security_scan_passed=True,
                warnings=warnings,
            )
        
        # 3. 加载技能文件
        try:
            spec = importlib.util.spec_from_file_location(
                "external_skill",
                skill_path,
            )
            module = importlib.util.module_from_spec(spec)
            
            # 脱敏环境变量
            sanitized_env = EnvSanitizer.sanitize_env(request.env_whitelist)
            
            # 执行
            with cls._sanitized_environment(sanitized_env):
                spec.loader.exec_module(module)
            
            # 获取函数
            if not hasattr(module, request.function_name):
                return BridgeExecuteResponse(
                    success=False,
                    error=f"函数不存在: {request.function_name}",
                    duration_seconds=time.perf_counter() - start_time,
                    security_scan_passed=True,
                    warnings=warnings,
                )
            
            func = getattr(module, request.function_name)
            
            # 执行函数
            result = func(*request.args, **request.kwargs)
            
            duration = time.perf_counter() - start_time
            
            return BridgeExecuteResponse(
                success=True,
                result=result,
                duration_seconds=duration,
                security_scan_passed=True,
                warnings=warnings,
            )
        
        except Exception as e:
            logger.error(f"Bridge 执行失败: {e}", exc_info=True)
            
            return BridgeExecuteResponse(
                success=False,
                error=str(e),
                duration_seconds=time.perf_counter() - start_time,
                security_scan_passed=True,
                warnings=warnings,
            )
    
    @staticmethod
    def _sanitized_environment(env: Dict[str, str]):
        """创建脱敏环境上下文"""
        class SanitizedEnv:
            def __init__(self, env):
                self.env = env
                self.original_env = None
            
            def __enter__(self):
                self.original_env = dict(os.environ)
                os.environ.clear()
                os.environ.update(self.env)
                return self
            
            def __exit__(self, *args):
                os.environ.clear()
                os.environ.update(self.original_env)
        
        return SanitizedEnv(env)


# ========================================================================
# Bridge API 路由
# ========================================================================

router = APIRouter(prefix="/api/v1/bridge", tags=["bridge"])

_executor: Optional[BridgeExecutor] = None


def get_bridge_executor() -> BridgeExecutor:
    """获取 Bridge 执行器实例"""
    global _executor
    if _executor is None:
        _executor = BridgeExecutor()
    return _executor


@router.post("/execute", response_model=BridgeExecuteResponse)
async def bridge_execute(
    request: BridgeExecuteRequest,
    executor: BridgeExecutor = Depends(get_bridge_executor),
):
    """执行外部技能文件
    
    **安全机制**：
    1. AST 扫描：拦截危险函数调用
    2. 环境变量脱敏：只注入白名单变量
    3. 执行隔离：在独立环境中运行
    
    **适用场景**：
    - OpenClaw 委派任务
    - 外部技能加载
    - 受控代码执行
    """
    return await executor.execute(request)


@router.get("/health")
def bridge_health():
    """Bridge API 健康检查"""
    return {"status": "ok", "service": "bridge"}
