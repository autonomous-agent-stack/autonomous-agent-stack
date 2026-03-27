# LangChain 配置模板

from langchain.agents import AgentExecutor
from langchain.chat_models import ChatOpenAI, ChatAnthropic
from langchain.tools import Tool
from langchain.memory import ConversationBufferMemory
from pydantic import BaseModel

class LangChainConfig(BaseModel):
    """LangChain 配置"""
    
    # 模型配置
    model_provider: str = "anthropic"  # openai | anthropic
    model_name: str = "claude-3-opus-20240229"
    temperature: float = 0.7
    max_tokens: int = 4096
    
    # Agent 配置
    agent_type: str = "react"  # react | plan-and-execute | openai-functions
    max_iterations: int = 10
    verbose: bool = True
    
    # 记忆配置
    memory_type: str = "buffer"  # buffer | window | summary
    memory_window: int = 5
    
    # 工具配置
    tools: list = [
        "search_web",
        "calculator",
        "read_file",
        "write_file"
    ]
    
    # 性能配置
    timeout: int = 60  # seconds
    retry_attempts: int = 3

# 配置实例
config = LangChainConfig()

# 创建 LLM
if config.model_provider == "anthropic":
    llm = ChatAnthropic(
        model=config.model_name,
        temperature=config.temperature,
        max_tokens=config.max_tokens
    )
else:
    llm = ChatOpenAI(
        model=config.model_name,
        temperature=config.temperature
    )

# 创建记忆
if config.memory_type == "buffer":
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )

# 创建 Agent
from langchain.agents import initialize_agent

agent = initialize_agent(
    tools=[],  # 添加工具
    llm=llm,
    agent=config.agent_type,
    memory=memory,
    verbose=config.verbose,
    max_iterations=config.max_iterations
)

# 运行 Agent
if __name__ == "__main__":
    result = agent.run("你好，请介绍一下自己")
    print(result)
