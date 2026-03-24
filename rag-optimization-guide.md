# RAG 系统高级优化指南

## 目录
1. [混合检索策略](#混合检索策略)
2. [重排序优化](#重排序优化)
3. [查询改写](#查询改写)
4. [分块策略](#分块策略)
5. [上下文压缩](#上下文压缩)
6. [完整实现示例](#完整实现示例)

---

## 混合检索策略

### 核心概念
混合检索结合了稠密检索（Dense Retrieval，基于向量）和稀疏检索（Sparse Retrieval，基于关键词）的优势。

### 实现方案

#### 1. 加权融合（Reciprocal Rank Fusion, RRF）

```python
from typing import List, Dict, Tuple
import numpy as np

class HybridRetriever:
    def __init__(self, dense_weight=0.5, sparse_weight=0.5, k=60):
        """
        混合检索器
        
        Args:
            dense_weight: 稠密检索权重
            sparse_weight: 稀疏检索权重
            k: RRF参数，控制排名融合的平滑度
        """
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.k = k
        
    def reciprocal_rank_fusion(self, 
                              dense_results: List[Tuple[str, float]], 
                              sparse_results: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
        """
        RRF算法融合两种检索结果
        
        Args:
            dense_results: 稠密检索结果 [(doc_id, score), ...]
            sparse_results: 稀疏检索结果 [(doc_id, score), ...]
            
        Returns:
            融合后的结果 [(doc_id, fused_score), ...]
        """
        # 计算RRF分数
        scores = {}
        
        # 稠密检索贡献
        for rank, (doc_id, _) in enumerate(dense_results):
            scores[doc_id] = scores.get(doc_id, 0) + self.dense_weight / (self.k + rank + 1)
        
        # 稀疏检索贡献
        for rank, (doc_id, _) in enumerate(sparse_results):
            scores[doc_id] = scores.get(doc_id, 0) + self.sparse_weight / (self.k + rank + 1)
        
        # 排序返回
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    def score_weighting(self,
                       dense_results: List[Tuple[str, float]],
                       sparse_results: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
        """
        基于分数加权融合
        
        需要对分数进行归一化处理
        """
        # 归一化稠密检索分数
        if dense_results:
            dense_scores = np.array([s for _, s in dense_results])
            dense_min, dense_max = dense_scores.min(), dense_scores.max()
            if dense_max > dense_min:
                dense_normalized = {doc_id: (s - dense_min) / (dense_max - dense_min) 
                                   for doc_id, s in dense_results}
            else:
                dense_normalized = {doc_id: 1.0 for doc_id, _ in dense_results}
        else:
            dense_normalized = {}
        
        # 归一化稀疏检索分数
        if sparse_results:
            sparse_scores = np.array([s for _, s in sparse_results])
            sparse_min, sparse_max = sparse_scores.min(), sparse_scores.max()
            if sparse_max > sparse_min:
                sparse_normalized = {doc_id: (s - sparse_min) / (sparse_max - sparse_min) 
                                    for doc_id, s in sparse_results}
            else:
                sparse_normalized = {doc_id: 1.0 for doc_id, _ in sparse_results}
        else:
            sparse_normalized = {}
        
        # 加权融合
        fused_scores = {}
        all_doc_ids = set(dense_normalized.keys()) | set(sparse_normalized.keys())
        
        for doc_id in all_doc_ids:
            dense_score = dense_normalized.get(doc_id, 0)
            sparse_score = sparse_normalized.get(doc_id, 0)
            fused_scores[doc_id] = (
                self.dense_weight * dense_score + 
                self.sparse_weight * sparse_score
            )
        
        return sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
```

#### 2. 学习型融合（Learned Fusion）

```python
from sklearn.ensemble import RandomForestRegressor
import numpy as np

class LearnedFusionRetriever:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.is_trained = False
        
    def extract_features(self, 
                        doc_id: str,
                        dense_score: float,
                        dense_rank: int,
                        sparse_score: float,
                        sparse_rank: int,
                        query_doc_similarity: float = None) -> np.ndarray:
        """
        提取融合特征
        
        Features:
        - 原始分数（归一化）
        - 排名（倒数）
        - 分数与排名的交互特征
        """
        features = [
            dense_score,
            sparse_score,
            1.0 / (dense_rank + 1),  # 排名倒数
            1.0 / (sparse_rank + 1),
            dense_score * (1.0 / (dense_rank + 1)),  # 交互特征
            sparse_score * (1.0 / (sparse_rank + 1)),
            abs(dense_rank - sparse_rank),  # 排名差异
        ]
        
        if query_doc_similarity is not None:
            features.append(query_doc_similarity)
            
        return np.array(features).reshape(1, -1)
    
    def train(self, training_data: List[Dict]):
        """
        训练融合模型
        
        training_data: [
            {
                'dense_score': float,
                'dense_rank': int,
                'sparse_score': float,
                'sparse_rank': int,
                'relevant_score': float  # 标签：真实相关性分数
            },
            ...
        ]
        """
        X = []
        y = []
        
        for data in training_data:
            features = self.extract_features(
                doc_id=data.get('doc_id', ''),
                dense_score=data['dense_score'],
                dense_rank=data['dense_rank'],
                sparse_score=data['sparse_score'],
                sparse_rank=data['sparse_rank']
            )
            X.append(features[0])
            y.append(data['relevant_score'])
        
        X = np.array(X)
        y = np.array(y)
        
        self.model.fit(X, y)
        self.is_trained = True
    
    def fuse(self,
            dense_results: List[Tuple[str, float]],
            sparse_results: List[Tuple[str, float]],
            query_doc_similarity: Dict[str, float] = None) -> List[Tuple[str, float]]:
        """
        使用训练好的模型进行融合
        """
        if not self.is_trained:
            raise ValueError("Model not trained yet!")
        
        # 创建文档ID到排名的映射
        dense_rank_map = {doc_id: rank for rank, (doc_id, _) in enumerate(dense_results)}
        sparse_rank_map = {doc_id: rank for rank, (doc_id, _) in enumerate(sparse_results)}
        
        # 归一化分数
        dense_scores = {doc_id: score for doc_id, score in dense_results}
        sparse_scores = {doc_id: score for doc_id, score in sparse_results}
        
        # 收集所有文档
        all_doc_ids = set(dense_scores.keys()) | set(sparse_scores.keys())
        
        # 预测融合分数
        fused_scores = {}
        for doc_id in all_doc_ids:
            features = self.extract_features(
                doc_id=doc_id,
                dense_score=dense_scores.get(doc_id, 0),
                dense_rank=dense_rank_map.get(doc_id, len(dense_results)),
                sparse_score=sparse_scores.get(doc_id, 0),
                sparse_rank=sparse_rank_map.get(doc_id, len(sparse_results)),
                query_doc_similarity=query_doc_similarity.get(doc_id) if query_doc_similarity else None
            )
            
            fused_scores[doc_id] = self.model.predict(features)[0]
        
        return sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
```

---

## 重排序优化

### 核心概念
重排序（Reranking）在初检（Retrieval）之后，对少量候选文档进行精细化的相关性排序。

### 实现方案

#### 1. 交叉编码器（Cross-Encoder）重排序

```python
from sentence_transformers import CrossEncoder
from typing import List, Tuple

class CrossEncoderReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        """
        交叉编码器重排序器
        
        Args:
            model_name: 预训练模型名称
            常见模型:
            - BAAI/bge-reranker-base (轻量)
            - BAAI/bge-reranker-large (高精度)
            - cross-encoder/ms-marco-MiniLM-L-6-v2 (多语言)
        """
        self.model = CrossEncoder(model_name)
        
    def rerank(self, 
               query: str, 
               documents: List[Tuple[str, str]], 
               top_k: int = None) -> List[Tuple[str, float]]:
        """
        重排序文档
        
        Args:
            query: 查询文本
            documents: [(doc_id, doc_text), ...]
            top_k: 返回前k个结果
            
        Returns:
            [(doc_id, rerank_score), ...]
        """
        # 构造query-doc对
        pairs = [[query, doc_text] for doc_id, doc_text in documents]
        
        # 计算相关性分数
        scores = self.model.predict(pairs)
        
        # 组合结果
        results = [(doc_id, float(score)) 
                   for (doc_id, _), score in zip(documents, scores)]
        
        # 排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k] if top_k else results
```

#### 2. 多样性重排序（Maximal Marginal Relevance, MMR）

```python
import numpy as np
from sentence_transformers import SentenceTransformer

class MMRReranker:
    def __init__(self, diversity_weight=0.5):
        """
        MMR重排序器
        
        Args:
            diversity_weight: 多样性权重 (0-1)
            - 接近0: 更相关，但结果更相似
            - 接近1: 更多样，但可能相关性较低
        """
        self.diversity_weight = diversity_weight
        self.encoder = SentenceTransformer('all-MiniLM-L-6-v2')
        
    def compute_similarity_matrix(self, docs: List[str]) -> np.ndarray:
        """计算文档间的相似度矩阵"""
        embeddings = self.encoder.encode(docs)
        # 归一化
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        # 计算余弦相似度
        similarity_matrix = np.dot(embeddings, embeddings.T)
        return similarity_matrix
    
    def rerank(self,
               query: str,
               documents: List[Tuple[str, str]],
               relevance_scores: List[float],
               top_k: int = None) -> List[Tuple[str, float]]:
        """
        MMR重排序
        
        Args:
            query: 查询文本
            documents: [(doc_id, doc_text), ...]
            relevance_scores: 初始相关性分数
            top_k: 返回前k个结果
        """
        doc_ids, doc_texts = zip(*documents)
        doc_texts = list(doc_texts)
        
        # 计算查询与文档的相似度（相关性）
        query_embedding = self.encoder.encode([query])
        doc_embeddings = self.encoder.encode(doc_texts)
        
        # 归一化
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        doc_embeddings = doc_embeddings / np.linalg.norm(doc_embeddings, axis=1, keepdims=True)
        
        query_doc_similarity = np.dot(query_embedding, doc_embeddings.T)[0]
        
        # 计算文档间相似度矩阵（多样性）
        doc_similarity = self.compute_similarity_matrix(doc_texts)
        
        # MMR算法
        selected_indices = []
        remaining_indices = list(range(len(documents)))
        
        while remaining_indices:
            # 计算MMR分数
            mmr_scores = []
            for idx in remaining_indices:
                # 相关性部分
                relevance = query_doc_similarity[idx]
                
                # 多样性部分：与已选文档的最大相似度
                if selected_indices:
                    max_similarity = max([doc_similarity[idx, s_idx] 
                                        for s_idx in selected_indices])
                else:
                    max_similarity = 0
                
                # MMR分数
                mmr = (1 - self.diversity_weight) * relevance - \
                       self.diversity_weight * max_similarity
                mmr_scores.append((idx, mmr))
            
            # 选择MMR分数最高的文档
            best_idx, best_score = max(mmr_scores, key=lambda x: x[1])
            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)
        
        # 返回结果
        results = [(doc_ids[i], query_doc_similarity[i]) 
                  for i in selected_indices]
        
        return results[:top_k] if top_k else results
```

#### 3. LLM辅助重排序

```python
class LLMReranker:
    def __init__(self, llm_client):
        """
        使用大语言模型进行重排序
        
        Args:
            llm_client: 大语言模型客户端
        """
        self.llm = llm_client
        
    def rerank(self,
               query: str,
               documents: List[Tuple[str, str]],
               top_k: int = None) -> List[Tuple[str, float]]:
        """
        使用LLM重排序
        
        Prompt策略：让LLM直接对文档进行相关性打分
        """
        # 构造prompt
        prompt = f"""请根据以下查询，对文档进行相关性评分（1-10分）。

查询: {query}

文档列表:
"""
        for idx, (doc_id, doc_text) in enumerate(documents):
            # 截断过长的文档
            text_preview = doc_text[:500]
            prompt += f"\n文档{idx+1} (ID: {doc_id}):\n{text_preview}\n"
        
        prompt += """
请以JSON格式返回评分结果:
{
    "scores": [
        {"doc_id": "xxx", "score": 8.5, "reason": "评分理由"},
        ...
    ]
}
"""
        
        # 调用LLM
        response = self.llm.generate(prompt)
        
        # 解析结果
        import json
        try:
            result = json.loads(response)
            scores_dict = {item['doc_id']: item['score'] 
                          for item in result['scores']}
            
            results = [(doc_id, scores_dict.get(doc_id, 0)) 
                      for doc_id, _ in documents]
            results.sort(key=lambda x: x[1], reverse=True)
            
            return results[:top_k] if top_k else results
        except Exception as e:
            print(f"LLM reranking failed: {e}")
            # 降级到原始顺序
            return [(doc_id, 0.0) for doc_id, _ in documents]
```

---

## 查询改写

### 核心概念
查询改写（Query Rewriting）改善原始查询，提高检索准确率。

### 实现方案

#### 1. 查询扩展（Query Expansion）

```python
from typing import List, Set
import numpy as np
from sentence_transformers import SentenceTransformer

class QueryExpander:
    def __init__(self):
        self.encoder = SentenceTransformer('all-MiniLM-L-6-v2')
        self.word_embeddings = None
        self.vocabulary = None
        
    def build_vocabulary(self, documents: List[str]):
        """从文档集构建词汇表"""
        from collections import Counter
        import re
        
        # 简单分词
        words = []
        for doc in documents:
            tokens = re.findall(r'\w+', doc.lower())
            words.extend(tokens)
        
        # 统计词频
        word_freq = Counter(words)
        
        # 过滤低频词
        self.vocabulary = {word for word, freq in word_freq.items() 
                          if freq >= 5}
        
        # 编码词汇
        vocab_list = list(self.vocabulary)
        self.word_embeddings = self.encoder.encode(vocab_list)
        self.vocab_list = vocab_list
        
    def expand_query(self, query: str, top_k: int = 5) -> List[str]:
        """
        查询扩展：添加相关词汇
        
        Returns:
            扩展后的查询列表 [原查询, 扩展1, 扩展2, ...]
        """
        if self.word_embeddings is None:
            return [query]
        
        # 分词
        import re
        query_words = set(re.findall(r'\w+', query.lower()))
        
        # 计算查询与每个词的相似度
        query_embedding = self.encoder.encode([query])[0]
        similarities = np.dot(self.word_embeddings, query_embedding)
        
        # 找到最相关的词
        top_indices = np.argsort(similarities)[-top_k*2:][::-1]
        
        # 选择不在原查询中的词
        expanded_words = []
        for idx in top_indices:
            word = self.vocab_list[idx]
            if word not in query_words and word not in expanded_words:
                expanded_words.append(word)
                if len(expanded_words) >= top_k:
                    break
        
        # 生成扩展查询
        expanded_queries = [query]
        for word in expanded_words:
            expanded_queries.append(f"{query} {word}")
        
        return expanded_queries
```

#### 2. 查询改写（Query Rewriting with LLM）

```python
class LLMAbstractor:
    def __init__(self, llm_client):
        self.llm = llm_client
        
    def rewrite_query(self, query: str, context: str = None) -> List[str]:
        """
        使用LLM改写查询
        
        Args:
            query: 原始查询
            context: 可选的上下文（如对话历史）
            
        Returns:
            改写后的查询列表
        """
        prompt = f"""请改写以下查询，生成3个不同但语义相似的查询变体。

原查询: {query}
"""
        if context:
            prompt += f"\n上下文: {context}\n"
        
        prompt += """
要求:
1. 保持语义一致
2. 使用不同的表述方式
3. 添加可能的关键词
4. 以JSON格式返回: {"rewrites": ["查询1", "查询2", "查询3"]}
"""
        
        response = self.llm.generate(prompt)
        
        import json
        try:
            result = json.loads(response)
            return result['rewrites']
        except:
            return [query]
    
    def decompose_query(self, query: str) -> List[str]:
        """
        分解复杂查询为多个子查询
        
        适用于多问题、多方面的查询
        """
        prompt = f"""请将以下复杂查询分解为多个简单的子查询。

查询: {query}

要求:
1. 每个子查询应该独立完整
2. 子查询应该覆盖原查询的所有方面
3. 以JSON格式返回: {"subqueries": ["子查询1", "子查询2", ...]}
"""
        
        response = self.llm.generate(prompt)
        
        import json
        try:
            result = json.loads(response)
            return result['subqueries']
        except:
            return [query]
```

#### 3. 对话历史感知的查询改写

```python
class ConversationalRewriter:
    def __init__(self, llm_client):
        self.llm = llm_client
        
    def rewrite_with_history(self,
                            current_query: str,
                            history: List[Dict]) -> str:
        """
        结合对话历史改写查询
        
        Args:
            current_query: 当前查询
            history: 对话历史 [{"role": "user", "content": "..."}, ...]
            
        Returns:
            改写后的独立查询
        """
        # 构造历史上下文
        history_text = ""
        for turn in history[-3:]:  # 最近3轮对话
            role = "用户" if turn["role"] == "user" else "助手"
            history_text += f"{role}: {turn['content']}\n"
        
        prompt = f"""请根据对话历史，将当前查询改写为一个独立完整的查询。

对话历史:
{history_text}

当前查询: {current_query}

要求:
1. 改写后的查询应该独立完整，不依赖历史
2. 解决代词引用（如"它"、"这个"）
3. 补充缺失的上下文
4. 直接返回改写后的查询，不要解释
"""
        
        response = self.llm.generate(prompt)
        return response.strip()
```

---

## 分块策略

### 核心概念
合理的分块（Chunking）策略对RAG系统至关重要。

### 实现方案

#### 1. 语义分块（Semantic Chunking）

```python
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Tuple

class SemanticChunker:
    def __init__(self, max_chunk_size=512, threshold=0.6):
        """
        语义分块器
        
        Args:
            max_chunk_size: 最大块大小（字符数）
            threshold: 语义相似度阈值（低于此值则分块）
        """
        self.max_chunk_size = max_chunk_size
        self.threshold = threshold
        self.encoder = SentenceTransformer('all-MiniLM-L-6-v2')
        
    def chunk(self, text: str) -> List[Tuple[str, int, int]]:
        """
        语义分块
        
        Returns:
            [(chunk_text, start_pos, end_pos), ...]
        """
        # 按句子分割
        sentences = self._split_sentences(text)
        
        if len(sentences) <= 1:
            return [(text, 0, len(text))]
        
        # 编码句子
        sentence_embeddings = self.encoder.encode(sentences)
        
        # 计算相邻句子的语义相似度
        similarities = np.dot(sentence_embeddings[:-1], sentence_embeddings[1:].T)
        similarities = np.diag(similarities)
        
        # 找到分割点（相似度低于阈值）
        split_indices = [0]
        for i, sim in enumerate(similarities):
            if sim < self.threshold:
                split_indices.append(i + 1)
        
        # 合并句子成块
        chunks = []
        current_chunk_sentences = []
        current_chunk_start = 0
        
        for i, sentence in enumerate(sentences):
            current_chunk_sentences.append(sentence)
            
            # 计算当前块大小
            chunk_text = ' '.join(current_chunk_sentences)
            
            # 如果是分割点或块大小超限
            if (i + 1 in split_indices or 
                len(chunk_text) >= self.max_chunk_size or
                i == len(sentences) - 1):
                
                chunk_start = current_chunk_start
                chunk_end = current_chunk_start + len(chunk_text)
                chunks.append((chunk_text, chunk_start, chunk_end))
                
                current_chunk_sentences = []
                current_chunk_start = chunk_end
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """简单句子分割"""
        import re
        # 按句号、问号、感叹号分割
        sentences = re.split(r'[。？！.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
```

#### 2. 滑动窗口分块

```python
class SlidingWindowChunker:
    def __init__(self, window_size=512, stride=256):
        """
        滑动窗口分块器
        
        Args:
            window_size: 窗口大小（字符数）
            stride: 步长（字符数）
        """
        self.window_size = window_size
        self.stride = stride
        
    def chunk(self, text: str) -> List[Tuple[str, int, int]]:
        """
        滑动窗口分块
        
        优点:
        - 保留上下文
        - 捕获重叠信息
        
        缺点:
        - 产生冗余块
        """
        chunks = []
        
        for start in range(0, len(text), self.stride):
            end = start + self.window_size
            chunk_text = text[start:end]
            
            chunks.append((chunk_text, start, end))
            
            if end >= len(text):
                break
        
        return chunks
```

#### 3. 层级分块（Hierarchical Chunking）

```python
class HierarchicalChunker:
    def __init__(self,
                 parent_size=2048,
                 child_size=512,
                 overlap=128):
        """
        层级分块器
        
        创建父子块关系，支持摘要检索
        
        Args:
            parent_size: 父块大小
            child_size: 子块大小
            overlap: 重叠大小
        """
        self.parent_size = parent_size
        self.child_size = child_size
        self.overlap = overlap
        
    def chunk(self, text: str) -> List[Dict]:
        """
        层级分块
        
        Returns:
            [
                {
                    'text': str,
                    'level': 'parent' | 'child',
                    'parent_id': int | None,
                    'start': int,
                    'end': int
                },
                ...
            ]
        """
        chunks = []
        
        # 创建父块
        parent_chunks = self._create_chunks(
            text, self.parent_size, self.overlap
        )
        
        for parent_idx, (parent_text, start, end) in enumerate(parent_chunks):
            chunks.append({
                'text': parent_text,
                'level': 'parent',
                'parent_id': None,
                'start': start,
                'end': end
            })
            
            # 创建子块
            child_chunks = self._create_chunks(
                parent_text, self.child_size, self.overlap // 2
            )
            
            for child_text, child_start, child_end in child_chunks:
                chunks.append({
                    'text': child_text,
                    'level': 'child',
                    'parent_id': parent_idx,
                    'start': start + child_start,
                    'end': start + child_end
                })
        
        return chunks
    
    def _create_chunks(self, text: str, size: int, overlap: int) -> List[Tuple[str, int, int]]:
        """创建固定大小的块"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + size
            chunk_text = text[start:end]
            chunks.append((chunk_text, start, end))
            start = end - overlap
        
        return chunks
```

#### 4. 自适应分块（Adaptive Chunking）

```python
class AdaptiveChunker:
    def __init__(self, 
                 min_size=256, 
                 max_size=1024, 
                 target_size=512):
        """
        自适应分块器
        
        根据内容类型和结构动态调整分块大小
        """
        self.min_size = min_size
        self.max_size = max_size
        self.target_size = target_size
        
    def chunk(self, text: str) -> List[Tuple[str, int, int]]:
        """
        自适应分块
        
        策略:
        1. 识别结构（标题、段落、列表等）
        2. 根据内容类型调整块大小
        3. 保持语义完整性
        """
        chunks = []
        
        # 按段落分割
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        chunk_start = 0
        
        for para in paragraphs:
            # 判断内容类型
            content_type = self._detect_content_type(para)
            
            # 根据类型决定块大小
            target_size = self._get_target_size(content_type)
            
            # 如果当前块 + 新段落超过目标大小
            if (len(current_chunk) + len(para) > target_size and 
                len(current_chunk) >= self.min_size):
                
                chunks.append((
                    current_chunk.strip(),
                    chunk_start,
                    chunk_start + len(current_chunk)
                ))
                chunk_start += len(current_chunk)
                current_chunk = para + "\n\n"
            else:
                current_chunk += para + "\n\n"
                
                # 如果超过最大大小，强制分割
                if len(current_chunk) >= self.max_size:
                    chunks.append((
                        current_chunk.strip(),
                        chunk_start,
                        chunk_start + len(current_chunk)
                    ))
                    chunk_start += len(current_chunk)
                    current_chunk = ""
        
        # 处理最后一个块
        if current_chunk.strip():
            chunks.append((
                current_chunk.strip(),
                chunk_start,
                chunk_start + len(current_chunk)
            ))
        
        return chunks
    
    def _detect_content_type(self, text: str) -> str:
        """检测内容类型"""
        if text.strip().startswith('#'):
            return 'heading'
        elif text.strip().startswith('-') or text.strip().startswith('*'):
            return 'list'
        elif len(text.strip()) < 100:
            return 'short'
        else:
            return 'paragraph'
    
    def _get_target_size(self, content_type: str) -> int:
        """根据内容类型返回目标大小"""
        sizes = {
            'heading': self.min_size,
            'list': self.min_size * 1.5,
            'short': self.min_size,
            'paragraph': self.target_size
        }
        return int(sizes.get(content_type, self.target_size))
```

---

## 上下文压缩

### 核心概念
上下文压缩（Context Compression）减少传递给LLM的上下文长度，同时保留关键信息。

### 实现方案

#### 1. 选择性压缩（Selective Compression）

```python
from sentence_transformers import SentenceTransformer
import numpy as np

class SelectiveCompressor:
    def __init__(self):
        self.encoder = SentenceTransformer('all-MiniLM-L-6-v2')
        
    def compress(self,
                 query: str,
                 contexts: List[str],
                 max_length: int = 2000,
                 min_relevance: float = 0.3) -> str:
        """
        选择性压缩：只保留高相关性的内容
        
        Args:
            query: 查询
            contexts: 候选上下文列表
            max_length: 最大长度（字符数）
            min_relevance: 最低相关性阈值
            
        Returns:
            压缩后的上下文
        """
        if not contexts:
            return ""
        
        # 计算相关性
        query_embedding = self.encoder.encode([query])[0]
        context_embeddings = self.encoder.encode(contexts)
        
        # 归一化
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        context_embeddings = context_embeddings / np.linalg.norm(
            context_embeddings, axis=1, keepdims=True
        )
        
        # 计算相似度
        similarities = np.dot(context_embeddings, query_embedding)
        
        # 过滤低相关性内容
        relevant_indices = np.where(similarities >= min_relevance)[0]
        
        if len(relevant_indices) == 0:
            # 如果都低于阈值，选择最高的
            relevant_indices = [np.argmax(similarities)]
        
        # 按相关性排序
        sorted_indices = relevant_indices[
            np.argsort(similarities[relevant_indices])[::-1]
        ]
        
        # 选择内容直到达到最大长度
        compressed = []
        current_length = 0
        
        for idx in sorted_indices:
            context = contexts[idx]
            if current_length + len(context) <= max_length:
                compressed.append(f"[相关度: {similarities[idx]:.2f}] {context}")
                current_length += len(context)
            else:
                # 尝试截断
                remaining = max_length - current_length
                if remaining > 100:  # 至少保留100字符
                    compressed.append(f"[相关度: {similarities[idx]:.2f}] {context[:remaining]}...")
                break
        
        return '\n\n---\n\n'.join(compressed)
```

#### 2. 信息提取压缩（Information Extraction）

```python
class InformationExtractor:
    def __init__(self, llm_client):
        self.llm = llm_client
        
    def compress(self,
                 query: str,
                 contexts: List[str]) -> str:
        """
        使用LLM提取关键信息
        
        策略: 让LLM识别并提取与查询最相关的关键信息
        """
        # 合并上下文
        combined_context = "\n\n---\n\n".join(contexts)
        
        prompt = f"""请从以下文档中提取与查询最相关的关键信息。

查询: {query}

文档:
{combined_context}

要求:
1. 只保留与查询直接相关的信息
2. 去除冗余和无关内容
3. 保持信息的完整性和准确性
4. 使用简洁的语言
5. 以要点形式组织输出
"""
        
        response = self.llm.generate(prompt)
        return response.strip()
```

#### 3. 摘要压缩（Summarization）

```python
class SummarizationCompressor:
    def __init__(self, llm_client):
        self.llm = llm_client
        
    def compress(self,
                 query: str,
                 contexts: List[str],
                 target_length: int = 500) -> str:
        """
        摘要压缩
        
        策略: 为每个上下文生成简短摘要
        """
        summaries = []
        
        for i, context in enumerate(contexts):
            prompt = f"""请为以下文档生成简短摘要（最多{target_length//len(contexts)}字符）。

查询: {query}

文档:
{context}

要求:
1. 专注于与查询相关的内容
2. 使用简洁的语言
3. 保留关键事实和数据
"""
            
            summary = self.llm.generate(prompt)
            summaries.append(f"文档{i+1}: {summary.strip()}")
        
        return '\n\n'.join(summaries)
```

#### 4. 结构化压缩（Structured Compression）

```python
class StructuredCompressor:
    def __init__(self, llm_client):
        self.llm = llm_client
        
    def compress(self,
                 query: str,
                 contexts: List[str]) -> str:
        """
        结构化压缩
        
        策略: 提取结构化信息（实体、关系、事件等）
        """
        # 合并上下文
        combined_context = "\n\n---\n\n".join(contexts)
        
        prompt = f"""请从以下文档中提取与查询相关的结构化信息。

查询: {query}

文档:
{combined_context}

请按以下结构输出:
1. 关键实体:
   - 实体1: 描述
   - 实体2: 描述

2. 重要关系:
   - 关系1: 描述
   - 关系2: 描述

3. 关键事件:
   - 事件1: 描述
   - 事件2: 描述

4. 数据和事实:
   - 事实1: 描述
   - 事实2: 描述
"""
        
        response = self.llm.generate(prompt)
        return response.strip()
```

---

## 完整实现示例

### 端到端RAG系统

```python
from typing import List, Dict, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder

class AdvancedRAGSystem:
    def __init__(self,
                 dense_model: str = "all-MiniLM-L-6-v2",
                 reranker_model: str = "BAAI/bge-reranker-base",
                 llm_client=None):
        """
        完整的RAG系统
        
        集成:
        - 混合检索
        - 重排序
        - 查询改写
        - 语义分块
        - 上下文压缩
        """
        # 初始化组件
        self.dense_encoder = SentenceTransformer(dense_model)
        self.reranker = CrossEncoderReranker(reranker_model)
        self.query_rewriter = LLMAbstractor(llm_client)
        self.chunker = SemanticChunker()
        self.compressor = SelectiveCompressor()
        
        # 存储文档和向量
        self.documents = {}  # {doc_id: {'text': str, 'metadata': dict}}
        self.doc_embeddings = None  # numpy array
        
    def index_documents(self, documents: List[Dict]):
        """
        索引文档
        
        Args:
            documents: [
                {
                    'id': str,
                    'text': str,
                    'metadata': dict
                },
                ...
            ]
        """
        # 分块
        all_chunks = []
        for doc in documents:
            chunks = self.chunker.chunk(doc['text'])
            for chunk_text, start, end in chunks:
                all_chunks.append({
                    'doc_id': doc['id'],
                    'text': chunk_text,
                    'start': start,
                    'end': end,
                    'metadata': doc.get('metadata', {})
                })
        
        # 存储文档