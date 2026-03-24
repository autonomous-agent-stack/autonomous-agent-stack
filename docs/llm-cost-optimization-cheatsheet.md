# LLM 成本优化 - 快速参考卡片

**版本:** 1.0  
**用途:** 快速查阅，按需复制代码

---

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install numpy aiohttp sentence-transformers faiss-cpu
```

### 2. 基本使用
```python
from llm_cost_optimization_scripts import (
    TokenCounter, SimpleMemoryCache, 
    ModelRouter, BudgetManager, LLMMetrics
)

# Token 计数
tokens = TokenCounter.count_tokens("你的文本")
cost = TokenCounter.estimate_cost("prompt", "response", "gpt-3.5-turbo")

# 缓存
cache = SimpleMemoryCache(max_size=1000)
cached = cache.get("prompt", "gpt-3.5-turbo")
cache.set("prompt", "gpt-3.5-turbo", "response")

# 模型路由
router = ModelRouter()
model = router.select_model("写一个 Python 函数")

# 预算管理
budget = BudgetManager(BudgetConfig(daily_limit=10.0))
if budget.check_budget(estimated_cost):
    # 执行请求...
    pass
```

---

## 📊 Token 计数

### 英文
```python
# 1 token ≈ 4 字符
tokens = len(text) / 4
```

### 中文
```python
# 1 token ≈ 1.5 字符
tokens = len(text) / 1.5
```

### 代码
```python
# 1 token ≈ 3 字符
tokens = len(code) / 3
```

### 自动检测
```python
from llm_cost_optimization_scripts import TokenCounter
tokens = TokenCounter.count_tokens(text, language="auto")
```

---

## 💰 成本估算

### 价格表（每 1K tokens）

| 模型 | 输入 | 输出 |
|------|------|------|
| GPT-3.5-Turbo | $0.002 | $0.002 |
| GPT-4 | $0.03 | $0.06 |
| Claude-3-Sonnet | $0.003 | $0.015 |
| Claude-3-Opus | $0.015 | $0.075 |

### 快速估算
```python
from llm_cost_optimization_scripts import TokenCounter

cost = TokenCounter.estimate_cost(
    prompt="你的提示词",
    response="响应内容",
    model="gpt-3.5-turbo"
)
print(f"Cost: ${cost:.6f}")
```

---

## 🔥 缓存装饰器

### 基本缓存
```python
from llm_cost_optimization_scripts import cached_llm_call

@cached_llm_call(ttl=3600)  # 缓存 1 小时
async def my_llm_function(prompt: str, model: str = "gpt-3.5-turbo"):
    # 你的 LLM 调用代码
    return await call_openai_api(prompt, model)
```

### 手动缓存
```python
from llm_cost_optimization_scripts import SimpleMemoryCache

cache = SimpleMemoryCache(max_size=1000)

# 获取
result = cache.get(prompt, model)

if not result:
    # 调用 API
    result = await call_llm_api(prompt, model)
    # 存入缓存
    cache.set(prompt, model, result, ttl=3600)
```

---

## 🎯 模型路由

### 任务分类
```python
from llm_cost_optimization_scripts import ModelRouter

router = ModelRouter()

# 自动分类并选择模型
model = router.select_model("写一个排序算法")
# 返回: "gpt-4" (代码生成任务)

model = router.select_model("今天天气如何？")
# 返回: "gpt-3.5-turbo" (简单问答)
```

### 任务类型映射
```
简单问答         → GPT-3.5-Turbo
摘要             → GPT-3.5-Turbo
翻译             → Claude-3-Sonnet
代码生成         → GPT-4
复杂推理         → GPT-4
创意写作         → Claude-3-Opus
```

---

## 💸 预算管理

### 基本设置
```python
from llm_cost_optimization_scripts import BudgetManager, BudgetConfig

config = BudgetConfig(
    daily_limit=10.0,        # 每日 $10
    alert_threshold=0.8,      # 80% 时警告
    shutdown_threshold=1.0   # 100% 时停止
)
budget = BudgetManager(config)
```

### 检查预算
```python
estimated_cost = 0.05  # 估算成本

if budget.check_budget(estimated_cost):
    # 执行请求
    response = await call_llm_api(prompt, model)
    
    # 记录花费
    actual_cost = calculate_actual_cost(prompt, response, model)
    budget.record_spend(model, tokens, actual_cost)
else:
    print("预算不足")
```

### 获取统计
```python
stats = budget.get_stats()
print(f"已使用: ${stats['daily_spend']:.2f}")
print(f"剩余: ${stats['remaining']:.2f}")
print(f"使用率: {stats['usage_percentage']:.1f}%")
```

---

## 📈 性能监控

### 基本使用
```python
from llm_cost_optimization_scripts import LLMMetrics

metrics = LLMMetrics()

# 记录请求
metrics.record_request(
    tokens=1500,
    cost=0.05,
    latency=1.2,
    cache_hit=False
)

# 获取摘要
summary = metrics.get_summary()
print(json.dumps(summary, indent=2))
```

### 导出报告
```python
metrics.export_to_json("metrics_report.json")
```

### 关键指标
```python
{
  "total_requests": 100,
  "total_tokens": 150000,
  "total_cost": 5.00,
  "avg_tokens_per_request": 1500,
  "avg_cost_per_request": 0.05,
  "cache_hit_rate": 35.0,
  "avg_latency": 1.2,
  "tokens_per_dollar": 30000
}
```

---

## 🚦 批处理

### 基本批处理
```python
from llm_cost_optimization_scripts import BatchProcessor

processor = BatchProcessor(batch_size=10, delay=1.0)

async def handle_response(response):
    print(f"Got: {response[:50]}...")

# 添加请求
await processor.add_request("prompt1", handle_response)
await processor.add_request("prompt2", handle_response)
# ... 添加更多

