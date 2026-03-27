# AI Agent 代码模板库

> **版本**: v1.0
> **更新时间**: 2026-03-28 00:05
> **模板数**: 30+

---

## 🚀 快速开始模板

### 1. 最小 Agent 模板

```python
"""
最小 Agent 模板
用途: 快速原型验证
"""
from langchain.agents import initialize_agent
from langchain.chat_models import ChatOpenAI

class MinimalAgent:
    def __init__(self, model='gpt-3.5-turbo'):
        self.llm = ChatOpenAI(model=model)
        self.agent = initialize_agent([], self.llm)
    
    def run(self, query: str) -> str:
        return self.agent.run(query)

# 使用
agent = MinimalAgent()
print(agent.run('Hello, AI Agent!'))
```

---

### 2. 带工具的 Agent 模板

```python
"""
带工具的 Agent 模板
用途: 实用 Agent 开发
"""
from langchain.agents import AgentExecutor
from langchain.chat_models import ChatOpenAI
from langchain.tools import Tool
from typing import Callable, List

class ToolAgent:
    def __init__(self, model='gpt-3.5-turbo', tools: List[Tool] = None):
        self.llm = ChatOpenAI(model=model)
        self.tools = tools or []
        self.agent = self._create_agent()
    
    def _create_agent(self):
        from langchain.agents import create_react_agent
        from langchain import hub
        prompt = hub.pull('hwchase17/react')
        agent = create_react_agent(self.llm, self.tools, prompt)
        return AgentExecutor(agent=agent, tools=self.tools)
    
    def add_tool(self, name: str, func: Callable, description: str):
        tool = Tool(name=name, func=func, description=description)
        self.tools.append(tool)
        self.agent = self._create_agent()
    
    def run(self, query: str) -> str:
        result = self.agent.invoke({'input': query})
        return result['output']

# 使用
agent = ToolAgent()
agent.add_tool('calculator', lambda x: str(eval(x)), 'Math calculator')
print(agent.run('What is 2 + 2?'))
```

---

### 3. 带记忆的 Agent 模板

```python
"""
带记忆的 Agent 模板
用途: 对话式 Agent
"""
from langchain.agents import AgentExecutor
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool

class MemoryAgent:
    def __init__(self, model='gpt-3.5-turbo'):
        self.llm = ChatOpenAI(model=model)
        self.memory = ConversationBufferMemory(
            memory_key='chat_history',
            return_messages=True
        )
        self.tools = []
        self.agent = self._create_agent()
    
    def _create_agent(self):
        from langchain.agents import create_react_agent
        from langchain import hub
        prompt = hub.pull('hwchase17/react-chat')
        agent = create_react_agent(self.llm, self.tools, prompt)
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True
        )
    
    def chat(self, message: str) -> str:
        result = self.agent.invoke({'input': message})
        return result['output']

# 使用
agent = MemoryAgent()
print(agent.chat('Hi, I am Alice'))
print(agent.chat('What is my name?'))  # 会记住 Alice
```

---

## 🔧 工具模板

### 4. API 工具模板

```python
"""
API 工具模板
用途: 调用外部 API
"""
import requests
from langchain.tools import Tool
from typing import Dict, Any

class APITool:
    def __init__(self, name: str, url: str, method: str = 'GET'):
        self.name = name
        self.url = url
        self.method = method
    
    def call(self, params: Dict[str, Any]) -> str:
        try:
            if self.method == 'GET':
                response = requests.get(self.url, params=params)
            else:
                response = requests.post(self.url, json=params)
            
            response.raise_for_status()
            return response.text
        except Exception as e:
            return f'Error: {str(e)}'
    
    def to_tool(self) -> Tool:
        return Tool(
            name=self.name,
            func=self.call,
            description=f'Call {self.name} API'
        )

# 使用
weather_tool = APITool(
    name='weather',
    url='https://api.openweathermap.org/data/2.5/weather',
    method='GET'
).to_tool()
```

---

### 5. 数据库工具模板

```python
"""
数据库工具模板
用途: 数据库查询
"""
from sqlalchemy import create_engine, text
from langchain.tools import Tool
from typing import Optional

class DatabaseTool:
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)
    
    def query(self, sql: str) -> str:
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql))
                rows = result.fetchall()
                return str(rows)
        except Exception as e:
            return f'Error: {str(e)}'
    
    def to_tool(self) -> Tool:
        return Tool(
            name='database',
            func=self.query,
            description='Execute SQL queries'
        )

# 使用
db_tool = DatabaseTool(
    'postgresql://user:pass@localhost/db'
).to_tool()
```

---

### 6. 文件工具模板

```python
"""
文件工具模板
用途: 文件操作
"""
import os
from langchain.tools import Tool
from typing import List

class FileTool:
    def __init__(self, base_dir: str = '.'):
        self.base_dir = base_dir
    
    def read(self, filename: str) -> str:
        try:
            filepath = os.path.join(self.base_dir, filename)
            with open(filepath, 'r') as f:
                return f.read()
        except Exception as e:
            return f'Error: {str(e)}'
    
    def write(self, args: str) -> str:
        try:
            filename, content = args.split('|', 1)
            filepath = os.path.join(self.base_dir, filename)
            with open(filepath, 'w') as f:
                f.write(content)
            return f'File {filename} written successfully'
        except Exception as e:
            return f'Error: {str(e)}'
    
    def list_files(self, directory: str = '.') -> str:
        try:
            dirpath = os.path.join(self.base_dir, directory)
            files = os.listdir(dirpath)
            return str(files)
        except Exception as e:
            return f'Error: {str(e)}'
    
    def to_tools(self) -> List[Tool]:
        return [
            Tool(name='read_file', func=self.read, description='Read a file'),
            Tool(name='write_file', func=self.write, description='Write a file'),
            Tool(name='list_files', func=self.list_files, description='List files')
        ]

# 使用
file_tools = FileTool('/path/to/base').to_tools()
```

