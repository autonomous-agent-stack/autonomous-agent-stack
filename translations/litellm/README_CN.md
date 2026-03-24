<h1 align="center">
        🚅 LiteLLM 中文版
    </h1>
    <p align="center">
        <p align="center">以 OpenAI 格式调用 100+ 个大语言模型。[Bedrock, Azure, OpenAI, VertexAI, Anthropic, Groq 等]
        </p>
    </p>

<h4 align="center">
    <a href="https://docs.litellm.ai/docs/simple_proxy" target="_blank">LiteLLM 代理服务器（AI 网关）</a> | 
    <a href="https://docs.litellm.ai/docs/enterprise#hosted-litellm-proxy" target="_blank">托管代理</a> | 
    <a href="https://docs.litellm.ai/docs/enterprise"target="_blank">企业版</a>
</h4>

<h4 align="center">
    <a href="https://pypi.org/project/litellm/" target="_blank">
        <img src="https://img.shields.io/pypi/v/litellm.svg" alt="PyPI 版本">
    </a>
    <a href="https://www.ycombinator.com/companies/berriai">
        <img src="https://img.shields.io/badge/Y%20Combinator-W23-orange?style=flat-square" alt="Y Combinator W23">
    </a>
    <a href="https://wa.link/huol9n">
        <img src="https://img.shields.io/static/v1?label=Chat%20on&message=WhatsApp&color=success&logo=WhatsApp&style=flat-square" alt="Whatsapp">
    </a>
    <a href="https://discord.gg/wuPM9dRgDw">
        <img src="https://img.shields.io/static/v1?label=Chat%20on&message=Discord&color=blue&logo=Discord&style=flat-square" alt="Discord">
    </a>
    <a href="https://www.litellm.ai/support">
        <img src="https://img.shields.io/static/v1?label=Chat%20on&message=Slack&color=black&logo=Slack&style=flat-square" alt="Slack">
    </a>
</h4>

---

## 📖 简介

**LiteLLM** 是一个统一的接口，让您可以用 OpenAI 的格式调用 100+ 个大语言模型（LLM），包括：
- **AWS Bedrock**
- **Azure OpenAI**
- **OpenAI**
- **Google VertexAI**
- **Anthropic Claude**
- **Groq**
- **更多模型...**

### 🎯 核心特性

1. **统一接口** - 所有模型都使用 OpenAI 格式
2. **代理服务器** - 提供 AI 网关功能
3. **100+ 模型** - 支持主流 LLM 提供商
4. **高性能** - 8ms P95 延迟（1k RPS）

---

## 🚀 快速开始

### 方式 1: Python SDK

#### 安装

```bash
pip install litellm
```

#### 基础使用

```python
from litellm import completion
import os

# 设置 API Keys
os.environ["OPENAI_API_KEY"] = "your-openai-key"
os.environ["ANTHROPIC_API_KEY"] = "your-anthropic-key"

# 调用 OpenAI
response = completion(
    model="openai/gpt-4o", 
    messages=[{"role": "user", "content": "你好！"}]
)

# 调用 Anthropic Claude
response = completion(
    model="anthropic/claude-sonnet-4-20250514", 
    messages=[{"role": "user", "content": "你好！"}]
)
```

---

### 方式 2: AI 网关（代理服务器）

#### 启动代理

```bash
# 安装代理依赖
pip install 'litellm[proxy]'

# 启动代理服务器
litellm --model gpt-4o
```

#### 使用代理

```python
import openai

# 连接到 LiteLLM 代理
client = openai.OpenAI(
    api_key="anything",  # 任意值
    base_url="http://0.0.0.0:4000"
)

# 调用模型
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "你好！"}]
)
```

---

## 🎨 使用场景

### 1. LLMs - 调用 100+ 个模型

**支持的所有端点**：
- `/chat/completions` - 聊天补全
- `/embeddings` - 文本嵌入
- `/images` - 图像生成
- `/audio` - 音频转写
- `/batches` - 批量处理
- `/rerank` - 重排序
- `/messages` - 消息端点

**Python SDK 示例**:

```python
from litellm import completion
import os

os.environ["OPENAI_API_KEY"] = "your-openai-key"
os.environ["ANTHROPIC_API_KEY"] = "your-anthropic-key"

# OpenAI
response = completion(
    model="openai/gpt-4o", 
    messages=[{"role": "user", "content": "Hello!"}]
)

# Anthropic  
response = completion(
    model="anthropic/claude-sonnet-4-20250514", 
    messages=[{"role": "user", "content": "Hello!"}]
)
```

---

### 2. Agents - 调用 A2A Agents

**支持的提供商**: LangGraph, Vertex AI Agent Engine, Azure AI Foundry, Bedrock AgentCore, Pydantic AI

**Python SDK - A2A 协议**:

```python
from litellm.a2a_protocol import A2AClient
from a2a.types import SendMessageRequest, MessageSendParams
from uuid import uuid4

client = A2AClient(base_url="http://localhost:10001")

request = SendMessageRequest(
    id=str(uuid4()),
    params=MessageSendParams(
        message={
            "role": "user",
            "parts": [{"kind": "text", "text": "Hello!"}],
            "messageId": uuid4().hex,
        }
    )
)
response = await client.send_message(request)
```

---

### 3. MCP Tools - 连接 MCP 服务器

**Python SDK - MCP 桥接**:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from litellm import experimental_mcp_client
import litellm