# 自动批处理
```

### 手动批处理
```python
import asyncio

async def batch_process(prompts):
    tasks = [call_llm_api(p) for p in prompts]
    results = await asyncio.gather(*tasks)
    return results

prompts = ["prompt1", "prompt2", "prompt3"]
results = await batch_process(prompts)
```

---

## ⚡ Prompt 优化

### 压缩 Prompt
```python
from llm_cost_optimization_scripts import PromptOptimizer

original = """
好的，我现在开始为您分析这个问题。
首先，让我仔细阅读一下文档。
"""

compressed = PromptOptimizer.compress_prompt(original)
# 结果: "分析问题。阅读文档。"
```

### 提取模板
```python
templates = PromptOptimizer.extract_templates(prompt)
# 返回: ["输入: {input} → 输出: {output}", ...]
```

---

## 🎨 实战技巧

### 1. 设置 max_tokens
```python
# 不要总是用最大值
task_limits = {
    "分类": 10,
    "摘要": 200,
    "解释": 500,
    "代码生成": 1000
}

max_tokens = task_limits.get(task_type, 500)
```

### 2. 使用 stop_sequences
```python
response = await call_llm(
    prompt,
    stop=["\n\n", "###", "END"],
    max_tokens=500
)
```

### 3. 优化系统提示词
```python
# 冗长版 (300 tokens)
system = """你是一个专业的AI助手，你的职责是..."""

# 精简版 (60 tokens)
system = """专业AI助手。准确、简洁。"""
```

### 4. 分段处理长文本
```python
def chunk_text(text, max_tokens=8000):
    chunks = []
    current = ""
    
    for sentence in text.split('.'):
        if len(current) + len(sentence) <= max_tokens:
            current += sentence + "."
        else:
            chunks.append(current)
            current = sentence + "."
    
    return chunks
```

---

## 🎯 优化检查清单

### 每日检查
- [ ] 缓存命中率 > 30%
- [ ] 预算使用率 < 80%
- [ ] 平均延迟正常

### 每周检查
- [ ] 模型路由是否需要调整
- [ ] 是否有高成本可缓存模式
- [ ] Prompt 模板优化

### 每月检查
- [ ] 运行基准测试
- [ ] 检查新模型/价格
- [ ] 分析成本趋势

---

## 🔧 故障排查

### 缓存命中率低
```python
# 增加 TTL
cache.set(prompt, model, response, ttl=7200)  # 2 小时

# 增加缓存大小
cache = SimpleMemoryCache(max_size=5000)
```

### 成本过高
```python
# 启用预算模式
model = router.select_model(prompt, budget_mode=True)

# 使用更便宜的模型
model = "gpt-3.5-turbo"
```

### 预算警告
```python
# 检查原因
stats = budget.get_stats()
print(stats)

# 调整预算限制
config = BudgetConfig(daily_limit=20.0)
```

---

## 📚 完整示例

```python
import asyncio
from llm_cost_optimization_scripts import (
    TokenCounter, SimpleMemoryCache, ModelRouter,
    BudgetManager, BudgetConfig, LLMMetrics
)

async def main():
    # 初始化
    cache = SimpleMemoryCache(max_size=1000)
    router = ModelRouter()
    budget = BudgetManager(BudgetConfig(daily_limit=10.0))
    metrics = LLMMetrics()
    
    # 处理请求
    prompts = ["写一个排序算法", "总结这篇文章"]
    
    for prompt in prompts:
        # Token 计数
        tokens = TokenCounter.count_tokens(prompt)
        
        # 模型选择
        model = router.select_model(prompt)
        
        # 成本估算
        estimated_cost = TokenCounter.estimate_cost(
            prompt, model=model
        )
        
        # 预算检查
        if not budget.check_budget(estimated_cost):
            print("预算不足")
            continue
        
        # 缓存检查
        cached = cache.get(prompt, model)
        if cached:
            response = cached
            is_cache_hit = True
        else:
            response = await call_llm_api(prompt, model)
            cache.set(prompt, model, response)
            is_cache_hit = False
        
        # 记录
        actual_cost = TokenCounter.estimate_cost(
            prompt, response, model
        )
        budget.record_spend(model, tokens, actual_cost)
        metrics.record_request(
            tokens=tokens,
            cost=actual_cost,
            latency=1.0,
            cache_hit=is_cache_hit
        )
    
    # 输出统计
    print(json.dumps(metrics.get_summary(), indent=2))

asyncio.run(main())
```

---

## 🎓 进阶技巧

### 语义缓存
```python
# 使用 sentence-transformers 实现相似问题缓存
from sentence_transformers import SentenceTransformer

encoder = SentenceTransformer('all-MiniLM-L6-v2')

def find_similar_cached_response(prompt):
    # 查找语义相似的缓存响应
    pass
```

### A/B 测试
```python
# 测试不同模型的效果
from llm_cost_optimization_scripts import ModelRouter

router = ModelRouter()

# 记录性能
router.record_performance(
    model="gpt-3.5-turbo",
    task="summarization",
    quality=0.85,
    cost=0.05
)

# 获取最佳模型
best_model = router.get_best_model("summarization")
```

### 动态降级
```python
async def call_with_fallback(prompt):
    # 先用便宜模型
    result = await call_llm(prompt, "gpt-3.5-turbo")
    
    # 质量不够就用贵的
    if not check_quality(result):
        result = await call_llm(prompt, "gpt-4")
    
    return result
```

---

## 📞 支持

- 完整文档: `llm-cost-optimization.md`
- 代码示例: `llm-cost-optimization-scripts.py`
- 问题反馈: 提交 Issue

---

**最后更新:** 2026-03-25  
**版本:** 1.0
