"""
Agent 认证中间件
支持 Bearer Token 和 API Key 认证
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import os
import hashlib
import secrets

security = HTTPBearer()

class AuthConfig:
    """认证配置"""
    # 从环境变量读取密钥
    SECRET_KEY = os.getenv("AUTH_SECRET_KEY", secrets.token_urlsafe(32))
    API_KEY = os.getenv("ADMIN_API_KEY", None)
    
    # Token 有效期（秒）
    TOKEN_EXPIRE_SECONDS = 3600 * 24  # 24 小时
    
    # 允许的 Agent ID 列表
    ALLOWED_AGENTS = os.getenv("ALLOWED_AGENTS", "").split(",") if os.getenv("ALLOWED_AGENTS") else []

def verify_token(token: str) -> Optional[dict]:
    """验证 Bearer Token"""
    # 简单的 token 验证（生产环境应使用 JWT）
    if token == AuthConfig.API_KEY:
        return {"role": "admin", "agent_id": "admin"}
    
    # 检查是否在允许列表中
    for agent_id in AuthConfig.ALLOWED_AGENTS:
        expected_token = hashlib.sha256(f"{agent_id}:{AuthConfig.SECRET_KEY}".encode()).hexdigest()
        if token == expected_token:
            return {"role": "agent", "agent_id": agent_id}
    
    return None

async def get_current_agent(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    获取当前认证的 Agent
    用于需要认证的端点
    """
    token = credentials.credentials
    
    # 验证 token
    agent_info = verify_token(token)
    
    if not agent_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return agent_info

async def get_optional_agent(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[dict]:
    """
    可选的 Agent 认证
    不强制要求认证，但如果有 token 则验证
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    return verify_token(token)

def generate_agent_token(agent_id: str) -> str:
    """为指定 Agent 生成 token"""
    return hashlib.sha256(f"{agent_id}:{AuthConfig.SECRET_KEY}".encode()).hexdigest()

# 导出常用依赖
__all__ = [
    "get_current_agent",
    "get_optional_agent",
    "generate_agent_token",
    "AuthConfig"
]
