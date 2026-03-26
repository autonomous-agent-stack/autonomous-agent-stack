"""
安全模块

提供以下安全功能：
- AppleDoubleCleaner: 物理清理 macOS 污染文件
- ASTAuditor: Python 代码静态安全审计
- WebAuthnTrigger: 物理验证触发
- SecurityHooks: 统一安全 Hook 接口
"""

from .apple_double_cleaner import AppleDoubleCleaner
from .ast_auditor import (
    ASTAuditor,
    SecurityException,
    SecurityIssue,
    Severity,
    audit_code,
    audit_file
)
from .webauthn_trigger import (
    WebAuthnTrigger,
    MockWebAuthnTrigger,
    VerificationStatus,
    VerificationRequest,
    VerificationResult
)
from .hooks import (
    SecurityHooks,
    HookResult,
    secure_task,
    require_verification,
    init_security
)

__all__ = [
    # AppleDouble 清理
    "AppleDoubleCleaner",
    
    # AST 审计
    "ASTAuditor",
    "SecurityException",
    "SecurityIssue",
    "Severity",
    "audit_code",
    "audit_file",
    
    # WebAuthn 验证
    "WebAuthnTrigger",
    "MockWebAuthnTrigger",
    "VerificationStatus",
    "VerificationRequest",
    "VerificationResult",
    
    # 安全 Hooks
    "SecurityHooks",
    "HookResult",
    "secure_task",
    "require_verification",
    "init_security",
]
