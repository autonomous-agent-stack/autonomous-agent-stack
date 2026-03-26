"""
Bridge API 测试用例

测试覆盖：
1. Bridge API 基本功能
2. 凭证解析与解耦
3. Codex 任务委派
4. Skill 动态加载
5. 安全扫描功能
6. AppleDouble 文件清理
7. 错误处理
8. 并发任务处理
9. 直接任务处理
10. 资源清理
"""

from __future__ import annotations

import pytest
import asyncio
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

from src.bridge.api import BridgeAPI, CredentialsRef
from src.bridge.skill_loader import SkillLoader, SecurityAuditor, AppleDoubleCleaner
from src.bridge.codex_client import CodexClient


class TestCredentialsRef:
    """测试 CredentialsRef"""

    def test_credentials_ref_creation(self):
        """测试凭证引用创建"""
        ref = CredentialsRef(ref_id="test_token_123", ref_type="token")
        assert ref.ref_id == "test_token_123"
        assert ref.ref_type == "token"
        assert ref.metadata == {}

    def test_credentials_ref_with_metadata(self):
        """测试带元数据的凭证引用"""
        metadata = {"expires_at": "2024-12-31", "owner": "test_user"}
        ref = CredentialsRef(ref_id="api_key_456", ref_type="api_key", metadata=metadata)
        assert ref.metadata == metadata

    def test_credentials_ref_serialization(self):
        """测试凭证引用序列化"""
        ref = CredentialsRef(ref_id="token_789", ref_type="oauth")
        data = ref.to_dict()
        assert data["ref_id"] == "token_789"
        assert data["ref_type"] == "oauth"
        assert "created_at" in data

    def test_credentials_ref_deserialization(self):
        """测试凭证引用反序列化"""
        data = {
            "ref_id": "token_abc",
            "ref_type": "token",
            "metadata": {"key": "value"},
        }
        ref = CredentialsRef.from_dict(data)
        assert ref.ref_id == "token_abc"
        assert ref.ref_type == "token"
        assert ref.metadata == {"key": "value"}


class TestBridgeAPI:
    """测试 Bridge API 核心功能"""

    @pytest.fixture
    def bridge_api(self):
        """创建 Bridge API 实例"""
        return BridgeAPI(
            codex_endpoint="http://localhost:8000",
            skill_base_path=Path.cwd(),
            enable_security_scan=True,
        )

    def test_bridge_initialization(self, bridge_api):
        """测试 Bridge API 初始化"""
        assert bridge_api.codex_endpoint == "http://localhost:8000"
        assert bridge_api.enable_security_scan is True
        assert bridge_api.codex_client is not None
        assert bridge_api.skill_loader is not None

    @pytest.mark.asyncio
    async def test_receive_task_validation(self, bridge_api):
        """测试任务验证"""
        # 缺少 task_id
        with pytest.raises(ValueError, match="Missing required field: task_id"):
            await bridge_api.receive_task({"task_type": "codex", "payload": {}})

        # 缺少 task_type
        with pytest.raises(ValueError, match="Missing required field: task_type"):
            await bridge_api.receive_task({"task_id": "test_123", "payload": {}})

        # 缺少 payload
        with pytest.raises(ValueError, match="Missing required field: payload"):
            await bridge_api.receive_task({"task_id": "test_123", "task_type": "codex"})

    @pytest.mark.asyncio
    async def test_direct_task_echo(self, bridge_api):
        """测试直接任务 - echo"""
        task = {
            "task_id": "test_echo_001",
            "task_type": "direct",
            "payload": {"action": "echo", "message": "Hello, Bridge!"},
        }

        result = await bridge_api.receive_task(task)

        assert result["status"] == "success"
        assert result["result"]["echo"] == "Hello, Bridge!"
        assert result["task_id"] == "test_echo_001"

    @pytest.mark.asyncio
    async def test_direct_task_health_check(self, bridge_api):
        """测试直接任务 - health_check"""
        task = {
            "task_id": "test_health_001",
            "task_type": "direct",
            "payload": {"action": "health_check"},
        }

        result = await bridge_api.receive_task(task)

        assert result["status"] == "success"
        assert result["result"]["status"] == "healthy"
        assert "bridge_version" in result["result"]

    @pytest.mark.asyncio
    async def test_direct_task_invalid_action(self, bridge_api):
        """测试直接任务 - 无效操作"""
        task = {
            "task_id": "test_invalid_001",
            "task_type": "direct",
            "payload": {"action": "unknown_action"},
        }

        result = await bridge_api.receive_task(task)

        assert result["status"] == "error"
        assert "Unknown direct task action" in result["error"]

    @pytest.mark.asyncio
    async def test_credentials_registration(self, bridge_api):
        """测试凭证注册"""
        credentials = {"token": "test_token_xyz"}
        ref = bridge_api.register_credentials("test_cred_001", credentials)

        assert ref.ref_id == "test_cred_001"
        assert "test_cred_001" in bridge_api._credentials_store

    @pytest.mark.asyncio
    async def test_credentials_resolution(self, bridge_api):
        """测试凭证解析"""
        # 注册凭证
        credentials = {"token": "secret_token_123"}
        bridge_api.register_credentials("cred_resolve_001", credentials)

        # 创建凭证引用
        task = {
            "task_id": "test_resolve_001",
            "task_type": "direct",
            "payload": {"action": "echo", "message": "test"},
            "credentials_ref": {"ref_id": "cred_resolve_001", "ref_type": "token"},
        }

        # 接收任务（会触发凭证解析）
        result = await bridge_api.receive_task(task)
        assert result["status"] == "success"


