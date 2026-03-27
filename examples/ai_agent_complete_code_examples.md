# AI Agent 完整代码示例集

> **版本**: v1.0
> **更新时间**: 2026-03-27 23:05
> **示例数**: 50+

---

## 🚀 快速开始示例

### 1. Hello World Agent

```python
from langchain.agents import initialize_agent
from langchain.chat_models import ChatOpenAI

# 创建 LLM
llm = ChatOpenAI(model='gpt-3.5-turbo', temperature=0)

# 创建 Agent
agent = initialize_agent([], llm, agent='zero-shot-react-description')

# 运行
response = agent.run('Hello, AI Agent!')
print(response)
```

---

### 2. 带工具的 Agent

```python
from langchain.agents import initialize_agent, Tool
from langchain.chat_models import ChatOpenAI

# 定义工具
def calculator(expression: str) -> str:
    return str(eval(expression))

def search(query: str) -> str:
    # 模拟搜索
    return f'Search results for: {query}'

tools = [
    Tool(name='calculator', func=calculator, description='Useful for math'),
    Tool(name='search', func=search, description='Useful for search')
]

# 创建 Agent
llm = ChatOpenAI(model='gpt-3.5-turbo')
agent = initialize_agent(tools, llm, agent='zero-shot-react-description')

# 运行
response = agent.run('What is 2 + 2?')
print(response)
```

---

### 3. 带 RAG 的 Agent

```python
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA

# 创建向量存储
embeddings = OpenAIEmbeddings()
texts = ['AI Agent is useful', 'LangChain is a framework']
vectorstore = Chroma.from_texts(texts, embeddings)

# 创建 RAG 链
llm = ChatOpenAI(model='gpt-3.5-turbo')
qa = RetrievalQA.from_chain_type(llm, retriever=vectorstore.as_retriever())

# 查询
response = qa.run('What is AI Agent?')
print(response)
```

---

## 🛠️ 工具示例

### 1. 自定义工具

```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

class WeatherInput(BaseModel):
    location: str = Field(description='City name')

class WeatherTool(BaseTool):
    name = 'weather'
    description = 'Get weather for a location'
    args_schema = WeatherInput
    
    def _run(self, location: str) -> str:
        # 模拟天气 API
        return f'Weather in {location}: Sunny, 25°C'
    
    async def _arun(self, location: str) -> str:
        return self._run(location)

# 使用
tool = WeatherTool()
result = tool.run('Beijing')
print(result)
```

---

### 2. 多工具协调

```python
from langchain.agents import AgentExecutor
from langchain.chat_models import ChatOpenAI
from langchain.tools import Tool

# 定义工具
def search(query):
    return f'Search: {query}'

def analyze(text):
    return f'Analysis: {text}'

def summarize(text):
    return f'Summary: {text}'

tools = [
    Tool(name='search', func=search, description='Search web'),
    Tool(name='analyze', func=analyze, description='Analyze text'),
    Tool(name='summarize', func=summarize, description='Summarize text')
]

# 创建 Agent
llm = ChatOpenAI(model='gpt-4')
from langchain.agents import create_react_agent
from langchain import hub
prompt = hub.pull('hwchase17/react')
agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# 运行
result = executor.invoke({
    'input': 'Search for AI news, analyze it, and summarize'
})
print(result['output'])
```

---

## 🧠 记忆示例

### 1. 对话记忆

```python
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain

# 创建记忆
memory = ConversationBufferMemory()

# 创建对话链
llm = ChatOpenAI(model='gpt-3.5-turbo')
conversation = ConversationChain(llm=llm, memory=memory, verbose=True)

# 对话
print(conversation.predict(input='Hi, I am Alice'))
print(conversation.predict(input='What is my name?'))
```

---

### 2. 向量记忆

```python
from langchain.memory import VectorStoreRetrieverMemory
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma

# 创建向量存储
embeddings = OpenAIEmbeddings()
vectorstore = Chroma(embedding_function=embeddings)

# 创建记忆
memory = VectorStoreRetrieverMemory(
    retriever=vectorstore.as_retriever()
)

# 保存记忆
memory.save_context(
    {'input': 'My favorite color is blue'},
    {'output': 'I will remember that'}
)

# 查询记忆
result = memory.load_memory_variables({'prompt': 'color'})
print(result)
```

---

## 🤖 多 Agent 示例

### 1. AutoGen 多 Agent

```python
from autogen import AssistantAgent, UserProxyAgent

# 创建配置
config_list = [{'model': 'gpt-4', 'api_key': 'your-key'}]

# 创建 Agent
planner = AssistantAgent(
    name='Planner',
    llm_config={'config_list': config_list},
    system_message='You are a planner'
)

coder = AssistantAgent(
    name='Coder',
    llm_config={'config_list': config_list},
    system_message='You are a coder'
)

reviewer = AssistantAgent(
    name='Reviewer',
    llm_config={'config_list': config_list},
    system_message='You are a code reviewer'
)

# 创建用户代理
user = UserProxyAgent(
    name='User',
    human_input_mode='NEVER',
    max_consecutive_auto_reply=10
)

# 开始协作
user.initiate_chat(
    planner,
    message='Plan a Python web scraper'
)
```

