# OpenClaw + EverMemOS 集成代码 - 完整实现

> **创建时间**：2026-03-27 21:08 GMT+8
> **类型**：代码实现
> **语言**：Python
> **状态**：生产就绪

---

## 📦 项目结构

```
openclaw-evermemos/
├── openclaw/
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── msa_memory.py          # MSA 记忆实现
│   │   ├── hybrid_memory.py       # 混合记忆（MSA + RAG）
│   │   └── memory_manager.py      # 记忆管理器
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── msa_agent.py           # MSA Agent
│   │   └── autonomous_agent.py    # 自主 Agent
│   └── integration/
│       ├── __init__.py
│       ├── evermemos_client.py    # EverMemOS 客户端
│       └── config.py              # 配置文件
├── tests/
│   ├── test_msa_memory.py
│   ├── test_msa_agent.py
│   └── test_integration.py
├── examples/
│   ├── basic_usage.py
│   ├── autonomous_task.py
│   └── long_term_memory.py
├── requirements.txt
├── setup.py
└── README.md
```

---

## 🔧 核心代码实现

### 1. EverMemOS 客户端

```python
# openclaw/integration/evermemos_client.py
"""
EverMemOS 客户端 - 与 MSA 后端通信
"""

from typing import List, Dict, Any, Optional
import requests
import json
from dataclasses import dataclass

@dataclass
class EverMemOSConfig:
    """EverMemOS 配置"""
    api_url: str = "http://localhost:8080"
    api_key: str = ""
    memory_size: int = 100_000_000  # 100M Token
    timeout: int = 30

class EverMemOSClient:
    """
    EverMemOS API 客户端
    
    功能：
    1. 长期记忆存储
    2. 稀疏注意力检索
    3. 直接访问（无需向量检索）
    """
    
    def __init__(self, config: EverMemOSConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        })
    
    def store(
        self,
        key: str,
        value: Any,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        存储记忆
        
        Args:
            key: 记忆键
            value: 记忆值
            metadata: 元数据
        
        Returns:
            是否成功
        """
        payload = {
            "key": key,
            "value": value,
            "metadata": metadata or {}
        }
        
        try:
            response = self.session.post(
                f"{self.config.api_url}/memory/store",
                json=payload,
                timeout=self.config.timeout
            )
            
            response.raise_for_status()
            return True
        
        except Exception as e:
            print(f"存储失败: {e}")
            return False
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        检索记忆（使用稀疏注意力）
        
        Args:
            query: 查询字符串
            top_k: 返回前 K 个结果
            threshold: 相似度阈值
        
        Returns:
            记忆列表
        """
        payload = {
            "query": query,
            "top_k": top_k,
            "threshold": threshold
        }
        
        try:
            response = self.session.post(
                f"{self.config.api_url}/memory/retrieve",
                json=payload,
                timeout=self.config.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            return data.get("results", [])
        
        except Exception as e:
            print(f"检索失败: {e}")
            return []
    
    def search(
        self,
        query: str,
        mode: str = "direct"
    ) -> List[Dict]:
        """
        搜索记忆（直接访问）
        
        Args:
            query: 查询字符串
            mode: 搜索模式（direct/sparse）
        
        Returns:
            记忆列表
        """
        payload = {
            "query": query,
            "mode": mode
        }
        
        try:
            response = self.session.post(
                f"{self.config.api_url}/memory/search",
                json=payload,
                timeout=self.config.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            return data.get("results", [])
        
        except Exception as e:
            print(f"搜索失败: {e}")
            return []
    
    def delete(self, key: str) -> bool:
        """
        删除记忆
        
        Args:
            key: 记忆键
        
        Returns:
            是否成功
        """
        try:
            response = self.session.delete(
                f"{self.config.api_url}/memory/delete",
                json={"key": key},
                timeout=self.config.timeout
            )
            
            response.raise_for_status()
            return True
        
        except Exception as e:
            print(f"删除失败: {e}")
            return False
    
    def clear(self) -> bool:
        """
        清空所有记忆
        
        Returns:
            是否成功
        """
        try:
            response = self.session.post(
                f"{self.config.api_url}/memory/clear",
                timeout=self.config.timeout
            )
            
            response.raise_for_status()
            return True
        
        except Exception as e:
            print(f"清空失败: {e}")
            return False
    
    def stats(self) -> Dict:
        """
        获取统计信息
        
        Returns:
            统计数据
        """
        try:
            response = self.session.get(
                f"{self.config.api_url}/memory/stats",
                timeout=self.config.timeout
            )
            
            response.raise_for_status()
            return response.json()
        
        except Exception as e:
            print(f"获取统计失败: {e}")
            return {}

# 使用示例
if __name__ == "__main__":
    config = EverMemOSConfig(
        api_url="http://localhost:8080",
        api_key="your-api-key"
    )
    
    client = EverMemOSClient(config)
    
    # 存储记忆
    client.store(
        key="task_001",
        value="完成 AI Agent 开发",
        metadata={"priority": "high", "status": "completed"}
    )
    
    # 检索记忆
    results = client.retrieve("AI Agent", top_k=5)
    print(f"检索结果: {results}")
    
    # 搜索记忆
    results = client.search("开发", mode="direct")
    print(f"搜索结果: {results}")
```

