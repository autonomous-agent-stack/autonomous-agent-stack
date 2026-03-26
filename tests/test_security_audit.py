"""审计系统测试用例

测试覆盖：
1. TokenSanitizer - Token 脱敏
2. AuditLogger - 审计日志记录
3. AuditRouter - 审计路由投递
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from src.security.token_sanitizer import TokenSanitizer
from src.security.audit_logger import AuditLogger
from src.security.audit_router import AuditRouter, AUDIT_GROUP_CONFIG


class TestTokenSanitizer:
    """Token 脱敏器测试"""
    
    def test_sanitize_api_token(self):
        """测试 1: API Token 脱敏（保留前 8 位）"""
        sanitizer = TokenSanitizer()
        
        text = "token=abc123def456ghi789jkl012mno345pqr678"
        result = sanitizer.sanitize(text)
        
        assert "abc123de***REDACTED***" in result
        assert "ghi789jkl012mno345pqr678" not in result
        
    def test_sanitize_password(self):
        """测试 2: 密码完全隐藏"""
        sanitizer = TokenSanitizer()
        
        text = "password=my_secret_password_123"
        result = sanitizer.sanitize(text)
        
        assert "***HIDDEN***" in result
        assert "my_secret_password_123" not in result
        
    def test_sanitize_bearer_token(self):
        """测试 3: Bearer Token 脱敏"""
        sanitizer = TokenSanitizer()
        
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = sanitizer.sanitize(text)
        
        assert "eyJhbGci***REDACTED***" in result
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        
    def test_sanitize_dict(self):
        """测试 4: 字典脱敏"""
        sanitizer = TokenSanitizer()
        
        data = {
            "api_key": "sk_live_1234567890abcdef",
            "user": "admin",
            "password": "secret123"
        }
        result = sanitizer.sanitize_dict(data)
        
        assert "sk_live_***REDACTED***" in result["api_key"]
        assert result["user"] == "admin"
        assert "***HIDDEN***" in result["password"]
        
    def test_sanitize_nested_dict(self):
        """测试 5: 嵌套字典脱敏"""
        sanitizer = TokenSanitizer()
        
        data = {
            "config": {
                "api_token": "token_abc123def456",
                "database": {
                    "password": "db_password_123"
                }
            }
        }
        result = sanitizer.sanitize_dict(data)
        
        assert "token_ab***REDACTED***" in result["config"]["api_token"]
        assert "***HIDDEN***" in result["config"]["database"]["password"]
        
    def test_sanitize_list(self):
        """测试 6: 列表脱敏"""
        sanitizer = TokenSanitizer()
        
        data = [
            "token=value123456789",
            "password=secret",
            {"secret_key": "key_value"}
        ]
        result = sanitizer.sanitize_list(data)
        
        assert "value123***REDACTED***" in result[0]
        assert "***HIDDEN***" in result[1]
        assert "***REDACTED***" in result[2]["secret_key"]


class TestAuditLogger:
    """审计日志器测试"""
    
    @pytest.fixture
    def temp_log_dir(self):
        """创建临时日志目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
        
    def test_log_route_operation(self, temp_log_dir):
        """测试 7: 记录路由操作"""
        logger = AuditLogger(log_dir=temp_log_dir)
        
        result = logger.log_route(
            source={"chat_id": -1001234567890, "thread_id": 10},
            target={"chat_id": -1009876543210, "thread_id": None},
            status="success"
        )
        
        assert result["action"] == "route_message"
        assert result["status"] == "success"
        assert "timestamp" in result
        assert result["source"]["chat_id"] == -1001234567890
        
    def test_log_mirror_operation(self, temp_log_dir):
        """测试 8: 记录镜像操作"""
        logger = AuditLogger(log_dir=temp_log_dir)
        
        result = logger.log_mirror(
            original={"chat_id": -1001111111111},
            backup={"chat_id": -1002222222222}
        )
        
        assert result["action"] == "mirror_message"
        assert result["status"] == "success"
        assert result["original"]["chat_id"] == -1001111111111
        
    def test_log_appledouble_clean(self, temp_log_dir):
        """测试 9: 记录 AppleDouble 清理"""
        logger = AuditLogger(log_dir=temp_log_dir)
        
        result = logger.log_appledouble_clean(
            cleaned_files=15,
            freed_bytes=1024 * 1024 * 5  # 5 MB
        )
        
        assert result["action"] == "appledouble_clean"
        assert result["cleaned_files"] == 15
        assert result["freed_mb"] == 5.0
        
    def test_get_logs(self, temp_log_dir):
        """测试 10: 获取审计日志"""
        logger = AuditLogger(log_dir=temp_log_dir)
        
        # 记录几条日志
        logger.log_route(
            source={"chat_id": 1},
            target={"chat_id": 2},
            status="success"
        )
        logger.log_route(
            source={"chat_id": 3},
            target={"chat_id": 4},
            status="failed"
        )
        
        # 获取所有日志
        all_logs = logger.get_logs(limit=10)
        assert len(all_logs) >= 2
        
        # 过滤状态
        success_logs = logger.get_logs(status="success", limit=10)
        assert all(log["status"] == "success" for log in success_logs)


