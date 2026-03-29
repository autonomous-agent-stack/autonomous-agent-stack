"""
OpenClaw + EverMemOS 集成代码
长期记忆系统完整实现

核心功能：
1. 长期记忆存储（基于 EverMemOS）
2. 记忆检索与召回
3. 记忆压缩与归档
4. 多智能体记忆共享
5. 记忆生命周期管理

作者: OpenClaw AI Assistant
日期: 2026-03-29
参考: https://github.com/EverMind-AI/EverMemOS
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import numpy as np
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """记忆类型"""
    EPISODIC = "episodic"      # 情节记忆（事件、经历）
    SEMANTIC = "semantic"       # 语义记忆（知识、概念）
    PROCEDURAL = "procedural"   # 程序记忆（技能、方法）
    WORKING = "working"         # 工作记忆（当前任务）


class MemoryPriority(Enum):
    """记忆优先级"""
    CRITICAL = "critical"   # 关键记忆（永久保留）
    HIGH = "high"           # 高优先级（长期保留）
    MEDIUM = "medium"       # 中优先级（中期保留）
    LOW = "low"             # 低优先级（短期保留）
    TEMPORARY = "temporary" # 临时记忆（自动清理）


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str                    # 记忆内容
    memory_type: MemoryType         # 记忆类型
    priority: MemoryPriority        # 优先级
    embedding: Optional[np.ndarray] = None  # 向量嵌入
    metadata: Dict = field(default_factory=dict)  # 元数据
    tags: List[str] = field(default_factory=list)  # 标签
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0           # 访问次数
    importance_score: float = 0.0   # 重要性评分（0-1）

    def to_dict(self) -> Dict:
        """转换为字典（用于序列化）"""
        data = asdict(self)
        data['memory_type'] = self.memory_type.value
        data['priority'] = self.priority.value
        data['embedding'] = self.embedding.tolist() if self.embedding is not None else None
        data['created_at'] = self.created_at.isoformat()
        data['accessed_at'] = self.accessed_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'MemoryEntry':
        """从字典创建（用于反序列化）"""
        data['memory_type'] = MemoryType(data['memory_type'])
        data['priority'] = MemoryPriority(data['priority'])
        data['embedding'] = np.array(data['embedding']) if data['embedding'] else None
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['accessed_at'] = datetime.fromisoformat(data['accessed_at'])
        return cls(**data)


class EverMemOSStorage:
    """EverMemOS 存储引擎（模拟）"""

    def __init__(self, storage_path: str = "~/.openclaw/memory/evermemos"):
        """
        初始化存储引擎

        Args:
            storage_path: 存储路径
        """
        self.storage_path = Path(storage_path).expanduser()
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        (self.storage_path / "episodic").mkdir(exist_ok=True)
        (self.storage_path / "semantic").mkdir(exist_ok=True)
        (self.storage_path / "procedural").mkdir(exist_ok=True)
        (self.storage_path / "working").mkdir(exist_ok=True)

        # 索引文件
        self.index_file = self.storage_path / "index.json"
        self.index = self._load_index()

        logger.info(f"EverMemOS Storage initialized at {self.storage_path}")

    def _load_index(self) -> Dict:
        """加载索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'memories': {},
            'stats': {
                'total_memories': 0,
                'by_type': {t.value: 0 for t in MemoryType},
                'by_priority': {p.value: 0 for p in MemoryPriority}
            }
        }

    def _save_index(self):
        """保存索引"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)

    def store(self, memory: MemoryEntry) -> bool:
        """
        存储记忆

        Args:
            memory: 记忆条目

        Returns:
            是否成功
        """
        try:
            # 生成文件名
            filename = f"{memory.id}.json"
            filepath = self.storage_path / memory.memory_type.value / filename

            # 保存到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(memory.to_dict(), f, ensure_ascii=False, indent=2)

            # 更新索引
            self.index['memories'][memory.id] = {
                'type': memory.memory_type.value,
                'priority': memory.priority.value,
                'created_at': memory.created_at.isoformat(),
                'access_count': memory.access_count
            }
            self.index['stats']['total_memories'] += 1
            self.index['stats']['by_type'][memory.memory_type.value] += 1
            self.index['stats']['by_priority'][memory.priority.value] += 1

            self._save_index()

            logger.info(f"Memory {memory.id} stored successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to store memory {memory.id}: {e}")
            return False

    def retrieve(self, memory_id: str) -> Optional[MemoryEntry]:
        """
        检索记忆

        Args:
            memory_id: 记忆ID

        Returns:
            记忆条目（如果存在）
        """
        if memory_id not in self.index['memories']:
            logger.warning(f"Memory {memory_id} not found in index")
            return None

        meta = self.index['memories'][memory_id]
        filepath = self.storage_path / meta['type'] / f"{memory_id}.json"

        if not filepath.exists():
            logger.warning(f"Memory file {filepath} not found")
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            memory = MemoryEntry.from_dict(data)
            memory.accessed_at = datetime.now()
            memory.access_count += 1

            # 更新索引
            self.index['memories'][memory_id]['access_count'] = memory.access_count
            self._save_index()

            return memory

        except Exception as e:
            logger.error(f"Failed to retrieve memory {memory_id}: {e}")
            return None

    def delete(self, memory_id: str) -> bool:
        """
        删除记忆

        Args:
            memory_id: 记忆ID

        Returns:
            是否成功
        """
        if memory_id not in self.index['memories']:
            return False

        meta = self.index['memories'][memory_id]
        filepath = self.storage_path / meta['type'] / f"{memory_id}.json"

        try:
            # 删除文件
            if filepath.exists():
                filepath.unlink()

            # 更新索引
            self.index['stats']['total_memories'] -= 1
            self.index['stats']['by_type'][meta['type']] -= 1
            self.index['stats']['by_priority'][meta['priority']] -= 1
            del self.index['memories'][memory_id]

            self._save_index()

            logger.info(f"Memory {memory_id} deleted successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False

    def search_by_type(self, memory_type: MemoryType, limit: int = 100) -> List[MemoryEntry]:
        """
        按类型搜索记忆

        Args:
            memory_type: 记忆类型
            limit: 最大返回数量

        Returns:
            记忆列表
        """
        memories = []
        type_dir = self.storage_path / memory_type.value

        if not type_dir.exists():
            return memories

        for filepath in list(type_dir.glob("*.json"))[:limit]:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                memories.append(MemoryEntry.from_dict(data))
            except Exception as e:
                logger.warning(f"Failed to load memory from {filepath}: {e}")

        return memories

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.index['stats'].copy()


class MemoryRetrievalSystem:
    """记忆检索系统"""

    def __init__(self, storage: EverMemOSStorage, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        初始化检索系统

        Args:
            storage: 存储引擎
            embedding_model: 嵌入模型
        """
        self.storage = storage
        # 注意：实际使用时需要安装 sentence-transformers
        # self.model = SentenceTransformer(embedding_model)
        self.embedding_dim = 384  # all-MiniLM-L6-v2 输出维度

        logger.info("Memory Retrieval System initialized")

    def encode_text(self, text: str) -> np.ndarray:
        """
        编码文本为向量

        Args:
            text: 输入文本

        Returns:
            384维向量
        """
        # 模拟嵌入（实际应使用 SentenceTransformer）
        # return self.model.encode(text, convert_to_numpy=True)

        # 简化实现：使用文本哈希生成伪向量
        hash_obj = hashlib.md5(text.encode('utf-8'))
        hash_bytes = hash_obj.digest()

        # 扩展到 384 维
        vector = np.zeros(self.embedding_dim)
        for i in range(min(len(hash_bytes) * 8, self.embedding_dim)):
            byte_idx = i // 8
            bit_idx = i % 8
            if hash_bytes[byte_idx] & (1 << bit_idx):
                vector[i] = 1.0

        return vector / np.linalg.norm(vector)  # 归一化

    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def search_similar(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
        threshold: float = 0.5
    ) -> List[Tuple[MemoryEntry, float]]:
        """
        搜索相似记忆

        Args:
            query: 查询文本
            memory_type: 记忆类型（可选）
            limit: 最大返回数量
            threshold: 相似度阈值

        Returns:
            (记忆条目, 相似度) 列表
        """
        query_embedding = self.encode_text(query)

        # 获取候选记忆
        if memory_type:
            candidates = self.storage.search_by_type(memory_type, limit=1000)
        else:
            # 搜索所有类型
            candidates = []
            for mt in MemoryType:
                candidates.extend(self.storage.search_by_type(mt, limit=250))

        # 计算相似度
        results = []
        for memory in candidates:
            if memory.embedding is None:
                memory.embedding = self.encode_text(memory.content)

            similarity = self.cosine_similarity(query_embedding, memory.embedding)

            if similarity >= threshold:
                results.append((memory, similarity))

        # 按相似度排序
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:limit]

    def hybrid_search(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10
    ) -> List[Tuple[MemoryEntry, float]]:
        """
        混合搜索（向量相似度 + 标签匹配）

        Args:
            query: 查询文本
            tags: 标签列表
            memory_type: 记忆类型
            limit: 最大返回数量

        Returns:
            (记忆条目, 综合得分) 列表
        """
        # 向量搜索
        vector_results = self.search_similar(query, memory_type, limit=100)

        # 标签过滤
        if tags:
            filtered_results = []
            for memory, similarity in vector_results:
                tag_match = any(tag in memory.tags for tag in tags)
                if tag_match:
                    # 提升得分
                    score = similarity * 1.2
                    filtered_results.append((memory, score))
            vector_results = filtered_results

        # 按得分排序
        vector_results.sort(key=lambda x: x[1], reverse=True)

        return vector_results[:limit]


