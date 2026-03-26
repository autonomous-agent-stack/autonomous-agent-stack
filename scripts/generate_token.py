#!/usr/bin/env python3
"""生成 Agent 认证 Token"""
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from autoresearch.core.auth.middleware import generate_agent_token

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python scripts/generate_token.py <agent_id>")
        print("示例: python scripts/generate_token.py agent-001")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    token = generate_agent_token(agent_id)
    
    print(f"Agent ID: {agent_id}")
    print(f"Token: {token}")
    print(f"\n使用方法:")
    print(f"curl -H 'Authorization: Bearer {token}' http://127.0.0.1:8000/api/v1/admin/agents")
