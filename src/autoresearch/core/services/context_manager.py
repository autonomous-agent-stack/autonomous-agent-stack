"""Context Manager - 上下文管理器

功能：
1. 获取会话历史对话
2. 格式化为 Claude CLI 可理解的格式
3. 传递给 Agent 作为上下文
"""

from __future__ import annotations

from typing import List, Dict, Any
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.shared.models import OpenClawSessionRead


class ContextManager:
    """上下文管理器"""
    
    def __init__(self, openclaw_service: OpenClawCompatService):
        self._openclaw_service = openclaw_service
    
    def get_conversation_history(
        self,
        session_id: str,
        max_turns: int = 10,
    ) -> List[Dict[str, str]]:
        """获取对话历史
        
        Args:
            session_id: 会话 ID
            max_turns: 最大轮次（默认 10）
            
        Returns:
            对话历史列表 [{"role": "user/assistant", "content": "..."}]
        """
        session = self._openclaw_service.get_session(session_id)
        
        if not session or not session.events:
            return []
        
        # 提取对话事件
        conversation = []
        for event in session.events:
            if isinstance(event, dict):
                role = event.get("role")
                content = event.get("content")
            else:
                role = getattr(event, "role", None)
                content = getattr(event, "content", None)

            # 只保留 user 和 assistant 事件
            if role in ["user", "assistant"] and content:
                conversation.append({
                    "role": role,
                    "content": content,
                })
        
        # 限制轮次（保留最近的对话）
        if len(conversation) > max_turns * 2:  # 每轮包含 user + assistant
            conversation = conversation[-(max_turns * 2):]
        
        return conversation
    
    def format_history_for_claude(
        self,
        history: List[Dict[str, str]],
    ) -> str:
        """格式化历史对话为 Claude CLI 可理解的格式
        
        Args:
            history: 对话历史
            
        Returns:
            格式化后的字符串
        """
        if not history:
            return ""
        
        formatted_lines = []
        formatted_lines.append("## 历史对话\n")
        
        for turn in history:
            role = turn["role"]
            content = turn["content"]
            
            if role == "user":
                formatted_lines.append(f"**用户**: {content}")
            elif role == "assistant":
                formatted_lines.append(f"**助手**: {content}")
        
        formatted_lines.append("\n---\n")
        
        return "\n".join(formatted_lines)
    
    def build_context_aware_prompt(
        self,
        session_id: str,
        current_prompt: str,
        max_turns: int = 10,
    ) -> str:
        """构建带上下文的 Prompt
        
        Args:
            session_id: 会话 ID
            current_prompt: 当前用户输入
            max_turns: 最大历史轮次
            
        Returns:
            带上下文的完整 Prompt
        """
        # 1. 获取历史对话
        history = self.get_conversation_history(session_id, max_turns)
        
        if not history:
            # 没有历史，直接返回当前 Prompt
            return current_prompt
        
        # 2. 格式化历史
        history_text = self.format_history_for_claude(history)
        
        # 3. 构建完整 Prompt
        full_prompt = f"{history_text}\n**当前用户输入**: {current_prompt}"
        
        return full_prompt
    
    def append_user_message(
        self,
        session_id: str,
        content: str,
        metadata: Dict[str, Any] = None,
    ):
        """追加用户消息到会话
        
        Args:
            session_id: 会话 ID
            content: 消息内容
            metadata: 元数据
        """
        from autoresearch.shared.models import OpenClawSessionEventAppendRequest
        
        self._openclaw_service.append_event(
            session_id=session_id,
            request=OpenClawSessionEventAppendRequest(
                role="user",
                content=content,
                metadata=metadata or {},
            ),
        )
    
    def append_assistant_message(
        self,
        session_id: str,
        content: str,
        metadata: Dict[str, Any] = None,
    ):
        """追加助手消息到会话
        
        Args:
            session_id: 会话 ID
            content: 消息内容
            metadata: 元数据
        """
        from autoresearch.shared.models import OpenClawSessionEventAppendRequest
        
        self._openclaw_service.append_event(
            session_id=session_id,
            request=OpenClawSessionEventAppendRequest(
                role="assistant",
                content=content,
                metadata=metadata or {},
            ),
        )
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """获取会话摘要
        
        Args:
            session_id: 会话 ID
            
        Returns:
            会话摘要
        """
        session = self._openclaw_service.get_session(session_id)
        
        if not session:
            return {
                "session_id": session_id,
                "exists": False,
                "total_events": 0,
                "conversation_turns": 0,
            }
        
        # 统计对话轮次
        conversation_events = []
        for event in session.events:
            if isinstance(event, dict):
                role = event.get("role")
            else:
                role = getattr(event, "role", None)
            if role in ["user", "assistant"]:
                conversation_events.append(event)
        
        return {
            "session_id": session_id,
            "exists": True,
            "total_events": len(session.events),
            "conversation_turns": len(conversation_events) // 2,
            "status": session.status.value,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }


# ========================================================================
# 测试
# ========================================================================

if __name__ == "__main__":
    from autoresearch.shared.store import SQLiteModelRepository
    from autoresearch.shared.models import OpenClawSessionRead
    
    # 创建测试仓库
    repo = SQLiteModelRepository[OpenClawSessionRead](
        db_path=":memory:",
        table_name="test_sessions",
        model_class=OpenClawSessionRead,
    )
    
    # 创建 OpenClaw 兼容服务
    from autoresearch.core.services.openclaw_compat import OpenClawCompatService
    openclaw_service = OpenClawCompatService(repo)
    
    # 创建上下文管理器
    context_manager = ContextManager(openclaw_service)
    
    # 创建测试会话
    from autoresearch.shared.models import OpenClawSessionCreateRequest
    session = openclaw_service.create_session(
        OpenClawSessionCreateRequest(
            channel="test",
            external_id="test_user",
            title="测试会话",
        )
    )
    
    # 添加对话历史
    context_manager.append_user_message(session.session_id, "你好")
    context_manager.append_assistant_message(session.session_id, "你好！有什么可以帮你的吗？")
    context_manager.append_user_message(session.session_id, "帮我写个 Python 脚本")
    context_manager.append_assistant_message(session.session_id, "好的，请问是什么类型的脚本？")
    
    # 获取历史对话
    history = context_manager.get_conversation_history(session.session_id)
    print(f"历史对话: {history}")
    
    # 构建带上下文的 Prompt
    current_prompt = "数据分析脚本"
    full_prompt = context_manager.build_context_aware_prompt(
        session_id=session.session_id,
        current_prompt=current_prompt,
    )
    print(f"\n完整 Prompt:\n{full_prompt}")