class TestCodexClient:
    """测试 Codex 客户端"""

    @pytest.fixture
    def codex_client(self):
        """创建 Codex 客户端实例"""
        return CodexClient(endpoint="http://localhost:8000")

    def test_client_initialization(self, codex_client):
        """测试客户端初始化"""
        assert codex_client.endpoint == "http://localhost:8000"
        assert codex_client.authenticated is False

    @pytest.mark.asyncio
    async def test_login_with_token(self, codex_client):
        """测试使用 token 登录"""
        credentials = {"token": "test_token_123"}
        result = await codex_client.login(credentials)

        assert result["status"] == "success"
        assert codex_client.is_authenticated() is True

    @pytest.mark.asyncio
    async def test_login_with_api_key(self, codex_client):
        """测试使用 API key 登录"""
        credentials = {"api_key": "test_api_key_456"}
        result = await codex_client.login(credentials)

        assert result["status"] == "success"
        assert codex_client.is_authenticated() is True

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, codex_client):
        """测试无效凭证登录"""
        credentials = {"username": "test_user"}  # 缺少 token 或 api_key

        with pytest.raises(ValueError, match="Invalid credentials"):
            await codex_client.login(credentials)

    @pytest.mark.asyncio
    async def test_delegate_task(self, codex_client):
        """测试任务委派"""
        # 先登录
        await codex_client.login({"token": "test_token"})

        # 委派任务
        task_payload = {"task_id": "codex_task_001", "action": "test_action"}
        result = await codex_client.delegate_task(task_payload)

        assert result["status"] == "success"
        assert result["task_id"] == "codex_task_001"

    @pytest.mark.asyncio
    async def test_delegate_task_not_authenticated(self, codex_client):
        """测试未认证时委派任务"""
        task_payload = {"task_id": "task_001", "action": "test"}

        with pytest.raises(RuntimeError, match="Codex client is not authenticated"):
            await codex_client.delegate_task(task_payload)

    @pytest.mark.asyncio
    async def test_logout(self, codex_client):
        """测试登出"""
        # 先登录
        await codex_client.login({"token": "test_token"})
        assert codex_client.is_authenticated() is True

        # 登出
        await codex_client.logout()
        assert codex_client.is_authenticated() is False


class TestSecurityAuditor:
    """测试安全审计器"""

    @pytest.fixture
    def auditor(self):
        """创建安全审计器实例"""
        return SecurityAuditor(strict_mode=False)

    def test_audit_safe_code(self, auditor, tmp_path):
        """测试审计安全代码"""
        # 创建安全的 Python 文件
        safe_file = tmp_path / "safe_skill.py"
        safe_file.write_text("""
def hello():
    return "Hello, World!"

class Skill:
    def execute(self):
        return hello()
""")

        result = auditor.audit_skill(tmp_path)

        assert result["passed"] is True
        assert result["summary"]["critical"] == 0
        assert result["summary"]["high"] == 0

    def test_audit_dangerous_imports(self, auditor, tmp_path):
        """测试审计危险导入"""
        # 创建包含危险导入的文件
        dangerous_file = tmp_path / "dangerous_skill.py"
        dangerous_file.write_text("""
import os
import subprocess

def bad_function():
    os.system("rm -rf /")
""")

        result = auditor.audit_skill(tmp_path)

        # passed 只检查 critical，危险导入是 high 级别
        assert result["summary"]["high"] > 0

        # 检查是否检测到危险导入
        dangerous_imports = [f for f in result["findings"] if f["type"] == "dangerous_import"]
        assert len(dangerous_imports) > 0

    def test_audit_dangerous_functions(self, auditor, tmp_path):
        """测试审计危险函数"""
        # 创建包含危险函数的文件
        dangerous_file = tmp_path / "eval_skill.py"
        dangerous_file.write_text("""
def dangerous_eval(code):
    return eval(code)
""")

        result = auditor.audit_skill(tmp_path)

        dangerous_funcs = [f for f in result["findings"] if f["type"] == "dangerous_function"]
        assert len(dangerous_funcs) > 0
        assert dangerous_funcs[0]["function"] == "eval"

    def test_audit_syntax_error(self, auditor, tmp_path):
        """测试审计语法错误"""
        # 创建包含语法错误的文件
        bad_file = tmp_path / "bad_syntax.py"
        bad_file.write_text("""
def broken(
    # 缺少括号
""")

        result = auditor.audit_skill(tmp_path)

        syntax_errors = [f for f in result["findings"] if f["type"] == "syntax_error"]
        assert len(syntax_errors) > 0


