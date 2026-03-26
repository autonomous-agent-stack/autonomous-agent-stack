"""
安全模块测试

测试覆盖：
- AppleDoubleCleaner: 3 个测试
- ASTAuditor: 4 个测试
- WebAuthnTrigger: 3 个测试
- SecurityHooks: 4 个测试
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

# 导入被测模块
from src.security.apple_double_cleaner import AppleDoubleCleaner
from src.security.ast_auditor import ASTAuditor, SecurityException, audit_code
from src.security.webauthn_trigger import (
    WebAuthnTrigger,
    MockWebAuthnTrigger,
    VerificationStatus
)
from src.security.hooks import SecurityHooks, secure_task, require_verification


# ============================================
# AppleDoubleCleaner 测试
# ============================================

class TestAppleDoubleCleaner:
    """AppleDouble 清理器测试"""
    
    def test_clean_basic_appledouble_files(self):
        """测试 1: 清理基本 AppleDouble 文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            Path(tmpdir, "code.py").write_text("print('hello')")
            Path(tmpdir, "._code.py").write_text("dirty")
            Path(tmpdir, ".DS_Store").write_text("metadata")
            
            # 执行清理
            result = AppleDoubleCleaner.clean(tmpdir)
            
            # 验证结果
            assert result["cleaned_files"] == 2
            assert result["freed_bytes"] > 0
            assert len(result["errors"]) == 0
            
            # 验证文件状态
            remaining = list(Path(tmpdir).glob("*"))
            remaining_names = [f.name for f in remaining]
            assert "code.py" in remaining_names
            assert "._code.py" not in remaining_names
            assert ".DS_Store" not in remaining_names
    
    def test_clean_nested_directories(self):
        """测试 2: 清理嵌套目录中的污染文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建嵌套结构
            subdir = Path(tmpdir, "subdir")
            subdir.mkdir()
            
            Path(tmpdir, "root.txt").write_text("root")
            Path(tmpdir, "._root.txt").write_text("dirty")
            Path(subdir, "nested.py").write_text("nested")
            Path(subdir, "._nested.py").write_text("dirty")
            Path(subdir, ".DS_Store").write_text("metadata")
            
            # 执行清理
            result = AppleDoubleCleaner.clean(tmpdir)
            
            # 验证
            assert result["cleaned_files"] == 3
            assert result["errors"] == []
    
    def test_scan_only_mode(self):
        """测试 3: 只扫描不删除模式"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            Path(tmpdir, "file.txt").write_text("content")
            Path(tmpdir, "._file.txt").write_text("dirty")
            Path(tmpdir, ".DS_Store").write_text("metadata")
            
            # 扫描
            cleaner = AppleDoubleCleaner()
            scan_result = cleaner.scan_only(tmpdir)
            
            # 验证扫描结果
            assert scan_result["count"] == 2
            assert scan_result["total_size"] > 0
            
            # 验证文件未被删除
            assert Path(tmpdir, "._file.txt").exists()
            assert Path(tmpdir, ".DS_Store").exists()


# ============================================
# ASTAuditor 测试
# ============================================

class TestASTAuditor:
    """AST 审计器测试"""
    
    def test_detect_os_system(self):
        """测试 4: 检测 os.system 调用"""
        code = '''
import os
os.system("ls -la")
'''
        result = audit_code(code)
        
        assert not result["safe"]
        assert any(
            issue["function"] == "os.system"
            for issue in result["issues"]
        )
    
    def test_detect_eval_exec(self):
        """测试 5: 检测 eval 和 exec 调用"""
        code = '''
x = eval("1 + 1")
exec("print('hello')")
'''
        result = audit_code(code)
        
        assert not result["safe"]
        functions = [issue["function"] for issue in result["issues"]]
        assert "eval" in functions
        assert "exec" in functions
    
    def test_detect_subprocess(self):
        """测试 6: 检测 subprocess 调用"""
        code = '''
import subprocess
subprocess.run(["echo", "test"])
subprocess.call(["ls"])
'''
        result = audit_code(code)
        
        assert not result["safe"]
        functions = [issue["function"] for issue in result["issues"]]
        assert "subprocess.run" in functions
        assert "subprocess.call" in functions
    
    def test_safe_code_passes(self):
        """测试 7: 安全代码通过审计"""
        code = '''
def hello(name: str) -> str:
    """A safe function"""
    return f"Hello, {name}!"

def calculate(a: int, b: int) -> int:
    return a + b

# Just normal operations
result = hello("World")
total = calculate(1, 2)
'''
        result = audit_code(code)
        
        assert result["safe"]
        assert len(result["issues"]) == 0


