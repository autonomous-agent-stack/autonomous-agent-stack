#!/usr/bin/env python3
"""
手动测试脚本 - 验证安全模块功能
"""
import sys
import tempfile
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.insert(0, "/Volumes/PS1008/Github/autonomous-agent-stack")

def test_apple_double_cleaner():
    """测试 AppleDouble 清理器"""
    print("\n" + "="*50)
    print("测试 1: AppleDoubleCleaner")
    print("="*50)
    
    from src.security.apple_double_cleaner import AppleDoubleCleaner
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文件
        Path(tmpdir, "code.py").write_text("print('hello')")
        Path(tmpdir, "._code.py").write_text("dirty")
        Path(tmpdir, ".DS_Store").write_text("metadata")
        
        # 执行清理
        result = AppleDoubleCleaner.clean(tmpdir)
        
        print(f"  清理文件数: {result['cleaned_files']}")
        print(f"  释放空间: {result['freed_bytes']} bytes")
        print(f"  错误: {result['errors']}")
        
        # 验证
        assert result["cleaned_files"] == 2, "应该清理 2 个文件"
        assert Path(tmpdir, "code.py").exists(), "正常文件应该保留"
        assert not Path(tmpdir, "._code.py").exists(), "AppleDouble 文件应该被删除"
        
    print("  ✅ 通过")
    return True


def test_ast_auditor_safe_code():
    """测试 AST 审计器 - 安全代码"""
    print("\n" + "="*50)
    print("测试 2: ASTAuditor - 安全代码")
    print("="*50)
    
    from src.security.ast_auditor import ASTAuditor
    
    safe_code = '''
def hello(name: str) -> str:
    return f"Hello, {name}!"

result = hello("World")
'''
    
    auditor = ASTAuditor()
    result = auditor.scan_code(safe_code)
    
    print(f"  安全: {result['safe']}")
    print(f"  问题数: {len(result['issues'])}")
    
    assert result["safe"] is True, "安全代码应该通过审计"
    assert len(result["issues"]) == 0, "安全代码不应该有问题"
    
    print("  ✅ 通过")
    return True


def test_ast_auditor_dangerous_code():
    """测试 AST 审计器 - 危险代码"""
    print("\n" + "="*50)
    print("测试 3: ASTAuditor - 危险代码")
    print("="*50)
    
    from src.security.ast_auditor import ASTAuditor
    
    dangerous_code = '''
import os
os.system("rm -rf /")
eval("malicious code")
'''
    
    auditor = ASTAuditor()
    result = auditor.scan_code(dangerous_code)
    
    print(f"  安全: {result['safe']}")
    print(f"  问题数: {len(result['issues'])}")
    
    for issue in result["issues"]:
        print(f"    - 第 {issue['line']} 行: {issue['function']} ({issue['severity']})")
    
    assert result["safe"] is False, "危险代码不应该通过审计"
    assert len(result["issues"]) > 0, "应该检测到问题"
    
    functions = [i["function"] for i in result["issues"]]
    assert "os.system" in functions, "应该检测到 os.system"
    assert "eval" in functions, "应该检测到 eval"
    
    print("  ✅ 通过")
    return True


def test_webauthn_request_creation():
    """测试 WebAuthn 请求创建"""
    print("\n" + "="*50)
    print("测试 4: WebAuthnTrigger - 请求创建")
    print("="*50)
    
    from src.security.webauthn_trigger import WebAuthnTrigger, VerificationStatus
    
    trigger = WebAuthnTrigger()
    request = trigger._create_request("Test verification", 60, {"key": "value"})
    
    print(f"  请求 ID: {request.request_id}")
    print(f"  原因: {request.reason}")
    print(f"  状态: {request.status.value}")
    
    assert request.request_id is not None, "应该生成请求 ID"
    assert request.reason == "Test verification"
    assert request.status == VerificationStatus.PENDING
    
    print("  ✅ 通过")
    return True


async def test_webauthn_external_confirmation():
    """测试 WebAuthn 外部确认"""
    print("\n" + "="*50)
    print("测试 5: WebAuthnTrigger - 外部确认")
    print("="*50)
    
    from src.security.webauthn_trigger import WebAuthnTrigger, VerificationStatus
    
    trigger = WebAuthnTrigger()
    request = trigger._create_request("External test", 60, None)
    
    # 添加到待处理
    WebAuthnTrigger._pending_requests[request.request_id] = request
    
    # 模拟外部确认
    WebAuthnTrigger.confirm_verification(request.request_id, success=True)
    
    print(f"  请求 ID: {request.request_id}")
    print(f"  状态: {request.status.value}")
    print(f"  验证时间: {request.verified_at}")
    
    assert request.status == VerificationStatus.VERIFIED
    assert request.verified_at is not None
    
    print("  ✅ 通过")
    return True


