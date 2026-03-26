"""P4 自我进化协议：端到端测试

测试场景：
1. 触发与解析
2. 沙盒试错
3. 人类审批
4. 热更新
"""

from __future__ import annotations

import asyncio
import pytest
from dataclasses import dataclass
from unittest.mock import patch, MagicMock, AsyncMock

from src.autoresearch.agents.integration_agent import TriggerAndParse
from src.autoresearch.agents.adapter_generator import SandboxTrial
from src.autoresearch.core.services.hitl_approval import HITLApproval
from src.autoresearch.core.services.tool_registry import HotSwapManager


# ========================================================================
# Mock 数据
# ========================================================================

@dataclass
class MockProtocolSpec:
    name: str
    version: str
    test_cases: list


@dataclass
class MockAdapter:
    id: str
    name: str
    code: str
    spec: Any
    test_result: Any


@dataclass
class MockTestResult:
    success: bool
    success_rate: float
    duration: float
    errors: list


@dataclass
class MockApprovalDecision:
    approved: bool
    approver_id: str


# ========================================================================
# Test 1: 触发与解析测试
# ========================================================================

class TestTriggerAndParse:
    """触发与解析测试"""
    
    @pytest.mark.asyncio
    async def test_parse_github_repo(self):
        """测试解析 GitHub 仓库"""
        tap = TriggerAndParse()
        
        # 模拟克隆仓库
        with patch.object(tap.agent, 'clone_repo') as mock_clone:
            mock_clone.return_value = MagicMock()
            
            # 模拟分析协议
            with patch.object(tap.agent, 'analyze_protocol') as mock_analyze:
                mock_analyze.return_value = MockProtocolSpec(
                    name="test-protocol",
                    version="1.0.0",
                    test_cases=[],
                )
                
                spec = await tap.parse_github_repo(
                    "https://github.com/test/test.git"
                )
                
                assert spec.name == "test-protocol"
                assert spec.version == "1.0.0"


# ========================================================================
# Test 2: 沙盒试错测试
# ========================================================================

class TestSandboxTrial:
    """沙盒试错测试"""
    
    @pytest.mark.asyncio
    async def test_generate_adapter(self):
        """测试生成适配器"""
        st = SandboxTrial()
        
        spec = MockProtocolSpec(
            name="test-protocol",
            version="1.0.0",
            test_cases=[{"name": "test_health", "expected": "ok"}],
        )
        
        # 模拟 Docker 压测
        with patch.object(st, '_run_in_docker') as mock_run:
            mock_run.return_value = MockTestResult(
                success=True,
                success_rate=1.0,
                duration=5.2,
                errors=[],
            )
            
            adapter = await st.generate_adapter(spec)
            
            assert adapter.name == "test-protocol"
            assert adapter.test_result.success_rate == 1.0


# ========================================================================
# Test 3: 人类审批测试
# ========================================================================

class TestHITLApproval:
    """人类审批测试"""
    
    @pytest.mark.asyncio
    async def test_request_approval(self):
        """测试请求审批"""
        approval = HITLApproval(
            admin_chat_id="123456",
            telegram_bot_token="test_token",
        )
        
        adapter = MockAdapter(
            id="adapter_123",
            name="test-adapter",
            code="print('hello')",
            spec=MockProtocolSpec(name="test", version="1.0", test_cases=[]),
            test_result=MockTestResult(
                success=True,
                success_rate=0.98,
                duration=5.2,
                errors=[],
            ),
        )
        
        # 模拟发送消息
        with patch.object(approval, '_send_telegram_message') as mock_send:
            mock_send.return_value = "msg_123"
            
            # 模拟等待审批
            with patch.object(approval, '_wait_for_approval') as mock_wait:
                mock_wait.return_value = MockApprovalDecision(
                    approved=True,
                    approver_id="admin_123",
                )
                
                decision = await approval.request_approval(adapter)
                
                assert decision.approved is True
                assert decision.approver_id == "admin_123"


# ========================================================================
# Test 4: 热更新测试
# ========================================================================

class TestHotSwap:
    """热更新测试"""
    
    @pytest.mark.asyncio
    async def test_hot_swap_tool(self):
        """测试热更新工具"""
        manager = HotSwapManager()
        
        adapter = MockAdapter(
            id="adapter_123",
            name="test-adapter",
            code="print('hello')",
            spec=MockProtocolSpec(name="test", version="1.0", test_cases=[]),
            test_result=None,
        )
        
        approval = MockApprovalDecision(
            approved=True,
            approver_id="admin_123",
        )
        
        # 模拟广播和审计
        with patch.object(manager, '_broadcast_to_agents') as mock_broadcast:
            with patch.object(manager, '_audit_log') as mock_audit:
                success = await manager.hot_swap_tool(adapter, approval)
                
                assert success is True
                assert len(manager.registry.list_all()) == 1
    
    @pytest.mark.asyncio
    async def test_hot_swap_rejected(self):
        """测试审批被拒绝"""
        manager = HotSwapManager()
        
        adapter = MockAdapter(
            id="adapter_456",
            name="test-adapter-2",
            code="print('hello')",
            spec=MockProtocolSpec(name="test", version="1.0", test_cases=[]),
            test_result=None,
        )
        
        approval = MockApprovalDecision(
            approved=False,
            approver_id="admin_123",
        )
        
        success = await manager.hot_swap_tool(adapter, approval)
        
        assert success is False
        assert len(manager.registry.list_all()) == 0


# ========================================================================
# Test 5: 端到端测试
# ========================================================================

class TestP4EndToEnd:
    """端到端测试"""
    
    @pytest.mark.asyncio
    async def test_full_p4_workflow(self):
        """测试完整 P4 工作流"""
        # 1. 触发与解析
        tap = TriggerAndParse()
        
        with patch.object(tap.agent, 'clone_repo') as mock_clone:
            with patch.object(tap.agent, 'analyze_protocol') as mock_analyze:
                mock_clone.return_value = MagicMock()
                mock_analyze.return_value = MockProtocolSpec(
                    name="e2e-protocol",
                    version="1.0.0",
                    test_cases=[],
                )
                
                spec = await tap.parse_github_repo(
                    "https://github.com/test/e2e.git"
                )
                
                assert spec.name == "e2e-protocol"
        
        # 2. 沙盒试错
        st = SandboxTrial()
        
        with patch.object(st, '_run_in_docker') as mock_run:
            mock_run.return_value = MockTestResult(
                success=True,
                success_rate=1.0,
                duration=5.2,
                errors=[],
            )
            
            adapter = await st.generate_adapter(spec)
            
            assert adapter.test_result.success_rate == 1.0
        
        # 3. 人类审批
        approval = HITLApproval(
            admin_chat_id="123456",
            telegram_bot_token="test_token",
        )
        
        with patch.object(approval, '_send_telegram_message') as mock_send:
            with patch.object(approval, '_wait_for_approval') as mock_wait:
                mock_send.return_value = "msg_123"
                mock_wait.return_value = MockApprovalDecision(
                    approved=True,
                    approver_id="admin_123",
                )
                
                decision = await approval.request_approval(adapter)
                
                assert decision.approved is True
        
        # 4. 热更新
        manager = HotSwapManager()
        
        with patch.object(manager, '_broadcast_to_agents'):
            with patch.object(manager, '_audit_log'):
                success = await manager.hot_swap_tool(adapter, decision)
                
                assert success is True
                assert len(manager.registry.list_all()) == 1
                assert manager.registry.list_all()[0].name == "e2e-protocol"
