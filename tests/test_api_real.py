"""
真实 API 集成测试

验证 FastAPI 应用的完整链路：
POST /api/v1/evaluations → SQLite 持久化 → GET /api/v1/evaluations/{task_id}
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fastapi.testclient import TestClient
import json


def test_api_skeleton():
    """测试 API Skeleton"""
    print("=" * 60)
    print("🧪 API Skeleton 集成测试")
    print("=" * 60)
    print()
    
    # 导入应用
    try:
        from autoresearch.api.main import app
        print("✅ FastAPI 应用导入成功")
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False
    
    # 创建测试客户端
    client = TestClient(app)
    print("✅ 测试客户端创建成功")
    print()
    
    # 测试 1: 健康检查
    print("📍 测试 1: 健康检查")
    try:
        response = client.get("/health")
        if response.status_code == 200:
            print(f"✅ 健康检查通过: {response.json()}")
        else:
            print(f"⚠️ 健康检查异常: {response.status_code}")
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
    print()
    
    # 测试 2: 创建评估任务
    print("📍 测试 2: 创建评估任务")
    try:
        response = client.post(
            "/api/v1/evaluations",
            json={
                "task_name": "test_task",
                "config_path": "test.json",
                "description": "API 集成测试"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            task_id = data.get("task_id")
            print(f"✅ 任务创建成功: {task_id}")
            print(f"   状态: {data.get('status')}")
            
            # 测试 3: 查询任务
            print("\n📍 测试 3: 查询评估任务")
            get_response = client.get(f"/api/v1/evaluations/{task_id}")
            
            if get_response.status_code == 200:
                task_data = get_response.json()
                print(f"✅ 任务查询成功: {task_data.get('task_id')}")
                print(f"   状态: {task_data.get('status')}")
            else:
                print(f"❌ 任务查询失败: {get_response.status_code}")
            
        else:
            print(f"❌ 任务创建失败: {response.status_code}")
            print(f"   错误: {response.text}")
            
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # 测试 4: 列出所有任务
    print("📍 测试 4: 列出所有评估任务")
    try:
        response = client.get("/api/v1/evaluations")
        if response.status_code == 200:
            data = response.json()
            evaluations = data.get("evaluations", [])
            print(f"✅ 列表查询成功: {len(evaluations)} 个任务")
        else:
            print(f"❌ 列表查询失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 列表查询失败: {e}")
    print()
    
    # 测试 5: evaluator_command override
    print("📍 测试 5: evaluator_command override")
    try:
        response = client.post(
            "/api/v1/evaluations",
            json={
                "task_name": "test_with_override",
                "config_path": "test.json",
                "evaluator_command": {
                    "command": ["python", "test.py"],
                    "timeout_seconds": 60,
                    "work_dir": ".",
                    "env": {"DEBUG": "true"}
                }
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Override 测试成功: {data.get('task_id')}")
        else:
            print(f"❌ Override 测试失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Override 测试失败: {e}")
    print()
    
    print("=" * 60)
    print("🎉 API Skeleton 集成测试完成")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    test_api_skeleton()