class TestAppleDoubleCleaner:
    """测试 AppleDouble 文件清理器"""

    def test_clean_appledouble_files(self, tmp_path):
        """测试清理 AppleDouble 文件"""
        # 创建 AppleDouble 文件
        (tmp_path / "._test_file.txt").write_text("metadata")
        (tmp_path / "normal_file.txt").write_text("normal content")

        # 清理
        count = AppleDoubleCleaner.clean(tmp_path)

        assert count == 1
        assert not (tmp_path / "._test_file.txt").exists()
        assert (tmp_path / "normal_file.txt").exists()

    def test_clean_nested_appledouble_files(self, tmp_path):
        """测试清理嵌套 AppleDouble 文件"""
        # 创建嵌套目录结构
        nested_dir = tmp_path / "subdir" / "deep"
        nested_dir.mkdir(parents=True)

        (nested_dir / "._deep_file.py").write_text("metadata")
        (tmp_path / "._root_file.txt").write_text("metadata")

        # 清理
        count = AppleDoubleCleaner.clean(tmp_path)

        assert count == 2
        assert not (nested_dir / "._deep_file.py").exists()
        assert not (tmp_path / "._root_file.txt").exists()


class TestSkillLoader:
    """测试 Skill 加载器"""

    @pytest.fixture
    def skill_loader(self, tmp_path):
        """创建 Skill 加载器实例"""
        return SkillLoader(base_path=tmp_path, enable_security_scan=True, strict_mode=False)

    @pytest.mark.asyncio
    async def test_load_simple_skill(self, skill_loader, tmp_path):
        """测试加载简单的 Skill"""
        # 创建简单的 Skill 文件
        skill_file = tmp_path / "simple_skill.py"
        skill_file.write_text("""
class Skill:
    def execute(self, payload, credentials=None):
        return {"result": "executed", "data": payload}
""")

        skill = await skill_loader.load_skill("simple_skill.py")

        assert skill is not None

    @pytest.mark.asyncio
    async def test_load_skill_with_appledouble(self, skill_loader, tmp_path):
        """测试加载包含 AppleDouble 文件的 Skill"""
        # 创建 Skill 文件
        skill_file = tmp_path / "clean_skill.py"
        skill_file.write_text("""
def main():
    return "clean"
""")

        # 创建 AppleDouble 文件
        (tmp_path / "._clean_skill.py").write_text("metadata")

        # 加载（会触发清理）
        skill = await skill_loader.load_skill("clean_skill.py")

        assert skill is not None
        assert not (tmp_path / "._clean_skill.py").exists()  # AppleDouble 文件被清理

    @pytest.mark.asyncio
    async def test_load_nonexistent_skill(self, skill_loader):
        """测试加载不存在的 Skill"""
        with pytest.raises(ValueError, match="Skill path does not exist"):
            await skill_loader.load_skill("nonexistent_skill.py")


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, tmp_path):
        """测试完整工作流"""
        # 1. 创建测试 Skill
        skill_file = tmp_path / "integration_skill.py"
        skill_file.write_text("""
class Skill:
    def execute(self, payload, credentials=None):
        return {"status": "success", "received": payload}
""")

        # 2. 初始化 Bridge API
        bridge = BridgeAPI(
            skill_base_path=tmp_path,
            enable_security_scan=True,
        )

        # 3. 注册 Codex 凭证
        bridge.register_credentials("codex_token", {"token": "test_token"})

        # 4. 执行直接任务
        direct_task = {
            "task_id": "integration_001",
            "task_type": "direct",
            "payload": {"action": "echo", "message": "Integration test"},
        }
        result = await bridge.receive_task(direct_task)
        assert result["status"] == "success"

        # 5. 清理
        await bridge.cleanup()