---

## 🧠 记忆模板

### 7. 向量记忆模板

```python
"""
向量记忆模板
用途: 长期记忆
"""
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.memory import VectorStoreRetrieverMemory

class VectorMemory:
    def __init__(self, persist_directory: str = './memory'):
        self.embeddings = OpenAIEmbeddings()
        self.vectorstore = Chroma(
            embedding_function=self.embeddings,
            persist_directory=persist_directory
        )
        self.memory = VectorStoreRetrieverMemory(
            retriever=self.vectorstore.as_retriever()
        )
    
    def save(self, input: str, output: str):
        self.memory.save_context(
            {'input': input},
            {'output': output}
        )
    
    def load(self, query: str) -> str:
        return self.memory.load_memory_variables({'prompt': query})
    
    def to_memory(self):
        return self.memory

# 使用
memory = VectorMemory()
memory.save('My name is Alice', 'Hello Alice!')
print(memory.load('What is my name?'))
```

---

### 8. 混合记忆模板

```python
"""
混合记忆模板
用途: 短期 + 长期记忆
"""
from langchain.memory import ConversationBufferMemory, VectorStoreRetrieverMemory
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma

class HybridMemory:
    def __init__(self):
        # 短期记忆
        self.short_term = ConversationBufferMemory(
            memory_key='chat_history',
            return_messages=True
        )
        
        # 长期记忆
        self.embeddings = OpenAIEmbeddings()
        self.vectorstore = Chroma(embedding_function=self.embeddings)
        self.long_term = VectorStoreRetrieverMemory(
            retriever=self.vectorstore.as_retriever()
        )
    
    def save(self, input: str, output: str):
        # 保存到短期记忆
        self.short_term.save_context(
            {'input': input},
            {'output': output}
        )
        
        # 保存到长期记忆
        self.long_term.save_context(
            {'input': input},
            {'output': output}
        )
    
    def load(self, query: str) -> dict:
        return {
            'short_term': self.short_term.load_memory_variables({}),
            'long_term': self.long_term.load_memory_variables({'prompt': query})
        }

# 使用
memory = HybridMemory()
memory.save('My name is Alice', 'Hello Alice!')
print(memory.load('What is my name?'))
```

---

## 📊 RAG 模板

### 9. 基础 RAG 模板

```python
"""
基础 RAG 模板
用途: 文档问答
"""
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

class RAGSystem:
    def __init__(self, model='gpt-3.5-turbo'):
        self.llm = ChatOpenAI(model=model)
        self.embeddings = OpenAIEmbeddings()
        self.vectorstore = None
        self.qa_chain = None
    
    def load_documents(self, file_path: str):
        # 加载文档
        loader = TextLoader(file_path)
        documents = loader.load()
        
        # 分割文档
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        texts = text_splitter.split_documents(documents)
        
        # 创建向量存储
        self.vectorstore = Chroma.from_documents(
            texts,
            self.embeddings
        )
        
        # 创建 QA 链
        self.qa_chain = RetrievalQA.from_chain_type(
            self.llm,
            retriever=self.vectorstore.as_retriever()
        )
    
    def query(self, question: str) -> str:
        if not self.qa_chain:
            raise ValueError('Please load documents first')
        
        result = self.qa_chain({'query': question})
        return result['result']

# 使用
rag = RAGSystem()
rag.load_documents('document.txt')
print(rag.query('What is the main topic?'))
```

---

### 10. 高级 RAG 模板

```python
"""
高级 RAG 模板
用途: 企业级 RAG
"""
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Qdrant
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from qdrant_client import QdrantClient

class AdvancedRAG:
    def __init__(self, model='gpt-4'):
        self.llm = ChatOpenAI(model=model)
        self.embeddings = OpenAIEmbeddings()
        self.client = QdrantClient(host='localhost', port=6333)
        self.vectorstore = None
        self.compression_retriever = None
    
    def create_collection(self, collection_name: str, documents: list):
        # 创建向量存储
        self.vectorstore = Qdrant.from_documents(
            documents,
            self.embeddings,
            url='http://localhost:6333',
            collection_name=collection_name
        )
        
        # 创建压缩检索器
        compressor = LLMChainExtractor.from_llm(self.llm)
        self.compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor,
            base_retriever=self.vectorstore.as_retriever()
        )
    
    def query(self, question: str) -> dict:
        if not self.compression_retriever:
            raise ValueError('Please create collection first')
        
        # 检索相关文档
        docs = self.compression_retriever.get_relevant_documents(question)
        
        # 生成答案
        qa_chain = RetrievalQA.from_chain_type(
            self.llm,
            retriever=self.compression_retriever,
            return_source_documents=True
        )
        
        result = qa_chain({'query': question})
        
        return {
            'answer': result['result'],
            'sources': result['source_documents'],
            'compressed_docs': docs
        }

# 使用
rag = AdvancedRAG()
rag.create_collection('my_collection', documents)
result = rag.query('What is AI?')
print(result['answer'])
```

---

**生成时间**: 2026-03-28 00:10 GMT+8