---

### 2. CrewAI 角色 Agent

```python
from crewai import Agent, Task, Crew

# 创建 Agent
researcher = Agent(
    role='Researcher',
    goal='Find information',
    backstory='Expert researcher',
    verbose=True
)

writer = Agent(
    role='Writer',
    goal='Write content',
    backstory='Professional writer',
    verbose=True
)

# 创建任务
research_task = Task(
    description='Research AI agents',
    agent=researcher
)

write_task = Task(
    description='Write article about AI agents',
    agent=writer
)

# 创建团队
crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    verbose=True
)

# 执行
result = crew.kickoff()
print(result)
```

---

## 📊 RAG 示例

### 1. 基础 RAG

```python
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# 加载文档
loader = TextLoader('document.txt')
documents = loader.load()

# 分割文档
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
texts = text_splitter.split_documents(documents)

# 创建向量存储
embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(texts, embeddings)

# 创建 RAG 链
llm = ChatOpenAI(model='gpt-4')
qa = RetrievalQA.from_chain_type(
    llm,
    retriever=vectorstore.as_retriever(),
    return_source_documents=True
)

# 查询
result = qa({'query': 'What is the main topic?'})
print(result['result'])
print(result['source_documents'])
```

---

### 2. 高级 RAG

```python
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor

# 创建压缩器
llm = ChatOpenAI(model='gpt-4')
compressor = LLMChainExtractor.from_llm(llm)

# 创建压缩检索器
compression_retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=vectorstore.as_retriever()
)

# 查询
docs = compression_retriever.get_relevant_documents('What is AI?')
for doc in docs:
    print(doc.page_content)
```

---

## 🔄 工作流示例

### 1. LangGraph 工作流

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class State(TypedDict):
    query: str
    search_result: str
    analysis: str
    summary: str

def search_node(state: State) -> State:
    # 搜索逻辑
    result = search(state['query'])
    return {'search_result': result}

def analyze_node(state: State) -> State:
    # 分析逻辑
    analysis = analyze(state['search_result'])
    return {'analysis': analysis}

def summarize_node(state: State) -> State:
    # 总结逻辑
    summary = summarize(state['analysis'])
    return {'summary': summary}

# 创建图
workflow = StateGraph(State)
workflow.add_node('search', search_node)
workflow.add_node('analyze', analyze_node)
workflow.add_node('summarize', summarize_node)

# 添加边
workflow.add_edge('search', 'analyze')
workflow.add_edge('analyze', 'summarize')
workflow.add_edge('summarize', END)

# 设置入口
workflow.set_entry_point('search')

# 编译
app = workflow.compile()

# 运行
result = app.invoke({'query': 'AI agents'})
print(result)
```

---

### 2. 条件工作流

```python
def should_continue(state: State) -> str:
    if state.get('needs_more_search'):
        return 'search'
    return 'summarize'

# 添加条件边
workflow.add_conditional_edges(
    'analyze',
    should_continue,
    {
        'search': 'search',
        'summarize': 'summarize'
    }
)
```

---

## 🎯 完整应用示例

### 1. 客服 Agent

```python
from langchain.agents import AgentExecutor
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool

class CustomerServiceAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model='gpt-4')
        self.memory = ConversationBufferMemory()
        self.tools = self._create_tools()
        self.agent = self._create_agent()
    
    def _create_tools(self):
        def check_order(order_id: str) -> str:
            # 检查订单
            return f'Order {order_id}: Shipped'
        
        def create_ticket(issue: str) -> str:
            # 创建工单
            return f'Ticket created for: {issue}'
        
        return [
            Tool(name='check_order', func=check_order, description='Check order status'),
            Tool(name='create_ticket', func=create_ticket, description='Create support ticket')
        ]
    
    def _create_agent(self):
        from langchain.agents import create_react_agent
        from langchain import hub
        prompt = hub.pull('hwchase17/react')
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
agent = CustomerServiceAgent()
print(agent.chat('Where is my order 12345?'))
print(agent.chat('I have an issue with my order'))
```

---

### 2. 研究助手 Agent

```python
class ResearchAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model='gpt-4')
        self.vectorstore = self._create_vectorstore()
    
    def _create_vectorstore(self):
        from langchain.embeddings import OpenAIEmbeddings
        from langchain.vectorstores import Chroma
        
        embeddings = OpenAIEmbeddings()
        return Chroma(embedding_function=embeddings)
    
    def research(self, topic: str) -> dict:
        # 搜索
        search_results = self._search(topic)
        
        # 分析
        analysis = self._analyze(search_results)
        
        # 总结
        summary = self._summarize(analysis)
        
        return {
            'topic': topic,
            'search_results': search_results,
            'analysis': analysis,
            'summary': summary
        }
    
    def _search(self, topic):
        # 实现搜索逻辑
        pass
    
    def _analyze(self, results):
        # 实现分析逻辑
        pass
    
    def _summarize(self, analysis):
        # 实现总结逻辑
        pass

# 使用
agent = ResearchAgent()
result = agent.research('AI Agent architectures')
print(result['summary'])
```

---

**生成时间**: 2026-03-27 23:10 GMT+8
