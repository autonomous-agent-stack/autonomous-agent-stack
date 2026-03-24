#!/usr/bin/env python3
"""
完整的高级RAG系统实现
集成混合检索、重排序、查询改写、分块策略、上下文压缩
"""

from typing import List, Dict, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
from collections import Counter
import re
import json


# ============================================================================
# 混合检索模块
# ============================================================================

class HybridRetriever:
    """混合检索器：结合稠密检索和稀疏检索"""
    
    def __init__(self, dense_weight=0.5, sparse_weight=0.5, k=60):
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.k = k
        
    def reciprocal_rank_fusion(self, 
                              dense_results: List[Tuple[str, float]], 
                              sparse_results: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
        """RRF算法融合两种检索结果"""
        scores = {}
        
        # 稠密检索贡献
        for rank, (doc_id, _) in enumerate(dense_results):
            scores[doc_id] = scores.get(doc_id, 0) + self.dense_weight / (self.k + rank + 1)
        
        # 稀疏检索贡献
        for rank, (doc_id, _) in enumerate(sparse_results):
            scores[doc_id] = scores.get(doc_id, 0) + self.sparse_weight / (self.k + rank + 1)
        
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# ============================================================================
# 重排序模块
# ============================================================================

class CrossEncoderReranker:
    """交叉编码器重排序器"""
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model = CrossEncoder(model_name)
        
    def rerank(self, 
               query: str, 
               documents: List[Tuple[str, str]], 
               top_k: int = None) -> List[Tuple[str, float]]:
        """重排序文档"""
        pairs = [[query, doc_text] for doc_id, doc_text in documents]
        scores = self.model.predict(pairs)
        
        results = [(doc_id, float(score)) 
                   for (doc_id, _), score in zip(documents, scores)]
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k] if top_k else results


# ============================================================================
# 查询改写模块
# ============================================================================

class LLMAbstractor:
    """基于LLM的查询改写器"""
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
        
    def rewrite_query(self, query: str, context: str = None) -> List[str]:
        """使用LLM改写查询"""
        if self.llm is None:
            # 降级到简单的查询扩展
            return self._simple_expand(query)
            
        prompt = f"""请改写以下查询，生成3个不同但语义相似的查询变体。
原查询: {query}
要求:
1. 保持语义一致
2. 使用不同的表述方式
3. 添加可能的关键词
4. 以JSON格式返回: {{"rewrites": ["查询1", "查询2", "查询3"]}}
"""
        
        try:
            response = self.llm.generate(prompt)
            result = json.loads(response)
            return result['rewrites']
        except:
            return [query]
    
    def _simple_expand(self, query: str) -> List[str]:
        """简单的查询扩展（基于同义词）"""
        # 这里可以集成同义词词典
        synonyms = {
            '人工智能': ['AI', '机器智能', '智能系统'],
            '机器学习': ['ML', 'Machine Learning', '算法学习'],
            '深度学习': ['Deep Learning', '神经网络', '深度网络'],
        }
        
        expanded = [query]
        for term, syn_list in synonyms.items():
            if term in query:
                for syn in syn_list:
                    expanded_query = query.replace(term, syn)
                    expanded.append(expanded_query)
                    
        return expanded[:3]  # 最多返回3个变体


# ============================================================================
# 分块模块
# ============================================================================

