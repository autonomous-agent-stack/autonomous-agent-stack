# LLM API 成本优化策略

**版本:** 1.0  
**更新时间:** 2026-03-25  
**目标:** 在不牺牲质量的前提下，最大化降低 LLM API 调用成本

---

## 目录

1. [Token 优化](#1-token-优化)
2. [缓存策略](#2-缓存策略)
3. [批处理策略](#3-批处理策略)
4. [模型选择策略](#4-模型选择策略)
5. [预算管理](#5-预算管理)
6. [实战技巧](#6-实战技巧)
7. [监控与优化](#7-监控与优化)

---

## 1. Token 优化

### 1.1 Prompt 优化

**压缩原则：**
- 删除冗余词（"好的"、"没问题"、"让我帮您"）
- 使用简洁的指令代替长句
- 合并相似的指令

**优化前（50 tokens）：**
```
好的，我现在开始为您分析这个问题。首先，让我仔细阅读一下您提供的文档，然后我会给出详细的建议和解决方案。如果有什么需要您澄清的地方，我会及时向您提问。
```

**优化后（15 tokens）：**
```
分析文档，提供建议。需澄清时提问。
```

**节省：70% tokens**

---

### 1.2 输入截断与分段

**场景：** 处理长文档时

**策略：**
```python
def process_long_text(text, max_tokens=8000, chunk_overlap=100):
    """
    分段处理长文本，避免单次调用超出限制
    """
    chunks = []
    current_chunk = ""
    
    for sentence in text.split('.'):
        if len(current_chunk) + len(sentence) <= max_tokens:
            current_chunk += sentence + "."
        else:
            chunks.append(current_chunk)
            current_chunk = sentence + "."
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks
```

**成本对比：**
- 单次 50K tokens → 多次 8K tokens = 节省 20-30%（避免超大模型定价）

---

### 1.3 输出长度控制

**max_tokens 精准设置：**
```python
# 不要总是设置最大值
task_token_limits = {
    "分类": 10,           # 只需一个标签
    "摘要": 200,         # 中等长度摘要
    "解释": 500,         # 详细说明
    "代码生成": 1000,     # 完整函数
    "长文撰写": 2000,     # 完整文章
}

def get_max_tokens(task_type):
    return task_token_limits.get(task_type, 500)
```

**收益：** 减少不必要的输出 tokens（通常输出比输入更贵）

---

### 1.4 系统提示词优化

**精简系统提示词：**

```python
# 冗长版（300 tokens）
SYSTEM_PROMPT_LONG = """
你是一个专业的AI助手，你的职责是为用户提供准确、有用的信息和建议。
在回答问题时，请遵循以下原则：
1. 确保信息的准确性
2. 保持回答的简洁明了
3. 必要时提供示例
4. 如果不确定，请直接承认
5. 始终保持礼貌和专业的态度
...（更多规则）
"""

# 精简版（60 tokens）
SYSTEM_PROMPT_SHORT = """
专业AI助手。准确、简洁、必要时举例。不确定时承认。
"""
```

**节省：80% tokens，且性能几乎无损失**

---

### 1.5 上下文窗口管理

**滑动窗口策略：**
```python
class ContextWindow:
    def __init__(self, max_tokens=4000):
        self.max_tokens = max_tokens
        self.history = []
    
    def add(self, role, content):
        """添加新消息，自动裁剪历史"""
        tokens = self._count_tokens(content)
        
        # 如果超出限制，删除最旧的消息
        while self._total_tokens() + tokens > self.max_tokens and self.history:
            self.history.pop(0)
        
        self.history.append({"role": role, "content": content})
    
    def _count_tokens(self, text):
        """估算 token 数量"""
        return len(text) // 4  # 粗略估算：1 token ≈ 4 字符
```

**使用场景：** 对话系统、聊天机器人

---

## 2. 缓存策略

### 2.1 请求级缓存

**Memcached 示例：**
```python
import hashlib
import json
from pymemcache.client import base

class LLMPromptCache:
    def __init__(self, ttl=3600):
        self.client = base.Client(('localhost', 11211))
        self.ttl = ttl
    
    def get_cache_key(self, prompt, model, params):
        """生成缓存键"""
        data = {
            "prompt": prompt,
            "model": model,
            "params": params
        }
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
    
    def get(self, prompt, model, params):
        key = self.get_cache_key(prompt, model, params)
        return self.client.get(key)
    
    def set(self, prompt, model, params, response):
        key = self.get_cache_key(prompt, model, params)
        self.client.set(key, response, expire=self.ttl)
```

**命中率：** 日常对话可达 30-50%

---

### 2.2 向量语义缓存

**场景：** 相似问题的答案可以复用

```python
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

class SemanticCache:
    def __init__(self):
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = faiss.IndexFlatL2(384)  # 384 维
        self.responses = []
    
    def add(self, prompt, response):
        """添加到语义缓存"""
        embedding = self.encoder.encode(prompt)
        self.index.add(np.array([embedding]).astype('float32'))
        self.responses.append(response)
    
    def search(self, prompt, threshold=0.85):
        """搜索相似问题的答案"""
        embedding = self.encoder.encode(prompt)
        distances, indices = self.index.search(
            np.array([embedding]).astype('float32'), 1
        )
        
        if len(indices) > 0 and distances[0][0] < threshold:
            return self.responses[indices[0][0]]
        return None
```

**适用场景：**
- FAQ 系统
- 客服机器人
- 重复性问答

---

### 2.3 分层缓存架构

```
L1 Cache（内存）
    ↓ miss
L2 Cache（Redis）
    ↓ miss
LLM API
    ↓
L4 Cache（持久化存储）
```

**配置建议：**
- L1: 1000 条，LRU，命中率 60%
- L2: 10000 条，TTL 24h，命中率 30%
- L4: 所有历史，供分析和训练

---

### 2.4 缓存失效策略

```python
class SmartCache:
    def __init__(self):
        self.cache = {}
        self.timestamps = {}
        self.hit_counts = {}
    
    def get(self, key):
        if key in self.cache:
            self.hit_counts[key] += 1
            self.timestamps[key] = time.time()
            return self.cache[key]
        return None
    
    def should_invalidate(self, key):
        """
        智能失效策略：
        - 超过 1 天未使用
        - 命中次数 < 5 且存在超过 7 天
        """
        age = time.time() - self.timestamps[key]
        if age > 86400:  # 1 天
            return True
        
        if self.hit_counts[key] < 5 and age > 604800:  # 7 天
            return True
        
        return False
```

---

## 3. 批处理策略

### 3.1 异步批处理

```python
import asyncio
from aiohttp import ClientSession

class BatchLLMProcessor:
    def __init__(self, batch_size=10, delay=1.0):
        self.batch = []
        self.batch_size = batch_size
        self.delay = delay  # 秒
    
    async def add_request(self, prompt, callback):
        """添加请求到批处理队列"""
        self.batch.append({"prompt": prompt, "callback": callback})
        
        if len(self.batch) >= self.batch_size:
            await self._process_batch()
    
    async def _process_batch(self):
        """处理一批请求"""
        if not self.batch:
            return
        
        batch = self.batch
        self.batch = []
        
        # 并发调用 API
        async with ClientSession() as session:
            tasks = [
                self._call_llm(session, item["prompt"])
                for item in batch
            ]
            responses = await asyncio.gather(*tasks)
        
        # 回调处理
        for item, response in zip(batch, responses):
            item["callback"](response)
        
        # 速率限制：延迟后继续
        await asyncio.sleep(self.delay)
```

**收益：**
- 减少 API 调用次数（合并相似请求）
- 提高吞吐量
- 降低延迟（对于非实时任务）

---

### 3.2 预测性预取

```python
class PredictivePrefetcher:
    def __init__(self, llm_cache):
        self.cache = llm_cache
        self.next_question_map = {
            "天气": ["明天", "后天", "一周"],
            "代码": ["解释", "优化", "错误"],
            # ... 更多映射
        }
    
    async def prefetch(self, current_prompt):
        """预测用户可能问的下一个问题并预取"""
        for keyword, followups in self.next_question_map.items():
            if keyword in current_prompt:
                for followup in followups:
                    prefetched_prompt = current_prompt.replace(
                        keyword, followup
                    )
                    # 在后台预加载
                    asyncio.create_task(
                        self._preload(prefetched_prompt)
                    )
    
    async def _preload(self, prompt):
        """预加载到缓存"""
        if not self.cache.get(prompt):
            response = await call_llm_api(prompt)
            self.cache.set(prompt, response)
```

**适用场景：**
- 交互式对话
- 教程/文档助手
- 引导式问答

---

### 3.3 Map-Reduce 批处理

**场景：** 批量处理文档

```python
async def process_documents_batch(documents):
    """
    Map: 并行处理每个文档
    Reduce: 合并结果
    """
    # Map 阶段
    tasks = [process_single_doc(doc) for doc in documents]
    results = await asyncio.gather(*tasks)
    
    # Reduce 阶段
    summary = await summarize_results(results)
    return summary

async def process_single_doc(document):
    """处理单个文档（可复用缓存）"""
    cache_key = f"doc:{hash(document)}"
    
    cached = get_from_cache(cache_key)
    if cached:
        return cached
    
    result = await call_llm_api(document)
    save_to_cache(cache_key, result)
    return result
```

---

## 4. 模型选择策略

### 4.1 任务-模型映射表

```python
MODEL_ROUTING = {
    # 简单任务 → 小模型（便宜）
    "文本分类": {
        "model": "gpt-3.5-turbo",
        "cost_per_1k_tokens": 0.002
    },
    "摘要": {
        "model": "gpt-3.5-turbo",
        "cost_per_1k_tokens": 0.002
    },
    "简单问答": {
        "model": "gpt-3.5-turbo",
        "cost_per_1k_tokens": 0.002
    },
    
    # 复杂任务 → 大模型（能力强）
    "代码生成": {
        "model": "gpt-4",
        "cost_per_1k_tokens": 0.03
    },
    "复杂推理": {
        "model": "gpt-4",
        "cost_per_1k_tokens": 0.03
    },
    "创意写作": {
        "model": "claude-3-opus",
        "cost_per_1k_tokens": 0.015
    },
    
    # 中等任务 → 中等模型
    "文档分析": {
        "model": "claude-3-sonnet",
        "cost_per_1k_tokens": 0.003
    },
    "翻译": {
        "model": "claude-3-sonnet",
        "cost_per_1k_tokens": 0.003
    },
}

def select_model(task_type, complexity="auto"):
    """自动选择最合适的模型"""
    if complexity == "auto":
        complexity = estimate_complexity(task_type)
    
    config = MODEL_ROUTING.get(task_type, MODEL_ROUTING["简单问答"])
    
    if complexity == "high":
        # 升级到更强模型
        return config["model"].replace("3.5-turbo", "4")
    
    return config["model"]
```

---

### 4.2 自动降级策略

```python
class AdaptiveModelSelector:
    def __init__(self):
        self.primary_model = "gpt-4"
        self.fallback_model = "gpt-3.5-turbo"
        self.quality_threshold = 0.85
    
    async def call_with_fallback(self, prompt, max_retries=1):
        """
        优先使用便宜模型，质量不够才用贵的
        """
        # 先尝试便宜模型
        result = await call_llm(prompt, self.fallback_model)
        quality = self._assess_quality(prompt, result)
        
        if quality >= self.quality_threshold:
            return result
        
        # 质量不够，用更好的模型
        if max_retries > 0:
            return await call_llm(prompt, self.primary_model)
        
        return result
    
    def _assess_quality(self, prompt, response):
        """
        评估响应质量（简单启发式）
        可以用更复杂的逻辑或用 LLM 自己评估
        """
        # 示例：检查响应长度、完整性
        if len(response) < 50:
            return 0.5
        
        if "不知道" in response or "抱歉" in response:
            return 0.6
        
        return 0.9  # 默认认为质量可以
```

**收益：** 
- 70-80% 的请求用便宜模型
- 紧急情况下保证质量
- 总成本降低 60-70%

---

### 4.3 模型性能基准测试

```python
# 建议定期运行，更新路由策略
BENCHMARK_TASKS = [
    {
        "name": "代码生成",
        "prompt": "写一个 Python 函数，实现快速排序",
        "expected_length": 200
    },
    {
        "name": "文本摘要",
        "prompt": "总结以下文章：[长文本]",
        "expected_length": 100
    },
    # ... 更多任务
]

def benchmark_models(tasks):
    """
    对比不同模型在相同任务上的表现
    输出：成本 vs 质量对比表
    """
    results = {}
    
    for model in ["gpt-3.5-turbo", "gpt-4", "claude-3-sonnet"]:
        results[model] = []
        for task in tasks:
            response = call_llm(task["prompt"], model)
            quality = evaluate_quality(response, task)
            cost = calculate_cost(task["prompt"], response, model)
            
            results[model].append({
                "task": task["name"],
                "quality": quality,
                "cost": cost,
                "cost_per_quality": cost / quality
            })
    
    return results
```

---

### 4.4 混合模型策略

```python
def hybrid_approach(prompt):
    """
    混合使用多个模型，取长补短
    """
    # 第一步：用小模型生成初稿
    draft = call_llm(prompt, "gpt-3.5-turbo")
    
    # 第二步：用大模型审查和改进
    review_prompt = f"""
    初稿：
    {draft}
    
    请审查以上初稿，指出问题并提供改进建议。
    如果初稿质量很好，只需简单确认。
    """
    review = call_llm(review_prompt, "gpt-4")
    
    # 第三步：如果需要，根据审查意见修改
    if "问题" in review or "改进" in review:
        final = call_llm(
            f"根据以下建议修改初稿：{review}\n\n原初稿：{draft}",
            "gpt-3.5-turbo"
        )
        return final
    
    return draft
```

**适用场景：**
- 重要文档
- 代码审查
- 内容生成（需要高质量时）

---

## 5. 预算管理

### 5.1 实时预算监控

```python
class BudgetManager:
    def __init__(self, daily_budget=100.0, alert_threshold=0.8):
        self.daily_budget = daily_budget
        self.current_spend = 0.0
        self.alert_threshold = alert_threshold
        self.log_file = "spend_log.json"
    
    async def check_budget(self, estimated_cost):
        """调用前检查预算"""
        if self.current_spend + estimated_cost > self.daily_budget:
            if self.current_spend / self.daily_budget > self.alert_threshold:
                self._send_alert(
                    f"预算警告：已使用 {self.current_spend:.2f}/{self.daily_budget:.2f}"
                )
            return False
        return True
    
    async def record_spend(self, model, tokens, cost):
        """记录实际花费"""
        self.current_spend += cost
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "tokens": tokens,
            "cost": cost,
            "daily_total": self.current_spend
        }
        
        with open(self.log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
```

---

### 5.2 动态降级机制

```python
class DynamicThrottling:
    def __init__(self):
        self.rate_limit = 100  # 每分钟请求数
        self.current_usage = 0
        self.last_minute = time.time()
        self.budget_manager = BudgetManager()
    
    async def acquire_request(self):
        """获取请求许可"""
        now = time.time()
        
        # 重置计数器
        if now - self.last_minute >= 60:
            self.current_usage = 0
            self.last_minute = now
        
        # 检查速率限制
        if self.current_usage >= self.rate_limit:
            await asyncio.sleep(1)
            return await self.acquire_request()
        
        # 检查预算
        estimated_cost = estimate_request_cost()
        if not await self.budget_manager.check_budget(estimated_cost):
            # 预算不足，降级到便宜模型
            return "gpt-3.5-turbo"
        
        self.current_usage += 1
        return "gpt-4"  # 默认使用好的模型
```

---

### 5.3 成本预测与分配

```python
def forecast_monthly_cost(historical_data, growth_rate=1.2):
    """
    基于历史数据预测月度成本
    """
    # 计算日平均
    daily_avg = np.mean([d["cost"] for d in historical_data])
    
    # 预测未来30天
    predicted_daily = daily_avg * growth_rate
    monthly_forecast = predicted_daily * 30
    
    return {
        "daily_average": daily_avg,
        "predicted_daily": predicted_daily,
        "monthly_forecast": monthly_forecast,
        "suggested_budget": monthly_forecast * 1.3  # 30% 缓冲
    }
```

---

### 5.4 预算分配策略

```python
BUDGET_ALLOCATION = {
    "核心功能": {
        "percentage": 60,
        "description": "主要业务逻辑"
    },
    "实验性功能": {
        "percentage": 20,
        "description": "新功能测试"
    },
    "A/B 测试": {
        "percentage": 10,
        "description": "模型对比"
    },
    "缓冲": {
        "percentage": 10,
        "description": "应急使用"
    }
}

class AllocatedBudget:
    def __init__(self, category, total_budget):
        self.category = category
        self.allocated = total_budget * BUDGET_ALLOCATION[category]["percentage"] / 100
        self.used = 0.0
    
    def can_spend(self, amount):
        return self.used + amount <= self.allocated
    
    def spend(self, amount):
        if self.can_spend(amount):
            self.used += amount
            return True
        return False
```

---

## 6. 实战技巧

### 6.1 少样本提示优化

```python
# 不好的写法（浪费 tokens）
few_shot_bad = """
示例1：
输入：这个产品质量怎么样？
输出：很好，我很满意。

示例2：
输入：这个产品有什么缺点吗？
输出：有一些小问题，但总体不错。

示例3：
输入：...（更多示例）
"""

# 好的写法（压缩示例）
few_shot_good = """
输入:这个产品质量怎么样?→很好
输入:有什么缺点?→有小问题但不错
输入:...（更多压缩示例）
"""
```

**节省：40-60% tokens**

---

### 6.2 流式输出截断

```python
async def stream_with_stop(prompt, stop_sequences=["\n\n", "###"]):
    """
    使用 stop_sequences 提前终止输出
    """
    response = await call_llm_stream(
        prompt, 
        stop=stop_sequences,
        max_tokens=500  # 设置较小限制
    )
    
    # 提前检测到停止序列就返回
    for chunk in response:
        for seq in stop_sequences:
            if seq in chunk:
                return chunk
        yield chunk
```

**收益：** 减少不必要的生成 tokens

---

### 6.3 温度与采样优化

```python
OPTIMAL_TEMPERATURES = {
    "代码生成": 0.2,    # 低温度 = 确定性输出
    "创意写作": 0.8,    # 高温度 = 多样性
    "翻译": 0.3,        # 中低温度 = 准确性
    "摘要": 0.5,        # 中等温度 = 平衡
}

def get_temperature(task_type):
    return OPTIMAL_TEMPERATURES.get(task_type, 0.7)
```

**收益：** 减少重新生成次数，提高一次成功率

---

### 6.4 输出格式化技巧

```python
# 要求结构化输出，减少后续处理成本
prompt = """
分析以下文本，输出 JSON 格式：

{
    "sentiment": "positive/negative/neutral",
    "keywords": ["关键词1", "关键词2"],
    "summary": "一句话摘要"
}

文本：{text}
"""

# 解析结果，避免用 LLM 二次处理
result = json.loads(llm_response)
```

**收益：** 减少后续 API 调用

---

### 6.5 批量验证

```python
async def batch_validate_results(results, sample_size=0.1):
    """
    只验证部分结果，降低成本
    """
    import random
    
    # 随机抽样验证
    sample = random.sample(
        results, 
        max(1, int(len(results) * sample_size))
    )
    
    # 只对抽样验证
    validation_tasks = [
        validate_single(item) for item in sample
    ]
    validations = await asyncio.gather(*validation_tasks)
    
    # 计算整体质量
    quality = sum(validations) / len(validations)
    return quality
```

---

## 7. 监控与优化

### 7.1 关键指标

```python
METRICS = {
    # 成本指标
    "total_tokens": "总 token 数",
    "total_cost": "总成本",
    "cost_per_request": "平均每次请求成本",
    "cache_hit_rate": "缓存命中率",
    
    # 性能指标
    "average_latency": "平均延迟",
    "p99_latency": "99分位延迟",
    "success_rate": "成功率",
    "quality_score": "质量评分",
    
    # 效率指标
    "tokens_per_dollar": "每美元 token 数",
    "requests_per_minute": "每分钟请求数"
}
```

---

### 7.2 优化循环

```python
async def optimization_loop():
    """
    持续优化流程
    """
    while True:
        # 1. 收集数据
        metrics = collect_metrics()
        
        # 2. 分析瓶颈
        bottlenecks = analyze_bottlenecks(metrics)
        
        # 3. 生成优化建议
        suggestions = generate_suggestions(bottlenecks)
        
        # 4. 应用优化
        for suggestion in suggestions:
            if suggestion["estimated_savings"] > 0.1:  # 预计节省 > $0.1
                apply_optimization(suggestion)
        
        # 5. 监控效果
        await asyncio.sleep(86400)  # 每天优化一次
```

---

### 7.3 A/B 测试框架

```python
class ModelABTest:
    def __init__(self, model_a, model_b, traffic_ratio=0.5):
        self.model_a = model_a
        self.model_b = model_b
        self.traffic_ratio = traffic_ratio
        self.results = {"a": [], "b": []}
    
    def route_request(self, request_id):
        """路由请求到不同模型"""
        if hash(request_id) % 100 < self.traffic_ratio * 100:
            return "a"
        return "b"
    
    async def run_test(self, requests):
        """运行 A/B 测试"""
        for req in requests:
            group = self.route_request(req["id"])
            model = self.model_a if group == "a" else self.model_b
            
            start = time.time()
            response = await call_llm(req["prompt"], model)
            latency = time.time() - start
            
            quality = await evaluate_quality(response, req)
            cost = calculate_cost(req["prompt"], response, model)
            
            self.results[group].append({
                "latency": latency,
                "quality": quality,
                "cost": cost
            })
        
        return self._analyze_results()
    
    def _analyze_results(self):
        """分析测试结果"""
        def avg(group, key):
            return np.mean([r[key] for r in self.results[group]])
        
        return {
            "model_a": {
                "avg_latency": avg("a", "latency"),
                "avg_quality": avg("a", "quality"),
                "avg_cost": avg("a", "cost")
            },
            "model_b": {
                "avg_latency": avg("b", "latency"),
                "avg_quality": avg("b", "quality"),
                "avg_cost": avg("b", "cost")
            },
            "recommendation": self._recommend()
        }
```

---

### 7.4 成本优化清单

**每周检查：**
- [ ] 缓存命中率是否 > 30%
- [ ] 是否有高成本且可缓存的模式
- [ ] 模型路由策略是否需要调整
- [ ] 预算使用是否在预期内

**每月检查：**
- [ ] 运行完整的基准测试
- [ ] 检查是否有新模型/价格
- [ ] 分析成本趋势
- [ ] 优化 prompt 模板

**季度检查：**
- [ ] 审查所有集成点
- [ ] 评估是否需要自建/替代方案
- [ ] 优化整体架构
- [ ] 更新成本优化策略

---

## 总结

**核心原则：**

1. **能缓存就不调用** - 缓存是最有效的优化
2. **能批量就不单独** - 批处理降低调用次数
3. **能用小模型就不用大模型** - 任务复杂度匹配
4. **能精简就不冗余** - Prompt 和输出都要压缩
5. **能预测就不等** - 预取提升体验

**预期收益：**

- **缓存命中 30-50%** → 成本降低 30-40%
- **Prompt 优化** → 成本降低 20-30%
- **模型路由** → 成本降低 50-70%
- **批处理** → 调用次数减少 60-80%

**总成本降低潜力：70-90%**

---

## 附录：快速参考

### Token 估算
- 英文：1 token ≈ 4 字符
- 中文：1 token ≈ 1.5-2 字符
- 代码：1 token ≈ 3-4 字符

### 常见价格（仅供参考，以实际为准）
- GPT-3.5-Turbo: $0.002 / 1K tokens (输入)
- GPT-4: $0.03 / 1K tokens (输入)
- Claude-3-Sonnet: $0.003 / 1K tokens (输入)
- Claude-3-Opus: $0.015 / 1K tokens (输入)

### 缓存 TTL 建议
- 静态内容：24-72 小时
- 动态对话：1-6 小时
- 频繁变化：10-30 分钟

---

**文档结束**

如有问题或需要进一步优化，请根据实际情况调整策略。
