# AI Agent 完整 API 参考文档

> **版本**: v1.0
> **更新时间**: 2026-03-27 22:20
> **端点数**: 50+

---

## 📚 API 概览

### 基础信息
- **Base URL**: `https://api.aiagent.com/v1`
- **协议**: HTTPS
- **格式**: JSON
- **认证**: Bearer Token

---

## 🔑 认证

### 获取 Token
```http
POST /auth/token
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password123"
}
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

---

### 使用 Token
```http
GET /agents
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 🤖 Agent 端点

### 创建 Agent
```http
POST /agents
Content-Type: application/json
Authorization: Bearer {token}

{
  "name": "Customer Service Agent",
  "model": "gpt-4",
  "tools": ["search", "calculator", "database"],
  "memory": {
    "type": "conversation",
    "max_tokens": 4000
  },
  "config": {
    "temperature": 0.7,
    "max_tokens": 2000
  }
}
```

**响应**:
```json
{
  "id": "agent_abc123",
  "name": "Customer Service Agent",
  "model": "gpt-4",
  "tools": ["search", "calculator", "database"],
  "memory": {
    "type": "conversation",
    "max_tokens": 4000
  },
  "config": {
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "created_at": "2026-03-27T22:20:00Z",
  "status": "active"
}
```

---

### 列出所有 Agent
```http
GET /agents?page=1&limit=20
Authorization: Bearer {token}
```

**响应**:
```json
{
  "agents": [
    {
      "id": "agent_abc123",
      "name": "Customer Service Agent",
      "model": "gpt-4",
      "status": "active"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20
}
```

---

### 获取 Agent 详情
```http
GET /agents/{agent_id}
Authorization: Bearer {token}
```

**响应**:
```json
{
  "id": "agent_abc123",
  "name": "Customer Service Agent",
  "model": "gpt-4",
  "tools": ["search", "calculator", "database"],
  "memory": {
    "type": "conversation",
    "max_tokens": 4000
  },
  "config": {
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "created_at": "2026-03-27T22:20:00Z",
  "updated_at": "2026-03-27T22:25:00Z",
  "status": "active",
  "usage": {
    "total_requests": 1000,
    "total_tokens": 500000
  }
}
```

---

### 更新 Agent
```http
PATCH /agents/{agent_id}
Content-Type: application/json
Authorization: Bearer {token}

{
  "name": "Updated Agent Name",
  "config": {
    "temperature": 0.8
  }
}
```

---

### 删除 Agent
```http
DELETE /agents/{agent_id}
Authorization: Bearer {token}
```

**响应**:
```json
{
  "message": "Agent deleted successfully",
  "id": "agent_abc123"
}
```

---

## 💬 对话端点

### 创建对话
```http
POST /conversations
Content-Type: application/json
Authorization: Bearer {token}

{
  "agent_id": "agent_abc123",
  "context": {
    "user_id": "user123",
    "session_id": "session456"
  }
}
```

**响应**:
```json
{
  "id": "conv_xyz789",
  "agent_id": "agent_abc123",
  "context": {
    "user_id": "user123",
    "session_id": "session456"
  },
  "created_at": "2026-03-27T22:30:00Z",
  "status": "active"
}
```

---

### 发送消息
```http
POST /conversations/{conversation_id}/messages
Content-Type: application/json
Authorization: Bearer {token}

{
  "content": "What is the weather today?",
  "metadata": {
    "source": "web"
  }
}
```

**响应**:
```json
{
  "id": "msg_qwe456",
  "conversation_id": "conv_xyz789",
  "role": "assistant",
  "content": "The weather today is sunny with a high of 25°C.",
  "tool_calls": [
    {
      "tool": "weather",
      "arguments": {
        "location": "Beijing"
      },
      "result": {
        "temperature": 25,
        "condition": "sunny"
      }
    }
  ],
  "created_at": "2026-03-27T22:31:00Z",
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 15,
    "total_tokens": 25
  }
}
```

---

### 获取对话历史
```http
GET /conversations/{conversation_id}/messages?page=1&limit=50
Authorization: Bearer {token}
```

**响应**:
```json
{
  "messages": [
    {
      "id": "msg_qwe456",
      "role": "user",
      "content": "What is the weather today?",
      "created_at": "2026-03-27T22:30:00Z"
    },
    {
      "id": "msg_qwe457",
      "role": "assistant",
      "content": "The weather today is sunny with a high of 25°C.",
      "created_at": "2026-03-27T22:31:00Z"
    }
  ],
  "total": 2,
  "page": 1,
  "limit": 50
}
```

---

## 🔧 工具端点

### 列出所有工具
```http
GET /tools
Authorization: Bearer {token}
```