class TestAuditRouter:
    """审计路由器测试"""
    
    @pytest.fixture
    def temp_log_dir(self):
        """创建临时日志目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
        
    @pytest.mark.asyncio
    async def test_execute_audit_delivery(self, temp_log_dir):
        """测试 11: 执行审计日志投递"""
        router = AuditRouter()
        router.audit_logger = AuditLogger(log_dir=temp_log_dir)
        
        context = {
            "action": "test_action",
            "status": "success",
            "details": {
                "token": "secret_token_12345678"
            }
        }
        
        result = await router.execute(context)
        
        assert result["status"] == "success"
        assert result["sanitized"] is True
        assert result["delivered"] is True
        
    @pytest.mark.asyncio
    async def test_route_appledouble_result(self, temp_log_dir):
        """测试 12: 投递 AppleDouble 清理结果"""
        router = AuditRouter()
        router.audit_logger = AuditLogger(log_dir=temp_log_dir)
        
        result = await router.route_appledouble_clean_result(
            cleaned_files=10,
            freed_bytes=1024 * 512  # 0.5 MB
        )
        
        assert result["status"] == "success"
        
    @pytest.mark.asyncio
    async def test_route_routing_operation(self, temp_log_dir):
        """测试 13: 投递路由操作日志"""
        router = AuditRouter()
        router.audit_logger = AuditLogger(log_dir=temp_log_dir)
        
        result = await router.route_routing_operation(
            source={"chat_id": -1001111111111, "thread_id": 5},
            target={"chat_id": -1002222222222, "thread_id": None},
            status="success",
            details={"message_id": 12345}
        )
        
        assert result["status"] == "success"
        
    @pytest.mark.asyncio
    async def test_route_mirror_operation(self, temp_log_dir):
        """测试 14: 投递镜像操作日志"""
        router = AuditRouter()
        router.audit_logger = AuditLogger(log_dir=temp_log_dir)
        
        result = await router.route_mirror_operation(
            original={"chat_id": -1001111111111},
            backup={"chat_id": -1002222222222},
            status="success"
        )
        
        assert result["status"] == "success"
        
    def test_sanitize_context(self, temp_log_dir):
        """测试 15: Token 脱敏上下文"""
        router = AuditRouter()
        router.audit_logger = AuditLogger(log_dir=temp_log_dir)
        
        context = {
            "action": "api_call",
            "api_key": "sk_live_1234567890abcdef",
            "password": "my_password",
            "user": "admin"
        }
        
        result = router._sanitize_context(context)
        
        assert "sk_live_***REDACTED***" in result["api_key"]
        assert "***HIDDEN***" in result["password"]
        assert result["user"] == "admin"
        
    def test_format_audit_card(self, temp_log_dir):
        """测试 16: 格式化审计卡片"""
        router = AuditRouter()
        router.audit_logger = AuditLogger(log_dir=temp_log_dir)
        
        data = {
            "status": "success",
            "action": "route_message",
            "timestamp": "2026-03-26T09:10:00Z",
            "details": {"key": "value"}
        }
        
        result = router._format_audit_card(data)
        
        assert result["title"] == "系统审计"
        assert result["token_sanitized"] is True
        assert len(result["fields"]) > 0
        
        # 验证字段顺序（status 权重最高，应该在第一位）
        assert result["fields"][0]["name"] == "status"
        assert result["fields"][0]["weight"] == 0.9


class TestIntegration:
    """集成测试"""
    
    @pytest.fixture
    def temp_log_dir(self):
        """创建临时日志目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
        
    @pytest.mark.asyncio
    async def test_full_audit_workflow(self, temp_log_dir):
        """测试 17: 完整审计工作流"""
        # 初始化组件
        sanitizer = TokenSanitizer()
        logger = AuditLogger(log_dir=temp_log_dir)
        router = AuditRouter()
        router.audit_logger = logger
        
        # 1. 准备审计数据（包含敏感信息）
        audit_data = {
            "action": "api_request",
            "status": "success",
            "token": "bearer_abc123def456",
            "password": "secret123",
            "user": "admin"
        }
        
        # 2. Token 脱敏
        sanitized_data = sanitizer.sanitize_dict(audit_data)
        assert "bearer_a***REDACTED***" in sanitized_data["token"]
        assert "***HIDDEN***" in sanitized_data["password"]
        
        # 3. 记录审计日志
        log_result = logger.log_route(
            source={"chat_id": -1001111111111},
            target={"chat_id": -1002222222222},
            status="success",
            details=sanitized_data
        )
        assert log_result["status"] == "success"
        
        # 4. 投递到审计群组
        delivery_result = await router.execute(sanitized_data)
        assert delivery_result["delivered"] is True
        
    @pytest.mark.asyncio
    async def test_error_handling(self, temp_log_dir):
        """测试 18: 错误处理"""
        logger = AuditLogger(log_dir=temp_log_dir)
        
        # 记录错误日志
        error_log = logger.log_error(
            action="api_call",
            error_message="Connection timeout",
            error_details={"timeout": 30}
        )
        
        assert error_log["status"] == "error"
        assert error_log["action"] == "api_call"
        assert "Connection timeout" in error_log["error_message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
