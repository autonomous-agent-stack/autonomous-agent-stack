# AI Agent 最佳实践总结

> **版本**: v1.0
> **更新时间**: 2026-03-27
> **实践数量**: 50+

---

## 🎯 核心原则

### 1. 简单优先（KISS）

**❌ 错误**:
```python
# 过度设计
class UltraComplexAgent:
    def __init__(self):
        self.sub_agents = [Agent() for _ in range(10)]
        self.orchestrator = Orchestrator()
        self.memory = MultiLayerMemory()
        self.optimizer = HyperOptimizer()
```

**✅ 正确**:
```python
# 简单直接
class SimpleAgent:
    def __init__(self, model: str):
        self.model = model
    
    def run(self, task: str) -> str:
        return self.llm.call(task)
```

### 2. 单一职责

**❌ 错误**:
```python
# 职责不清
class SuperAgent:
    def chat(self): pass
    def code(self): pass
    def search(self): pass
    def translate(self): pass
```

**✅ 正确**:
```python
# 职责明确
class CustomerServiceAgent:
    """只负责客服"""
    pass

class CodeReviewAgent:
    """只负责代码审查"""
    pass
```

### 3. 可测试性

**❌ 错误**:
```python
# 难以测试
def agent_run():
    result = llm.call(task)  # 依赖真实 LLM
    return result
```

**✅ 正确**:
```python
# 可测试
def agent_run(llm=RealLLM()):
    result = llm.call(task)
    return result

# 测试
def test_agent():
    mock_llm = MockLLM(return_value="test")
    result = agent_run(mock_llm)
    assert result == "test"
```

---

## 🛠️ 工具设计

### 1. 参数验证

**❌ 错误**:
```python
def search(query):
    # 没有验证
    return api.search(query)
```

**✅ 正确**:
```python
def search(query: str, limit: int = 10) -> List[Dict]:
    """搜索工具"""
    # 验证
    if not query or len(query) > 1000:
        raise ValueError("Invalid query")
    
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be 1-100")
    
    # 执行
    return api.search(query, limit)
```

### 2. 错误处理

**❌ 错误**:
```python
def call_api():
    response = requests.get(url)
    return response.json()  # 可能崩溃
```

**✅ 正确**:
```python
def call_api():
    """安全的 API 调用"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        return {"error": "请求超时"}
    except requests.HTTPError as e:
        return {"error": f"HTTP 错误: {e}"}
    except Exception as e:
        return {"error": f"未知错误: {e}"}
```

---

## 💾 记忆管理

### 1. 分层记忆

**❌ 错误**:
```python
# 只用短期记忆
class Agent:
    def __init__(self):
        self.history = []  # 无限增长
```

**✅ 正确**:
```python
# 分层记忆
class Agent:
    def __init__(self):
        self.short_term = deque(maxlen=10)  # 短期
        self.long_term = VectorDB()        # 长期
    
    def add_memory(self, message: str):
        # 短期记忆
        self.short_term.append(message)
        
        # 重要内容存入长期记忆
        if self._is_important(message):
            self.long_term.add(message)
```

### 2. 记忆检索

**❌ 错误**:
```python
# 简单字符串匹配
def get_context(query):
    return [m for m in memory if query in m]
```

**✅ 正确**:
```python
# 语义检索
def get_context(query: str) -> List[str]:
    """语义检索记忆"""
    # 使用向量检索
    results = self.long_term.search(
        query=query,
        n_results=5,
        min_distance=0.7
    )
    
    # 过滤低质量结果
    filtered = [
        r for r in results
        if r["distance"] < 0.7
    ]
    
    return filtered
```

---

## ⚡ 性能优化

### 1. 异步处理

**❌ 错误**:
```python
# 同步串行
def run_tasks(tasks):
    results = []
    for task in tasks:
        result = agent.run(task)
        results.append(result)
    return results
```

**✅ 正确**:
```python
# 异步并行
async def run_tasks(tasks):
    results = await asyncio.gather(
        *[agent.async_run(task) for task in tasks]
    )
    return results
```

### 2. 缓存机制

**❌ 错误**:
```python
# 无缓存
def query_llm(prompt):
    return llm.call(prompt)
```

**✅ 正确**:
```python
# 带缓存
@lru_cache(maxsize=1000)
def query_llm(prompt_hash: str, prompt: str):
    return llm.call(prompt)

def cached_query(prompt: str):
    hash_key = hashlib.md5(prompt.encode()).hexdigest()
    return query_llm(hash_key, prompt)
```

---

## 🔒 安全加固

### 1. 输入验证

**❌ 错误**:
```python
# 直接使用用户输入
def run(user_input):
    return llm.call(user_input)
```

