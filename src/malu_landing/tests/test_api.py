"""
玛露遮瑕膏落地页 - API 测试

测试内容：
- 预约创建测试
- 预约查询测试
- 边界测试
- 错误处理测试
"""

import pytest
from fastapi.testclient import TestClient
from src.malu_landing.api.reservation import app

client = TestClient(app)

class TestReservationAPI:
    """预约 API 测试"""
    
    def test_create_reservation_success(self):
        """测试：成功创建预约"""
        response = client.post("/api/reservation", json={
            "name": "测试用户",
            "phone": "13800138000",
            "email": "test@example.com",
            "shade": "light",
            "message": "测试留言"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "测试用户"
        assert data["phone"] == "13800138000"
        assert data["status"] == "pending"
    
    def test_create_reservation_minimal(self):
        """测试：最小化预约（仅必填字段）"""
        response = client.post("/api/reservation", json={
            "name": "张三",
            "phone": "13900139000",
            "shade": "medium"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "张三"
    
    def test_get_reservation_success(self):
        """测试：成功查询预约"""
        # 先创建预约
        create_response = client.post("/api/reservation", json={
            "name": "李四",
            "phone": "13700137000",
            "shade": "dark"
        })
        
        reservation_id = create_response.json()["id"]
        
        # 查询预约
        get_response = client.get(f"/api/reservation/{reservation_id}")
        
        assert get_response.status_code == 200
        assert get_response.json()["id"] == reservation_id
    
    def test_get_reservation_not_found(self):
        """测试：查询不存在的预约"""
        response = client.get("/api/reservation/INVALID_ID")
        
        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]

class TestValidation:
    """数据验证测试"""
    
    def test_invalid_phone_too_short(self):
        """测试：手机号太短"""
        response = client.post("/api/reservation", json={
            "name": "测试",
            "phone": "1380013800",  # 10位
            "shade": "light"
        })
        
        assert response.status_code == 422
    
    def test_invalid_phone_too_long(self):
        """测试：手机号太长"""
        response = client.post("/api/reservation", json={
            "name": "测试",
            "phone": "138001380001",  # 12位
            "shade": "light"
        })
        
        assert response.status_code == 422
    
    def test_invalid_phone_wrong_start(self):
        """测试：手机号开头错误"""
        response = client.post("/api/reservation", json={
            "name": "测试",
            "phone": "23800138000",  # 不以1开头
            "shade": "light"
        })
        
        assert response.status_code == 422
    
    def test_invalid_name_too_short(self):
        """测试：姓名太短"""
        response = client.post("/api/reservation", json={
            "name": "张",  # 1个字符
            "phone": "13800138000",
            "shade": "light"
        })
        
        assert response.status_code == 422
    
    def test_invalid_shade(self):
        """测试：色号无效"""
        response = client.post("/api/reservation", json={
            "name": "测试",
            "phone": "13800138000",
            "shade": "invalid_shade"
        })
        
        assert response.status_code == 422
    
    def test_missing_required_fields(self):
        """测试：缺少必填字段"""
        response = client.post("/api/reservation", json={
            "name": "测试"
            # 缺少 phone 和 shade
        })
        
        assert response.status_code == 422

class TestHealthCheck:
    """健康检查测试"""
    
    def test_health_check(self):
        """测试：健康检查"""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

# 边界测试
class TestBoundary:
    """边界测试"""
    
    def test_max_name_length(self):
        """测试：姓名最大长度"""
        response = client.post("/api/reservation", json={
            "name": "张" * 50,  # 50个字符
            "phone": "13800138000",
            "shade": "light"
        })
        
        assert response.status_code == 201
    
    def test_name_exceed_max_length(self):
        """测试：姓名超过最大长度"""
        response = client.post("/api/reservation", json={
            "name": "张" * 51,  # 51个字符
            "phone": "13800138000",
            "shade": "light"
        })
        
        assert response.status_code == 422
    
    def test_max_message_length(self):
        """测试：留言最大长度"""
        response = client.post("/api/reservation", json={
            "name": "测试",
            "phone": "13800138000",
            "shade": "light",
            "message": "测" * 500  # 500个字符
        })
        
        assert response.status_code == 201
    
    def test_message_exceed_max_length(self):
        """测试：留言超过最大长度"""
        response = client.post("/api/reservation", json={
            "name": "测试",
            "phone": "13800138000",
            "shade": "light",
            "message": "测" * 501  # 501个字符
        })
        
        assert response.status_code == 422

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
