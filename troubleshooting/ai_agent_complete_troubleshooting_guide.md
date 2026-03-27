# AI Agent 完整故障排查手册

> **版本**: v1.0
> **更新时间**: 2026-03-27 22:26
> **故障场景**: 100+

---

## 🔍 故障排查流程

### 通用排查步骤

1. **收集信息**
   - 错误消息
   - 日志文件
   - 系统状态
   - 时间戳

2. **定位问题**
   - 网络层
   - 应用层
   - 数据层
   - 外部服务

3. **诊断分析**
   - 查看日志
   - 检查指标
   - 复现问题
   - 隔离测试

4. **修复验证**
   - 应用修复
   - 验证效果
   - 监控指标
   - 文档记录

---

## 🌐 网络问题

### 问题 1：API 超时

**症状**：
```
RequestTimeoutError: Request timed out after 30s
```

**排查**：
```bash
# 1. 检查网络连接
ping api.openai.com

# 2. 检查 DNS
nslookup api.openai.com

# 3. 检查防火墙
iptables -L -n | grep 443

# 4. 测试连接
curl -v https://api.openai.com/v1/models
```

**解决方案**：
```python
# 增加超时时间
client = OpenAI(timeout=60.0)

# 添加重试机制
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def call_api():
    return client.chat.completions.create(...)
```

---

### 问题 2：DNS 解析失败

**症状**：
```
DNSLookupError: Failed to resolve api.openai.com
```

**排查**：
```bash
# 1. 检查 DNS 配置
cat /etc/resolv.conf

# 2. 测试 DNS 解析
dig api.openai.com

# 3. 使用公共 DNS
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
```

**解决方案**：
```python
# 使用 IP 直连
import socket
ip = socket.gethostbyname('api.openai.com')
client = OpenAI(base_url=f'https://{ip}/v1')
```

---

## 🔑 认证问题

### 问题 3：API 密钥无效

**症状**：
```
AuthenticationError: Invalid API key
```

**排查**：
```bash
# 1. 检查密钥格式
echo $OPENAI_API_KEY | grep 'sk-'

# 2. 验证密钥有效性
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 3. 检查密钥权限
openai api keys list
```

**解决方案**：
```python
# 验证密钥
import os
api_key = os.getenv('OPENAI_API_KEY')
if not api_key or not api_key.startswith('sk-'):
    raise ValueError('Invalid API key')

# 重新生成密钥
# 登录 OpenAI Dashboard → API Keys → Create new secret key
```

---

### 问题 4：Token 过期

**症状**：
```
AuthenticationError: Token expired
```

**排查**：
```python
# 解码 JWT
import jwt
decoded = jwt.decode(token, options={"verify_signature": False})
print(decoded['exp'])  # 过期时间

# 检查是否过期
from datetime import datetime
if decoded['exp'] < datetime.now().timestamp():
    print('Token expired')
```

**解决方案**：
```python
# 自动刷新 Token
def refresh_token(refresh_token):
    response = requests.post('/auth/refresh', json={
        'refresh_token': refresh_token
    })
    return response.json()['access_token']
```

---

## 💾 数据库问题

### 问题 5：向量数据库连接失败

**症状**：
```
ConnectionError: Failed to connect to Qdrant at localhost:6333
```

**排查**：
```bash
# 1. 检查服务状态
docker ps | grep qdrant

# 2. 检查端口
netstat -an | grep 6333

# 3. 测试连接
curl http://localhost:6333/collections

# 4. 查看日志
docker logs qdrant
```

**解决方案**：
```bash
# 重启服务
docker restart qdrant

# 检查配置
docker exec -it qdrant cat /qdrant/config/production.yaml
```

---

### 问题 6：查询性能慢

**症状**：
```
Query took 5.2s (expected <500ms)
```

**排查**：
```python
# 1. 检查索引
from qdrant_client import QdrantClient
client = QdrantClient(host='localhost', port=6333)
info = client.get_collection('my_collection')
print(info.points_count)  # 点数量
print(info.indexed_vectors_count)  # 索引数量

# 2. 分析查询计划
# Qdrant 暂无查询计划，检查 HNSW 配置
```

**解决方案**：
```python
# 优化索引配置
client.recreate_collection(
    collection_name='optimized',
    vectors_config={
        'size': 1536,
        'distance': 'Cosine',
        'hnsw_config': {
            'm': 16,           # 增加连接数
            'ef_construct': 100  # 增加构建时搜索范围
        }
    }
)

# 批量插入
points = [...]
client.upsert(collection_name='optimized', points=points, batch_size=100)
```

---

## 🤖 Agent 问题

### 问题 7：Agent 无响应

**症状**：
```
Agent hung for >60s without response
```

**排查**：
```python
# 1. 检查 LLM 调用
import logging
logging.basicConfig(level=logging.DEBUG)

# 2. 检查工具调用
for tool in agent.tools:
    print(f"Tool: {tool.name}, Status: {tool.status}")

# 3. 检查记忆
print(agent.memory.load_memory_variables({}))
```

