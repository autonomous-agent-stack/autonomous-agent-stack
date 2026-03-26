"""Unified Router - 四大能力统一入口

整合连贯对话、Claude CLI、OpenSage、MAS Factory
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field

# 导入各模块
import sys
from pathlib import Path

# 添加 src 到路径
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from memory.session_store import SessionStore, get_session_store
from executors.claude_cli_adapter import ClaudeCLIAdapter, get_claude_adapter
from opensage.tool_synthesizer import ToolSynthesizer, get_tool_synthesizer
from opensage.topology_engine import TopologyEngine, get_topology_engine
from bridge.mas_factory_bridge import MASFactoryBridge, get_mas_bridge
from bridge.consensus_manager import ConsensusManager, get_consensus_manager

logger = logging.getLogger(__name__)


@dataclass
class UnifiedRequest:
    """统一请求"""
    request_id: str
    request_type: str  # chat, task, synthesize, orchestrate
    content: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedResponse:
    """统一响应"""
    request_id: str
    status: str  # success, failed, pending
    content: Optional[str] = None
    session_id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class UnifiedRouter:
    """统一路由器"""
    
    def __init__(self):
        self.session_store = get_session_store()
        self.claude_adapter = get_claude_adapter()
        self.tool_synthesizer = get_tool_synthesizer()
        self.topology_engine = get_topology_engine()
        self.mas_bridge = get_mas_bridge()
        self.consensus_manager = get_consensus_manager()
        
    async def route(self, request: UnifiedRequest) -> UnifiedResponse:
        """路由请求到对应处理器
        
        Args:
            request: 统一请求
            
        Returns:
            统一响应
        """
        logger.info(f"[Unified Router] 路由请求: {request.request_type}")
        
        try:
            if request.request_type == "chat":
                return await self._handle_chat(request)
            elif request.request_type == "task":
                return await self._handle_task(request)
            elif request.request_type == "synthesize":
                return await self._handle_synthesize(request)
            elif request.request_type == "orchestrate":
                return await self._handle_orchestrate(request)
            else:
                return UnifiedResponse(
                    request_id=request.request_id,
                    status="failed",
                    error=f"未知请求类型: {request.request_type}"
                )
                
        except Exception as e:
            logger.error(f"[Unified Router] 处理失败: {e}")
            
            return UnifiedResponse(
                request_id=request.request_id,
                status="failed",
                error=str(e)
            )
            
    async def _handle_chat(self, request: UnifiedRequest) -> UnifiedResponse:
        """处理对话请求"""
        logger.info("[Unified Router] 处理对话请求")
        
        # 创建或获取会话
        if not request.session_id:
            request.session_id = await self.session_store.create_session(
                user_id=request.user_id or "default"
            )
            
        # 加载上下文
        context = await self.session_store.load_context(request.session_id)
        
        # 调用 Claude CLI
        response = await self.claude_adapter.execute(
            prompt=request.content,
            context=context
        )
        
        # 保存历史
        await self.session_store.save_history(
            session_id=request.session_id,
            role="user",
            content=request.content
        )
        
        await self.session_store.save_history(
            session_id=request.session_id,
            role="assistant",
            content=response
        )
        
        return UnifiedResponse(
            request_id=request.request_id,
            status="success",
            content=response,
            session_id=request.session_id
        )
        
    async def _handle_task(self, request: UnifiedRequest) -> UnifiedResponse:
        """处理任务请求"""
        logger.info("[Unified Router] 处理任务请求")
        
        # 生成拓扑
        topology = await self.topology_engine.generate_topology(
            task=request.content,
            available_agents=["claude", "glm"]
        )
        
        # 获取执行顺序
        execution_order = self.topology_engine.get_execution_order()
        
        # 执行任务
        results = {}
        
        for node_id in execution_order:
            node = self.topology_engine.nodes[node_id]
            
            # 执行节点
            result = await self.claude_adapter.execute(
                prompt=node.description
            )
            
            results[node_id] = result
            
        return UnifiedResponse(
            request_id=request.request_id,
            status="success",
            result={
                "topology": self.topology_engine.visualize(),
                "results": results
            }
        )
        
    async def _handle_synthesize(self, request: UnifiedRequest) -> UnifiedResponse:
        """处理工具合成请求"""
        logger.info("[Unified Router] 处理工具合成请求")
        
        # 合成工具
        tool = await self.tool_synthesizer.synthesize(
            task_description=request.content,
            code_snippet=request.metadata.get("code", "")
        )
        
        return UnifiedResponse(
            request_id=request.request_id,
            status="success" if tool.is_valid else "failed",
            result={
                "tool_name": tool.name,
                "is_valid": tool.is_valid,
                "error": tool.error
            }
        )
        
    async def _handle_orchestrate(self, request: UnifiedRequest) -> UnifiedResponse:
        """处理编排请求"""
        logger.info("[Unified Router] 处理编排请求")
        
        # 提交任务到 MAS Bridge
        from bridge.mas_factory_bridge import TaskSpec
        import hashlib
        
        task_id = f"task_{hashlib.md5(request.content.encode()).hexdigest()[:8]}"
        
        task = TaskSpec(
            task_id=task_id,
            description=request.content,
            required_capabilities=["general"]
        )
        
        await self.mas_bridge.submit_task(task)
        
        # 编排任务
        result = await self.mas_bridge.orchestrate(task_id)
        
        return UnifiedResponse(
            request_id=request.request_id,
            status="success" if result.status == "success" else "failed",
            result={
                "task_id": task_id,
                "status": result.status,
                "output": result.output,
                "error": result.error
            }
        )
        
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "session_store": "active",
            "claude_adapter": "active" if self.claude_adapter else "inactive",
            "tool_synthesizer": "active",
            "topology_engine": "active",
            "mas_bridge": self.mas_bridge.get_status(),
            "consensus_manager": "active"
        }


# 单例实例
_unified_router: Optional[UnifiedRouter] = None


def get_unified_router() -> UnifiedRouter:
    """获取统一路由器单例"""
    global _unified_router
    if _unified_router is None:
        _unified_router = UnifiedRouter()
    return _unified_router
