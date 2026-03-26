"""
v2.0 Core Tests - 分布式架构单元测试

测试内容：
1. Blitz Router 核心功能
2. SessionMemory 连贯对话
3. OpenSageEngine 动态演化
4. MASFactoryBridge 多 Agent 编排
5. System Health API
"""

import pytest
from datetime import datetime
import json
import os
import sys

# 添加 src 到路径
sys.path.insert(0, '/Volumes/PS1008/Github/autonomous-agent-stack/src')

from bridge.router import router as system_router
from bridge.unified_router import (
    SessionMemory,
    ClaudeCLIExecutor,
    OpenSageEngine,
    MASFactoryBridge,
    BlitzTask,
)


# ========================================================================
# Test 1: SessionMemory - 连贯对话测试
# ========================================================================

class TestSessionMemory:
    """测试连贯对话管理器"""
    
    def test_create_session(self):
        """测试创建会话"""
        session = SessionMemory("test-session-001")
        assert session.session_id == "test-session-001"
    
    def test_save_and_get_context(self):
        """测试保存和获取上下文"""
        session = SessionMemory("test-session-002")
        
        # 保存消息
        session.save_message("user", "你好")
        session.save_message("assistant", "你好！有什么可以帮你的吗？")
        
        # 获取上下文
        context = session.get_context(10)
        
        assert len(context) == 2
        assert context[0]["role"] == "user"
        assert context[0]["content"] == "你好"
        assert context[1]["role"] == "assistant"
    
    def test_context_depth_limit(self):
        """测试上下文深度限制"""
        session = SessionMemory("test-session-003")
        
        # 保存 10 条消息
        for i in range(10):
            session.save_message("user", f"消息 {i}")
        
        # 获取最近 5 条
        context = session.get_context(5)
        assert len(context) == 5


# ========================================================================
# Test 2: OpenSageEngine - 动态演化测试
# ========================================================================

class TestOpenSageEngine:
    """测试动态演化引擎"""
    
    def test_synthesize_safe_code(self):
        """测试合成安全代码"""
        safe_code = """
def hello_world():
    return "Hello, World!"
"""
        result = OpenSageEngine.synthesize_tool(safe_code)
        
        assert result["status"] == "success"
        assert "path" in result
    
    def test_block_dangerous_code(self):
        """测试拦截危险代码"""
        dangerous_codes = [
            "os.system('rm -rf /')",
            "subprocess.call(['cmd'])",
            "eval('print(1)')",
            "exec('print(1)')"
        ]
        
        for code in dangerous_codes:
            result = OpenSageEngine.synthesize_tool(code)
            assert result["status"] == "blocked"


# ========================================================================
# Test 3: MASFactoryBridge - 多 Agent 编排测试
# ========================================================================

class TestMASFactoryBridge:
    """测试多 Agent 编排"""
    
    def test_dispatch_to_matrix(self):
        """测试分发到矩阵"""
        task = "执行数据分析任务"
        result = MASFactoryBridge.dispatch_to_matrix(task)
        
        assert isinstance(result, list)
        assert len(result) == 3
        
        # 验证 Agent 角色
        agents = [r["agent"] for r in result]
        assert "Planner" in agents
        assert "Executor" in agents
        assert "Evaluator" in agents
    
    def test_task_decomposition(self):
        """测试任务分解"""
        task = "分析销售数据并生成报告"
        result = MASFactoryBridge.dispatch_to_matrix(task)
        
        # 验证每个 Agent 都有动作
        for agent_result in result:
            assert "agent" in agent_result
            assert "action" in agent_result


# ========================================================================
# Test 4: System Health API 测试
# ========================================================================

class TestSystemHealthAPI:
    """测试系统健康 API"""
    
    @pytest.mark.asyncio
    async def test_health_endpoint_structure(self):
        """测试健康端点结构"""
        from bridge.router import get_system_health
        
        result = await get_system_health()
        
        # 验证必需字段
        assert "status" in result
        assert "timestamp" in result
        assert "matrix_active" in result
        assert "agents" in result
        assert "audit_metrics" in result
        
        # 验证状态
        assert result["status"] == "online"
        assert isinstance(result["matrix_active"], bool)
    
    @pytest.mark.asyncio
    async def test_agents_structure(self):
        """测试 Agent 结构"""
        from bridge.router import get_system_health
        
        result = await get_system_health()
        
        # 验证每个 Agent 的结构
        for agent in result["agents"]:
            assert "name" in agent
            assert "status" in agent
            assert "task" in agent
    
    @pytest.mark.asyncio
    async def test_audit_metrics(self):
        """测试审计指标"""
        from bridge.router import get_system_health
        
        result = await get_system_health()
        
        metrics = result["audit_metrics"]
        
        assert "apple_double_cleaned" in metrics
        assert "ast_blocks" in metrics
        assert "sandbox_type" in metrics
        assert "storage_path" in metrics


# ========================================================================
# Test 5: Blitz Router 集成测试
# ========================================================================

class TestBlitzRouter:
    """测试 Blitz Router 集成"""
    
    def test_blitz_task_model(self):
        """测试 BlitzTask 模型"""
        task = BlitzTask(
            session_id="test-001",
            prompt="测试任务",
            use_claude_cli=True,
            enable_opensage=True,
            context_depth=5
        )
        
        assert task.session_id == "test-001"
        assert task.prompt == "测试任务"
        assert task.use_claude_cli is True
        assert task.enable_opensage is True
        assert task.context_depth == 5
    
    @pytest.mark.asyncio
    async def test_matrix_status(self):
        """测试矩阵状态"""
        from bridge.unified_router import get_matrix_status
        
        result = await get_matrix_status()
        
        assert result["matrix_active"] is True
        assert len(result["agents"]) == 4
        assert "system_audit" in result


# ========================================================================
# Test 6: 性能测试
# ========================================================================

class TestPerformance:
    """性能测试"""
    
    def test_session_memory_performance(self):
        """测试会话记忆性能"""
        import time
        
        session = SessionMemory("perf-test")
        
        # 插入 100 条消息
        start = time.time()
        for i in range(100):
            session.save_message("user", f"消息 {i}")
        elapsed = time.time() - start
        
        # 应该在 1 秒内完成
        assert elapsed < 1.0
    
    def test_dispatch_performance(self):
        """测试分发性能"""
        import time
        
        start = time.time()
        for _ in range(100):
            MASFactoryBridge.dispatch_to_matrix("测试任务")
        elapsed = time.time() - start
        
        # 100 次分发应该在 1 秒内完成
        assert elapsed < 1.0


# ========================================================================
# 运行测试
# ========================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