async def test_security_hooks_code_audit():
    """测试安全 Hooks 代码审计"""
    print("\n" + "="*50)
    print("测试 6: SecurityHooks - 代码审计")
    print("="*50)
    
    from src.security.hooks import SecurityHooks
    
    SecurityHooks.initialize(enabled=True, auto_clean=False)
    
    # 测试安全代码
    safe_code = '''
def hello():
    print("Hello")
'''
    result = await SecurityHooks.pre_code_execution_hook(safe_code)
    print(f"  安全代码结果: {result.success}")
    assert result.success is True
    
    # 测试危险代码
    dangerous_code = '''
import os
os.system("ls")
'''
    result = await SecurityHooks.pre_code_execution_hook(dangerous_code)
    print(f"  危险代码结果: {result.success}")
    assert result.success is False
    print(f"  检测到问题数: {len(result.details.get('issues', []))}")
    
    print("  ✅ 通过")
    return True


async def test_security_hooks_disabled():
    """测试禁用 Hooks"""
    print("\n" + "="*50)
    print("测试 7: SecurityHooks - 禁用模式")
    print("="*50)
    
    from src.security.hooks import SecurityHooks
    
    SecurityHooks.initialize(enabled=False)
    
    # 即使是危险代码也应该通过
    dangerous_code = '''
import os
os.system("ls")
'''
    result = await SecurityHooks.pre_code_execution_hook(dangerous_code)
    
    print(f"  结果: {result.success}")
    print(f"  跳过: {result.details.get('skipped')}")
    
    assert result.success is True
    assert result.details.get("skipped") is True
    
    print("  ✅ 通过")
    return True


async def test_secure_task_decorator():
    """测试 secure_task 装饰器"""
    print("\n" + "="*50)
    print("测试 8: secure_task 装饰器")
    print("="*50)
    
    from src.security.hooks import SecurityHooks, secure_task
    
    SecurityHooks.initialize(enabled=True, auto_clean=False)
    
    @secure_task
    async def safe_task():
        return "success"
    
    result = await safe_task()
    print(f"  任务结果: {result}")
    
    assert result == "success"
    
    print("  ✅ 通过")
    return True


def test_scan_only_mode():
    """测试只扫描模式"""
    print("\n" + "="*50)
    print("测试 9: AppleDoubleCleaner - 只扫描模式")
    print("="*50)
    
    from src.security.apple_double_cleaner import AppleDoubleCleaner
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文件
        Path(tmpdir, "file.txt").write_text("content")
        Path(tmpdir, "._file.txt").write_text("dirty")
        Path(tmpdir, ".DS_Store").write_text("metadata")
        
        # 扫描
        cleaner = AppleDoubleCleaner()
        scan_result = cleaner.scan_only(tmpdir)
        
        print(f"  发现文件数: {scan_result['count']}")
        print(f"  总大小: {scan_result['total_size']} bytes")
        
        # 验证文件未被删除
        assert Path(tmpdir, "._file.txt").exists(), "只扫描模式不应删除文件"
        assert Path(tmpdir, ".DS_Store").exists(), "只扫描模式不应删除文件"
        assert scan_result["count"] == 2
        
    print("  ✅ 通过")
    return True


async def test_full_workflow():
    """测试完整工作流"""
    print("\n" + "="*50)
    print("测试 10: 完整安全工作流")
    print("="*50)
    
    from src.security.hooks import SecurityHooks
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试环境
        Path(tmpdir, "script.py").write_text('''
def main():
    print("Safe operation")
''')
        Path(tmpdir, "._script.py").write_text("dirty")
        
        # 初始化
        SecurityHooks.initialize(enabled=True, auto_clean=True)
        
        # 读取代码
        code = Path(tmpdir, "script.py").read_text()
        
        # 执行预检查
        result = await SecurityHooks.pre_task_hook(
            code=code,
            working_dir=tmpdir
        )
        
        print(f"  成功: {result.success}")
        print(f"  清理文件数: {result.details.get('apple_double_cleaned', 0)}")
        print(f"  代码安全: {result.details.get('code_audit', {}).get('safe')}")
        
        assert result.success is True
        assert result.details.get("apple_double_cleaned", 0) >= 1
    
    print("  ✅ 通过")
    return True


def main():
    """运行所有测试"""
    print("\n" + "#"*60)
    print("# 安全模块测试套件")
    print("#"*60)
    
    tests = [
        ("AppleDoubleCleaner 基本清理", test_apple_double_cleaner),
        ("ASTAuditor 安全代码", test_ast_auditor_safe_code),
        ("ASTAuditor 危险代码", test_ast_auditor_dangerous_code),
        ("WebAuthn 请求创建", test_webauthn_request_creation),
        ("AppleDouble 只扫描模式", test_scan_only_mode),
    ]
    
    async_tests = [
        ("WebAuthn 外部确认", test_webauthn_external_confirmation),
        ("SecurityHooks 代码审计", test_security_hooks_code_audit),
        ("SecurityHooks 禁用模式", test_security_hooks_disabled),
        ("secure_task 装饰器", test_secure_task_decorator),
        ("完整工作流", test_full_workflow),
    ]
    
    passed = 0
    failed = 0
    
    # 运行同步测试
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            failed += 1
    
    # 运行异步测试
    for name, test_func in async_tests:
        try:
            asyncio.run(test_func())
            passed += 1
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            failed += 1
    
    # 汇总
    print("\n" + "#"*60)
    print(f"# 测试结果: {passed} 通过, {failed} 失败")
    print("#"*60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