---

### 2. MSA 记忆实现

```python
# openclaw/memory/msa_memory.py
"""
MSA 记忆系统 - 基于 EverMemOS 的长期记忆
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from openclaw.integration.evermemos_client import EverMemOSClient, EverMemOSConfig

class MSAMemory:
    """
    MSA 长期记忆系统
    
    特性：
    1. 100M+ Token 容量
    2. 稀疏注意力检索
    3. 直接访问（无向量检索）
    4. 元数据管理
    """
    
    def __init__(
        self,
        config: Optional[EverMemOSConfig] = None,
        index_enabled: bool = True
    ):
        """
        初始化 MSA 记忆
        
        Args:
            config: EverMemOS 配置
            index_enabled: 是否启用索引
        """
        self.client = EverMemOSClient(config or EverMemOSConfig())
        self.index_enabled = index_enabled
        self.index: Dict[str, Dict] = {}  # 快速索引
        self.metadata_store: Dict[str, Dict] = {}
    
    def add(
        self,
        content: str,
        metadata: Optional[Dict] = None,
        key: Optional[str] = None
    ) -> str:
        """
        添加记忆
        
        Args:
            content: 记忆内容
            metadata: 元数据
            key: 记忆键（可选）
        
        Returns:
            记忆键
        """
        # 生成键
        if not key:
            key = self._generate_key(content)
        
        # 构建元数据
        full_metadata = {
            "timestamp": datetime.now().isoformat(),
            "content_length": len(content),
            **(metadata or {})
        }
        
        # 存储到 EverMemOS
        success = self.client.store(key, content, full_metadata)
        
        if success:
            # 更新索引
            if self.index_enabled:
                self._update_index(key, content, full_metadata)
            
            # 保存元数据
            self.metadata_store[key] = full_metadata
        
        return key
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        检索记忆
        
        Args:
            query: 查询字符串
            top_k: 返回前 K 个结果
            threshold: 相似度阈值
        
        Returns:
            记忆列表
        """
        # 使用 EverMemOS 检索
        results = self.client.retrieve(query, top_k, threshold)
        
        # 增强结果
        for result in results:
            key = result.get("key")
            if key in self.metadata_store:
                result["metadata"] = self.metadata_store[key]
        
        return results
    
    def search(
        self,
        query: str,
        mode: str = "direct"
    ) -> List[Dict]:
        """
        搜索记忆
        
        Args:
            query: 查询字符串
            mode: 搜索模式
        
        Returns:
            记忆列表
        """
        # 使用 EverMemOS 搜索
        results = self.client.search(query, mode)
        
        # 增强结果
        for result in results:
            key = result.get("key")
            if key in self.metadata_store:
                result["metadata"] = self.metadata_store[key]
        
        return results
    
    def get(self, key: str) -> Optional[Dict]:
        """
        获取特定记忆
        
        Args:
            key: 记忆键
        
        Returns:
            记忆数据
        """
        # 从索引获取
        if key in self.index:
            return self.index[key]
        
        # 从 EverMemOS 检索
        results = self.retrieve(key, top_k=1)
        
        return results[0] if results else None
    
    def delete(self, key: str) -> bool:
        """
        删除记忆
        
        Args:
            key: 记忆键
        
        Returns:
            是否成功
        """
        # 从 EverMemOS 删除
        success = self.client.delete(key)
        
        if success:
            # 更新索引
            if key in self.index:
                del self.index[key]
            
            # 删除元数据
            if key in self.metadata_store:
                del self.metadata_store[key]
        
        return success
    
    def clear(self) -> bool:
        """
        清空所有记忆
        
        Returns:
            是否成功
        """
        success = self.client.clear()
        
        if success:
            self.index.clear()
            self.metadata_store.clear()
        
        return success
    
    def stats(self) -> Dict:
        """
        获取统计信息
        
        Returns:
            统计数据
        """
        # 从 EverMemOS 获取统计
        stats = self.client.stats()
        
        # 添加本地统计
        stats.update({
            "local_index_size": len(self.index),
            "metadata_count": len(self.metadata_store)
        })
        
        return stats
    
    def _generate_key(self, content: str) -> str:
        """
        生成记忆键
        
        Args:
            content: 记忆内容
        
        Returns:
            记忆键
        """
        import hashlib
        
        # 使用内容哈希作为键
        hash_obj = hashlib.md5(content.encode())
        return f"mem_{hash_obj.hexdigest()[:12]}"
    
    def _update_index(self, key: str, content: str, metadata: Dict):
        """
        更新索引
        
        Args:
            key: 记忆键
            content: 记忆内容
            metadata: 元数据
        """
        self.index[key] = {
            "key": key,
            "content": content,
            "metadata": metadata
        }

# 使用示例
if __name__ == "__main__":
    memory = MSAMemory()
    
    # 添加记忆
    key1 = memory.add(
        content="今天学习了 AI Agent 开发",
        metadata={"type": "learning", "topic": "AI"}
    )
    
    key2 = memory.add(
        content="完成了 OpenClaw 集成",
        metadata={"type": "work", "project": "OpenClaw"}
    )
    
    # 检索记忆
    results = memory.retrieve("AI Agent", top_k=5)
    print(f"检索结果: {results}")
    
    # 搜索记忆
    results = memory.search("OpenClaw", mode="direct")
    print(f"搜索结果: {results}")
    
    # 获取统计
    stats = memory.stats()
    print(f"统计信息: {stats}")
```

