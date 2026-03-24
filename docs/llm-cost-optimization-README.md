# LLM API 成本优化工具包

> 在不牺牲质量的前提下，最大化降低 LLM API 调用成本

**预期成本降低：70-90%**

---

## 📦 包含内容

- ✅ **完整文档** (`llm-cost-optimization.md`) - 7 大优化策略的详细指南
- ✅ **Python 脚本** (`llm-cost-optimization-scripts.py`) - 可直接使用的代码实现
- ✅ **快速参考** (`llm-cost-optimization-cheatsheet.md`) - 常用代码和命令速查
- ✅ **配置模板** (`llm-cost-optimization-config.json`) - 项目配置示例

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
    ModelRouter, BudgetManager
)

# 估算成本
tokens = TokenCounter.count_tokens("你的文本")
cost = TokenCounter.estimate_cost("prompt", model="gpt-3.5-turbo")
print(f"Cost: ${cost:.6f}")

# 使用缓存
cache = SimpleMemoryCache(max_size=1000)
cache.set("prompt", "gpt-3.5-turbo", "response")
result = cache.get("prompt", "gpt-3.5-turbo")

# 智能模型选择
router = ModelRouter()
model = router.select_model("写一个 Python 函数")
```

### 3. 配置项目

复制配置模板并修改：

```bash
cp llm-cost-optimization-config.json my_project_config.json
```

编辑配置文件，设置：
- 每日预算限制
- 启用的模型
- 缓存策略
- 监控选项

---

## 📊 核心功能

### 1. Token 优化
- 自动估算 token 数量
- 成本预测
- Prompt 压缩
- 输出长度控制

**预期节省：20-30%**

### 2. 智能缓存
- 内存缓存（快速）
- Redis 缓存（持久）
- 语义缓存（相似问题）
- 自动过期策略

**预期节省：30-40%**

### 3. 模型路由
- 任务自动分类
- 智能模型选择
- 成本敏感模式
- 性能基准测试

**预期节省：50-70%**

### 4. 批处理
- 异步批处理
- 预测性预取
- Map-Reduce 模式
- 并发控制

**预期节省：60-80%**

### 5. 预算管理
- 实时预算监控
- 动态降级
- 成本预测
- 告警机制

**避免超支：100%**

---

## 📚 文档结构

```
.
├── README.md                                    # 本文件
├── llm-cost-optimization.md                    # 完整文档（必读）
├── llm-cost-optimization-scripts.py            # 代码实现
├── llm-cost-optimization-cheatsheet.md         # 快速参考
└── llm-cost-optimization-config.json           # 配置模板
```

### 文档阅读顺序

1. **快速参考** (`cheatsheet.md`) - 5 分钟快速上手
2. **完整文档** (`llm-cost-optimization.md`) - 深入理解
3. **代码实现** (`scripts.py`) - 集成到项目
4. **配置模板** (`config.json`) - 生产环境配置

---

## 💡 使用场景

### 场景 1: 聊天机器人

```python
from llm_cost_optimization_scripts import (
    SimpleMemoryCache, ModelRouter
)

cache = SimpleMemoryCache(max_size=5000)
router = ModelRouter()

async def chat_response(user_message):
    # 检查缓存
    cached = cache.get(user_message, "gpt-3.5-turbo")
    if cached:
        return cached
    
    # 选择模型
    model = router.select_model(user_message, budget_mode=True)
    
    # 调用 API
    response = await call_llm_api(user_message, model)
    
    # 存入缓存
    cache.set(user_message, model, response, ttl=3600)
    
    return response
```

### 场景 2: 批量文档处理

```python
from llm_cost_optimization_scripts import BatchProcessor

processor = BatchProcessor(batch_size=10, delay=1.0)

async def process_document(doc):
    def handle_summary(summary):
        save_summary(doc.id, summary)
    
    await processor.add_request(
        f"总结以下文档：{doc.text}",
        handle_summary
    )
```

### 场景 3: 预算控制

```python
from llm_cost_optimization_scripts import BudgetManager, BudgetConfig

budget = BudgetManager(BudgetConfig(daily_limit=10.0))

async def safe_llm_call(prompt):
    tokens = TokenCounter.count_tokens(prompt)
    estimated_cost = tokens * 0.000002  # gpt-3.5 价格
    
    if not budget.check_budget(estimated_cost):
        # 预算不足，降级到更便宜的模型
        return await call_llm(prompt, model="gpt-3.5-turbo")
    
    response = await call_llm(prompt, model="gpt-4")
    actual_cost = calculate_cost(prompt, response, "gpt-4")
    budget.record_spend("gpt-4", tokens, actual_cost)
    
    return response