class SemanticChunker:
    """语义分块器"""
    
    def __init__(self, max_chunk_size=512, threshold=0.6):
        self.max_chunk_size = max_chunk_size
        self.threshold = threshold
        self.encoder = SentenceTransformer('all-MiniLM-L-6-v2')
        
    def chunk(self, text: str) -> List[Tuple[str, int, int]]:
        """语义分块"""
        sentences = self._split_sentences(text)
        
        if len(sentences) <= 1:
            return [(text, 0, len(text))]
        
        # 编码句子
        sentence_embeddings = self.encoder.encode(sentences)
        
        # 计算相邻句子的语义相似度
        similarities = np.dot(sentence_embeddings[:-1], sentence_embeddings[1:].T)
        similarities = np.diag(similarities)
        
        # 找到分割点
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
            chunk_text = ' '.join(current_chunk_sentences)
            
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
        sentences = re.split(r'[。？！.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]


class HierarchicalChunker:
    """层级分块器：创建父子块关系"""
    
    def __init__(self, parent_size=2048, child_size=512, overlap=128):
        self.parent_size = parent_size
        self.child_size = child_size
        self.overlap = overlap
        
    def chunk(self, text: str) -> List[Dict]:
        """层级分块"""
        chunks = []
        
        # 创建父块
        parent_chunks = self._create_chunks(text, self.parent_size, self.overlap)
        
        for parent_idx, (parent_text, start, end) in enumerate(parent_chunks):
            chunks.append({
                'text': parent_text,
                'level': 'parent',
                'parent_id': None,
                'start': start,
                'end': end
            })
            
            # 创建子块
            child_chunks = self._create_chunks(parent_text, self.child_size, self.overlap // 2)
            
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


# ============================================================================
# 上下文压缩模块
# ============================================================================

class SelectiveCompressor:
    """选择性压缩：只保留高相关性的内容"""
    
    def __init__(self):
        self.encoder = SentenceTransformer('all-MiniLM-L-6-v2')
        
    def compress(self,
                 query: str,
                 contexts: List[str],
                 max_length: int = 2000,
                 min_relevance: float = 0.3) -> str:
        """选择性压缩"""
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
            relevant_indices = [np.argmax(similarities)]
        
        # 按相关性排序
        sorted_indices = relevant_indices[
            np.argsort(similarities[relevant_indices])[::-1]
        ]
        
        # 选择内容
        compressed = []
        current_length = 0
        
        for idx in sorted_indices:
            context = contexts[idx]
            if current_length + len(context) <= max_length:
                compressed.append(f"[相关度: {similarities[idx]:.2f}] {context}")
                current_length += len(context)
            else:
                remaining = max_length - current_length
                if remaining > 100:
                    compressed.append(f"[相关度: {similarities[idx]:.2f}] {context[:remaining]}...")
                break
        
        return '\n\n---\n\n'.join(compressed)


# ============================================================================
# 完整的RAG系统
# ============================================================================

class AdvancedRAGSystem:
    """完整的高级RAG系统"""
    
    def __init__(self,
                 dense_model: str = "all-MiniLM-L-6-v2",
                 reranker_model: str = "BAAI/bge-reranker-base",
                 llm_client=None):
        """
        初始化RAG系统
        
        Args:
            dense_model: 稠密检索模型
            reranker_model: 重排序模型
            llm_client: LLM客户端（用于查询改写和答案生成）
        """
        # 初始化组件
        self.dense_encoder = SentenceTransformer(dense_model)
        self.reranker = CrossEncoderReranker(reranker_model)
        self.query_rewriter = LLMAbstractor(llm_client)
        self.chunker = SemanticChunker()
        self.compressor = SelectiveCompressor()
        self.hybrid_retriever = HybridRetriever()
        
        # 存储文档和向量
        self.documents = {}
        self.chunks = []
        self.chunk_texts = []
        self.doc_embeddings = None
        
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
        print(f"开始索引 {len(documents)} 个文档...")
        
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
        self.chunks = all_chunks
        self.chunk_texts = [chunk['text'] for chunk in all_chunks]
        
        # 编码向量
        print(f"编码 {len(all_chunks)} 个文档块的向量...")
        self.doc_embeddings = self.dense_encoder.encode(self.chunk_texts)
        
        print(f"索引完成: {len(documents)}个文档 → {len(all_chunks)}个块")
    
    def retrieve(self, 
                 query: str,
                 top_k: int = 10,
                 use_reranking: bool = True,
                 use_query_expansion: bool = True,
                 compress_context: bool = True,
                 max_context_length: int = 2000) -> Dict:
        """
        完整的检索流程
        
        Returns:
            {
                'query': str,
                'rewritten_queries': List[str],
                'results': List[Dict],
                'compressed_context': str
            }
        """
        print(f"\n检索查询: {query}")
        
        # 1. 查询改写/扩展
        rewritten_queries = [query]
        if use_query_expansion:
            print("执行查询改写...")
            expanded = self.query_rewriter.rewrite_query(query)
            rewritten_queries.extend(expanded)
            print(f"改写后的查询: {rewritten_queries}")
        
        # 2. 混合检索
        all_results = []
        for rewritten_query in rewritten_queries:
            # 稠密检索
            dense_results = self._dense_retrieve(rewritten_query, top_k * 2)
            
            # 稀疏检索
            sparse_results = self._sparse_retrieve(rewritten_query, top_k * 2)
            
            # 融合
            fused = self.hybrid_retriever.reciprocal_rank_fusion(
                dense_results, sparse_results
            )
            all_results.extend(fused)
        
        # 3. 去重和重排序
        print("去重和重排序...")
        unique_results = self._deduplicate_results(all_results)
        
        if use_reranking:
            print(f"使用CrossEncoder重排序Top-{len(unique_results)}结果...")
            unique_results = self.reranker.rerank(
                query,
                [(chunk_id, self.chunks[int(chunk_id)]['text']) 
                 for chunk_id, _ in unique_results],
                top_k=top_k
            )
        else:
            unique_results = unique_results[:top_k]
        
        # 4. 构造结果
        results = []
        for chunk_id, score in unique_results:
            chunk_idx = int(chunk_id)
            chunk = self.chunks[chunk_idx]
            results.append({
                'chunk_id': chunk_id,
                'doc_id': chunk['doc_id'],
                'text': chunk['text'],
                'score': float(score),
                'metadata': chunk['metadata']
            })
        
        # 5. 上下文压缩
        compressed_context = ""
        if compress_context:
            print("执行上下文压缩...")
            contexts = [r['text'] for r in results]
            compressed_context = self.compressor.compress(
                query,
                contexts,
                max_length=max_context_length
            )
        else:
            compressed_context = '\n\n---\n\n'.join([r['text'] for r in results])
        
        print(f"检索完成: 返回{len(results)}个结果")
        
        return {
            'query': query,
            'rewritten_queries': rewritten_queries,
            'results': results,
            'compressed_context': compressed_context
        }
    
    def _dense_retrieve(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        """稠密检索（向量相似度）"""
        query_embedding = self.dense_encoder.encode([query])[0]
        
        # 计算余弦相似度
        similarities = np.dot(self.doc_embeddings, query_embedding)
        
        # Top-K
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        return [(str(i), float(similarities[i])) for i in top_indices]
    
    def _sparse_retrieve(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        """稀疏检索（简化的BM25）"""
        query_terms = set(re.findall(r'\w+', query.lower()))
        
        scores = []
        for idx, chunk in enumerate(self.chunks):
            chunk_terms = set(re.findall(r'\w+', chunk['text'].lower()))
            
            # 计算匹配分数
            match_count = len(query_terms & chunk_terms)
            if match_count > 0:
                score = match_count / len(chunk_terms)
                scores.append((str(idx), score))
        
        # Top-K
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
    
    def _deduplicate_results(self, 
                            results: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
        """去重（保留最高分数）"""
        seen = {}
        for doc_id, score in results:
            if doc_id not in seen or score > seen[doc_id]:
                seen[doc_id] = score
        
        return sorted(seen.items(), key=lambda x: x[1], reverse=True)
    
    def generate_answer(self, query: str, retrieval_result: Dict = None) -> str:
        """
        生成答案
        
        这是一个简化版本，实际应用中应该集成具体的LLM
        """
        if retrieval_result is None:
            retrieval_result = self.retrieve(query)
        
        # 构造prompt
        prompt = f"""请根据以下上下文回答问题。

问题: {query}

上下文:
{retrieval_result['compressed_context']}

要求:
1. 答案必须基于提供的上下文
2. 如果上下文中没有相关信息，请明确说明
3. 使用清晰简洁的语言
4. 必要时引用来源
"""
        
        # 这里应该调用LLM，简化起见返回prompt
        return prompt
    
    def evaluate(self, 
                 test_queries: List[Dict],
                 metrics: List[str] = ['recall', 'precision', 'mrr']) -> Dict:
        """
        评估系统性能
        
        Args:
            test_queries: [
                {
                    'query': str,
                    'relevant_docs': List[str]  # 相关文档ID列表
                },
                ...
            ]
            metrics: 评估指标列表
        
        Returns:
            评估结果字典
        """
        results = {
            'recall': [],
            'precision': [],
            'mrr': []
        }
        
        for test_case in test_queries:
            query = test_case['query']
            relevant_docs = set(test_case['relevant_docs'])
            
            # 检索
            retrieval_result = self.retrieve(query, top_k=10)
            retrieved_docs = set([r['doc_id'] for r in retrieval_result['results']])
            
            # 计算指标
            if 'recall' in metrics:
                recall = len(retrieved_docs & relevant_docs) / len(relevant_docs) if relevant_docs else 0
                results['recall'].append(recall)
            
            if 'precision' in metrics:
                precision = len(retrieved_docs & relevant_docs) / len(retrieved_docs) if retrieved_docs else 0
                results['precision'].append(precision)
            
            if 'mrr' in metrics:
                # 计算第一个相关文档的排名
                mrr = 0
                for i, result in enumerate(retrieval_result['results']):
                    if result['doc_id'] in relevant_docs:
                        mrr = 1 / (i + 1)
                        break
                results['mrr'].append(mrr)
        
        # 计算平均值
        summary = {}
        for metric in metrics:
            if results[metric]:
                summary[f'avg_{metric}'] = np.mean(results[metric])
                summary[f'std_{metric}'] = np.std(results[metric])
        
        return summary


# ============================================================================
# 使用示例
# ============================================================================

def main():
    """主函数：演示RAG系统的使用"""
    
    print("=" * 80)
    print("高级RAG系统演示")
    print("=" * 80)
    
    # 1. 初始化系统
    print("\n初始化RAG系统...")
    system = AdvancedRAGSystem(
        dense_model="all-MiniLM-L-6-v2",
        reranker_model="BAAI/bge-reranker-base",
        llm_client=None  # 实际使用时传入LLM客户端
    )
    
    # 2. 准备示例文档
    sample_documents = [
        {
            'id': 'doc1',
            'text': '''
            人工智能（Artificial Intelligence，简称AI）是计算机科学的一个分支，
            它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
            该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。
            
            机器学习是人工智能的核心，是使计算机具有智能的根本途径。
            深度学习是机器学习领域中一个新的研究方向，它被引入机器学习使其更接近于最初的目标——人工智能。
            ''',
            'metadata': {'source': 'wiki', 'date': '2024-01-01'}
        },
        {
            'id': 'doc2',
            'text': '''
            自然语言处理（NLP）是人工智能的重要分支领域。
            它研究能实现人与计算机之间用自然语言进行有效通信的各种理论和方法。
            
            自然语言处理是一门融语言学、计算机科学、数学于一体的科学。
            因此，这一领域的研究将涉及自然语言，即人们日常使用的语言，
            所以它与语言学的研究有着密切的联系，但又有重要的区别。
            
            自然语言处理并不是一般地研究自然语言，
            而在于研制能有效地实现自然语言通信的计算机系统，
            特别是其中的软件系统。因而它是计算机科学的一部分。
            ''',
            'metadata': {'source': 'textbook', 'date': '2024-01-02'}
        },
        {
            'id': 'doc3',
            'text': '''
            计算机视觉是人工智能的另一个重要分支。
            它是一门研究如何使机器"看"的科学，更进一步的说，
            就是指用摄影机和电脑代替人眼对目标进行识别、跟踪和测量等机器视觉，
            并进一步做图形处理。
            
            计算机视觉使用计算机程序从图像或多维数据中获取信息、
            理解信息并采取行动。在工业、医疗、军事、交通等领域有广泛应用。
            常见的任务包括图像分类、目标检测、语义分割等。
            ''',
            'metadata': {'source': 'paper', 'date': '2024-01-03'}
        }
    ]
    
    # 3. 索引文档
    print("\n" + "=" * 80)
    system.index_documents(sample_documents)
    
    # 4. 执行检索
    print("\n" + "=" * 80)
    print("执行检索...")
    
    test_queries = [
        "什么是机器学习？",
        "自然语言处理的研究内容是什么？",
        "人工智能有哪些应用领域？",
        "深度学习和机器学习的关系"
    ]
    
    for query in test_queries:
        print("\n" + "-" * 80)
        result = system.retrieve(
            query=query,
            top_k=3,
            use_reranking=True,
            use_query_expansion=True,
            compress_context=True
        )
        
        print(f"\n查询: {result['query']}")
        print(f"改写后的查询: {result['rewritten_queries']}")
        print(f"\n检索结果 (Top {len(result['results'])}):")
        for i, r in enumerate(result['results'], 1):
            print(f"{i}. [分数: {r['score']:.4f}] {r['text'][:100]}...")
        
        print(f"\n压缩后的上下文 ({len(result['compressed_context'])} 字符):")
        print(result['compressed_context'][:500] + "...")
    
    # 5. 评估系统
    print("\n" + "=" * 80)
    print("系统评估...")
    
    test_cases = [
        {
            'query': '机器学习',
            'relevant_docs': ['doc1']
        },
        {
            'query': '自然语言处理',
            'relevant_docs': ['doc2']
        },
        {
            'query': '计算机视觉',
            'relevant_docs': ['doc3']
        }
    ]
    
    eval_results = system.evaluate(test_cases)
    print("\n评估结果:")
    for metric, value in eval_results.items():
        print(f"{metric}: {value:.4f}")
    
    print("\n" + "=" * 80)
    print("演示完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
