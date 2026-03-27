"""
RAG Agent 模板
基于检索增强生成的 Agent 实现
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import chromadb
from chromadb.config import Settings

class Document(BaseModel):
    """文档定义"""
    id: str
    content: str
    metadata: Dict[str, Any] = {}

class RAGAgent:
    """RAG Agent 实现"""
    
    def __init__(
        self,
        model: str,
        persist_dir: str = "./chroma_db",
        collection_name: str = "documents"
    ):
        """
        初始化 RAG Agent
        
        Args:
            model: LLM 模型名称
            persist_dir: 向量数据库持久化目录
            collection_name: 集合名称
        """
        self.model = model
        
        # 初始化向量数据库
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_dir
        ))
        self.collection = self.client.get_or_create_collection(collection_name)
    
    def add_documents(self, documents: List[Document]):
        """
        添加文档到向量数据库
        
        Args:
            documents: 文档列表
        """
        self.collection.add(
            documents=[doc.content for doc in documents],
            metadatas=[doc.metadata for doc in documents],
            ids=[doc.id for doc in documents]
        )
    
    def retrieve(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            n_results: 返回结果数量
        
        Returns:
            检索结果列表
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        return [
            {
                "content": doc,
                "metadata": meta,
                "distance": dist
            }
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )
        ]
    
    def generate(self, query: str, context: List[Dict[str, Any]]) -> str:
        """
        基于上下文生成答案
        
        Args:
            query: 用户问题
            context: 检索到的上下文
        
        Returns:
            生成的答案
        """
        context_str = "\n\n".join([
            f"文档 {i+1}:\n{c['content']}"
            for i, c in enumerate(context)
        ])
        
        prompt = f"""基于以下文档回答问题。如果文档中没有相关信息，请明确说明。

文档:
{context_str}

问题: {query}

答案:"""
        
        # 调用 LLM 生成答案
        response = self._call_llm(prompt)
        
        return response
    
    def run(self, query: str, n_results: int = 5) -> str:
        """
        运行 RAG Agent
        
        Args:
            query: 用户问题
            n_results: 检索文档数量
        
        Returns:
            生成的答案
        """
        # 1. 检索相关文档
        context = self.retrieve(query, n_results)
        
        # 2. 基于上下文生成答案
        answer = self.generate(query, context)
        
        return answer
    
    def _call_llm(self, prompt: str) -> str:
        """调用 LLM（需要实现）"""
        # TODO: 实现 LLM 调用
        raise NotImplementedError


# 使用示例
if __name__ == "__main__":
    # 创建 RAG Agent
    agent = RAGAgent(model="gpt-4")
    
    # 添加文档
    documents = [
        Document(
            id="doc1",
            content="Python 是一种高级编程语言，由 Guido van Rossum 于 1991 年创建。",
            metadata={"source": "python_intro.txt"}
        ),
        Document(
            id="doc2",
            content="FastAPI 是一个现代、快速的 Web 框架，用于构建 API。",
            metadata={"source": "fastapi_intro.txt"}
        )
    ]
    agent.add_documents(documents)
    
    # 查询
    answer = agent.run("什么是 Python？")
    print(answer)