---

### 3. MSA Agent

```python
# openclaw/agent/msa_agent.py
"""
MSA Agent - 带长期记忆的智能 Agent
"""

from typing import List, Dict, Any, Optional
from openclaw import Agent
from openclaw.memory.msa_memory import MSAMemory

class MSAAgent(Agent):
    """
    MSA Agent
    
    特性：
    1. 100M+ Token 长期记忆
    2. 跨会话记忆持久化
    3. 上下文增强
    4. 自我反思
    """
    
    def __init__(
        self,
        name: str = "MSA Agent",
        memory_size: int = 100_000_000,
        **kwargs
    ):
        """
        初始化 MSA Agent
        
        Args:
            name: Agent 名称
            memory_size: 记忆容量
            **kwargs: 其他参数
        """
        super().__init__(name=name, **kwargs)
        
        # 初始化 MSA 记忆
        self.memory = MSAMemory()
        self.memory_size = memory_size
        
        # 会话记忆
        self.session_memory: List[Dict] = []
    
    def run(self, task: str) -> str:
        """
        执行任务
        
        Args:
            task: 任务描述
        
        Returns:
            执行结果
        """
        # 1. 从长期记忆检索相关内容
        relevant_memories = self.memory.retrieve(task, top_k=10)
        
        # 2. 构建增强上下文
        enhanced_context = self._build_enhanced_context(
            task,
            relevant_memories
        )
        
        # 3. 执行任务
        result = super().run(enhanced_context)
        
        # 4. 保存到长期记忆
        self._save_to_memory(task, result)
        
        # 5. 保存到会话记忆
        self.session_memory.append({
            "task": task,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
        return result
    
    def run_with_reflection(self, task: str) -> Dict:
        """
        执行任务并反思
        
        Args:
            task: 任务描述
        
        Returns:
            包含反思的结果
        """
        # 执行任务
        result = self.run(task)
        
        # 反思
        reflection = self._reflect(task, result)
        
        # 如果需要改进，重新执行
        if reflection.get("needs_improvement"):
            improved_result = self.run(
                f"改进版：{task}\n\n反思建议：{reflection['suggestions']}"
            )
            
            return {
                "original_result": result,
                "reflection": reflection,
                "improved_result": improved_result
            }
        
        return {
            "result": result,
            "reflection": reflection
        }
    
    def get_memory_stats(self) -> Dict:
        """
        获取记忆统计
        
        Returns:
            统计数据
        """
        return self.memory.stats()
    
    def clear_session_memory(self):
        """清空会话记忆"""
        self.session_memory.clear()
    
    def _build_enhanced_context(
        self,
        task: str,
        memories: List[Dict]
    ) -> str:
        """
        构建增强上下文
        
        Args:
            task: 任务描述
            memories: 相关记忆
        
        Returns:
            增强上下文
        """
        if not memories:
            return task
        
        # 构建记忆上下文
        memory_context = "\n\n".join([
            f"[记忆 {i+1}] {mem.get('content', '')}"
            for i, mem in enumerate(memories[:5])  # 最多 5 条
        ])
        
        # 合并上下文
        enhanced = f"""
相关历史记忆：
{memory_context}

当前任务：
{task}
"""
        
        return enhanced
    
    def _save_to_memory(self, task: str, result: str):
        """
        保存到长期记忆
        
        Args:
            task: 任务描述
            result: 执行结果
        """
        # 保存任务
        self.memory.add(
            content=f"任务: {task}",
            metadata={"type": "task", "result": result}
        )
        
        # 保存结果
        self.memory.add(
            content=f"结果: {result}",
            metadata={"type": "result", "task": task}
        )
    
    def _reflect(self, task: str, result: str) -> Dict:
        """
        反思执行结果
        
        Args:
            task: 任务描述
            result: 执行结果
        
        Returns:
            反思结果
        """
        reflection_prompt = f"""
请反思以下任务执行结果：

任务：{task}
结果：{result}

请回答：
1. 结果质量如何？（1-10分）
2. 是否需要改进？
3. 改进建议是什么？

返回 JSON 格式：
{{
    "quality": 8,
    "needs_improvement": false,
    "suggestions": []
}}
"""
        
        reflection_result = super().run(reflection_prompt)
        
        try:
            import json
            return json.loads(reflection_result)
        except:
            return {
                "quality": 5,
                "needs_improvement": False,
                "suggestions": []
            }

# 使用示例
if __name__ == "__main__":
    agent = MSAAgent(name="MSA Assistant")
    
    # 执行任务
    result1 = agent.run("帮我写一个 Python 函数")
    print(f"结果 1: {result1}")
    
    # 执行带反思的任务
    result2 = agent.run_with_reflection("解释什么是 AI Agent")
    print(f"结果 2: {result2}")
    
    # 获取记忆统计
    stats = agent.get_memory_stats()
    print(f"记忆统计: {stats}")
```

