"""
安全集成 Hooks

提供统一的安全 Hook 接口，整合 AppleDouble 清理、AST 审计和 WebAuthn 验证。
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable
from functools import wraps
from dataclasses import dataclass

from .apple_double_cleaner import AppleDoubleCleaner
from .ast_auditor import ASTAuditor, SecurityException
from .webauthn_trigger import WebAuthnTrigger

logger = logging.getLogger(__name__)


@dataclass
class HookResult:
    """Hook 执行结果"""
    success: bool
    hook_name: str
    message: str
    details: Dict[str, Any]


class SecurityHooks:
    """
    安全集成 Hooks
    
    提供：
    - pre_task_hook: 任务执行前的安全检查
    - pre_sensitive_hook: 敏感操作前的验证
    - pre_code_execution_hook: 代码执行前的审计
    """
    
    # 全局配置
    _enabled: bool = True
    _strict_mode: bool = False
    _auto_clean: bool = True
    
    # 审计器实例
    _ast_auditor: Optional[ASTAuditor] = None
    
    # 回调注册
    _on_security_violation: Optional[Callable] = None
    
    @classmethod
    def initialize(
        cls,
        enabled: bool = True,
        strict_mode: bool = False,
        auto_clean: bool = True
    ) -> None:
        """
        初始化安全 Hooks
        
        Args:
            enabled: 是否启用安全检查
            strict_mode: 严格模式（更低的容忍度）
            auto_clean: 是否自动清理 AppleDouble 文件
        """
        cls._enabled = enabled
        cls._strict_mode = strict_mode
        cls._auto_clean = auto_clean
        cls._ast_auditor = ASTAuditor(strict_mode=strict_mode)
        
        logger.info("[Agent-Stack-Bridge] Security hooks initialized")
        logger.info(f"  - enabled: {enabled}")
        logger.info(f"  - strict_mode: {strict_mode}")
        logger.info(f"  - auto_clean: {auto_clean}")
    
    @classmethod
    def set_violation_callback(cls, callback: Callable) -> None:
        """设置安全违规回调"""
        cls._on_security_violation = callback
    
    @classmethod
    async def pre_task_hook(
        cls,
        code: Optional[str] = None,
        working_dir: str = "."
    ) -> HookResult:
        """
        任务执行前的安全 Hook
        
        执行：
        1. 清理 AppleDouble 文件（如果启用）
        2. 扫描代码（如果提供）
        3. 检查环境安全
        
        Args:
            code: 要执行的代码（可选）
            working_dir: 工作目录
            
        Returns:
            HookResult
        """
        if not cls._enabled:
            return HookResult(
                success=True,
                hook_name="pre_task_hook",
                message="安全检查已禁用",
                details={"skipped": True}
            )
        
        details = {}
        
        try:
            # 1. 清理 AppleDouble
            if cls._auto_clean:
                cleaner = AppleDoubleCleaner()
                clean_result = cleaner.clean_directory(working_dir)
                details["apple_double_cleaned"] = clean_result["cleaned_files"]
                details["freed_bytes"] = clean_result["freed_bytes"]
                
                logger.info(
                    f"[Agent-Stack-Bridge] AppleDouble cleaned: "
                    f"{clean_result['cleaned_files']} files"
                )
            
            # 2. 代码审计
            if code:
                if cls._ast_auditor is None:
                    cls._ast_auditor = ASTAuditor(strict_mode=cls._strict_mode)
                
                audit_result = cls._ast_auditor.scan_code(code)
                details["code_audit"] = {
                    "safe": audit_result["safe"],
                    "issues_count": len(audit_result["issues"])
                }
                
                logger.info(
                    f"[Agent-Stack-Bridge] AST scan complete: "
                    f"{len(audit_result['issues'])} issues"
                )
                
                if not audit_result["safe"]:
                    # 检查是否有高危问题
                    high_severity_issues = [
                        i for i in audit_result["issues"]
                        if i["severity"] in ("high", "critical")
                    ]
                    
                    if high_severity_issues or cls._strict_mode:
                        await cls._handle_violation("code_audit", audit_result["issues"])
                        
                        return HookResult(
                            success=False,
                            hook_name="pre_task_hook",
                            message="代码审计发现安全问题",
                            details=details
                        )
            
            return HookResult(
                success=True,
                hook_name="pre_task_hook",
                message="安全检查通过",
                details=details
            )
            
        except Exception as e:
            logger.error(f"[SecurityHooks] pre_task_hook 异常: {e}")
            return HookResult(
                success=False,
                hook_name="pre_task_hook",
                message=f"安全检查异常: {e}",
                details={"error": str(e)}
            )
    
    @classmethod
    async def pre_sensitive_hook(
        cls,
        reason: str = "Sensitive operation detected",
        timeout: int = 60
    ) -> HookResult:
        """
        敏感操作前的 Hook
        
        触发 WebAuthn 验证
        
        Args:
            reason: 验证原因
            timeout: 超时时间
            
        Returns:
            HookResult
        """
        if not cls._enabled:
            return HookResult(
                success=True,
                hook_name="pre_sensitive_hook",
                message="安全检查已禁用",
                details={"skipped": True}
            )
        
        try:
            # 触发 WebAuthn 验证
            verified = await WebAuthnTrigger.request_verification(
                reason=reason,
                timeout=timeout
            )
            
            status = "verified" if verified else "failed"
            logger.info(f"[Agent-Stack-Bridge] WebAuthn verification: {status}")
            
            if not verified:
                await cls._handle_violation("webauthn", [{
                    "type": "verification_failed",
                    "reason": reason
                }])
                
                raise SecurityException([{
                    "line": 0,
                    "function": "webauthn_verification",
                    "severity": "critical",
                    "message": "WebAuthn verification failed"
                }])
            
            return HookResult(
                success=True,
                hook_name="pre_sensitive_hook",
                message="WebAuthn 验证通过",
                details={"verified": True, "reason": reason}
            )
            
        except SecurityException:
            raise
        except Exception as e:
            logger.error(f"[SecurityHooks] pre_sensitive_hook 异常: {e}")
            return HookResult(
                success=False,
                hook_name="pre_sensitive_hook",
                message=f"验证异常: {e}",
                details={"error": str(e)}
            )
    
    @classmethod
    async def pre_code_execution_hook(
        cls,
        code: str,
        filename: str = "<string>"
    ) -> HookResult:
        """
        代码执行前的专用 Hook
        
        执行严格的代码审计
        
        Args:
            code: 要执行的代码
            filename: 文件名
            
        Returns:
            HookResult
        """
        if not cls._enabled:
            return HookResult(
                success=True,
                hook_name="pre_code_execution_hook",
                message="安全检查已禁用",
                details={"skipped": True}
            )
        
        try:
            if cls._ast_auditor is None:
                cls._ast_auditor = ASTAuditor(strict_mode=True)  # 代码执行总是严格模式
            
            result = cls._ast_auditor.scan_code(code, filename)
            
            details = {
                "safe": result["safe"],
                "issues": result["issues"],
                "imports": result["imports"],
                "summary": result["summary"]
            }
            
            if not result["safe"]:
                await cls._handle_violation("code_execution", result["issues"])
                
                return HookResult(
                    success=False,
                    hook_name="pre_code_execution_hook",
                    message="代码审计失败",
                    details=details
                )
            
            return HookResult(
                success=True,
                hook_name="pre_code_execution_hook",
                message="代码审计通过",
                details=details
            )
            
        except Exception as e:
            logger.error(f"[SecurityHooks] pre_code_execution_hook 异常: {e}")
            return HookResult(
                success=False,
                hook_name="pre_code_execution_hook",
                message=f"审计异常: {e}",
                details={"error": str(e)}
            )
    
    @classmethod
    async def _handle_violation(
        cls,
        violation_type: str,
        issues: List[dict]
    ) -> None:
        """处理安全违规"""
        logger.warning(
            f"[Agent-Stack-Bridge] Security violation: {violation_type}"
        )
        
        if cls._on_security_violation:
            try:
                await cls._on_security_violation(violation_type, issues)
            except Exception as e:
                logger.error(f"违规回调执行失败: {e}")


def secure_task(func: Callable) -> Callable:
    """
    装饰器：为任务自动添加安全检查
    
    用法：
        @secure_task
        async def my_task():
            # 任务代码
            pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 执行预检查
        result = await SecurityHooks.pre_task_hook()
        if not result.success:
            raise SecurityException([{
                "line": 0,
                "function": "secure_task_decorator",
                "severity": "high",
                "message": result.message
            }])
        
        # 执行原函数
        return await func(*args, **kwargs)
    
    return wrapper


