# RAG 系统优化快速参考

## 🚀 快速开始

### 基础RAG vs 高级RAG

| 特性 | 基础RAG | 高级RAG |
|------|---------|---------|
| 检索方式 | 单一向量检索 | 混合检索（稠密+稀疏） |
| 排序 | 向量相似度 | 交叉编码器重排序 |
| 查询处理 | 原始查询 | 查询改写/扩展 |
| 分块策略 | 固定大小 | 语义/层级/自适应 |
| 上下文处理 | 全部传递 | 选择性压缩 |
| 准确率 | 中等 | 高 |
| 延迟 | 低 | 中等 |

---

## 📊 技术选型决策树

```
开始
  │
  ├─ 数据规模 < 10K 文档？
  │   └─ 是 → 使用全部优化技术
  │
  ├─ 需要高准确率？
  │   ├─ 是 → 启用混合检索 + 重排序
  │   └─ 否 → 使用向量检索即可
  │
  ├─ 查询复杂度高？
  │   ├─ 是 → 启用查询改写
  │   └─ 否 → 跳过
  │
  ├─ 上下文超长？
  │   ├─ 是 → 启用上下文压缩
  │   └─ 否 → 可选
  │
  └─ 性能要求高？
      ├─ 是 → 使用缓存 + 批量处理
      └─ 否 → 全部启用
```

---

## 🎯 关键参数配置

### 检索参数

```python
# 混合检索
dense_weight = 0.5      # 稠密检索权重 (0-1)
sparse_weight = 0.5     # 稀疏检索权重 (0-1)
rrf_k = 60              # RRF参数 (推荐: 60)

# 检索数量
initial_retrieve = 50   # 初检数量 (推荐: 30-100)
final_top_k = 10        # 最终返回数量 (推荐: 5-20)
```

### 重排序参数

```python
# 重排序
reranker_model = "BAAI/bge-reranker-base"  # 轻量级
# 或 "BAAI/bge-reranker-large"              # 高精度
rerank_top_k = 20      # 重排序数量 (推荐: 10-50)
```

### 分块参数

```python
# 语义分块
max_chunk_size = 512    # 最大块大小 (字符)
similarity_threshold = 0.6  # 相似度阈值 (0-1)

# 层级分块
parent_size = 2048      # 父块大小
child_size = 512        # 子块大小
overlap = 128           # 重叠大小

# 滑动窗口
window_size = 512
stride = 256
```

### 上下文压缩参数

```python
max_context_length = 2000    # 最大上下文长度
min_relevance = 0.3          # 最低相关性阈值
```

---

## 🔧 常见问题速查

### 问题1: 检索召回率低

**症状**: 找不到相关文档

**诊断**:
```python
# 检查查询和文档的语义差距
query_embedding = model.encode(query)
doc_embedding = model.encode(document)
similarity = cosine_similarity(query_embedding, doc_embedding)
print(f"相似度: {similarity}")
```

**解决方案**:
1. ✅ 启用查询改写/扩展
2. ✅ 增加检索数量 (top_k: 10 → 50)
3. ✅ 使用混合检索
4. ✅ 优化分块策略
5. ✅ 尝试领域特定的向量模型

### 问题2: 检索精度低

**症状**: 结果包含不相关文档

**解决方案**:
1. ✅ 启用重排序 (Cross-Encoder)
2. ✅ 提高相似度阈值
3. ✅ 使用多样性重排序 (MMR)
4. ✅ 优化稀疏检索的BM25参数

### 问题3: 性能慢

**症状**: 响应时间 > 5秒

**优化清单**:
```python
# 1. 减少重排序数量
rerank_top_k = 20  # 从50减少到20

# 2. 禁用查询扩展
use_query_expansion = False

# 3. 使用缓存
@lru_cache(maxsize=1000)
def cached_retrieve(query):
    return retrieve(query)

# 4. 批量处理
def batch_retrieve(queries):
    return [retrieve(q) for q in queries]

# 5. 使用更小的模型
dense_model = "all-MiniLM-L-6-v2"  # 而非 large 版本
```

### 问题4: 答案质量差

**症状**: LLM生成的答案不准确

**解决方案**:
1. ✅ 检索更多上下文 (增加top_k)
2. ✅ 优化上下文压缩策略
3. ✅ 改进LLM提示词
4. ✅ 使用更好的LLM模型
5. ✅ 添加引用来源

---

## 📈 性能优化技巧

### 1. 向量检索优化

```python
# 使用FAISS加速
import faiss

# 构建索引
index = faiss.IndexFlatL2(dimension)
index.add(document_embeddings)

# 检索
distances, indices = index.search(query_embedding, k)
```

### 2. 缓存策略

