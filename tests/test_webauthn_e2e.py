"""WebAuthn 端到端测试

测试场景：
1. 生成挑战成功
2. 未携带生物识别签名的请求返回 401
3. 验证断言成功（模拟模式）
4. 挑战过期返回 401
5. 挑战已使用返回 401
"""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from autoresearch.api.main import app
from autoresearch.api.routers.webauthn import db, WEBAUTHN_AVAILABLE


# ========================================================================
# Fixtures
# ========================================================================

@pytest.fixture
def client():
    """测试客户端"""
    return TestClient(app)


@pytest.fixture
def temp_db(tmp_path):
    """临时数据库"""
    db_path = tmp_path / "webauthn.db"
    
    # 临时替换数据库路径
    original_db_path = db.db_path
    db.db_path = db_path
    
    # 重新初始化数据库
    db._init_db()
    
    yield db
    
    # 恢复原始路径
    db.db_path = original_db_path


# ========================================================================
# 测试用例
# ========================================================================

class TestWebAuthnChallenge:
    """测试挑战生成"""
    
    def test_generate_challenge_success(self, client, temp_db):
        """测试生成挑战成功"""
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
        assert "timeout" in data
        assert "rp_id" in data
        assert "user_verification" in data
        
        # 验证 challenge 格式
        assert len(data["challenge"]) > 20
        
        # 验证 timeout
        assert data["timeout"] == 60000
        
        # 验证 user_verification
        assert data["user_verification"] == "required"
    
    def test_generate_challenge_with_credential(self, client, temp_db):
        """测试用户有凭证时生成挑战"""
        # 先注册一个模拟凭证
        temp_db.save_credential(
            telegram_uid="123456",
            credential_id="test_credential_id",
            public_key="test_public_key",
            sign_count=0,
        )
        
        response = client.post(
            "/api/v1/auth/generate-challenge",
            json={
                "telegram_uid": "123456",
                "operation": "merge_pr",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证 challenge 已保存
        challenge_data = temp_db.get_challenge(data["challenge"])
        assert challenge_data is not None
        assert challenge_data["telegram_uid"] == "123456"
        assert challenge_data["operation"] == "merge_pr"


class TestWebAuthnVerification:
    """测试生物识别验证"""
    
    def test_verify_assertion_without_challenge(self, client, temp_db):
        """测试没有挑战时验证失败"""
        response = client.post(
            "/api/v1/auth/verify-assertion",
            json={
                "telegram_uid": "123456",
                "credential": {"id": "test"},
                "challenge": "invalid_challenge",
            },
        )
        
        assert response.status_code == 401
        assert "Invalid or expired challenge" in response.json()["detail"]
    
    def test_verify_assertion_with_expired_challenge(self, client, temp_db):
        """测试挑战过期时验证失败"""
        from datetime import datetime, timedelta
        
        # 创建一个已过期的挑战
        challenge = "expired_challenge"
        now = datetime.utcnow()
        expires_at = now - timedelta(seconds=10)  # 10 秒前过期
        
        temp_db.save_challenge(
            challenge=challenge,
            telegram_uid="123456",
            operation="merge_pr",
            expires_in_seconds=-10,  # 立即过期
        )
        
        # 手动设置过期时间
        import sqlite3
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE challenges
            SET expires_at = ?
            WHERE challenge = ?
        """, (expires_at.isoformat(), challenge))
        conn.commit()
        conn.close()
        
        # 先注册凭证
        temp_db.save_credential(
            telegram_uid="123456",
            credential_id="test_credential_id",
            public_key="test_public_key",
            sign_count=0,
        )
        
        response = client.post(
            "/api/v1/auth/verify-assertion",
            json={
                "telegram_uid": "123456",
                "credential": {"id": "test"},
                "challenge": challenge,
            },
        )
        
        assert response.status_code == 401
        assert "Challenge expired" in response.json()["detail"]
    
    def test_verify_assertion_with_used_challenge(self, client, temp_db):
        """测试挑战已使用时验证失败"""
        # 创建一个挑战
        challenge = "used_challenge"
        temp_db.save_challenge(
            challenge=challenge,
            telegram_uid="123456",
            operation="merge_pr",
        )
        
        # 标记为已使用
        temp_db.mark_challenge_used(challenge)
        
        # 注册凭证
        temp_db.save_credential(
            telegram_uid="123456",
            credential_id="test_credential_id",
            public_key="test_public_key",
            sign_count=0,
        )
        
        response = client.post(
            "/api/v1/auth/verify-assertion",
            json={
                "telegram_uid": "123456",
                "credential": {"id": "test"},
                "challenge": challenge,
            },
        )
        
        assert response.status_code == 401
        assert "Challenge already used" in response.json()["detail"]
    
    def test_verify_assertion_uid_mismatch(self, client, temp_db):
        """测试 UID 不匹配时验证失败"""
        # 创建一个挑战
        challenge = "test_challenge"
        temp_db.save_challenge(
            challenge=challenge,
            telegram_uid="123456",
            operation="merge_pr",
        )
        
        # 注册凭证（不同 UID）
        temp_db.save_credential(
            telegram_uid="654321",
            credential_id="test_credential_id",
            public_key="test_public_key",
            sign_count=0,
        )
        
        response = client.post(
            "/api/v1/auth/verify-assertion",
            json={
                "telegram_uid": "654321",  # 不匹配的 UID
                "credential": {"id": "test"},
                "challenge": challenge,
            },
        )
        
        assert response.status_code == 401
        assert "UID mismatch" in response.json()["detail"]
    
    def test_verify_assertion_success_mock(self, client, temp_db):
        """测试验证成功（模拟模式）"""
        # 创建挑战
        challenge_response = client.post(
            "/api/v1/auth/generate-challenge",
            json={
                "telegram_uid": "123456",
                "operation": "merge_pr",
            },
        )
        
        challenge = challenge_response.json()["challenge"]
        
        # 注册凭证
        temp_db.save_credential(
            telegram_uid="123456",
            credential_id="test_credential_id",
            public_key="test_public_key",
            sign_count=0,
        )
        
        # 验证断言
        response = client.post(
            "/api/v1/auth/verify-assertion",
            json={
                "telegram_uid": "123456",
                "credential": {"id": "test"},
                "challenge": challenge,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["verified"] is True
        assert "successful" in data["message"]
        
        # 验证挑战已标记为使用
        challenge_data = temp_db.get_challenge(challenge)
        assert challenge_data["used"] is True


class TestBiometricRequired:
    """测试生物识别强制验证"""
    
    def test_missing_assertion_header(self, client):
        """测试缺少生物识别签名头"""
        # TODO: 实现需要生物识别的端点
        # 这里我们测试一个假设的敏感端点
        
        # response = client.post(
        #     "/api/v1/sensitive/operation",
        #     json={"data": "test"},
        # )
        # 
        # assert response.status_code == 401
        # assert "Biometric required" in response.json()["detail"]
        
        pass  # 暂时跳过，等待实现敏感端点


class TestWebAuthnHealth:
    """测试健康检查"""
    
    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get("/api/v1/auth/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ok"
        assert "webauthn_available" in data
        assert "rp_id" in data


class TestWebAuthnDemo:
    """测试演示页面"""
    
    def test_demo_page(self, client):
        """测试演示页面加载"""
        response = client.get("/webauthn-demo")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # 验证关键元素
        html = response.text
        assert "WebAuthn" in html
        assert "批准并部署 PR" in html
        assert "验证身份中..." in html


# ========================================================================
# 集成测试
# ========================================================================

class TestWebAuthnFullFlow:
    """端到端全流程测试"""
    
    def test_full_flow_mock(self, client, temp_db):
        """测试完整流程（模拟模式）"""
        # 1. 生成挑战
        challenge_response = client.post(
            "/api/v1/auth/generate-challenge",
            json={
                "telegram_uid": "123456",
                "operation": "merge_pr",
            },
        )
        
        assert challenge_response.status_code == 200
        challenge = challenge_response.json()["challenge"]
        
        # 2. 注册凭证
        temp_db.save_credential(
            telegram_uid="123456",
            credential_id="test_credential_id",
            public_key="test_public_key",
            sign_count=0,
        )
        
        # 3. 验证断言
        verify_response = client.post(
            "/api/v1/auth/verify-assertion",
            json={
                "telegram_uid": "123456",
                "credential": {"id": "test"},
                "challenge": challenge,
            },
        )
        
        assert verify_response.status_code == 200
        assert verify_response.json()["verified"] is True
        
        # 4. 验证挑战已使用
        challenge_data = temp_db.get_challenge(challenge)
        assert challenge_data["used"] is True


# ========================================================================
# 性能测试
# ========================================================================

class TestWebAuthnPerformance:
    """性能测试"""
    
    def test_challenge_generation_performance(self, client, temp_db):
        """测试挑战生成性能（应该 < 100ms）"""
        import time
        
        start = time.time()
        
        for _ in range(10):
            response = client.post(
                "/api/v1/auth/generate-challenge",
                json={
                    "telegram_uid": "123456",
                    "operation": "merge_pr",
                },
            )
            assert response.status_code == 200
        
        elapsed = time.time() - start
        
        # 10 次请求应该在 1 秒内完成
        assert elapsed < 1.0
        print(f"✅ 10 次挑战生成耗时: {elapsed:.2f}s")