def require_verification(reason: str = "Sensitive operation") -> Callable:
    """
    装饰器：要求 WebAuthn 验证
    
    用法：
        @require_verification("Delete all data")
        async def delete_all():
            # 敏感操作
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 执行验证
            result = await SecurityHooks.pre_sensitive_hook(reason)
            if not result.success:
                raise SecurityException([{
                    "line": 0,
                    "function": "require_verification_decorator",
                    "severity": "critical",
                    "message": result.message
                }])
            
            # 执行原函数
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# 环境初始化
def init_security():
    """初始化安全环境"""
    # 1. 清理 AppleDouble
    AppleDoubleCleaner.clean()
    
    # 2. 初始化 Hooks
    SecurityHooks.initialize()
    
    logger.info("[Agent-Stack-Bridge] Security environment initialized")


if __name__ == "__main__":
    import sys
    
    async def demo():
        """演示安全 Hooks"""
        print("安全 Hooks 演示")
        print("-" * 40)
        
        # 初始化
        SecurityHooks.initialize()
        
        # 测试 1: 代码审计
        print("\n1. 测试代码审计")
        safe_code = '''
def hello():
    print("Hello, World!")
'''
        result = await SecurityHooks.pre_code_execution_hook(safe_code)
        print(f"安全代码: {result.success} - {result.message}")
        
        unsafe_code = '''
import os
os.system("rm -rf /")
'''
        result = await SecurityHooks.pre_code_execution_hook(unsafe_code)
        print(f"危险代码: {result.success} - {result.message}")
        if not result.success:
            print(f"发现问题: {len(result.details.get('issues', []))} 个")
        
        # 测试 2: 任务 Hook
        print("\n2. 测试任务 Hook")
        result = await SecurityHooks.pre_task_hook()
        print(f"任务预检: {result.success} - {result.message}")
        
        # 测试 3: 装饰器
        print("\n3. 测试装饰器")
        
        @secure_task
        async def my_task():
            return "任务完成"
        
        try:
            result = await my_task()
            print(f"任务结果: {result}")
        except SecurityException as e:
            print(f"安全异常: {e}")
    
    asyncio.run(demo())
