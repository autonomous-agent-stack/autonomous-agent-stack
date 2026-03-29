"""
DyTopo: Dynamic Topology for Multi-Agent Reasoning
基于语义匹配的多智能体推理动态拓扑路由

核心特性：
1. 动态拓扑路由 - 根据实时需求动态重组网络
2. 语义匹配引擎 - 384维向量空间余弦相似度匹配
3. 自适应拓扑排序 - 解决死锁问题
4. AI Manager - 全局状态聚合与停机决策

作者: OpenClaw AI Assistant
日期: 2026-03-29
参考论文: DyTopo: Dynamic Topology for Multi-Agent Reasoning via Semantic Matching
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import networkx as nx
from sentence_transformers import SentenceTransformer
import logging
from collections import defaultdict

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """智能体角色类型"""
    RESEARCHER = "researcher"      # 研究员 - 提供算法思路
    DEVELOPER = "developer"        # 开发者 - 实现代码
    TESTER = "tester"             # 测试员 - 验证代码
    MANAGER = "manager"           # 经理 - 全局决策


@dataclass
class AgentDescriptor:
    """智能体描述符（轻量级通信协议）"""
    query: str          # 需求描述（买方信号）
    key: str            # 供应描述（卖方信号）
    confidence: float   # 置信度
    role: AgentRole     # 角色类型
    
    def __post_init__(self):
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")


@dataclass
class AgentState:
    """智能体状态"""
    id: str
    role: AgentRole
    descriptor: Optional[AgentDescriptor] = None
    context: str = ""                # 实质内容（代码、公式等）
    connections: Set[str] = field(default_factory=set)  # 当前连接的智能体ID
    message_history: List[str] = field(default_factory=list)


class SemanticMatchingEngine:
    """语义匹配引擎"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        初始化语义匹配引擎
        
        Args:
            model_name: 句子嵌入模型名称
        """
        self.model = SentenceTransformer(model_name)
        self.vector_dim = 384  # all-MiniLM-L6-v2 输出维度
        logger.info(f"Semantic Matching Engine initialized with {model_name}")
    
    def encode(self, text: str) -> np.ndarray:
        """
        将文本编码为384维向量
        
        Args:
            text: 输入文本
            
        Returns:
            384维向量
        """
        return self.model.encode(text, convert_to_numpy=True)
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        计算余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
            
        Returns:
            余弦相似度（0-1之间）
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def match(self, descriptor1: AgentDescriptor, descriptor2: AgentDescriptor) -> float:
        """
        匹配两个智能体描述符
        
        Args:
            descriptor1: 智能体1的描述符
            descriptor2: 智能体2的描述符
            
        Returns:
            匹配分数（0-1之间）
        """
        # 编码 Query 和 Key
        query_vec1 = self.encode(descriptor1.query)
        key_vec1 = self.encode(descriptor1.key)
        query_vec2 = self.encode(descriptor2.query)
        key_vec2 = self.encode(descriptor2.key)
        
        # 计算双向匹配分数
        # Agent1的Query vs Agent2的Key（Agent1需要，Agent2能提供）
        score_1_to_2 = self.cosine_similarity(query_vec1, key_vec2)
        
        # Agent2的Query vs Agent1的Key（Agent2需要，Agent1能提供）
        score_2_to_1 = self.cosine_similarity(query_vec2, key_vec1)
        
        # 返回最大匹配分数（单向连接即可）
        return max(score_1_to_2, score_2_to_1)


class DynamicTopologyRouter:
    """动态拓扑路由器"""
    
    def __init__(self, threshold: float = 0.3):
        """
        初始化动态拓扑路由器
        
        Args:
            threshold: 匹配阈值（0.3适合代码生成，0.4+适合数学推理）
        """
        self.threshold = threshold
        self.semantic_engine = SemanticMatchingEngine()
        self.graph = nx.DiGraph()  # 有向图
        self.agents: Dict[str, AgentState] = {}
        
        logger.info(f"Dynamic Topology Router initialized with threshold={threshold}")
    
    def register_agent(self, agent_state: AgentState):
        """
        注册智能体到网络
        
        Args:
            agent_state: 智能体状态
        """
        self.agents[agent_state.id] = agent_state
        self.graph.add_node(agent_state.id, role=agent_state.role)
        logger.info(f"Agent {agent_state.id} ({agent_state.role.value}) registered")
    
    def build_dynamic_topology(self, current_round: int) -> nx.DiGraph:
        """
        构建动态拓扑网络
        
        Args:
            current_round: 当前轮次
            
        Returns:
            动态拓扑图
        """
        # 清空当前图的边
        self.graph.clear_edges()
        
        # 遍历所有智能体对，计算匹配分数
        agent_ids = list(self.agents.keys())
        edges = []
        
        for i, id1 in enumerate(agent_ids):
            for id2 in agent_ids[i+1:]:
                agent1 = self.agents[id1]
                agent2 = self.agents[id2]
                
                # 检查描述符是否存在
                if agent1.descriptor is None or agent2.descriptor is None:
                    continue
                
                # 计算匹配分数
                match_score = self.semantic_engine.match(agent1.descriptor, agent2.descriptor)
                
                # 如果匹配分数超过阈值，建立连接
                if match_score >= self.threshold:
                    # 根据语义方向确定有向边
                    # 这里简化为双向边（实际应根据 Query/Key 方向）
                    edges.append((id1, id2, {'weight': match_score}))
                    edges.append((id2, id1, {'weight': match_score}))
                    
                    # 更新智能体连接状态
                    agent1.connections.add(id2)
                    agent2.connections.add(id1)
                    
                    logger.debug(f"Edge created: {id1} <-> {id2} (score={match_score:.3f})")
        
        # 添加边到图中
        self.graph.add_edges_from(edges)
        
        logger.info(f"Round {current_round}: {len(edges)//2} bidirectional edges created")
        return self.graph
    
    def detect_and_break_cycles(self) -> List[Tuple[str, str]]:
        """
        检测并打破循环依赖
        
        Returns:
            被切断的边列表
        """
        broken_edges = []
        
        # 检测强连通分量（循环）
        scc = list(nx.strongly_connected_components(self.graph))
        
        for component in scc:
            if len(component) > 1:  # 大于1表示存在循环
                logger.warning(f"Cycle detected in component: {component}")
                
                # 计算每个节点的入度
                in_degrees = {}
                for node in component:
                    in_degrees[node] = self.graph.in_degree(node)
                
                # 找到入度最大的节点（最依赖别人的节点）
                max_in_degree_node = max(in_degrees, key=in_degrees.get)
                
                # 切断该节点的入边中最弱的一条
                in_edges = list(self.graph.in_edges(max_in_degree_node, data=True))
                if in_edges:
                    # 按权重排序，切断最弱的边
                    in_edges.sort(key=lambda x: x[2].get('weight', 0))
                    weakest_edge = in_edges[0]
                    
                    self.graph.remove_edge(weakest_edge[0], weakest_edge[1])
                    broken_edges.append((weakest_edge[0], weakest_edge[1]))
                    
                    # 更新智能体连接状态
                    if weakest_edge[1] in self.agents:
                        self.agents[weakest_edge[1]].connections.discard(weakest_edge[0])
                    
                    logger.info(f"Cycle broken by removing edge: {weakest_edge[0]} -> {weakest_edge[1]}")
        
        return broken_edges
    
    def topological_sort(self) -> List[str]:
        """
        拓扑排序（将图转换为线性序列）
        
        Returns:
            拓扑排序后的智能体ID列表
        """
        try:
            return list(nx.topological_sort(self.graph))
        except nx.NetworkXError:
            # 如果存在循环，先打破循环再排序
            self.detect_and_break_cycles()
            return list(nx.topological_sort(self.graph))


class AIManager:
    """AI Manager - 全局状态聚合与停机决策"""
    
    def __init__(self, max_rounds: int = 10, convergence_threshold: float = 0.95):
        """
        初始化 AI Manager
        
        Args:
            max_rounds: 最大轮次
            convergence_threshold: 收敛阈值（任务完成度）
        """
        self.max_rounds = max_rounds
        self.convergence_threshold = convergence_threshold
        self.current_round = 0
        self.task_complete = False
        
        logger.info(f"AI Manager initialized (max_rounds={max_rounds}, threshold={convergence_threshold})")
    
    def aggregate_global_state(self, agents: Dict[str, AgentState]) -> Dict:
        """
        聚合全局状态
        
        Args:
            agents: 所有智能体状态
            
        Returns:
            全局状态字典
        """
        global_state = {
            'round': self.current_round,
            'total_agents': len(agents),
            'active_connections': sum(len(a.connections) for a in agents.values()) // 2,
            'roles_distribution': defaultdict(int),
            'average_confidence': 0.0,
            'task_progress': 0.0
        }
        
        # 统计角色分布
        for agent in agents.values():
            global_state['roles_distribution'][agent.role.value] += 1
        
        # 计算平均置信度
        confidences = [a.descriptor.confidence for a in agents.values() if a.descriptor]
        if confidences:
            global_state['average_confidence'] = np.mean(confidences)
        
        # 计算任务进度（简化：基于置信度和连接数）
        # 实际应根据具体任务类型计算
        global_state['task_progress'] = min(
            global_state['average_confidence'] * 1.2,
            1.0
        )
        
        return global_state
    
    def should_halt(self, global_state: Dict) -> bool:
        """
        判断是否应该停机
        
        Args:
            global_state: 全局状态
            
        Returns:
            是否停机
        """
        # 条件1：达到最大轮次
        if self.current_round >= self.max_rounds:
            logger.info(f"Halting: max rounds ({self.max_rounds}) reached")
            return True
        
        # 条件2：任务完成度达到阈值
        if global_state['task_progress'] >= self.convergence_threshold:
            logger.info(f"Halting: task progress ({global_state['task_progress']:.2%}) reached threshold")
            return True
        
        # 条件3：网络连接数过低（孤立）
        if global_state['active_connections'] == 0:
            logger.warning("Halting: network is isolated (no active connections)")
            return True
        
        return False
    
    def next_round(self):
        """进入下一轮"""
        self.current_round += 1
        logger.info(f"Entering round {self.current_round}")


class DyTopoFramework:
    """DyTopo 完整框架"""
    
    def __init__(
        self,
        threshold: float = 0.3,
        max_rounds: int = 10,
        convergence_threshold: float = 0.95
    ):
        """
        初始化 DyTopo 框架
        
        Args:
            threshold: 匹配阈值
            max_rounds: 最大轮次
            convergence_threshold: 收敛阈值
        """
        self.router = DynamicTopologyRouter(threshold=threshold)
        self.manager = AIManager(max_rounds=max_rounds, convergence_threshold=convergence_threshold)
        
        logger.info("DyTopo Framework initialized")
    
    def add_agent(self, agent_state: AgentState):
        """添加智能体"""
        self.router.register_agent(agent_state)
    
    def run_round(self) -> Dict:
        """
        运行一轮协作
        
        Returns:
            本轮结果
        """
        # 1. 构建动态拓扑
        graph = self.router.build_dynamic_topology(self.manager.current_round)
        
        # 2. 检测并打破循环
        broken_edges = self.router.detect_and_break_cycles()
        
        # 3. 拓扑排序
        execution_order = self.router.topological_sort()
        
        # 4. 按顺序执行（这里简化，实际应调用各智能体的推理接口）
        for agent_id in execution_order:
            agent = self.router.agents[agent_id]
            # 模拟智能体推理
            # 实际应调用: agent.inference()
            logger.debug(f"Agent {agent_id} executed")
        
        # 5. 聚合全局状态
        global_state = self.manager.aggregate_global_state(self.router.agents)
        
        # 6. 判断是否停机
        should_halt = self.manager.should_halt(global_state)
        
        # 7. 进入下一轮
        if not should_halt:
            self.manager.next_round()
        
        return {
            'round': self.manager.current_round,
            'graph': graph,
            'broken_edges': broken_edges,
            'execution_order': execution_order,
            'global_state': global_state,
            'should_halt': should_halt
        }
    
    def run(self) -> List[Dict]:
        """
        运行完整协作流程
        
        Returns:
            所有轮次的结果列表
        """
        results = []
        
        while True:
            result = self.run_round()
            results.append(result)
            
            if result['should_halt']:
                logger.info("DyTopo framework execution completed")
                break
        
        return results


# ========== 使用示例 ==========

def example_usage():
    """DyTopo 框架使用示例"""
    
    # 1. 创建框架实例
    # 代码生成任务使用 0.3 阈值
    framework = DyTopoFramework(threshold=0.3, max_rounds=10)
    
    # 2. 创建智能体
    researcher = AgentState(
        id="researcher_1",
        role=AgentRole.RESEARCHER,
        descriptor=AgentDescriptor(
            query="需要解决整数溢出问题的算法思路",
            key="我提供基于模运算的防溢出算法",
            confidence=0.85,
            role=AgentRole.RESEARCHER
        )
    )
    
    developer = AgentState(
        id="developer_1",
        role=AgentRole.DEVELOPER,
        descriptor=AgentDescriptor(
            query="需要整数溢出的边界测试用例",
            key="我实现了防溢出的加法函数代码",
            confidence=0.75,
            role=AgentRole.DEVELOPER
        )
    )
    
    tester = AgentState(
        id="tester_1",
        role=AgentRole.TESTER,
        descriptor=AgentDescriptor(
            query="需要验证的代码实现",
            key="我提供涵盖边界异常的测试数据",
            confidence=0.90,
            role=AgentRole.TESTER
        )
    )
    
    # 3. 注册智能体
    framework.add_agent(researcher)
    framework.add_agent(developer)
    framework.add_agent(tester)
    
    # 4. 运行协作
    results = framework.run()
    
    # 5. 输出结果
    print(f"\n{'='*60}")
    print("DyTopo Framework Execution Results")
    print(f"{'='*60}")
    
    for i, result in enumerate(results):
        print(f"\nRound {i+1}:")
        print(f"  - Active connections: {result['global_state']['active_connections']}")
        print(f"  - Task progress: {result['global_state']['task_progress']:.2%}")
        print(f"  - Broken edges: {len(result['broken_edges'])}")
        print(f"  - Should halt: {result['should_halt']}")
    
    print(f"\n{'='*60}")
    print(f"Total rounds: {len(results)}")
    print(f"Final task progress: {results[-1]['global_state']['task_progress']:.2%}")
    print(f"{'='*60}\n")
    
    return results


if __name__ == "__main__":
    # 运行示例
    results = example_usage()
    
    # 输出统计
    print("\n📊 DyTopo Framework Statistics:")
    print(f"  Total rounds: {len(results)}")
    print(f"  Average connections: {np.mean([r['global_state']['active_connections'] for r in results]):.2f}")
    print(f"  Total broken edges: {sum(len(r['broken_edges']) for r in results)}")
    print(f"  Final progress: {results[-1]['global_state']['task_progress']:.2%}")