```python
from functools import lru_cache
import hashlib

def get_cache_key(query, params):
    return hashlib.md5(f"{query}{params}".encode()).hexdigest()

@lru_cache(maxsize=1000)
def retrieve_with_cache(query, top_k):
    return retrieve(query, top_k)
```

### 3. 批量处理

```python
def batch_encode(texts, batch_size=32):
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        emb = model.encode(batch)
        embeddings.extend(emb)
    return embeddings
```

### 4. 并行处理

```python
from concurrent.futures import ThreadPoolExecutor

def parallel_retrieve(queries, max_workers=4):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(retrieve, queries))
    return results
```

---

## 🎓 最佳实践

### 1. 渐进式优化

```
第1周: 实现基础RAG（向量检索）
第2周: 添加重排序
第3周: 实现查询改写
第4周: 优化分块策略
第5周: 添加上下文压缩
第6周: 性能优化和缓存
```

### 2. 评估驱动

```python
# 建立评估基准
test_cases = [
    {'query': '...', 'relevant_docs': [...]},
    {'query': '...', 'relevant_docs': [...]},
]

# 每次优化后评估
results = system.evaluate(test_cases)
print(f"Recall: {results['avg_recall']:.4f}")
```

### 3. A/B测试

```python
# 对比不同配置
config_a = {'use_reranking': True}
config_b = {'use_reranking': False}

score_a = evaluate(config_a)
score_b = evaluate(config_b)

print(f"Config A: {score_a}")
print(f"Config B: {score_b}")
```

---

## 📚 推荐模型

### 向量模型（稠密检索）

| 模型 | 大小 | 特点 | 适用场景 |
|------|------|------|----------|
| all-MiniLM-L-6-v2 | 80MB | 轻量，快速 | 通用，资源受限 |
| all-mpnet-base-v2 | 420MB | 平衡 | 通用，推荐 |
| bge-large-zh | 1.3GB | 中文优化 | 中文场景 |
| bge-m3 | 2.2GB | 多语言 | 多语言场景 |

### 重排序模型

| 模型 | 大小 | 特点 | 适用场景 |
|------|------|------|----------|
| bge-reranker-base | 400MB | 轻量 | 快速重排序 |
| bge-reranker-large | 1.3GB | 高精度 | 高精度要求 |
| cross-encoder-ms-marco | 400MB | 多语言 | 多语言场景 |

### LLM模型（答案生成）

| 模型 | 特点 | 适用场景 |
|------|------|----------|
| GPT-3.5 | 快速，成本低 | 一般问答 |
| GPT-4 | 高质量 | 复杂推理 |
| Claude | 长上下文 | 长文档处理 |
| Llama 2 | 开源 | 本地部署 |

---

## 🔗 相关资源

### 论文

- [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)
- [Dense Passage Retrieval for Open-Domain Question Answering](https://arxiv.org/abs/2004.04906)
- [Query Reformulation for Passage Retrieval](https://arxiv.org/abs/2010.08675)

### 工具库

- [LangChain](https://github.com/langchain-ai/langchain) - RAG框架
- [LlamaIndex](https://github.com/run-llama/llama_index) - 数据框架
- [Haystack](https://github.com/deepset-ai/haystack) - NLP框架
- [FAISS](https://github.com/facebookresearch/faiss) - 向量检索
- [Chroma](https://github.com/chroma-core/chroma) - 向量数据库

### 学习资源

- [RAG教程 - Pinecone](https://www.pinecone.io/learn/)
- [RAG实战指南](https://github.com/anarchy-99/LLM-RLHF-Practical-Guide)
- [向量数据库对比](https://zilliz.com/learn/what-is-vector-database)

---

## 💡 提示清单

### 部署前检查

- [ ] 向量模型已优化（量化/ONNX）
- [ ] 重排序模型已优化
- [ ] 实现了缓存机制
- [ ] 批量处理已启用
- [ ] 评估指标已建立
- [ ] 日志记录已完善
- [ ] 错误处理已添加
- [ ] 性能监控已配置

### 持续优化

- [ ] 定期评估模型性能
- [ ] 收集用户反馈
- [ ] 更新文档库
- [ ] 优化检索策略
- [ ] 调整参数配置

---

## 🎯 快速决策

| 需求 | 推荐方案 |
|------|----------|
| 快速启动 | 基础RAG + 向量检索 |
| 高准确率 | 混合检索 + 重排序 |
| 复杂查询 | 查询改写 + 分解 |
| 长文档 | 层级分块 + 摘要检索 |
| 低延迟 | 缓存 + 批量处理 |
| 多语言 | 多语言模型 + 翻译 |

---

**记住**: 没有银弹。最好的方案取决于你的具体需求、数据特点和资源约束。从简单开始，逐步优化！
