"""Test OpenSage Components - LLM Backend + MessageBus + Decomposer"""

import asyncio
import pytest

from src.autoresearch.llm import ClaudeBackend, GLMBackend, OpenAIBackend
from src.autoresearch.communication import Message, MessageBus, MessageType
from src.autoresearch.core.decomposer import TaskComplexity, TaskDecomposer


class TestLLMBackend:
    """测试 LLM 后端"""
    
    @pytest.mark.asyncio
    async def test_claude_backend(self):
        """测试 Claude 后端"""
        backend = ClaudeBackend(api_key="test_key")
        
        # 测试生成
        response = await backend.generate("Hello, Claude!")
        assert "[Claude]" in response
        
        # 测试 token 计数
        token_count = await backend.count_tokens("Hello, world!")
        assert token_count == 3  # 13 // 4 = 3
        
    @pytest.mark.asyncio
    async def test_openai_backend(self):
        """测试 OpenAI 后端"""
        backend = OpenAIBackend(api_key="test_key")
        
        response = await backend.generate("Hello, GPT!")
        assert "[OpenAI]" in response
        
    @pytest.mark.asyncio
    async def test_glm_backend(self):
        """测试 GLM-5 后端"""
        backend = GLMBackend(api_key="test_key")
        
        response = await backend.generate("你好，GLM！")
        assert "[GLM-5]" in response
        
        # 测试中文 token 计数
        token_count = await backend.count_tokens("你好世界")
        assert token_count == 2  # 4 // 2 = 2


class TestMessageBus:
    """测试消息总线"""
    
    @pytest.mark.asyncio
    async def test_message_bus_basic(self):
        """测试基本消息传递"""
        bus = MessageBus()
        await bus.start()
        
        received_messages = []
        
        async def handler(message: Message):
            received_messages.append(message)
            
        # 订阅
        await bus.subscribe("agent_1", handler)
        
        # 发布消息
        message = Message(
            type=MessageType.TASK,
            sender="system",
            receiver="agent_1",
            payload={"task": "test"}
        )
        await bus.publish(message)
        
        # 等待消息处理
        await asyncio.sleep(0.5)
        
        assert len(received_messages) == 1
        assert received_messages[0].payload["task"] == "test"
        
        await bus.stop()
        
    @pytest.mark.asyncio
    async def test_message_bus_broadcast(self):
        """测试广播消息"""
        bus = MessageBus()
        await bus.start()
        
        received_count = 0
        
        async def handler(message: Message):
            nonlocal received_count
            received_count += 1
            
        # 多个订阅者
        await bus.subscribe("agent_1", handler)
        await bus.subscribe("agent_2", handler)
        await bus.subscribe("all", handler)
        
        # 广播消息
        message = Message(
            type=MessageType.HEARTBEAT,
            sender="system",
            receiver="all",
            payload={"status": "ok"}
        )
        await bus.publish(message)
        
        await asyncio.sleep(0.5)
        
        # agent_1, agent_2, all 都收到
        assert received_count >= 2
        
        await bus.stop()


class TestTaskDecomposer:
    """测试任务分解器"""
    
    @pytest.mark.asyncio
    async def test_analyze_complexity(self):
        """测试任务复杂度分析"""
        decomposer = TaskDecomposer()
        
        # 简单任务
        complexity = await decomposer.analyze_complexity("写一个函数")
        assert complexity == TaskComplexity.SIMPLE
        
        # 中等任务
        complexity = await decomposer.analyze_complexity("创建一个 API 端点，然后添加认证，最后测试")
        assert complexity in [TaskComplexity.MEDIUM, TaskComplexity.COMPLEX]
        
        # 层级任务
        complexity = await decomposer.analyze_complexity("分解这个复杂项目为子任务")
        assert complexity == TaskComplexity.HIERARCHICAL
        
    @pytest.mark.asyncio
    async def test_decompose_simple(self):
        """测试简单任务分解"""
        decomposer = TaskDecomposer()
        
        subtasks = await decomposer.decompose("写一个 Hello World 程序")
        
        assert len(subtasks) == 1
        assert subtasks[0].task_id == "task_0"
        assert subtasks[0].dependencies == []
        
    @pytest.mark.asyncio
    async def test_decompose_medium(self):
        """测试中等任务分解"""
        decomposer = TaskDecomposer()
        
        task = "创建 API 端点。添加认证。编写测试。部署到生产环境。"
        subtasks = await decomposer.decompose(task)
        
        assert len(subtasks) >= 2
        assert subtasks[0].dependencies == []
        assert len(subtasks[1].dependencies) > 0
        
    @pytest.mark.asyncio
    async def test_execution_order(self):
        """测试任务执行顺序"""
        decomposer = TaskDecomposer()
        
        task = "步骤一。步骤二。步骤三。"
        subtasks = await decomposer.decompose(task)
        
        order = decomposer.get_execution_order(subtasks)
        
        assert len(order) == len(subtasks)
        # 拓扑顺序应该是 task_0, task_1, task_2
        assert order[0] == "task_0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
