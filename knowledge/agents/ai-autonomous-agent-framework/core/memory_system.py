# knowledge/agents/ai-autonomous-agent-framework/core/memory_system.py

"""
记忆系统

管理短期记忆、长期记忆和工作记忆
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
import hashlib
from collections import defaultdict


@dataclass
class MemoryItem:
    """记忆项"""
    key: str
    value: Any
    metadata: Dict[str, Any]
    timestamp: float
    access_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "key": self.key,
            "value": self.value,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "access_count": self.access_count
        }


class MemorySystem:
    """
    记忆系统

    管理短期记忆、长期记忆和工作记忆
    """

    def __init__(self, max_short_term_size=100, max_long_term_size=1000):
        """
        初始化记忆系统

        Args:
            max_short_term_size: 短期记忆最大容量
            max_long_term_size: 长期记忆最大容量
        """
        # 短期记忆：最近的交互
        self.short_term = {}
        self.max_short_term_size = max_short_term_size

        # 长期记忆：重要的信息
        self.long_term = {}
        self.max_long_term_size = max_long_term_size

        # 工作记忆：当前任务相关
        self.working_memory = {}

        # 索引
        self.key_index = defaultdict(list)

    def store(
        self,
        key: str,
        value: Any,
        memory_type: str = "short_term",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        存储记忆

        Args:
            key: 键
            value: 值
            memory_type: 记忆类型 (short_term, long_term, working)
            metadata: 元数据
        """
        import time

        metadata = metadata or {}

        memory_item = MemoryItem(
            key=key,
            value=value,
            metadata=metadata,
            timestamp=time.time()
        )

        if memory_type == "short_term":
            self._store_short_term(key, memory_item)
        elif memory_type == "long_term":
            self._store_long_term(key, memory_item)
        elif memory_type == "working":
            self._store_working_memory(key, memory_item)

        # 更新索引
        self._update_index(key, value, metadata)

    def retrieve(self, key: str) -> Optional[MemoryItem]:
        """
        检索记忆

        Args:
            key: 键

        Returns:
            记忆项或 None
        """
        # 优先从工作记忆检索
        if key in self.working_memory:
            item = self.working_memory[key]
            item.access_count += 1
            return item

        # 然后从短期记忆检索
        if key in self.short_term:
            item = self.short_term[key]
            item.access_count += 1
            return item

        # 最后从长期记忆检索
        if key in self.long_term:
            item = self.long_term[key]
            item.access_count += 1
            return item

        return None

    def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """
        搜索记忆

        Args:
            query: 查询字符串
            limit: 返回结果数量限制

        Returns:
            相关记忆项列表
        """
        results = []

        # 从短期记忆搜索
        for key, item in self.short_term.items():
            if query.lower() in key.lower() or query.lower() in str(item.value).lower():
                results.append(item)

        # 从长期记忆搜索
        for key, item in self.long_term.items():
            if query.lower() in key.lower() or query.lower() in str(item.value).lower():
                results.append(item)

        # 从工作记忆搜索
        for key, item in self.working_memory.items():
            if query.lower() in key.lower() or query.lower() in str(item.value).lower():
                results.append(item)

        # 按访问次数和时间排序
        results.sort(key=lambda x: (x.access_count, x.timestamp), reverse=True)

        return results[:limit]

    def get_context(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取上下文

        Args:
            task_id: 任务 ID（可选）

        Returns:
            上下文字典
        """
        context = {
            "short_term_items": len(self.short_term),
            "long_term_items": len(self.long_term),
            "working_memory_items": len(self.working_memory)
        }

        if task_id:
            # 获取任务相关的记忆
            task_memories = self.search(task_id, limit=5)
            context["task_memories"] = [
                item.to_dict() for item in task_memories
            ]

        return context

    def get_final_result(self, goal: str) -> Any:
        """
        获取最终结果

        Args:
            goal: 目标

        Returns:
            最终结果
        """
        # 搜索与目标相关的记忆
        relevant_memories = self.search(goal, limit=1)

        if relevant_memories:
            return relevant_memories[0].value

        # 如果没有找到，返回最近的结果
        if self.working_memory:
            return list(self.working_memory.values())[0].value

        return None

    def clear_working_memory(self):
        """清空工作记忆"""
        self.working_memory.clear()

    def _store_short_term(self, key: str, item: MemoryItem):
        """存储到短期记忆"""
        # 如果超过容量，移除最旧的
        if len(self.short_term) >= self.max_short_term_size:
            oldest_key = min(self.short_term.items(),
                           key=lambda x: x[1].timestamp)[0]
            del self.short_term[oldest_key]

        self.short_term[key] = item

    def _store_long_term(self, key: str, item: MemoryItem):
        """存储到长期记忆"""
        # 如果超过容量，移除访问次数最少的
        if len(self.long_term) >= self.max_long_term_size:
            least_accessed_key = min(self.long_term.items(),
                                     key=lambda x: x[1].access_count)[0]
            del self.long_term[least_accessed_key]

        self.long_term[key] = item

    def _store_working_memory(self, key: str, item: MemoryItem):
        """存储到工作记忆"""
        self.working_memory[key] = item

    def _update_index(self, key: str, value: Any, metadata: Dict[str, Any]):
        """更新索引"""
        # 简单的关键词索引
        words = str(key).lower().split()
        for word in words:
            self.key_index[word].append(key)

    def export(self, filepath: str):
        """
        导出记忆到文件

        Args:
            filepath: 文件路径
        """
        data = {
            "short_term": [item.to_dict() for item in self.short_term.values()],
            "long_term": [item.to_dict() for item in self.long_term.values()],
            "working_memory": [item.to_dict() for item in self.working_memory.values()]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def import_memory(self, filepath: str):
        """
        从文件导入记忆

        Args:
            filepath: 文件路径
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 导入短期记忆
        for item_data in data.get("short_term", []):
            item = MemoryItem(**item_data)
            self.short_term[item.key] = item

        # 导入长期记忆
        for item_data in data.get("long_term", []):
            item = MemoryItem(**item_data)
            self.long_term[item.key] = item

        # 导入工作记忆
        for item_data in data.get("working_memory", []):
            item = MemoryItem(**item_data)
            self.working_memory[item.key] = item


if __name__ == "__main__":
    memory = MemorySystem()

    # 存储记忆
    memory.store("task_1", "执行任务 1 的结果", "short_term")
    memory.store("important_info", "关键信息", "long_term")
    memory.store("current_task", "当前任务状态", "working")

    # 检索记忆
    item = memory.retrieve("task_1")
    print(f"检索结果: {item.value}")

    # 搜索记忆
    results = memory.search("任务", limit=5)
    print(f"\n搜索结果:")
    for result in results:
        print(f"  - {result.key}: {result.value}")

    # 获取上下文
    context = memory.get_context("task_1")
    print(f"\n上下文: {json.dumps(context, indent=2, ensure_ascii=False)}")
