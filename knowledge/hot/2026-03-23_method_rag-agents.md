# RAG + Agent 融合方案研究

**日期**: 2026-03-23
**来源**: GitHub Search

## 🔥 热门项目

### Graph RAG

| Stars | 名称 | 说明 |
|-------|------|------|
| 2k | [graph-rag-agent](https://github.com/1517005260/graph-rag-agent) | GraphRAG + LightRAG + Neo4j 融合 |
| 1.6k | [Controllable-RAG-Agent](https://github.com/NirDiamant/Controllable-RAG-Agent) | 图算法控制 RAG |
| 9.3k | [awesome-ai-apps](https://github.com/Arindom200/awesome-ai-apps) | RAG/Agents/Workflows 集合 |

### 企业方案

| Stars | 名称 | 说明 |
|-------|------|------|
| 419 | [RAG-Agents-Accelerator](https://github.com/pablomarin/RAG-Agents-Accelerator) | Azure AI Search + OpenAI |
| 4.7k | [Kiln](https://github.com/Kiln-AI/Kiln) | 评估 + RAG + Agents + MCP |
| 120 | [gpt-rag-agentic](https://github.com/Azure/gpt-rag-agentic) | Azure 官方 RAG Agent |
| 152 | [granite-retrieval-agent](https://github.com/ibm-granite-community/granite-retrieval-agent) | IBM Granite 本地 RAG |

### 混合检索

| Stars | 名称 | 说明 |
|-------|------|------|
| 103 | [MongoDB-RAG-Agent](https://github.com/coleam00/MongoDB-RAG-Agent) | MongoDB + 向量 + 文本混合 |
| 56 | [human-in-the-loop-rag-agent](https://github.com/coleam00/human-in-the-loop-rag-agent) | 实时源验证 + 人机协作 |

## 🏗️ 架构模式

### 1. Graph RAG Agent

```
文档 → 知识图谱构建 → 实体关系抽取 → 图遍历 → 上下文组装 → LLM 生成
```

**优势**: 结构化知识、多跳推理
**劣势**: 构建成本高、维护复杂

### 2. Controllable RAG

```
问题 → 路由决策 → 多源检索 → 重排序 → 答案生成
         ↓
    图算法控制流
```

**优势**: 灵活控制、可解释
**劣势**: 需要调优路由策略

### 3. Hybrid RAG

```
查询 ──┬── 向量检索 ──┐
       │              │
       └── 关键词检索 ─┴── Reciprocal Rank Fusion ── LLM
```

**优势**: 召回率高、互补
**劣势**: 需要平衡权重

## 💡 洞察

1. **Graph RAG 崛起** — 知识图谱 + RAG 成为趋势
2. **混合检索标配** — 向量 + 关键词融合
3. **Human-in-the-Loop** — 人机协作验证源
4. **企业级加速器** — Azure/IBM 都有官方方案
5. **评估驱动** — Kiln 4.7k stars，评估是刚需

## 🔧 技术栈

### 向量数据库
- MongoDB Atlas Vector
- Pinecone
- Qdrant
- Milvus
- Chroma

### 知识图谱
- Neo4j
- NetworkX
- GraphRAG (Microsoft)

### 框架
- LangChain
- LlamaIndex
- Haystack

## 📊 对比

| 方案 | 复杂度 | 效果 | 成本 |
|------|--------|------|------|
| 纯向量 RAG | 低 | 中 | 低 |
| Graph RAG | 高 | 高 | 高 |
| Hybrid RAG | 中 | 高 | 中 |
| Controllable RAG | 中 | 高 | 中 |

## 🔗 待研究

- [ ] GraphRAG vs LightRAG 对比
- [ ] Kiln 的评估体系
- [ ] Azure RAG Accelerator 架构
- [ ] MongoDB 混合检索实现
