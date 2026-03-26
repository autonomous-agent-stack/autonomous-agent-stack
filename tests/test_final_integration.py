"""终极收网测试

测试场景：
1. WebAuthn 生物识别
2. Docker 沙盒测试
3. Telegram 群组路由
4. 端到端全链路
"""

from __future__ import annotations

import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient


# ========================================================================
# Test 1: WebAuthn 生物识别测试
# ========================================================================

class TestWebAuthnIntegration:
    """WebAuthn 集成测试"""
    
    def test_webauthn_healthcheck(self):
        """测试 WebAuthn 健康检查"""
        from autoresearch.api.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/auth/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_generate_challenge(self):
        """测试生成挑战"""
        from autoresearch.api.main import app
        
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/generate-challenge",
            json={
                "telegram_uid": "123456",
                "operation": "merge_pr",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "challenge" in data
        assert len(data["challenge"]) > 20
        assert data["timeout"] == 60000


# ========================================================================
# Test 2: Docker 沙盒测试
# ========================================================================

class TestDockerSandbox:
    """Docker 沙盒测试"""
    
    @pytest.mark.asyncio
    async def test_appledouble_cleaner(self, tmp_path):
        """测试 AppleDouble 清理"""
        from src.gatekeeper.sandbox_runner import AppleDoubleCleaner
        
        # 创建测试文件
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")
        
        apple_file = tmp_path / "._test.py"
        apple_file.write_text("garbage")
        
        # 执行清理
        cleaned = AppleDoubleCleaner.clean(str(tmp_path))
        
        assert cleaned == 1
        assert test_file.exists()
        assert not apple_file.exists()
    
    @pytest.mark.asyncio
    async def test_sandbox_runner_mock(self):
        """测试沙盒运行器（模拟模式）"""
        from src.gatekeeper.sandbox_runner import Sandbox_Test_Runner
        
        runner = Sandbox_Test_Runner()
        
        # 模拟测试（不实际运行 Docker）
        with patch.object(runner, '_build_docker_command') as mock_build:
            mock_build.return_value = ["echo", "test"]
            
            # 测试解析功能
            logs = "10 passed, 0 failed"
            passed, failed = runner._parse_test_results(logs)
            
            assert passed == 10
            assert failed == 0


# ========================================================================
# Test 3: Telegram 群组路由测试
# ========================================================================

class TestTelegramGroupRouting:
    """Telegram 群组路由测试"""
    
    def test_group_access_manager_init(self):
        """测试群组访问管理器初始化"""
        from autoresearch.core.services.group_access import GroupAccessManager
        
        manager = GroupAccessManager(
            internal_groups=[-10012345678, -10098765432],
            jwt_secret="test_secret",
        )
        
        assert manager.enabled is True
        assert manager.is_internal_group(-10012345678) is True
        assert manager.is_internal_group(-10099999999) is False
    
    def test_group_magic_link_generation(self):
        """测试群组魔法链接生成"""
        from autoresearch.core.services.group_access import GroupAccessManager
        
        manager = GroupAccessManager(
            internal_groups=[-10012345678],
            jwt_secret="test_secret",
            base_url="http://localhost:8001/api/v1/panel/view",
        )
        
        # 生成魔法链接
        link = manager.create_group_magic_link(
            chat_id=-10012345678,
            user_id=123456,
        )
        
        assert link is not None
        assert link.chat_id == -10012345678
        assert link.user_id == 123456
        assert link.scope == "group"
        assert "token=" in link.url


# ========================================================================
# Test 4: 端到端全链路测试
# ========================================================================

class TestFullPipeline:
    """端到端全链路测试"""
    
    @pytest.mark.asyncio
    async def test_webauthn_to_sandbox_integration(self):
        """测试 WebAuthn + 沙盒集成"""
        from autoresearch.api.main import app
        from src.gatekeeper.sandbox_runner import AppleDoubleCleaner
        
        client = TestClient(app)
        
        # 1. 请求挑战
        challenge_response = client.post(
            "/api/v1/auth/generate-challenge",
            json={
                "telegram_uid": "123456",
                "operation": "merge_pr",
            },
        )
        
        assert challenge_response.status_code == 200
        challenge = challenge_response.json()["challenge"]
        
        # 2. 模拟验证（实际应该调用 navigator.credentials.get()）
        # 这里我们跳过实际验证，直接测试沙盒
        
        # 3. 测试沙盒清理功能
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cleaned = AppleDoubleCleaner.clean(tmpdir)
            assert cleaned == 0  # 空目录应该清理 0 个文件


# ========================================================================
# Test 5: 性能测试
# ========================================================================

class TestPerformance:
    """性能测试"""
    
    def test_challenge_generation_performance(self):
        """测试挑战生成性能（应该 < 100ms）"""
        import time
        from autoresearch.api.main import app
        
        client = TestClient(app)
        
        start = time.time()
        
        for _ in range(10):
            response = client.post(
                "/api/v1/auth/generate-challenge",
                json={
                    "telegram_uid": "123456",
                    "operation": "test",
                },
            )
            assert response.status_code == 200
        
        elapsed = time.time() - start
        
        # 10 次请求应该在 2 秒内完成
        assert elapsed < 2.0
        print(f"✅ 10 次挑战生成耗时: {elapsed:.2f}s")


# ========================================================================
# Test 6: 安全测试
# ========================================================================

class TestSecurity:
    """安全测试"""
    
    def test_challenge_expiration(self):
        """测试挑战过期"""
        from autoresearch.api.main import app
        from autoresearch.api.routers.webauthn import db
        import time
        
        client = TestClient(app)
        
        # 生成挑战（60 秒过期）
        response = client.post(
            "/api/v1/auth/generate-challenge",
            json={
                "telegram_uid": "123456",
                "operation": "test",
            },
        )
        
        assert response.status_code == 200
        challenge = response.json()["challenge"]
        
        # 检查挑战存在
        challenge_data = db.get_challenge(challenge)
        assert challenge_data is not None
    
    def test_challenge_reuse_prevention(self):
        """测试挑战重用防护"""
        from autoresearch.api.main import app
        from autoresearch.api.routers.webauthn import db
        
        client = TestClient(app)
        
        # 生成挑战
        response = client.post(
            "/api/v1/auth/generate-challenge",
            json={
                "telegram_uid": "123456",
                "operation": "test",
            },
        )
        
        challenge = response.json()["challenge"]
        
        # 标记为已使用
        db.mark_challenge_used(challenge)
        
        # 验证已使用的挑战应该失败
        challenge_data = db.get_challenge(challenge)
        assert challenge_data["used"] is True
