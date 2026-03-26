"""
安全模块

提供以下安全功能：
- AppleDoubleCleaner: 物理清理 macOS 污染文件
- ASTAuditor: Python 代码静态安全审计
- WebAuthnTrigger: 物理验证触发
- SecurityHooks: 统一安全 Hook 接口
- TokenSanitizer: Token 脱敏处理
- AuditLogger/AuditRouter: 审计日志与路由策略
"""

from .apple_double_cleaner import AppleDoubleCleaner
from .ast_auditor import (
    ASTAuditor,
    SecurityException,
    SecurityIssue,
    Severity,
    audit_code,
    audit_file,
)
from .webauthn_trigger import (
    MockWebAuthnTrigger,
    VerificationRequest,
    VerificationResult,
    VerificationStatus,
    WebAuthnTrigger,
)
from .hooks import (
    HookResult,
    SecurityHooks,
    init_security,
    require_verification,
    secure_task,
)
from .token_sanitizer import TokenSanitizer
from .audit_logger import AuditLogger
from .audit_router import AuditRouter, AUDIT_GROUP_CONFIG, SECURE_TOPIC_CARD_WEIGHTS

__all__ = [
    "AppleDoubleCleaner",
    "ASTAuditor",
    "SecurityException",
    "SecurityIssue",
    "Severity",
    "audit_code",
    "audit_file",
    "WebAuthnTrigger",
    "MockWebAuthnTrigger",
    "VerificationStatus",
    "VerificationRequest",
    "VerificationResult",
    "SecurityHooks",
    "HookResult",
    "secure_task",
    "require_verification",
    "init_security",
    "TokenSanitizer",
    "AuditLogger",
    "AuditRouter",
    "AUDIT_GROUP_CONFIG",
    "SECURE_TOPIC_CARD_WEIGHTS",
]