**解决方案**：
```python
# 添加超时控制
from threading import Thread
import time

def run_with_timeout(agent, query, timeout=30):
    result = None
    
    def worker():
        nonlocal result
        result = agent.run(query)
    
    thread = Thread(target=worker)
    thread.start()
    thread.join(timeout=timeout)
    
    if thread.is_alive():
        return "Timeout: Agent took too long"
    return result
```

---

### 问题 8：工具调用失败

**症状**：
```
ToolExecutionError: Tool 'search' failed: Connection refused
```

**排查**：
```python
# 1. 测试工具
from langchain.tools import Tool
tool = Tool(name='search', func=search_func, description='Search')
try:
    result = tool.run('test query')
    print(f"Tool result: {result}")
except Exception as e:
    print(f"Tool error: {e}")

# 2. 检查工具配置
print(tool.args_schema.schema())
```

**解决方案**：
```python
# 添加错误处理
def safe_tool_call(tool, *args, **kwargs):
    try:
        return tool.run(*args, **kwargs)
    except Exception as e:
        logging.error(f"Tool {tool.name} failed: {e}")
        return f"Error: {str(e)}"

# 添加重试机制
from tenacity import retry, stop_after_attempt

@retry(stop=stop_after_attempt(3))
def call_tool_with_retry(tool, *args, **kwargs):
    return tool.run(*args, **kwargs)
```

---

## 💰 成本问题

### 问题 9：成本激增

**症状**：
```
Daily cost increased from $10 to $100
```

**排查**：
```python
# 1. 分析使用情况
from openai import OpenAI
client = OpenAI()

usage = client.usage.list(start_date='2026-03-01', end_date='2026-03-27')
print(usage)

# 2. 检查 Token 使用
for agent in agents:
    print(f"Agent: {agent.name}, Tokens: {agent.total_tokens}")
```

**解决方案**：
```python
# 1. Token 优化
def optimize_prompt(prompt):
    # 移除冗余
    prompt = prompt.strip()
    # 限制长度
    if len(prompt) > 4000:
        prompt = prompt[:4000] + '...'
    return prompt

# 2. 使用更便宜的模型
def select_model(complexity):
    if complexity == 'simple':
        return 'gpt-3.5-turbo'  # $0.0005/1K
    else:
        return 'gpt-4'  # $0.03/1K

# 3. 缓存常见查询
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_query(query_hash):
    return agent.run(query)
```

---

## 🚀 性能问题

### 问题 10：响应时间慢

**症状**：
```
P95 response time: 5s (target: <2s)
```

**排查**：
```python
# 1. 性能分析
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# 运行 Agent
agent.run('test query')

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)

# 2. 检查瓶颈
import time

start = time.time()
response = llm.invoke('test')
print(f"LLM time: {time.time() - start}")

start = time.time()
result = tool.run('test')
print(f"Tool time: {time.time() - start}")
```

**解决方案**：
```python
# 1. 异步处理
import asyncio

async def async_agent_run(query):
    # 并行调用工具
    tasks = [
        asyncio.create_task(tool.arun(query))
        for tool in agent.tools
    ]
    results = await asyncio.gather(*tasks)
    return results

# 2. 缓存
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_llm_call(prompt):
    return llm.invoke(prompt)

# 3. 批处理
def batch_process(queries):
    return [llm.invoke(q) for q in queries]
```

---

## 📊 监控问题

### 问题 11：指标丢失

**症状**：
```
Prometheus metrics not showing up
```

**排查**：
```bash
# 1. 检查端点
curl http://localhost:8000/metrics

# 2. 检查 Prometheus 配置
cat /etc/prometheus/prometheus.yml

# 3. 检查日志
journalctl -u prometheus -f
```

**解决方案**：
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'ai-agent'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 15s
```

---

## 🛠️ 通用排查工具

### 日志分析
```bash
# 查看错误日志
grep -i error /var/log/ai-agent/*.log

# 实时监控
tail -f /var/log/ai-agent/app.log | grep ERROR

# 统计错误类型
awk '/ERROR/ {print $5}' /var/log/ai-agent/app.log | sort | uniq -c
```

---

### 系统诊断
```bash
# 系统资源
top -p $(pgrep -d',' python)

# 网络连接
netstat -an | grep ESTABLISHED

# 磁盘使用
df -h

# 内存使用
free -m
```

---

## 📝 故障排查清单

### 网络层
- [ ] 检查网络连接
- [ ] 检查 DNS 解析
- [ ] 检查防火墙规则
- [ ] 检查代理配置

### 应用层
- [ ] 检查日志文件
- [ ] 检查错误消息
- [ ] 检查配置文件
- [ ] 检查依赖版本

### 数据层
- [ ] 检查数据库连接
- [ ] 检查查询性能
- [ ] 检查索引状态
- [ ] 检查数据一致性

### 外部服务
- [ ] 检查 API 状态
- [ ] 检查认证信息
- [ ] 检查速率限制
- [ ] 检查服务健康

---

**生成时间**: 2026-03-27 22:30 GMT+8
