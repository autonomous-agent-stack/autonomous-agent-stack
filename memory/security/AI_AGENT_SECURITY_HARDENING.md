# AI Agent 安全加固指南

> **版本**: v1.0
> **更新时间**: 2026-03-27
> **安全等级**: 企业级

---

## 🔒 安全威胁模型

### 常见威胁

| 威胁类型 | 风险等级 | 影响 |
|---------|---------|------|
| **提示注入** | 🔴 高 | 数据泄露、权限绕过 |
| **数据泄露** | 🔴 高 | 敏感信息暴露 |
| **权限滥用** | 🟡 中 | 未授权操作 |
| **资源耗尽** | 🟡 中 | 服务不可用 |
| **模型攻击** | 🟢 低 | 模型质量下降 |

---

## 🛡️ 安全加固方案

### 1. 输入验证

```python
import re
from typing import Optional

class InputValidator:
    """输入验证器"""
    
    def __init__(self):
        self.max_length = 10000
        self.dangerous_patterns = [
            r"ignore (all )?previous instructions",
            r"you are (now )?a?",
            r"system:",
            r"<\|.*?\|>",
            r"###\s*instruction",
        ]
    
    def validate(self, user_input: str) -> tuple[bool, Optional[str]]:
        """
        验证用户输入
        
        Returns:
            (is_valid, error_message)
        """
        # 1. 长度检查
        if len(user_input) > self.max_length:
            return False, f"输入过长（最大 {self.max_length} 字符）"
        
        # 2. 危险模式检查
        for pattern in self.dangerous_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                return False, f"检测到危险模式: {pattern}"
        
        # 3. 特殊字符检查
        if re.search(r'[<>(){}[\]]', user_input):
            return False, "包含不允许的特殊字符"
        
        return True, None
    
    def sanitize(self, user_input: str) -> str:
        """清理输入"""
        # 移除危险模式
        cleaned = user_input
        for pattern in self.dangerous_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        
        # 移除特殊字符
        cleaned = re.sub(r'[<>(){}[\]]', '', cleaned)
        
        # 压缩空格
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()
```

### 2. 输出过滤

```python
class OutputFilter:
    """输出过滤器"""
    
    def __init__(self):
        self.sensitive_patterns = [
            (r'\b\d{16}\b', '信用卡号'),          # 信用卡
            (r'\b\d{17}\b', '身份证号'),          # 身份证
            (r'[A-Z]{2}\d{9}', '护照号'),          # 护照
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '邮箱'),  # 邮箱
            (r'\b1[3-9]\d{9}\b', '手机号'),       # 手机号
        ]
    
    def filter(self, output: str) -> str:
        """过滤输出"""
        filtered = output
        
        for pattern, name in self.sensitive_patterns:
            if re.search(pattern, output):
                # 替换为 [REDACTED]
                filtered = re.sub(pattern, f'[{name}已隐藏]', filtered)
                # 记录警告
                self._log_warning(name, output)
        
        return filtered
    
    def _log_warning(self, sensitive_type: str, original: str):
        """记录警告"""
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"检测到敏感信息 ({sensitive_type}): "
            f"{original[:50]}..."
        )
```

### 3. 权限控制

```python
from enum import Enum
from typing import Set

class Permission(Enum):
    """权限枚举"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"

class RoleBasedAccessControl:
    """基于角色的访问控制"""
    
    def __init__(self):
        # 角色权限映射
        self.role_permissions = {
            "guest": {Permission.READ},
            "user": {Permission.READ, Permission.WRITE},
            "admin": {Permission.READ, Permission.WRITE, Permission.EXECUTE, Permission.ADMIN}
        }
        
        # 用户角色映射
        self.user_roles = {}
    
    def assign_role(self, user_id: str, role: str):
        """分配角色"""
        if role not in self.role_permissions:
            raise ValueError(f"Invalid role: {role}")
        
        self.user_roles[user_id] = role
    
    def check_permission(self, user_id: str, permission: Permission) -> bool:
        """检查权限"""
        role = self.user_roles.get(user_id, "guest")
        permissions = self.role_permissions[role]
        
        return permission in permissions
    
    def require_permission(self, user_id: str, permission: Permission):
        """要求权限（装饰器）"""
        if not self.check_permission(user_id, permission):
            raise PermissionError(
                f"User {user_id} lacks permission: {permission}"
            )


# 使用装饰器保护函数
def require_permission(permission: Permission):
    """权限装饰器"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            # 检查权限
            self.rbac.require_permission(self.user_id, permission)
            
            # 执行函数
            return func(self, *args, **kwargs)
        
        return wrapper
    return decorator


class SecureAgent:
    """安全 Agent"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.rbac = RoleBasedAccessControl()
    
    @require_permission(Permission.READ)
    def read_data(self, data_id: str):
        """读取数据"""
        return f"Reading data {data_id}"
    
    @require_permission(Permission.WRITE)
    def write_data(self, data_id: str, data: str):
        """写入数据"""
        return f"Writing data {data_id}: {data}"
    
    @require_permission(Permission.EXECUTE)
    def execute_command(self, command: str):
        """执行命令"""
        return f"Executing: {command}"
```