**✅ 正确**:
```python
# 验证并清理
def run(user_input: str):
    # 长度检查
    if len(user_input) > 10000:
        raise ValueError("Input too long")
    
    # 危险模式检查
    dangerous = ["ignore previous", "system:"]
    for pattern in dangerous:
        if pattern in user_input.lower():
            raise ValueError("Dangerous input detected")
    
    # 清理
    safe_input = sanitize(user_input)
    
    return llm.call(safe_input)
```

### 2. 权限控制

**❌ 错误**:
```python
# 无权限检查
def execute_tool(tool_name, params):
    return tools[tool_name].execute(params)
```

**✅ 正确**:
```python
# 权限检查
def execute_tool(user_id: str, tool_name: str, params: dict):
    # 检查权限
    if not has_permission(user_id, tool_name):
        raise PermissionError(f"No permission for {tool_name}")
    
    # 审计日志
    log_tool_access(user_id, tool_name, params)
    
    # 执行
    return tools[tool_name].execute(params)
```

---

## 📊 监控告警

### 1. 关键指标

**✅ 必须监控**:
- 响应时间
- 成功率
- 错误率
- 成本
- Token 使用

### 2. 告警设置

**✅ 告警阈值**:
- 响应时间 > 5s
- 成功率 < 95%
- 错误率 > 5%
- 日成本 > $10
- CPU > 80%

---

## 🧪 测试策略

### 1. 单元测试

**✅ 必须测试**:
- 工具函数
- 记忆管理
- 意图识别
- 参数验证

### 2. 集成测试

**✅ 必须测试**:
- Agent 完整流程
- 工具调用链
- 记忆检索

### 3. E2E 测试

**✅ 必须测试**:
- 用户对话流程
- 错误恢复
- 性能压力

---

## 📝 文档规范

### 1. 代码文档

**✅ 好的文档**:
```python
def search(query: str, limit: int = 10) -> List[Dict]:
    """
    搜索工具
    
    Args:
        query: 搜索关键词（1-1000 字符）
        limit: 返回结果数量（1-100）
    
    Returns:
        搜索结果列表，每个结果包含:
        - title: 标题
        - url: 链接
        - snippet: 摘要
    
    Raises:
        ValueError: 参数无效
        NetworkError: 网络错误
    
    Example:
        >>> search("Python 教程", limit=5)
        [{"title": "...", "url": "...", "snippet": "..."}]
    """
```

### 2. API 文档

**✅ 好的 API 文档**:
```markdown
## POST /chat

与 Agent 对话

### 请求

```json
{
  "message": "你好",
  "context": {
    "user_id": "123"
  }
}
```

### 响应

```json
{
  "response": "你好！有什么可以帮您的吗？",
  "intent": "greeting",
  "confidence": 0.95
}
```

### 错误

| 状态码 | 说明 |
|--------|------|
| 400 | 参数错误 |
| 429 | 速率限制 |
| 500 | 服务器错误 |
```

---

## 🚀 部署最佳实践

### 1. 环境隔离

**✅ 推荐配置**:
- 开发环境: 本地
- 测试环境: Docker
- 生产环境: Kubernetes

### 2. 配置管理

**✅ 推荐方案**:
```yaml
# config.yaml
development:
  model: "claude-3-opus"
  cache: false
  
production:
  model: "glm-5"
  cache: true
  rate_limit: 100
```

### 3. 日志管理

**✅ 推荐方案**:
- 结构化日志（JSON）
- 日志级别: INFO/WARNING/ERROR
- 日志轮转
- 集中式存储

---

## 📚 学习资源

### 必读文档

1. **OpenAI Cookbook** - https://github.com/openai/openai-cookbook
2. **Anthropic Academy** - https://www.anthropic.com/academy
3. **LangChain Docs** - https://python.langchain.com
4. **OpenClaw Docs** - https://docs.openclaw.ai

### 推荐课程

1. **DeepLearning.AI** - AI Agent 课程
2. **FastAPI** - Web 框架
3. **Pytest** - 测试框架

---

## 🎯 Checklist

### 开发前

- [ ] 明确 Agent 职责
- [ ] 设计工具接口
- [ ] 规划记忆系统
- [ ] 制定测试计划

### 开发中

- [ ] 使用类型注解
- [ ] 编写单元测试
- [ ] 实现错误处理
- [ ] 添加日志监控

### 部署前

- [ ] 安全审计
- [ ] 性能测试
- [ ] 文档完善
- [ ] 配置管理

### 运行时

- [ ] 持续监控
- [ ] 定期优化
- [ ] 用户反馈
- [ ] 版本迭代

---

**生成时间**: 2026-03-27 13:50 GMT+8