class MemoryLifecycleManager:
    """记忆生命周期管理器"""

    def __init__(self, storage: EverMemOSStorage):
        """
        初始化生命周期管理器

        Args:
            storage: 存储引擎
        """
        self.storage = storage

        # 保留策略（天）
        self.retention_policy = {
            MemoryPriority.CRITICAL: 36500,    # 100 年
            MemoryPriority.HIGH: 365,          # 1 年
            MemoryPriority.MEDIUM: 90,         # 3 个月
            MemoryPriority.LOW: 30,            # 1 个月
            MemoryPriority.TEMPORARY: 7        # 1 周
        }

        logger.info("Memory Lifecycle Manager initialized")

    def cleanup_expired(self) -> int:
        """
        清理过期记忆

        Returns:
            清理的记忆数量
        """
        cleaned = 0
        now = datetime.now()

        for memory_id, meta in list(self.storage.index['memories'].items()):
            created_at = datetime.fromisoformat(meta['created_at'])
            priority = MemoryPriority(meta['priority'])
            retention_days = self.retention_policy[priority]

            age = (now - created_at).days

            if age > retention_days:
                if self.storage.delete(memory_id):
                    cleaned += 1

        logger.info(f"Cleaned up {cleaned} expired memories")
        return cleaned

    def compress_memories(self, threshold_days: int = 30) -> int:
        """
        压缩旧记忆（归档低频访问）

        Args:
            threshold_days: 阈值天数

        Returns:
            压缩的记忆数量
        """
        compressed = 0
        now = datetime.now()

        for memory_id, meta in list(self.storage.index['memories'].items()):
            memory = self.storage.retrieve(memory_id)
            if not memory:
                continue

            # 检查访问频率
            age = (now - memory.created_at).days
            if age < threshold_days:
                continue

            # 如果访问次数很低，降低优先级
            if memory.access_count < 2 and memory.priority != MemoryPriority.TEMPORARY:
                old_priority = memory.priority
                memory.priority = MemoryPriority(max(
                    MemoryPriority.TEMPORARY.value,
                    memory.priority.value - 1
                ))

                # 更新存储
                self.storage.store(memory)
                compressed += 1

                logger.info(f"Compressed memory {memory_id}: {old_priority.value} -> {memory.priority.value}")

        logger.info(f"Compressed {compressed} memories")
        return compressed

    def get_memory_stats(self) -> Dict:
        """获取记忆统计"""
        stats = self.storage.get_stats()

        # 添加生命周期信息
        now = datetime.now()
        age_distribution = {
            '<7d': 0,
            '7-30d': 0,
            '30-90d': 0,
            '90-365d': 0,
            '>365d': 0
        }

        for memory_id, meta in self.storage.index['memories'].items():
            created_at = datetime.fromisoformat(meta['created_at'])
            age = (now - created_at).days

            if age < 7:
                age_distribution['<7d'] += 1
            elif age < 30:
                age_distribution['7-30d'] += 1
            elif age < 90:
                age_distribution['30-90d'] += 1
            elif age < 365:
                age_distribution['90-365d'] += 1
            else:
                age_distribution['>365d'] += 1

        stats['age_distribution'] = age_distribution
        return stats