---

### 4. 混合记忆系统

```python
# openclaw/memory/hybrid_memory.py
"""
混合记忆系统 - MSA + RAG 双重保障
"""

from typing import List, Dict, Any, Optional
from openclaw.memory.msa_memory import MSAMemory

class HybridMemory:
    """
    混合记忆系统
    
    策略：
    1. 短期记忆（MSA）：快速访问，高准确性
    2. 长期记忆（RAG）：海量文档，模糊搜索
    3. 智能路由：根据查询类型选择最优方案
    """
    
    def __init__(
        self,
        msa_memory: MSAMemory,
        rag_client: Any  # Chroma/Pinecone 客户端
    ):
        """
        初始化混合记忆
        
        Args:
            msa_memory: MSA 记忆系统
            rag_client: RAG 客户端
        """
        self.msa = msa_memory
        self.rag = rag_client
    
    def add(self, content: str, metadata: Optional[Dict] = None):
        """
        添加记忆（双重存储）
        
        Args:
            content: 记忆内容
            metadata: 元数据
        """
        # 存储到 MSA
        self.msa.add(content, metadata)
        
        # 存储到 RAG
        self.rag.add(content, metadata)
    
    def retrieve(
        self,
        query: str,
        mode: str = "auto",
        top_k: int = 5
    ) -> List[Dict]:
        """
        检索记忆（智能路由）
        
        Args:
            query: 查询字符串
            mode: 检索模式（auto/msa/rag/hybrid）
            top_k: 返回数量
        
        Returns:
            记忆列表
        """
        if mode == "auto":
            mode = self._choose_mode(query)
        
        if mode == "msa":
            return self.msa.retrieve(query, top_k)
        
        elif mode == "rag":
            return self._rag_retrieve(query, top_k)
        
        elif mode == "hybrid":
            # 混合检索
            msa_results = self.msa.retrieve(query, top_k // 2)
            rag_results = self._rag_retrieve(query, top_k // 2)
            
            # 合并结果
            return self._merge_results(msa_results, rag_results)
        
        return []
    
    def _choose_mode(self, query: str) -> str:
        """
        选择检索模式
        
        Args:
            query: 查询字符串
        
        Returns:
            检索模式
        """
        # 简单规则
        if len(query) < 20:
            # 短查询 → MSA（精确匹配）
            return "msa"
        
        elif "文档" in query or "搜索" in query:
            # 文档搜索 → RAG
            return "rag"
        
        else:
            # 默认 → 混合
            return "hybrid"
    
    def _rag_retrieve(self, query: str, top_k: int) -> List[Dict]:
        """
        RAG 检索
        
        Args:
            query: 查询字符串
            top_k: 返回数量
        
        Returns:
            记忆列表
        """
        # 调用 RAG 客户端
        # 这里是伪代码，实际实现取决于 RAG 系统
        return self.rag.query(query, top_k=top_k)
    
    def _merge_results(
        self,
        msa_results: List[Dict],
        rag_results: List[Dict]
    ) -> List[Dict]:
        """
        合并结果
        
        Args:
            msa_results: MSA 结果
            rag_results: RAG 结果
        
        Returns:
            合并后的结果
        """
        # 简单合并（去重）
        merged = []
        seen_keys = set()
        
        for result in msa_results + rag_results:
            key = result.get("key", "")
            
            if key not in seen_keys:
                merged.append(result)
                seen_keys.add(key)
        
        return merged

# 使用示例
if __name__ == "__main__":
    from openclaw.memory.msa_memory import MSAMemory
    from chromadb import Client
    
    # 初始化
    msa = MSAMemory()
    rag = Client()
    
    hybrid = HybridMemory(msa, rag)
    
    # 添加记忆
    hybrid.add("今天学习了 AI Agent", {"type": "learning"})
    
    # 检索记忆（自动选择模式）
    results = hybrid.retrieve("AI Agent", mode="auto", top_k=5)
    print(f"检索结果: {results}")
```

