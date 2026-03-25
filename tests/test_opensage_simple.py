#!/usr/bin/env python3
"""Simple test for OpenSage components"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
from src.autoresearch.llm import ClaudeBackend, GLMBackend, OpenAIBackend
from src.autoresearch.communication import Message, MessageBus, MessageType
from src.autoresearch.core.decomposer import TaskComplexity, TaskDecomposer


async def test_llm_backends():
    """测试 LLM 后端"""
    print("\n=== 测试 LLM 后端 ===")
    
    # Claude
    claude = ClaudeBackend(api_key="test")
    response = await claude.generate("Hello")
    print(f"✅ Claude: {response}")
    
    # OpenAI
    openai = OpenAIBackend(api_key="test")
    response = await openai.generate("Hello")
    print(f"✅ OpenAI: {response}")
    
    # GLM-5
    glm = GLMBackend(api_key="test")
    response = await glm.generate("你好")
    print(f"✅ GLM-5: {response}")
    
    # Token 计数
    count = await glm.count_tokens("你好世界")
    print(f"✅ GLM-5 Token 计数: {count}")
    
    print("✅ LLM 后端测试通过！")


async def test_message_bus():
    """测试消息总线"""
    print("\n=== 测试消息总线 ===")
    
    bus = MessageBus()
    await bus.start()
    
    received = []
    
    async def handler(msg):
        received.append(msg)
        
    await bus.subscribe("agent_1", handler)
    
    msg = Message(
        type=MessageType.TASK,
        sender="system",
        receiver="agent_1",
        payload={"task": "test"}
    )
    await bus.publish(msg)
    
    await asyncio.sleep(0.5)
    
    assert len(received) == 1, f"Expected 1 message, got {len(received)}"
    print(f"✅ 收到消息: {received[0].payload}")
    
    await bus.stop()
    print("✅ 消息总线测试通过！")


async def test_decomposer():
    """测试任务分解器"""
    print("\n=== 测试任务分解器 ===")
    
    decomposer = TaskDecomposer()
    
    # 测试复杂度分析
    complexity = await decomposer.analyze_complexity("写一个函数")
    print(f"✅ 简单任务复杂度: {complexity.value}")
    assert complexity == TaskComplexity.SIMPLE
    
    complexity = await decomposer.analyze_complexity("分解这个任务")
    print(f"✅ 层级任务复杂度: {complexity.value}")
    assert complexity == TaskComplexity.HIERARCHICAL
    
    # 测试任务分解
    task = "创建 API 端点。添加认证。编写测试。"
    subtasks = await decomposer.decompose(task)
    print(f"✅ 分解为 {len(subtasks)} 个子任务")
    
    for subtask in subtasks:
        print(f"  - {subtask.task_id}: {subtask.description[:30]}...")
        
    # 测试执行顺序
    order = decomposer.get_execution_order(subtasks)
    print(f"✅ 执行顺序: {order}")
    
    print("✅ 任务分解器测试通过！")


async def main():
    """运行所有测试"""
    print("\n🚀 开始测试 OpenSage 组件...")
    
    try:
        await test_llm_backends()
        await test_message_bus()
        await test_decomposer()
        
        print("\n" + "="*50)
        print("✅ 所有测试通过！")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