class OpenClawLongTermMemory:
    """OpenClaw 长期记忆系统（完整集成）"""

    def __init__(self, storage_path: str = "~/.openclaw/memory/evermemos"):
        """
        初始化长期记忆系统

        Args:
            storage_path: 存储路径
        """
        self.storage = EverMemOSStorage(storage_path)
        self.retrieval = MemoryRetrievalSystem(self.storage)
        self.lifecycle = MemoryLifecycleManager(self.storage)

        logger.info("OpenClaw Long-Term Memory System initialized")

    def remember(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.EPISODIC,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        记住内容

        Args:
            content: 记忆内容
            memory_type: 记忆类型
            priority: 优先级
            tags: 标签
            metadata: 元数据

        Returns:
            记忆ID
        """
        # 生成记忆ID
        memory_id = hashlib.md5(
            f"{content}{datetime.now().isoformat()}".encode('utf-8')
        ).hexdigest()[:16]

        # 生成嵌入
        embedding = self.retrieval.encode_text(content)

        # 创建记忆条目
        memory = MemoryEntry(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            priority=priority,
            embedding=embedding,
            tags=tags or [],
            metadata=metadata or {},
            importance_score=self._calculate_importance(content, priority)
        )

        # 存储
        self.storage.store(memory)

        logger.info(f"Remembered: {memory_id} ({memory_type.value}, {priority.value})")
        return memory_id

    def recall(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        回忆相关内容

        Args:
            query: 查询文本
            memory_type: 记忆类型（可选）
            tags: 标签（可选）
            limit: 最大返回数量

        Returns:
            记忆列表
        """
        results = self.retrieval.hybrid_search(query, tags, memory_type, limit)

        memories = []
        for memory, score in results:
            memories.append({
                'id': memory.id,
                'content': memory.content,
                'type': memory.memory_type.value,
                'priority': memory.priority.value,
                'score': score,
                'accessed_at': memory.accessed_at.isoformat(),
                'access_count': memory.access_count,
                'tags': memory.tags
            })

        logger.info(f"Recalled {len(memories)} memories for query: {query[:50]}...")
        return memories

    def forget(self, memory_id: str) -> bool:
        """
        遗忘记忆

        Args:
            memory_id: 记忆ID

        Returns:
            是否成功
        """
        return self.storage.delete(memory_id)

    def maintain(self) -> Dict:
        """
        维护记忆系统

        Returns:
            维护结果
        """
        # 清理过期记忆
        cleaned = self.lifecycle.cleanup_expired()

        # 压缩低频记忆
        compressed = self.lifecycle.compress_memories()

        # 获取统计
        stats = self.lifecycle.get_memory_stats()

        result = {
            'cleaned_memories': cleaned,
            'compressed_memories': compressed,
            'stats': stats
        }

        logger.info(f"Memory maintenance completed: {result}")
        return result

    def _calculate_importance(self, content: str, priority: MemoryPriority) -> float:
        """计算重要性评分"""
        # 基于优先级的基础分
        base_score = {
            MemoryPriority.CRITICAL: 0.9,
            MemoryPriority.HIGH: 0.7,
            MemoryPriority.MEDIUM: 0.5,
            MemoryPriority.LOW: 0.3,
            MemoryPriority.TEMPORARY: 0.1
        }[priority]

        # 基于内容长度的调整（假设内容越长越重要）
        length_factor = min(len(content) / 1000, 0.1)

        return min(base_score + length_factor, 1.0)

    def export_memories(self, output_path: str) -> bool:
        """
        导出记忆到文件

        Args:
            output_path: 输出文件路径

        Returns:
            是否成功
        """
        try:
            all_memories = []
            for mt in MemoryType:
                memories = self.storage.search_by_type(mt, limit=10000)
                all_memories.extend([m.to_dict() for m in memories])

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(all_memories, f, ensure_ascii=False, indent=2)

            logger.info(f"Exported {len(all_memories)} memories to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export memories: {e}")
            return False


# ========== 使用示例 ==========

def example_usage():
    """OpenClaw + EverMemOS 集成示例"""

    # 1. 初始化长期记忆系统
    ltm = OpenClawLongTermMemory()

    print("\n" + "="*60)
    print("OpenClaw + EverMemOS Integration Demo")
    print("="*60)

    # 2. 记住一些内容
    print("\n📝 Storing memories...")

    memory_id_1 = ltm.remember(
        content="2026-03-29: 完成 DyTopo 深度分析，80亿参数小模型击败1200亿大模型",
        memory_type=MemoryType.EPISODIC,
        priority=MemoryPriority.HIGH,
        tags=["AI", "DyTopo", "multi-agent"],
        metadata={"source": "youtube", "video_id": "pTNE1qZKf1M"}
    )

    memory_id_2 = ltm.remember(
        content="MSA (Memory Sparse Attention) 技术：4B参数处理1亿Token上下文",
        memory_type=MemoryType.SEMANTIC,
        priority=MemoryPriority.HIGH,
        tags=["AI", "MSA", "long-context"],
        metadata={"source": "github", "repo": "EverMind-AI/MSA"}
    )

    memory_id_3 = ltm.remember(
        content="火力全开模式工作流程：每6小时检查MSA进展，知识库健康度99.5%",
        memory_type=MemoryType.PROCEDURAL,
        priority=MemoryPriority.MEDIUM,
        tags=["workflow", "monitoring"],
        metadata={"routine": "heartbeat"}
    )

    print(f"  ✓ Memory 1: {memory_id_1}")
    print(f"  ✓ Memory 2: {memory_id_2}")
    print(f"  ✓ Memory 3: {memory_id_3}")

    # 3. 回忆相关内容
    print("\n🔍 Recalling memories about 'AI'...")

    results = ltm.recall(
        query="AI 技术突破",
        tags=["AI"],
        limit=5
    )

    for i, result in enumerate(results, 1):
        print(f"\n  [{i}] {result['content'][:60]}...")
        print(f"      Type: {result['type']}, Score: {result['score']:.3f}")
        print(f"      Tags: {', '.join(result['tags'])}")

    # 4. 维护记忆系统
    print("\n🔧 Maintaining memory system...")

    maintenance_result = ltm.maintain()

    print(f"  ✓ Cleaned: {maintenance_result['cleaned_memories']} memories")
    print(f"  ✓ Compressed: {maintenance_result['compressed_memories']} memories")
    print(f"  ✓ Total: {maintenance_result['stats']['total_memories']} memories")

    # 5. 导出记忆
    print("\n💾 Exporting memories...")

    export_path = "/tmp/openclaw_memories_export.json"
    if ltm.export_memories(export_path):
        print(f"  ✓ Exported to {export_path}")

    print("\n" + "="*60)
    print("Demo completed!")
    print("="*60 + "\n")

    return ltm


if __name__ == "__main__":
    # 运行示例
    ltm = example_usage()

    # 输出最终统计
    print("\n📊 Final Statistics:")
    stats = ltm.lifecycle.get_memory_stats()
    print(f"  Total memories: {stats['total_memories']}")
    print(f"  By type: {stats['by_type']}")
    print(f"  By priority: {stats['by_priority']}")
    print(f"  Age distribution: {stats['age_distribution']}")