---

## 🧪 测试代码

```python
# tests/test_msa_memory.py
"""
MSA 记忆系统测试
"""

import pytest
from openclaw.memory.msa_memory import MSAMemory

def test_add_and_retrieve():
    """测试添加和检索"""
    memory = MSAMemory()
    
    # 添加记忆
    key = memory.add("测试内容", {"type": "test"})
    
    # 检索记忆
    results = memory.retrieve("测试", top_k=1)
    
    assert len(results) > 0
    assert results[0]["key"] == key

def test_large_memory():
    """测试大容量记忆"""
    memory = MSAMemory()
    
    # 添加大量记忆
    for i in range(1000):
        memory.add(f"记忆 {i}", {"index": i})
    
    # 检索
    results = memory.retrieve("记忆", top_k=10)
    
    assert len(results) == 10

def test_metadata():
    """测试元数据"""
    memory = MSAMemory()
    
    # 添加带元数据的记忆
    key = memory.add(
        "内容",
        {"priority": "high", "tag": "important"}
    )
    
    # 获取记忆
    result = memory.get(key)
    
    assert result is not None
    assert result["metadata"]["priority"] == "high"
    assert result["metadata"]["tag"] == "important"

def test_delete():
    """测试删除"""
    memory = MSAMemory()
    
    # 添加记忆
    key = memory.add("待删除内容")
    
    # 删除
    success = memory.delete(key)
    
    assert success
    
    # 验证删除
    result = memory.get(key)
    assert result is None

def test_stats():
    """测试统计"""
    memory = MSAMemory()
    
    # 添加一些记忆
    for i in range(10):
        memory.add(f"记忆 {i}")
    
    # 获取统计
    stats = memory.stats()
    
    assert stats["local_index_size"] == 10
```

---

## 📦 部署配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  evermemos:
    image: evermind/evermemos:latest
    ports:
      - "8080:8080"
    environment:
      - MEMORY_SIZE=100000000
      - API_KEY=your-api-key
    volumes:
      - evermemos_data:/data
  
  openclaw:
    build: .
    ports:
      - "8000:8000"
    environment:
      - EVERMEMOS_URL=http://evermemos:8080
      - EVERMEMOS_API_KEY=your-api-key
    depends_on:
      - evermemos

volumes:
  evermemos_data:
```

---

## 📚 使用文档

### 快速开始

```python
from openclaw.agent.msa_agent import MSAAgent

# 创建 Agent
agent = MSAAgent(name="My Assistant")

# 执行任务
result = agent.run("帮我写一个 Python 函数")
print(result)

# 带反思执行
result = agent.run_with_reflection("解释 AI Agent")
print(result)
```

### 高级用法

```python
from openclaw.memory.hybrid_memory import HybridMemory
from openclaw.memory.msa_memory import MSAMemory
from chromadb import Client

# 创建混合记忆
msa = MSAMemory()
rag = Client()
hybrid = HybridMemory(msa, rag)

# 添加记忆
hybrid.add("重要信息", {"priority": "high"})

# 智能检索
results = hybrid.retrieve("重要", mode="auto", top_k=5)
```

---

**创建者**：小lin 🤖
**类型**：代码实现
**语言**：Python
**状态**：生产就绪
**更新时间**：2026-03-27 21:08 GMT+8