### 4. 审计日志

```python
import logging
from datetime import datetime
from typing import Dict, Any
import json

class AuditLogger:
    """审计日志"""
    
    def __init__(self, log_file: str = "audit.log"):
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        
        # 文件处理器
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
    
    def log_action(
        self,
        user_id: str,
        action: str,
        resource: str,
        details: Dict[str, Any] = None
    ):
        """记录操作"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "details": details or {}
        }
        
        self.logger.info(json.dumps(log_entry))
    
    def log_tool_call(
        self,
        user_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        result: str
    ):
        """记录工具调用"""
        self.log_action(
            user_id=user_id,
            action="tool_call",
            resource=tool_name,
            details={
                "parameters": parameters,
                "result_preview": result[:100]  # 只记录前 100 字符
            }
        )
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        user_id: str = None
    ):
        """记录安全事件"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "description": description,
            "user_id": user_id
        }
        
        if severity == "high":
            self.logger.error(json.dumps(log_entry))
        elif severity == "medium":
            self.logger.warning(json.dumps(log_entry))
        else:
            self.logger.info(json.dumps(log_entry))
```

### 5. 速率限制

```python
import time
from collections import defaultdict
from typing import Dict

class RateLimiter:
    """速率限制器"""
    
    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, user_id: str) -> bool:
        """检查是否允许请求"""
        now = time.time()
        
        # 清理过期请求
        self.requests[user_id] = [
            timestamp
            for timestamp in self.requests[user_id]
            if now - timestamp < self.window_seconds
        ]
        
        # 检查数量
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # 记录请求
        self.requests[user_id].append(now)
        
        return True
    
    def get_remaining(self, user_id: str) -> int:
        """获取剩余请求数"""
        now = time.time()
        
        # 清理过期请求
        self.requests[user_id] = [
            timestamp
            for timestamp in self.requests[user_id]
            if now - timestamp < self.window_seconds
        ]
        
        return self.max_requests - len(self.requests[user_id])


# 使用示例
class SecureAgentWithRateLimit:
    """带速率限制的安全 Agent"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
        self.audit_logger = AuditLogger()
    
    def run(self, user_id: str, task: str) -> str:
        """运行 Agent"""
        # 1. 检查速率限制
        if not self.rate_limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded")
        
        # 2. 执行任务
        result = self._execute(task)
        
        # 3. 记录审计日志
        self.audit_logger.log_action(
            user_id=user_id,
            action="run_agent",
            resource="agent",
            details={"task": task[:50]}
        )
        
        return result
```

---

## 🔍 安全检查清单

### 部署前检查

- [ ] ✅ 输入验证已启用
- [ ] ✅ 输出过滤已配置
- [ ] ✅ 权限控制已实施
- [ ] ✅ 审计日志已启用
- [ ] ✅ 速率限制已设置
- [ ] ✅ 敏感信息已加密
- [ ] ✅ API Key 已保护
- [ ] ✅ 错误信息已脱敏

### 运行时监控

- [ ] ✅ 异常行为检测
- [ ] ✅ 失败请求监控
- [ ] ✅ 权限滥用检测
- [ ] ✅ 资源使用监控
- [ ] ✅ 安全事件告警

---

**生成时间**: 2026-03-27 13:20 GMT+8
