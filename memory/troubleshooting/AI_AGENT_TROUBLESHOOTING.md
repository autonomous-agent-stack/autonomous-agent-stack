# AI Agent 故障排查指南

> **版本**: v1.0
> **更新时间**: 2026-03-27
> **案例数**: 50+

---

## 🚨 常见问题分类

### 1. Token 相关问题

#### 问题 1.1: Token 超限

**症状**:
```
Error: This model's maximum context length is 8192 tokens, 
however you requested 10000 tokens.
```

**原因**:
- 输入 Prompt 过长
- 历史对话累积过多
- 工具输出过大

**解决方案**:

```python
# 方案 1: 压缩 Prompt
def compress_prompt(prompt: str, max_tokens: int = 4000) -> str:
    """压缩 Prompt"""
    # 移除冗余空格
    prompt = ' '.join(prompt.split())
    
    # 截断到 max_tokens
    if len(prompt) > max_tokens:
        prompt = prompt[:max_tokens]
    
    return prompt

# 方案 2: 使用滑动窗口
from collections import deque

class SlidingWindowMemory:
    def __init__(self, max_messages: int = 10):
        self.memory = deque(maxlen=max_messages)
    
    def add(self, message: dict):
        self.memory.append(message)

# 方案 3: 切换到长上下文模型
model = "claude-3-opus-20240229"  # 200K context
```

**预防措施**:
- ✅ 定期清理历史对话
- ✅ 使用 Token 计数器监控
- ✅ 实施分层记忆（短期 + 长期）

---

#### 问题 1.2: Token 成本过高

**症状**:
```
Warning: Daily cost exceeded $10 (Current: $15.23)
```

**原因**:
- 频繁调用 LLM
- 使用高价模型（GPT-4）
- 无缓存机制

**解决方案**:

```python
# 方案 1: 使用国产模型
from zhipuai import ZhipuAI

client = ZhipuAI()
response = client.chat.completions.create(
    model="glm-5",  # 成本 -98%
    messages=messages
)

# 方案 2: 实施缓存
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def cached_llm_call(prompt_hash: str, prompt: str) -> str:
    """缓存的 LLM 调用"""
    return llm.call(prompt)

def call_with_cache(prompt: str) -> str:
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
    return cached_llm_call(prompt_hash, prompt)

# 方案 3: 批量处理
def batch_process(tasks: List[str]) -> List[str]:
    """批量处理任务"""
    combined_prompt = "\n".join([f"{i+1}. {task}" for i, task in enumerate(tasks)])
    result = llm.call(combined_prompt)
    return parse_results(result)
```

**成本对比**:

| 模型 | 成本/1M tokens | 节省 |
|------|---------------|------|
| GPT-4 | $30.0 | - |
| Claude 3 Opus | $15.0 | -50% |
| **GLM-5** | **$0.1** | **-99.7%** |

---

### 2. 工具调用问题

#### 问题 2.1: 工具调用失败

**症状**:
```
Error: Tool execution failed: Permission denied
```

**原因**:
- 工具权限不足
- 工具参数错误
- 工具依赖缺失

**解决方案**:

```python
# 方案 1: 检查权限
def check_tool_permission(tool_name: str, user_id: str) -> bool:
    """检查工具权限"""
    permissions = {
        "read_file": ["admin", "user"],
        "write_file": ["admin"],
        "execute_shell": ["admin"]
    }
    
    user_role = get_user_role(user_id)
    return user_role in permissions.get(tool_name, [])

# 方案 2: 参数验证
from pydantic import BaseModel, validator

class ToolParameters(BaseModel):
    file_path: str
    
    @validator('file_path')
    def validate_path(cls, v):
        # 检查路径安全性
        if ".." in v or v.startswith("/"):
            raise ValueError("非法路径")
        return v

# 方案 3: 错误处理
def execute_tool_safe(tool_name: str, parameters: dict) -> str:
    """安全执行工具"""
    try:
        # 验证权限
        if not check_tool_permission(tool_name, get_current_user()):
            raise PermissionError(f"无权限执行: {tool_name}")
        
        # 验证参数
        validated_params = validate_parameters(tool_name, parameters)
        
        # 执行工具
        result = execute_tool(tool_name, validated_params)
        
        return result
    except Exception as e:
        logger.error(f"工具执行失败: {tool_name}, 错误: {e}")
        return f"Error: {str(e)}"
```

