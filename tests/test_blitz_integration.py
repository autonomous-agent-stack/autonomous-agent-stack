#!/usr/bin/env python3
"""Blitz Integration Test - 全链路压测脚本

测试四大能力集成：
1. 连贯对话 (A)
2. Claude CLI 适配 (B)
3. OpenSage 核心逻辑 (C)
4. MAS Factory 桥接 (D)
"""

import asyncio
import sys
import time
from pathlib import Path

# 添加 src 到路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from bridge.unified_router import UnifiedRouter, UnifiedRequest


async def test_chat():
    """测试连贯对话"""
    print("\n" + "="*50)
    print("测试 1: 连贯对话 (A)")
    print("="*50)
    
    router = UnifiedRouter()
    
    # 第一轮对话
    request1 = UnifiedRequest(
        request_id="chat_001",
        request_type="chat",
        content="你好，我是测试用户",
        user_id="test_user"
    )
    
    response1 = await router.route(request1)
    
    print(f"✅ 第一轮响应: {response1.status}")
    print(f"   Session ID: {response1.session_id}")
    
    # 第二轮对话（使用同一 session）
    request2 = UnifiedRequest(
        request_id="chat_002",
        request_type="chat",
        content="记住我的名字",
        session_id=response1.session_id,
        user_id="test_user"
    )
    
    response2 = await router.route(request2)
    
    print(f"✅ 第二轮响应: {response2.status}")
    
    # 第三轮对话（测试记忆）
    request3 = UnifiedRequest(
        request_id="chat_003",
        request_type="chat",
        content="我叫什么名字？",
        session_id=response1.session_id,
        user_id="test_user"
    )
    
    response3 = await router.route(request3)
    
    print(f"✅ 第三轮响应: {response3.status}")
    print(f"   Content: {response3.content[:100] if response3.content else 'None'}")
    
    return response3.status == "success"


async def test_task():
    """测试任务编排"""
    print("\n" + "="*50)
    print("测试 2: 任务编排 (B + C)")
    print("="*50)
    
    router = UnifiedRouter()
    
    request = UnifiedRequest(
        request_id="task_001",
        request_type="task",
        content="分析市场数据。生成报告。发送邮件通知。",
        user_id="test_user"
    )
    
    response = await router.route(request)
    
    print(f"✅ 任务状态: {response.status}")
    print(f"   拓扑结构: {response.result.get('topology', '')[:100]}")
    
    return response.status == "success"


async def test_synthesize():
    """测试工具合成"""
    print("\n" + "="*50)
    print("测试 3: 工具合成 (C)")
    print("="*50)
    
    router = UnifiedRouter()
    
    request = UnifiedRequest(
        request_id="synthesize_001",
        request_type="synthesize",
        content="计算两个数的和",
        metadata={
            "code": "def add(a, b): return a + b"
        }
    )
    
    response = await router.route(request)
    
    print(f"✅ 合成状态: {response.status}")
    print(f"   工具名称: {response.result.get('tool_name', 'None')}")
    print(f"   是否有效: {response.result.get('is_valid', False)}")
    
    return response.status == "success"


async def test_orchestrate():
    """测试多智能体编排"""
    print("\n" + "="*50)
    print("测试 4: 多智能体编排 (D)")
    print("="*50)
    
    router = UnifiedRouter()
    
    request = UnifiedRequest(
        request_id="orchestrate_001",
        request_type="orchestrate",
        content="分析用户反馈数据并生成报告",
        user_id="test_user"
    )
    
    response = await router.route(request)
    
    print(f"✅ 编排状态: {response.status}")
    print(f"   任务 ID: {response.result.get('task_id', 'None')}")
    print(f"   执行状态: {response.result.get('status', 'None')}")
    
    return response.status == "success"


async def test_integration():
    """测试完整集成"""
    print("\n" + "="*50)
    print("测试 5: 完整集成 (A + B + C + D)")
    print("="*50)
    
    router = UnifiedRouter()
    
    # 测试系统状态
    status = router.get_status()
    
    print("系统状态:")
    for key, value in status.items():
        print(f"  - {key}: {value}")
        
    # 测试完整流程
    request = UnifiedRequest(
        request_id="integration_001",
        request_type="chat",
        content="帮我分析市场趋势，生成报告，并发送给团队",
        user_id="test_user"
    )
    
    response = await router.route(request)
    
    print(f"\n✅ 集成测试状态: {response.status}")
    
    return response.status == "success"


async def main():
    """运行所有测试"""
    print("\n" + "="*50)
    print("🚀 Blitz Integration Test")
    print("="*50)
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # 运行测试
    start_time = time.time()
    
    try:
        results.append(("连贯对话", await test_chat()))
    except Exception as e:
        print(f"❌ 连贯对话测试失败: {e}")
        results.append(("连贯对话", False))
        
    try:
        results.append(("任务编排", await test_task()))
    except Exception as e:
        print(f"❌ 任务编排测试失败: {e}")
        results.append(("任务编排", False))
        
    try:
        results.append(("工具合成", await test_synthesize()))
    except Exception as e:
        print(f"❌ 工具合成测试失败: {e}")
        results.append(("工具合成", False))
        
    try:
        results.append(("多智能体编排", await test_orchestrate()))
    except Exception as e:
        print(f"❌ 多智能体编排测试失败: {e}")
        results.append(("多智能体编排", False))
        
    try:
        results.append(("完整集成", await test_integration()))
    except Exception as e:
        print(f"❌ 完整集成测试失败: {e}")
        results.append(("完整集成", False))
        
    elapsed_time = time.time() - start_time
    
    # 输出总结
    print("\n" + "="*50)
    print("📊 测试结果总结")
    print("="*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
        
    print(f"\n总计: {passed}/{total} 通过")
    print(f"耗时: {elapsed_time:.2f} 秒")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️ {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
