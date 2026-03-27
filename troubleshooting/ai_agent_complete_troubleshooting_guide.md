# AI Agent 完整故障排查手册

> **版本**: v1.0
> **更新时间**: 2026-03-27 16:44
> **故障类型**: 50+

---

## 🚨 故障分类

### 1. API 相关故障

#### 1.1 API Key 无效

**症状**:
```
Error: Invalid API key provided
```

**原因**:
- API Key 错误
- API Key 过期
- API Key 权限不足

**解决方案**:
```python
# 1. 检查 API Key
import os
api_key = os.getenv("OPENAI_API_KEY")
print(f"API Key: {api_key[:10]}...")  # 只打印前 10 位

# 2. 验证 API Key
import openai
openai.api_key = api_key

try:
    openai.Model.list()
    print("API Key 有效")
except Exception as e:
    print(f"API Key 无效: {e}")

# 3. 更新 API Key
# 登录 OpenAI 平台重新生成
```

---

#### 1.2 API 限流

**症状**:
```
Error: Rate limit exceeded
```

**原因**:
- 请求过快
- 超过配额

**解决方案**:
```python
# 1. 添加重试机制
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def call_api(prompt):
    return openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

# 2. 添加速率限制
import time
from functools import wraps

def rate_limit(calls_per_minute=60):
    min_interval = 60.0 / calls_per_minute
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left = min_interval - elapsed
            
            if left > 0:
                time.sleep(left)
            
            last_called[0] = time.time()
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

@rate_limit(calls_per_minute=50)
def safe_call(prompt):
    return call_api(prompt)
```

---

#### 1.3 超时错误

**症状**:
```
Error: Request timeout
```

**原因**:
- 网络慢
- 模型响应慢
- 请求过大

**解决方案**:
```python
# 1. 增加超时时间
import requests

response = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Hello"}]
    },
    timeout=30  # 30 秒超时
)

# 2. 添加超时重试
@retry(stop=stop_after_attempt(3))
def call_with_timeout(prompt, timeout=30):
    try:
        return call_api(prompt, timeout=timeout)
    except requests.Timeout:
        print("请求超时，正在重试...")
        raise
```

---

### 2. Token 相关故障

#### 2.1 Token 超限

**症状**:
```
Error: This model's maximum context length is 8192 tokens
```

**原因**:
- 输入过长
- 历史记录过多

**解决方案**:
```python
# 1. 计算 Token 数
import tiktoken

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """计算 Token 数"""
    encoder = tiktoken.encoding_for_model(model)
    return len(encoder.encode(text))

# 2. 截断文本
def truncate_text(text: str, max_tokens: int = 7000) -> str:
    """截断文本到指定 Token 数"""
    encoder = tiktoken.encoding_for_model("gpt-4")
    tokens = encoder.encode(text)
    
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
        text = encoder.decode(tokens)
    
    return text

# 3. 分段处理
def split_long_text(text: str, max_tokens: int = 3000) -> List[str]:
    """分段处理长文本"""
    encoder = tiktoken.encoding_for_model("gpt-4")
    tokens = encoder.encode(text)
    
    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i+max_tokens]
        chunk_text = encoder.decode(chunk_tokens)
        chunks.append(chunk_text)
    
    return chunks
```

---

#### 2.2 Token 成本过高

**症状**:
- 账单快速增长
- 超出预算

**原因**:
- 模型选择不当
- 请求过于频繁
- 未使用缓存

**解决方案**:
```python
# 1. 使用缓存
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_call(prompt: str) -> str:
    """缓存 LLM 调用"""
    return call_api(prompt)

# 2. 选择更便宜的模型
def smart_model_selection(prompt: str) -> str:
    """智能模型选择"""
    token_count = count_tokens(prompt)
    
    if token_count < 500:
        model = "gpt-3.5-turbo"  # 便宜
    else:
        model = "gpt-4"  # 强大
    
    return call_api(prompt, model=model)

# 3. 设置成本警告
def cost_monitor(func):
    """成本监控装饰器"""
    total_cost = [0.0]
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        # 计算成本
        cost = calculate_cost(result)
        total_cost[0] += cost
        
        # 警告
        if total_cost[0] > 100:  # 超过 $100
            print(f"⚠️ 成本警告: ${total_cost[0]:.2f}")
        
        return result
    
    return wrapper
```

---

### 3. 网络相关故障

#### 3.1 连接失败

**症状**:
```
Error: Connection refused
```

**原因**:
- 服务未启动
- 防火墙阻止
- DNS 解析失败

**解决方案**:
```python
# 1. 检查服务状态
import socket

def check_connection(host: str, port: int) -> bool:
    """检查连接"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        return result == 0
    except Exception as e:
        print(f"连接失败: {e}")
        return False

# 2. 添加连接池
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_session():
    """创建连接池会话"""
    session = requests.Session()
    
    # 重试策略
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )
    
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session
```

---

### 4. 数据库相关故障

#### 4.1 连接失败

**症状**:
```
Error: Could not connect to database
```

**原因**:
- 数据库未启动
- 连接字符串错误
- 权限不足

**解决方案**:
```python
# 1. 测试数据库连接
async def test_db_connection(connection_string: str) -> bool:
    """测试数据库连接"""
    try:
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return False

# 2. 添加连接池
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    connection_string,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True  # 检查连接是否有效
)
```

---

### 5. 内存相关故障

#### 5.1 内存溢出

**症状**:
```
Error: Out of memory
```

**原因**:
- 加载大数据
- 内存泄漏
- 未释放资源

**解决方案**:
```python
# 1. 监控内存
import psutil

def monitor_memory():
    """监控内存使用"""
    process = psutil.Process()
    memory_info = process.memory_info()
    
    print(f"内存使用: {memory_info.rss / 1024 / 1024:.2f} MB")
    
    if memory_info.rss > 1024 * 1024 * 1024:  # 1GB
        print("⚠️ 内存使用过高")

# 2. 释放资源
def process_large_file(file_path: str):
    """处理大文件"""
    with open(file_path, 'r') as f:
        for line in f:
            # 逐行处理
            process_line(line)
            # 不保存所有行在内存中
```

---

## 📊 故障排查流程

```
1. 确认故障症状
   ↓
2. 查看错误日志
   ↓
3. 分析可能原因
   ↓
4. 尝试解决方案
   ↓
5. 验证修复效果
   ↓
6. 记录解决方案
```

---

## 🔍 调试工具

```python
# 1. 日志记录
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 2. 性能分析
import cProfile

cProfile.run('agent.run("test")')

# 3. 内存追踪
import tracemalloc

tracemalloc.start()

# ... 运行代码 ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)
```

---

## 📝 故障预防

1. ✅ 添加错误处理
2. ✅ 实现重试机制
3. ✅ 设置超时时间
4. ✅ 监控资源使用
5. ✅ 定期备份数据
6. ✅ 测试边界情况
7. ✅ 文档化常见问题
8. ✅ 建立故障恢复计划

---

**生成时间**: 2026-03-27 16:46 GMT+8