```

---

## 🎯 优化效果

### 成本对比示例

| 优化项 | 未优化 | 优化后 | 节省 |
|--------|--------|--------|------|
| 单日请求数 | 10,000 | 10,000 | - |
| 平均 tokens/请求 | 500 | 300 | 40% |
| 缓存命中率 | 0% | 40% | - |
| 实际 API 调用 | 10,000 | 6,000 | 40% |
| 模型成本 | $20.00 | $2.00 | 90% |
| **总成本** | **$20.00** | **$2.00** | **90%** |

### 性能指标

- **缓存命中率**: 30-50%
- **Token 减少**: 20-40%
- **延迟改善**: 60-80%（缓存命中时）
- **成本降低**: 70-90%

---

## 🔧 高级功能

### 语义缓存

```python
from sentence_transformers import SentenceTransformer
import faiss

# 缓存相似问题的答案
encoder = SentenceTransformer('all-MiniLM-L6-v2')
index = faiss.IndexFlatL2(384)

def find_similar_response(prompt):
    embedding = encoder.encode(prompt)
    distances, indices = index.search([embedding], 1)
    
    if distances[0][0] < 0.85:
        return cached_responses[indices[0][0]]
    return None
```

### A/B 测试

```python
from llm_cost_optimization_scripts import ModelRouter

router = ModelRouter()

# 测试不同模型
for prompt in test_prompts:
    model_a = router.select_model(prompt)
    model_b = "gpt-4"
    
    result_a = await call_llm(prompt, model_a)
    result_b = await call_llm(prompt, model_b)
    
    quality_a = evaluate_quality(result_a)
    quality_b = evaluate_quality(result_b)
    
    router.record_performance(
        model_a, "task", quality_a, cost_a
    )
```

### 动态降级

```python
async def adaptive_call(prompt):
    # 先用便宜模型
    result = await call_llm(prompt, "gpt-3.5-turbo")
    quality = assess_quality(result)
    
    # 质量不够就用贵的
    if quality < 0.7:
        result = await call_llm(prompt, "gpt-4")
    
    return result
```

---

## 📈 监控与分析

### 启用监控

```python
from llm_cost_optimization_scripts import LLMMetrics

metrics = LLMMetrics()

# 记录每次请求
metrics.record_request(
    tokens=1500,
    cost=0.05,
    latency=1.2,
    cache_hit=False
)

# 获取摘要
summary = metrics.get_summary()
print(summary)

# 导出报告
metrics.export_to_json("metrics_report.json")
```

### 关键指标

```json
{
  "total_requests": 1000,
  "total_tokens": 1500000,
  "total_cost": 50.00,
  "cache_hit_rate": 35.0,
  "avg_latency": 1.2,
  "tokens_per_dollar": 30000
}
```

---

## 🎓 最佳实践

### 1. 从小开始
- 先启用内存缓存
- 逐步添加其他优化
- 监控效果后再调整

### 2. 持续优化
- 定期查看缓存命中率
- 分析成本趋势
- 调整模型路由策略

### 3. 质量优先
- 不要为了省钱牺牲质量
- 使用 A/B 测试验证
- 收集用户反馈

### 4. 监控告警
- 设置预算阈值
- 配置告警通知
- 定期审查报告

---

## 🐛 故障排查

### 缓存命中率低

**问题**: 缓存命中率 < 20%

**解决方案**:
```python
# 增加 TTL
cache.set(prompt, model, response, ttl=7200)

# 增加缓存大小
cache = SimpleMemoryCache(max_size=5000)

# 启用语义缓存
semantic_cache = SemanticCache()
```

### 成本仍然过高

**问题**: 成本降低不明显

**解决方案**:
```python
# 启用预算模式
model = router.select_model(prompt, budget_mode=True)

# 压缩 prompt
compressed = PromptOptimizer.compress_prompt(prompt)

# 限制输出长度
max_tokens = task_token_limits.get(task_type, 500)
```

### 预算告警

**问题**: 频繁收到预算告警

**解决方案**:
```python
# 增加预算限制
config = BudgetConfig(daily_limit=20.0)

# 查看成本来源
stats = budget.get_stats()
print(stats)

# 优化高频任务
high_cost_tasks = identify_high_cost_tasks()
optimize_tasks(high_cost_tasks)
```

---

## 📝 更新日志

### v1.0 (2026-03-25)
- ✅ 完整的优化策略文档
- ✅ Python 实现代码
- ✅ 快速参考卡片
- ✅ 配置模板
- ✅ 使用示例

---

## 🤝 贡献

欢迎提交问题和改进建议！

---

## 📄 许可证

MIT License

---

## 📞 支持

如有问题，请参考：
- 完整文档：`llm-cost-optimization.md`
- 快速参考：`llm-cost-optimization-cheatsheet.md`
- 代码示例：`llm-cost-optimization-scripts.py`

---

**开始优化你的 LLM 成本吧！** 🚀