**响应**:
```json
{
  "tools": [
    {
      "id": "tool_search",
      "name": "Web Search",
      "description": "Search the web for information",
      "parameters": {
        "query": {
          "type": "string",
          "description": "Search query"
        }
      }
    },
    {
      "id": "tool_calculator",
      "name": "Calculator",
      "description": "Perform mathematical calculations",
      "parameters": {
        "expression": {
          "type": "string",
          "description": "Mathematical expression"
        }
      }
    }
  ]
}
```

---

### 执行工具
```http
POST /tools/{tool_id}/execute
Content-Type: application/json
Authorization: Bearer {token}

{
  "parameters": {
    "query": "AI Agent frameworks 2026"
  }
}
```

**响应**:
```json
{
  "result": {
    "query": "AI Agent frameworks 2026",
    "results": [
      {
        "title": "Top 10 AI Agent Frameworks",
        "url": "https://example.com",
        "snippet": "..."
      }
    ]
  },
  "execution_time": 0.5
}
```

---

## 📊 分析端点

### 获取使用统计
```http
GET /analytics/usage?start_date=2026-03-01&end_date=2026-03-27
Authorization: Bearer {token}
```

**响应**:
```json
{
  "period": {
    "start_date": "2026-03-01",
    "end_date": "2026-03-27"
  },
  "usage": {
    "total_requests": 10000,
    "total_tokens": 5000000,
    "by_agent": [
      {
        "agent_id": "agent_abc123",
        "requests": 5000,
        "tokens": 2500000
      }
    ],
    "by_model": [
      {
        "model": "gpt-4",
        "requests": 3000,
        "tokens": 1500000
      },
      {
        "model": "gpt-3.5-turbo",
        "requests": 7000,
        "tokens": 3500000
      }
    ]
  },
  "costs": {
    "total": 150.50,
    "by_model": [
      {
        "model": "gpt-4",
        "cost": 120.00
      },
      {
        "model": "gpt-3.5-turbo",
        "cost": 30.50
      }
    ]
  }
}
```

---

### 获取性能指标
```http
GET /analytics/performance?period=7d
Authorization: Bearer {token}
```

**响应**:
```json
{
  "period": "7d",
  "metrics": {
    "response_time": {
      "p50": 0.5,
      "p95": 2.0,
      "p99": 5.0
    },
    "throughput": {
      "requests_per_second": 100,
      "peak_rps": 250
    },
    "errors": {
      "total": 50,
      "rate": 0.005
    },
    "availability": 99.95
  }
}
```

---

## 🚨 错误码

| 错误码 | 描述 | 解决方案 |
|--------|------|---------|
| **400** | Bad Request | 检查请求参数 |
| **401** | Unauthorized | 检查认证 Token |
| **403** | Forbidden | 检查权限 |
| **404** | Not Found | 检查资源 ID |
| **429** | Too Many Requests | 降低请求频率 |
| **500** | Internal Server Error | 联系支持 |
| **503** | Service Unavailable | 稍后重试 |

---

### 错误响应格式
```json
{
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "The 'temperature' parameter must be between 0 and 2",
    "details": {
      "parameter": "temperature",
      "value": 3.0,
      "allowed_range": [0, 2]
    }
  }
}
```

---

## 📝 速率限制

| 端点 | 限制 | 时间窗口 |
|------|------|---------|
| `/agents` | 100 次 | 1 分钟 |
| `/conversations` | 1000 次 | 1 分钟 |
| `/tools` | 500 次 | 1 分钟 |
| `/analytics` | 50 次 | 1 分钟 |

---

## 🔒 安全

### HTTPS
- 所有 API 调用必须使用 HTTPS
- 强制 TLS 1.3

### 认证
- Bearer Token 认证
- Token 有效期：1 小时
- 支持 Refresh Token

### 数据加密
- 传输加密（TLS 1.3）
- 存储加密（AES-256）

---

## 📚 SDK

### Python SDK
```python
from aiagent import Agent, Conversation

# 初始化
agent = Agent(api_key='your-api-key')

# 创建 Agent
my_agent = agent.create(
    name='My Agent',
    model='gpt-4',
    tools=['search']
)

# 发送消息
response = my_agent.chat('Hello!')
print(response.content)
```

### JavaScript SDK
```javascript
import { Agent } from '@aiagent/sdk';

const agent = new Agent({ apiKey: 'your-api-key' });

const myAgent = await agent.create({
  name: 'My Agent',
  model: 'gpt-4',
  tools: ['search']
});

const response = await myAgent.chat('Hello!');
console.log(response.content);
```

---

**生成时间**: 2026-03-27 22:25 GMT+8