server_params = StdioServerParameters(
    command="python", 
    args=["mcp_server.py"]
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()

        # 加载 MCP 工具（OpenAI 格式）
        tools = await experimental_mcp_client.load_mcp_tools(
            session=session, 
            format="openai"
        )

        # 使用任意 LiteLLM 模型
        response = await litellm.acompletion(
            model="gpt-4o",
            messages=[{"role": "user", "content": "3 + 5 等于多少？"}],
            tools=tools
        )
```

---

## 📚 LiteLLM 使用方式对比

| 特性 | **LiteLLM AI 网关** | **LiteLLM Python SDK** |
|------|-------------------|---------------------|
| **使用场景** | 中心化服务（LLM 网关）访问多个模型 | 直接在 Python 代码中使用 LiteLLM |
| **适用人群** | AI 平台团队 / ML 平台团队 | 构建 LLM 项目的开发者 |
| **核心功能** | • 中心化 API 网关<br>• 认证和授权<br>• 多租户成本跟踪<br>• 虚拟密钥<br>• 管理界面 UI | • 直接集成 Python 库<br>• 路由器（重试/降级）<br>• 负载均衡<br>• 异常处理<br>• 可观测性回调 |

**性能**: 在 1k RPS 下 **8ms P95 延迟**

---

## 🏢 开源采用者

使用 LiteLLM 的公司：
- **Stripe**
- **Google ADK**
- **Netflix**
- **OpenHands**
- **OpenAI Agents SDK**
- 更多...

---

## 🌐 支持的提供商

### 主要提供商

| 提供商 | 聊天补全 | 消息 | 嵌入 | 图像生成 | 音频转写 | 音频生成 | 批处理 | 重排序 |
|--------|---------|------|------|---------|---------|---------|--------|--------|
| **OpenAI** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |
| **Anthropic** | ✅ | ✅ |  |  |  |  | ✅ |  |
| **Azure OpenAI** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |  |
| **AWS Bedrock** | ✅ | ✅ | ✅ |  |  |  |  | ✅ |
| **Google VertexAI** | ✅ | ✅ | ✅ |  |  |  |  |  |
| **Groq** | ✅ | ✅ |  |  |  |  |  |  |
| **Cohere** | ✅ | ✅ | ✅ |  |  |  |  | ✅ |
| **Hugging Face** | ✅ | ✅ | ✅ |  |  |  |  |  |
| **AI21** | ✅ | ✅ |  |  |  |  |  |  |
| **更多...** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**完整列表**: https://models.litellm.ai/

---

## 💡 核心优势

### 1. 统一接口

```python
# 所有模型使用相同的接口
from litellm import completion

# OpenAI
response = completion(model="openai/gpt-4o", messages=[...])

# Anthropic
response = completion(model="anthropic/claude-sonnet-4-20250514", messages=[...])

# Azure
response = completion(model="azure/gpt-4o", messages=[...])

# AWS Bedrock
response = completion(model="bedrock/anthropic.claude-3-sonnet", messages=[...])
```

### 2. 成本跟踪

```python
# 自动跟踪每个请求的成本
response = completion(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}]
)

print(response._hidden_params["response_cost"])  # 输出成本
```

### 3. 降级和重试

```python
from litellm import Router

# 配置多个模型
model_list = [
    {"model_name": "gpt-4", "litellm_params": {"model": "openai/gpt-4o"}},
    {"model_name": "gpt-4", "litellm_params": {"model": "azure/gpt-4o"}},
]

router = Router(model_list=model_list)

# 自动降级
response = router.completion(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)
```

---

## 🔧 高级功能

### 1. 流式输出

```python
from litellm import completion

response = completion(
    model="gpt-4o",
    messages=[{"role": "user", "content": "写一首诗"}],
    stream=True
)

for chunk in response:
    print(chunk.choices[0].delta.content, end="")
```

### 2. 工具调用

```python
from litellm import completion

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "城市名称"}
                }
            }
        }
    }
]

response = completion(
    model="gpt-4o",
    messages=[{"role": "user", "content": "北京今天天气如何？"}],
    tools=tools
)
```

### 3. 异步调用

```python
import litellm

# 异步调用
response = await litellm.acompletion(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}]
)
```

---

## 📖 文档资源

### 官方文档
- **主页**: https://docs.litellm.ai/
- **代理服务器**: https://docs.litellm.ai/docs/simple_proxy
- **提供商列表**: https://docs.litellm.ai/docs/providers
- **企业版**: https://docs.litellm.ai/docs/enterprise

### 社区
- **Discord**: https://discord.gg/wuPM9dRgDw
- **Slack**: https://www.litellm.ai/support
- **WhatsApp**: https://wa.link/huol9n
- **GitHub Issues**: https://github.com/BerriAI/litellm/issues

---

## 🚀 部署选项

### 1. Docker

```bash
docker run -d \
  -p 4000:4000 \
  -e OPENAI_API_KEY=your-key \
  ghcr.io/berriai/litellm:main-latest
```

### 2. Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/BerriAI/litellm)

### 3. Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/HLP0Ub?referralCode=jch2ME)

---

## 📊 性能基准

**测试条件**:
- 并发: 1000 RPS
- P95 延迟: **8ms**
- 模型: GPT-4o

**详细基准**: https://docs.litellm.ai/docs/benchmarks

---

## 🤝 贡献

欢迎贡献！请查看 [贡献指南](https://github.com/BerriAI/litellm/blob/main/CONTRIBUTING.md)

---

## 📄 许可证

MIT License

---

## 🙏 致谢

感谢所有贡献者和采用者！

特别感谢：
- **Y Combinator** (W23)
- **所有开源贡献者**
- **企业用户**

---

## 📮 联系方式

- **官网**: https://litellm.ai
- **邮箱**: krrish@berri.ai
- **Twitter**: [@LiteLLM](https://twitter.com/LiteLLM)

---

<div align="center">

**用 ❤️ 制作 | LiteLLM 团队**

**中文翻译**: OpenClaw Agent (2026-03-24)

</div>
