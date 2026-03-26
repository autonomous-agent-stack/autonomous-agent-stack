"""Consensus Manager - 冲突解决与共识管理

处理多 Agent 结果合并
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class ConflictType(Enum):
    """冲突类型"""
    RESULT_MISMATCH = "result_mismatch"
    TIMEOUT_CONFLICT = "timeout_conflict"
    PRIORITY_CONFLICT = "priority_conflict"
    DATA_INCONSISTENCY = "data_inconsistency"


@dataclass
class Conflict:
    """冲突"""
    conflict_id: str
    conflict_type: ConflictType
    agents: List[str]
    results: Dict[str, Any]
    resolution: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Resolution:
    """解决方案"""
    resolution_id: str
    conflict_id: str
    strategy: str
    winner: Optional[str] = None
    merged_result: Optional[Any] = None
    confidence: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ConsensusManager:
    """共识管理器"""
    
    def __init__(self):
        self.conflicts: Dict[str, Conflict] = {}
        self.resolutions: Dict[str, Resolution] = {}
        
    async def detect_conflicts(
        self,
        agent_outputs: Dict[str, Any]
    ) -> List[Conflict]:
        """检测冲突
        
        Args:
            agent_outputs: Agent 输出 {agent_id: output}
            
        Returns:
            冲突列表
        """
        logger.info(f"[Consensus Manager] 检测冲突: {len(agent_outputs)} 个 Agent")
        
        conflicts = []
        
        # 检查结果一致性
        unique_results = set()
        for agent_id, output in agent_outputs.items():
            # 简化：将结果转为字符串进行比较
            result_str = str(output)
            unique_results.add(result_str)
            
        # 如果结果不一致，创建冲突
        if len(unique_results) > 1:
            import hashlib
            
            conflict_id = f"conflict_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}"
            
            conflict = Conflict(
                conflict_id=conflict_id,
                conflict_type=ConflictType.RESULT_MISMATCH,
                agents=list(agent_outputs.keys()),
                results=agent_outputs
            )
            
            conflicts.append(conflict)
            self.conflicts[conflict_id] = conflict
            
            logger.warning(f"[Consensus Manager] 检测到冲突: {conflict_id}")
            
        return conflicts
        
    async def resolve_conflicts(
        self,
        conflicts: List[Conflict],
        strategy: str = "majority_vote"
    ) -> List[Resolution]:
        """解决冲突
        
        Args:
            conflicts: 冲突列表
            strategy: 解决策略（majority_vote, priority, merge, random）
            
        Returns:
            解决方案列表
        """
        logger.info(f"[Consensus Manager] 解决冲突: {len(conflicts)} 个, 策略: {strategy}")
        
        resolutions = []
        
        for conflict in conflicts:
            if strategy == "majority_vote":
                resolution = await self._resolve_by_majority_vote(conflict)
            elif strategy == "priority":
                resolution = await self._resolve_by_priority(conflict)
            elif strategy == "merge":
                resolution = await self._resolve_by_merge(conflict)
            else:  # random
                resolution = await self._resolve_randomly(conflict)
                
            resolutions.append(resolution)
            self.resolutions[resolution.resolution_id] = resolution
            
            logger.info(f"[Consensus Manager] 冲突已解决: {resolution.resolution_id}")
            
        return resolutions
        
    async def _resolve_by_majority_vote(self, conflict: Conflict) -> Resolution:
        """多数投票解决"""
        import hashlib
        
        # 统计每个结果的出现次数
        result_counts: Dict[str, List[str]] = {}
        
        for agent_id, result in conflict.results.items():
            result_str = str(result)
            
            if result_str not in result_counts:
                result_counts[result_str] = []
                
            result_counts[result_str].append(agent_id)
            
        # 找出出现次数最多的结果
        max_count = 0
        winner_result = None
        winner_agents = []
        
        for result_str, agents in result_counts.items():
            if len(agents) > max_count:
                max_count = len(agents)
                winner_result = result_str
                winner_agents = agents
                
        # 创建解决方案
        resolution_id = f"resolution_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}"
        
        resolution = Resolution(
            resolution_id=resolution_id,
            conflict_id=conflict.conflict_id,
            strategy="majority_vote",
            winner=winner_agents[0] if winner_agents else None,
            merged_result=winner_result,
            confidence=max_count / len(conflict.results)
        )
        
        return resolution
        
    async def _resolve_by_priority(self, conflict: Conflict) -> Resolution:
        """优先级解决"""
        import hashlib
        
        # 简化：选择第一个 Agent 的结果
        winner = conflict.agents[0] if conflict.agents else None
        winner_result = conflict.results.get(winner) if winner else None
        
        resolution_id = f"resolution_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}"
        
        resolution = Resolution(
            resolution_id=resolution_id,
            conflict_id=conflict.conflict_id,
            strategy="priority",
            winner=winner,
            merged_result=winner_result,
            confidence=1.0
        )
        
        return resolution
        
    async def _resolve_by_merge(self, conflict: Conflict) -> Resolution:
        """合并解决"""
        import hashlib
        
        # 尝试合并结果
        # 简化：将所有结果合并为列表
        merged_result = list(conflict.results.values())
        
        resolution_id = f"resolution_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}"
        
        resolution = Resolution(
            resolution_id=resolution_id,
            conflict_id=conflict.conflict_id,
            strategy="merge",
            merged_result=merged_result,
            confidence=0.5
        )
        
        return resolution
        
    async def _resolve_randomly(self, conflict: Conflict) -> Resolution:
        """随机解决"""
        import hashlib
        import random
        
        winner = random.choice(conflict.agents) if conflict.agents else None
        winner_result = conflict.results.get(winner) if winner else None
        
        resolution_id = f"resolution_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}"
        
        resolution = Resolution(
            resolution_id=resolution_id,
            conflict_id=conflict.conflict_id,
            strategy="random",
            winner=winner,
            merged_result=winner_result,
            confidence=0.3
        )
        
        return resolution
        
    async def merge_results(
        self,
        agent_outputs: Dict[str, Any],
        strategy: str = "majority_vote"
    ) -> Tuple[Any, Optional[Resolution]]:
        """合并多个 Agent 的结果
        
        Args:
            agent_outputs: Agent 输出
            strategy: 合并策略
            
        Returns:
            (合并结果, 解决方案)
        """
        # 检测冲突
        conflicts = await self.detect_conflicts(agent_outputs)
        
        if not conflicts:
            # 无冲突，直接返回第一个结果
            first_result = list(agent_outputs.values())[0] if agent_outputs else None
            return first_result, None
            
        # 解决冲突
        resolutions = await self.resolve_conflicts(conflicts, strategy)
        
        if resolutions:
            return resolutions[0].merged_result, resolutions[0]
            
        return None, None


# 单例实例
_consensus_manager: Optional[ConsensusManager] = None


def get_consensus_manager() -> ConsensusManager:
    """获取共识管理器单例"""
    global _consensus_manager
    if _consensus_manager is None:
        _consensus_manager = ConsensusManager()
    return _consensus_manager