# ============================================
# WebAuthnTrigger 测试
# ============================================

class TestWebAuthnTrigger:
    """WebAuthn 触发器测试"""
    
    @pytest.mark.asyncio
    async def test_mock_auto_approve(self):
        """测试 8: Mock 触发器自动批准"""
        MockWebAuthnTrigger.set_auto_approve(True)
        MockWebAuthnTrigger.set_delay(0.1)
        
        trigger = MockWebAuthnTrigger()
        result = await trigger._execute_verification(
            reason="Test verification",
            timeout=5,
            metadata=None
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_verification_request_creation(self):
        """测试 9: 验证请求创建"""
        trigger = WebAuthnTrigger()
        request = trigger._create_request("Test reason", 60, {"key": "value"})
        
        assert request.request_id is not None
        assert request.reason == "Test reason"
        assert request.status == VerificationStatus.PENDING
        assert request.metadata == {"key": "value"}
    
    @pytest.mark.asyncio
    async def test_external_confirmation(self):
        """测试 10: 外部确认验证"""
        trigger = WebAuthnTrigger()
        request = trigger._create_request("External test", 60, None)
        
        # 添加到待处理
        WebAuthnTrigger._pending_requests[request.request_id] = request
        
        # 模拟外部确认
        WebAuthnTrigger.confirm_verification(request.request_id, success=True)
        
        # 验证状态更新
        assert request.status == VerificationStatus.VERIFIED
        assert request.verified_at is not None


# ============================================
# SecurityHooks 测试
# ============================================

class TestSecurityHooks:
    """安全 Hooks 测试"""
    
    @pytest.mark.asyncio
    async def test_pre_task_hook_with_clean(self):
        """测试 11: 任务前 Hook 清理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建污染文件
            Path(tmpdir, "._dirty").write_text("dirty")
            
            # 初始化
            SecurityHooks.initialize(auto_clean=True)
            
            # 执行 Hook
            result = await SecurityHooks.pre_task_hook(working_dir=tmpdir)
            
            assert result.success
            assert result.details.get("apple_double_cleaned", 0) >= 1
    
    @pytest.mark.asyncio
    async def test_pre_code_execution_hook_blocks_dangerous(self):
        """测试 12: 代码执行 Hook 阻止危险代码"""
        SecurityHooks.initialize(enabled=True)
        
        dangerous_code = '''
import os
os.system("rm -rf /")
'''
        result = await SecurityHooks.pre_code_execution_hook(dangerous_code)
        
        assert not result.success
        assert "issues" in result.details
    
    @pytest.mark.asyncio
    async def test_secure_task_decorator(self):
        """测试 13: secure_task 装饰器"""
        SecurityHooks.initialize(enabled=True, auto_clean=False)
        
        @secure_task
        async def safe_task():
            return "success"
        
        # 应该成功执行
        result = await safe_task()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_hooks_disabled(self):
        """测试 14: 禁用 Hooks"""
        SecurityHooks.initialize(enabled=False)
        
        # 即使是危险代码也应该通过
        dangerous_code = '''
import os
os.system("ls")
'''
        result = await SecurityHooks.pre_code_execution_hook(dangerous_code)
        
        assert result.success
        assert result.details.get("skipped") is True


# ============================================
# 集成测试
# ============================================

class TestSecurityIntegration:
    """安全模块集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_security_workflow(self):
        """测试 15: 完整安全工作流"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试环境
            Path(tmpdir, "script.py").write_text('''
def main():
    print("Safe operation")
''')
            Path(tmpdir, "._script.py").write_text("dirty")
            
            # 初始化安全模块
            SecurityHooks.initialize(enabled=True, auto_clean=True)
            
            # 读取代码
            code = Path(tmpdir, "script.py").read_text()
            
            # 执行预检查
            result = await SecurityHooks.pre_task_hook(
                code=code,
                working_dir=tmpdir
            )
            
            # 验证
            assert result.success
            assert result.details.get("apple_double_cleaned", 0) >= 1
            assert result.details.get("code_audit", {}).get("safe") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
