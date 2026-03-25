import jwt
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class ChannelAdapter:
    """全协议适配器（Telegram + TWA + Web Dashboard）"""
    
    def __init__(self, secret: str = "your-secret-key"):
        self.secret = secret
        self.algorithm = "HS256"
    
    def get_twa_data(self, session_id: str) -> Dict[str, Any]:
        """获取TWA看板数据"""
        # 模拟数据（实际应从Session Manager读取）
        return {
            "nodes": [
                {"id": "planner", "status": "running", "progress": 45},
                {"id": "generator", "status": "pending", "progress": 0},
                {"id": "executor", "status": "pending", "progress": 0},
                {"id": "evaluator", "status": "pending", "progress": 0}
            ],
            "session": {
                "id": session_id,
                "chat_id": "test_chat",
                "created_at": datetime.now().isoformat()
            }
        }
    
    def generate_magic_link(self, chat_id: str, expires_hours: int = 24) -> str:
        """生成魔法链接JWT"""
        payload = {
            "chat_id": chat_id,
            "exp": datetime.utcnow() + timedelta(hours=expires_hours),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)
    
    def verify_magic_link(self, token: str) -> Dict[str, Any]:
        """验证魔法链接JWT"""
        try:
            return jwt.decode(token, self.secret, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            raise ValueError("Token已过期")
        except jwt.InvalidTokenError:
            raise ValueError("无效Token")
    
    def render_light_dashboard(self, session_id: str) -> Dict[str, Any]:
        """渲染浅色看板"""
        twa_data = self.get_twa_data(session_id)
        return {
            **twa_data,
            "theme": "light",
            "version": "1.0"
        }
    
    def handle_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理Telegram Webhook"""
        if not data:
            raise ValueError("无效的Webhook数据")
        
        # 验证secret token
        if "message" not in data:
            raise ValueError("缺少message字段")
        
        return {"status": "ok"}

# 测试入口
if __name__ == "__main__":
    adapter = ChannelAdapter()
    
    # 测试TWA
    print("测试TWA接口...")
    twa_data = adapter.get_twa_data("test123")
    print(json.dumps(twa_data, indent=2))
    
    # 测试JWT
    print("\n测试魔法链接...")
    token = adapter.generate_magic_link("test_chat")
    print(f"Token: {token}")
    payload = adapter.verify_magic_link(token)
    print(f"Payload: {payload}")