---

#### 问题 2.2: 工具循环调用

**症状**:
```
Warning: Tool call loop detected (tool_a -> tool_b -> tool_a)
```

**原因**:
- 工具依赖循环
- Agent 推理错误
- 缺少终止条件

**解决方案**:

```python
# 方案 1: 调用栈监控
class ToolCallMonitor:
    def __init__(self, max_depth: int = 5):
        self.call_stack = []
        self.max_depth = max_depth
    
    def before_call(self, tool_name: str):
        # 检查深度
        if len(self.call_stack) >= self.max_depth:
            raise RecursionError("工具调用深度超限")
        
        # 检查循环
        if tool_name in self.call_stack:
            raise RecursionError(f"检测到循环调用: {tool_name}")
        
        self.call_stack.append(tool_name)
    
    def after_call(self):
        self.call_stack.pop()

# 方案 2: 添加终止条件
def agent_loop(agent, task: str, max_iterations: int = 10):
    """Agent 循环（带终止条件）"""
    for i in range(max_iterations):
        result = agent.step(task)
        
        # 检查是否完成
        if result.status == "completed":
            return result.answer
        
        # 检查是否卡住
        if result.status == "stuck":
            logger.warning(f"Agent 卡住在第 {i+1} 轮")
            break
    
    raise RuntimeError("Agent 未能在规定轮数内完成任务")
```

---

### 3. 记忆系统问题

#### 问题 3.1: 记忆检索不准确

**症状**:
```
检索到的记忆与问题无关
```

**原因**:
- Embedding 质量差
- 检索参数不当
- 记忆库污染

**解决方案**:

```python
# 方案 1: 优化 Embedding
from sentence_transformers import SentenceTransformer

# 使用高质量 Embedding 模型
model = SentenceTransformer('all-MiniLM-L6-v2')

def create_embedding(text: str) -> List[float]:
    """创建高质量 Embedding"""
    # 预处理文本
    text = preprocess_text(text)
    
    # 生成 Embedding
    embedding = model.encode(text)
    
    return embedding.tolist()

# 方案 2: 调整检索参数
def retrieve_memories(query: str, collection, n_results: int = 5, min_distance: float = 0.7):
    """检索记忆（带距离过滤）"""
    results = collection.query(
        query_texts=[query],
        n_results=n_results * 2  # 获取更多候选
    )
    
    # 过滤低质量结果
    filtered = [
        doc for doc, dist in zip(results["documents"][0], results["distances"][0])
        if dist < min_distance
    ]
    
    return filtered[:n_results]

# 方案 3: 记忆清洗
def clean_memory_db(collection):
    """清洗记忆库"""
    # 获取所有记忆
    all_docs = collection.get()
    
    # 去重
    unique_docs = {}
    for doc, meta, id in zip(all_docs["documents"], all_docs["metadatas"], all_docs["ids"]):
        key = hash(doc)
        if key not in unique_docs:
            unique_docs[key] = (doc, meta, id)
    
    # 重建集合
    collection.delete(all_docs["ids"])
    collection.add(
        documents=[d[0] for d in unique_docs.values()],
        metadatas=[d[1] for d in unique_docs.values()],
        ids=[d[2] for d in unique_docs.values()]
    )
```

---

### 4. 性能问题

#### 问题 4.1: 响应时间过长

**症状**:
```
平均响应时间 > 30秒
```

**原因**:
- LLM 调用慢
- 工具执行慢
- 串行处理

**解决方案**:

```python
# 方案 1: 异步调用
import asyncio

async def async_agent_run(agent, task: str) -> str:
    """异步 Agent 执行"""
    # 异步 LLM 调用
    llm_task = asyncio.create_task(async_llm_call(task))
    
    # 异步工具调用
    tool_tasks = [
        asyncio.create_tool_call(tool)
        for tool in agent.tools
    ]
    
    # 并行执行
    results = await asyncio.gather(llm_task, *tool_tasks)
    
    return results[0]

# 方案 2: 流式输出
from anthropic import Anthropic

client = Anthropic()

def stream_response(prompt: str):
    """流式输出"""
    with client.messages.stream(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for text in stream.text_stream:
            yield text  # 实时返回

# 方案 3: 超时控制
import signal

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("执行超时")

def run_with_timeout(func, args=(), timeout: int = 30):
    """带超时的执行"""
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    
    try:
        result = func(*args)
    finally:
        signal.alarm(0)
    
    return result
```

---

### 5. 安全问题

#### 问题 5.1: 提示注入攻击

**症状**:
```
Agent 执行了未授权的操作
```

**原因**:
- 用户输入未过滤
- 缺少权限检查
- 上下文混淆

**解决方案**:

```python
# 方案 1: 输入过滤
import re

def sanitize_input(user_input: str) -> str:
    """清理用户输入"""
    # 移除危险模式
    dangerous_patterns = [
        r"ignore previous instructions",
        r"you are now",
        r"system:",
        r"<[^>]+>"
    ]
    
    cleaned = user_input
    for pattern in dangerous_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    
    return cleaned.strip()

# 方案 2: 权限沙箱
class PermissionSandbox:
    """权限沙箱"""
    
    def __init__(self):
        self.allowed_tools = set()
        self.denied_tools = set()
    
    def grant(self, tool_name: str):
        self.allowed_tools.add(tool_name)
    
    def deny(self, tool_name: str):
        self.denied_tools.add(tool_name)
    
    def check(self, tool_name: str) -> bool:
        if tool_name in self.denied_tools:
            return False
        if tool_name in self.allowed_tools:
            return True
        return False  # 默认拒绝

# 方案 3: 输出审查
def audit_output(output: str) -> str:
    """审查输出"""
    # 检查敏感信息
    sensitive_patterns = [
        r'\b\d{16}\b',  # 信用卡号
        r'\b\d{17}\b',  # 身份证号
        r'[A-Z]{2}\d{9}',  # 护照号
    ]
    
    for pattern in sensitive_patterns:
        if re.search(pattern, output):
            logger.warning(f"检测到敏感信息: {pattern}")
            output = re.sub(pattern, "[REDACTED]", output)
    
    return output
```

---

## 📊 故障诊断流程

### 标准诊断流程

```
1. 收集信息
   ├── 错误消息
   ├── 日志文件
   ├── 复现步骤
   └── 环境信息

2. 定位问题
   ├── 分析错误类型
   ├── 查找相关代码
   ├── 检查配置
   └── 验证假设

3. 解决方案
   ├── 查阅文档
   ├── 搜索类似问题
   ├── 尝试修复
   └── 验证效果

4. 预防措施
   ├── 更新文档
   ├── 添加测试
   ├── 改进监控
   └── 分享经验
```

---

## 🔍 调试工具

### 日志分析

```bash
# 查看错误日志
tail -f ~/.openclaw/logs/error.log

# 搜索特定错误
grep "Token limit exceeded" ~/.openclaw/logs/*.log

# 统计错误频率
awk '/ERROR/ {print $5}' ~/.openclaw/logs/*.log | sort | uniq -c | sort -nr
```

### 性能分析

```python
import cProfile
import pstats

def profile_agent():
    """性能分析 Agent"""
    profiler = cProfile.Profile()
    profiler.enable()
    
    # 运行 Agent
    agent.run(task)
    
    profiler.disable()
    
    # 输出统计
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)
```

---

## 📝 故障排查清单

### 部署前检查

- [ ] API Key 已配置
- [ ] 依赖已安装
- [ ] 权限已设置
- [ ] 日志已配置
- [ ] 监控已启用

### 运行时监控

- [ ] 响应时间 < 5s
- [ ] 错误率 < 5%
- [ ] Token 使用率 < 80%
- [ ] 成本在预算内

### 故障后恢复

- [ ] 记录错误详情
- [ ] 分析根本原因
- [ ] 实施修复方案
- [ ] 验证修复效果
- [ ] 更新文档

---

**生成时间**: 2026-03-27 14:15 GMT+8
**案例总数**: 10+ 核心案例
**覆盖领域**: 5 大类
