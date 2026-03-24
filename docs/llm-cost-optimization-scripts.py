#!/usr/bin/env python3
"""
LLM API 成本优化 - 实用脚本集合

包含可直接使用的代码示例，涵盖：
- Token 计数与优化
- 缓存实现
- 模型路由
- 预算管理
"""

import hashlib
import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from functools import wraps
import numpy as np

# ============================================================================
# 1. Token 计数与优化
# ============================================================================

class TokenCounter:
    """简单的 Token 计数器（基于估算）"""
    
    @staticmethod
    def count_tokens(text: str, language: str = "auto") -> int:
        """
        估算文本的 token 数量
        
        Args:
            text: 输入文本
            language: 语言类型 (auto, english, chinese, code)
        
        Returns:
            估算的 token 数量
        """
        if not text:
            return 0
        
        if language == "auto":
            # 自动检测语言
            chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            if chinese_chars > len(text) * 0.3:
                language = "chinese"
            else:
                language = "english"
        
        if language == "chinese":
            # 中文：1 token ≈ 1.5 字符
            return int(len(text) / 1.5)
        elif language == "code":
            # 代码：1 token ≈ 3 字符
            return int(len(text) / 3)
        else:
            # 英文：1 token ≈ 4 字符
            return int(len(text) / 4)
    
    @staticmethod
    def estimate_cost(
        prompt: str, 
        response: str = "", 
        model: str = "gpt-3.5-turbo"
    ) -> float:
        """
        估算 API 调用成本（美元）
        
        Args:
            prompt: 输入提示词
            response: 输出响应（可选）
            model: 模型名称
        
        Returns:
            估算成本（美元）
        """
        # 价格表（输入/输出，每 1K tokens）
        PRICES = {
            "gpt-3.5-turbo": (0.002, 0.002),
            "gpt-4": (0.03, 0.06),
            "claude-3-sonnet": (0.003, 0.015),
            "claude-3-opus": (0.015, 0.075),
        }
        
        if model not in PRICES:
            model = "gpt-3.5-turbo"
        
        input_price, output_price = PRICES[model]
        
        input_tokens = TokenCounter.count_tokens(prompt)
        output_tokens = TokenCounter.count_tokens(response)
        
        input_cost = (input_tokens / 1000) * input_price
        output_cost = (output_tokens / 1000) * output_price
        
        return input_cost + output_cost


class PromptOptimizer:
    """Prompt 优化器"""
    
    @staticmethod
    def compress_prompt(prompt: str, target_reduction: float = 0.5) -> str:
        """
        压缩 prompt
        
        Args:
            prompt: 原始 prompt
            target_reduction: 目标压缩比例 (0.5 = 压缩到 50%)
        
        Returns:
            压缩后的 prompt
        """
        # 移除冗余词
        filler_words = [
            "好的", "没问题", "让我", "为您", "我会", "可以",
            "please", "I will", "let me", "for you", "can"
        ]
        
        lines = prompt.split('\n')
        compressed = []
        
        for line in lines:
            # 移除每行开头的填充词
            for filler in filler_words:
                if line.strip().lower().startswith(filler.lower()):
                    line = line[len(filler):].strip()
                    break
            
            # 压缩空行
            if line.strip():
                compressed.append(line)
        
        return '\n'.join(compressed)
    
    @staticmethod
    def extract_templates(prompt: str) -> List[str]:
        """提取 prompt 中的可复用模板"""
        # 简单实现：提取包含占位符的部分
        templates = []
        for line in prompt.split('\n'):
            if '{' in line and '}' in line:
                templates.append(line.strip())
        return templates


# ============================================================================
# 2. 缓存实现
# ============================================================================

@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: str
    timestamp: float
    hit_count: int = 0
    ttl: int = 3600  # 默认 1 小时


class SimpleMemoryCache:
    """简单的内存缓存"""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
    
    def _generate_key(self, prompt: str, model: str, params: dict) -> str:
        """生成缓存键"""
        data = {
            "prompt": prompt,
            "model": model,
            "params": params
        }
        return hashlib.md5(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()
    
    def get(self, prompt: str, model: str, params: dict = None) -> Optional[str]:
        """获取缓存"""
        if params is None:
            params = {}
        
        key = self._generate_key(prompt, model, params)
        
        if key in self.cache:
            entry = self.cache[key]
            
            # 检查是否过期
            if time.time() - entry.timestamp > entry.ttl:
                del self.cache[key]
                return None
            
            # 更新命中次数
            entry.hit_count += 1
            return entry.value
        
        return None
    
    def set(self, prompt: str, model: str, value: str, params: dict = None, ttl: int = 3600):
        """设置缓存"""
        if params is None:
            params = {}
        
        key = self._generate_key(prompt, model, params)
        
        # 如果缓存已满，删除最少使用的条目
        if len(self.cache) >= self.max_size:
            lru_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].hit_count
            )
            del self.cache[lru_key]
        
        self.cache[key] = CacheEntry(
            key=key,
            value=value,
            timestamp=time.time(),
            ttl=ttl
        )
    
    def clear_expired(self):
        """清除过期缓存"""
        now = time.time()
        expired_keys = [
            k for k, v in self.cache.items()
            if now - v.timestamp > v.ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]
    
    def get_stats(self) -> dict:
        """获取缓存统计"""
        total_hits = sum(v.hit_count for v in self.cache.values())
        return {
            "size": len(self.cache),
            "total_hits": total_hits,
            "max_size": self.max_size
        }


def cached_llm_call(ttl: int = 3600):
    """
    LLM 调用装饰器，自动缓存结果
    
    Args:
        ttl: 缓存时间（秒）
    """
    cache = SimpleMemoryCache()
    
    def decorator(func):
        @wraps(func)
        async def wrapper(prompt: str, model: str = "gpt-3.5-turbo", **kwargs):
            # 尝试从缓存获取
            cached = cache.get(prompt, model, kwargs)
            if cached:
                return cached
            
            # 调用实际函数
            result = await func(prompt, model, **kwargs)
            
            # 存入缓存
            cache.set(prompt, model, result, kwargs, ttl)
            
            return result
        
        return wrapper
    return decorator


# ============================================================================
# 3. 模型路由
# ============================================================================

@dataclass
class TaskType:
    """任务类型定义"""
    name: str
    complexity: str  # low, medium, high
    primary_model: str
    fallback_model: str
    cost_sensitivity: float  # 0-1, 1 = 最敏感


class ModelRouter:
    """智能模型路由器"""
    
    def __init__(self):
        self.task_types = self._init_task_types()
        self.performance_history = {}
    
    def _init_task_types(self) -> Dict[str, TaskType]:
        """初始化任务类型"""
        return {
            "simple_qa": TaskType(
                name="简单问答",
                complexity="low",
                primary_model="gpt-3.5-turbo",
                fallback_model="gpt-3.5-turbo",
                cost_sensitivity=1.0
            ),
            "code_gen": TaskType(
                name="代码生成",
                complexity="high",
                primary_model="gpt-4",
                fallback_model="claude-3-sonnet",
                cost_sensitivity=0.5
            ),
            "summarization": TaskType(
                name="摘要",
                complexity="medium",
                primary_model="gpt-3.5-turbo",
                fallback_model="claude-3-sonnet",
                cost_sensitivity=0.8
            ),
            "creative_writing": TaskType(
                name="创意写作",
                complexity="high",
                primary_model="claude-3-opus",
                fallback_model="claude-3-sonnet",
                cost_sensitivity=0.3
            ),
        }
    
    def classify_task(self, prompt: str) -> str:
        """
        分类任务类型
        
        Args:
            prompt: 输入 prompt
        
        Returns:
            任务类型标识
        """
        prompt_lower = prompt.lower()
        
        # 关键词匹配
        if any(k in prompt_lower for k in ["code", "函数", "编程", "写一个"]):
            return "code_gen"
        elif any(k in prompt_lower for k in ["摘要", "总结", "概括"]):
            return "summarization"
        elif any(k in prompt_lower for k in ["故事", "创意", "想象", "创作"]):
            return "creative_writing"
        else:
            return "simple_qa"
    
    def select_model(
        self, 
        prompt: str, 
        budget_mode: bool = False
    ) -> str:
        """
        选择最合适的模型
        
        Args:
            prompt: 输入 prompt
            budget_mode: 是否启用预算模式（优先选择便宜模型）
        
        Returns:
            模型名称
        """
        task_type = self.classify_task(prompt)
        task = self.task_types[task_type]
        
        if budget_mode and task.cost_sensitivity > 0.7:
            return task.fallback_model
        
        return task.primary_model
    
    def record_performance(
        self, 
        model: str, 
        task: str, 
        quality: float,
        cost: float
    ):
        """记录模型性能"""
        if model not in self.performance_history:
            self.performance_history[model] = []
        
        self.performance_history[model].append({
            "task": task,
            "quality": quality,
            "cost": cost,
            "timestamp": time.time()
        })
    
    def get_best_model(self, task: str) -> str:
        """基于历史数据选择最佳模型"""
        task_performance = []
        
        for model, records in self.performance_history.items():
            task_records = [r for r in records if r["task"] == task]
            if task_records:
                avg_quality = np.mean([r["quality"] for r in task_records])
                avg_cost = np.mean([r["cost"] for r in task_records])
                task_performance.append({
                    "model": model,
                    "quality": avg_quality,
                    "cost": avg_cost,
                    "value": avg_quality / avg_cost  # 性价比
                })
        
        if not task_performance:
            # 无历史数据，使用默认配置
            return self.task_types.get(task, self.task_types["simple_qa"]).primary_model
        
        # 选择性价比最高的模型
        best = max(task_performance, key=lambda x: x["value"])
        return best["model"]


# ============================================================================
# 4. 预算管理
# ============================================================================

@dataclass
class BudgetConfig:
    """预算配置"""
    daily_limit: float
    alert_threshold: float = 0.8  # 80% 时警告
    shutdown_threshold: float = 1.0  # 100% 时停止


class BudgetManager:
    """预算管理器"""
    
    def __init__(self, config: BudgetConfig):
        self.config = config
        self.daily_spend = 0.0
        self.spend_log = []
        self.reset_time = time.time()
    
    def check_budget(self, estimated_cost: float) -> bool:
        """
        检查是否可以执行请求
        
        Args:
            estimated_cost: 估算成本
        
        Returns:
            是否允许执行
        """
        # 检查是否需要重置每日预算
        if time.time() - self.reset_time > 86400:  # 24 小时
            self._reset_daily()
        
        if self.daily_spend + estimated_cost > self.config.daily_limit:
            return False
        
        return True
    
    def record_spend(self, model: str, tokens: int, cost: float):
        """记录实际花费"""
        self.daily_spend += cost
        
        self.spend_log.append({
            "timestamp": time.time(),
            "model": model,
            "tokens": tokens,
            "cost": cost,
            "daily_total": self.daily_spend
        })
        
        # 检查是否需要警告
        if self.daily_spend >= self.config.daily_limit * self.config.alert_threshold:
            self._send_alert()
    
    def _reset_daily(self):
        """重置每日预算"""
        self.daily_spend = 0.0
        self.reset_time = time.time()
    
    def _send_alert(self):
        """发送预算警告"""
        print(f"⚠️ 预算警告：已使用 {self.daily_spend:.2f}/{self.config.daily_limit:.2f}")
    
    def get_stats(self) -> dict:
        """获取预算统计"""
        return {
            "daily_spend": self.daily_spend,
            "daily_limit": self.config.daily_limit,
            "usage_percentage": (self.daily_spend / self.config.daily_limit) * 100,
            "remaining": self.config.daily_limit - self.daily_spend,
            "total_requests": len(self.spend_log)
        }


# ============================================================================
# 5. 批处理
# ============================================================================

class BatchProcessor:
    """批量处理器"""
    
    def __init__(self, batch_size: int = 10, delay: float = 1.0):
        self.batch_size = batch_size
        self.delay = delay
        self.batch = []
        self.processing = False
    
    async def add_request(
        self, 
        prompt: str, 
        callback: Callable[[str], Any]
    ):
        """
        添加请求到批处理队列
        
        Args:
            prompt: 请求 prompt
            callback: 回调函数，接收 LLM 响应
        """
        self.batch.append({"prompt": prompt, "callback": callback})
        
        if len(self.batch) >= self.batch_size and not self.processing:
            await self._process_batch()
    
    async def _process_batch(self):
        """处理当前批次"""
        if not self.batch:
            return
        
        self.processing = True
        batch = self.batch
        self.batch = []
        
        # 并发处理
        tasks = [
            self._call_llm(item["prompt"])
            for item in batch
        ]
        responses = await asyncio.gather(*tasks)
        
        # 调用回调
        for item, response in zip(batch, responses):
            item["callback"](response)
        
        # 速率限制
        await asyncio.sleep(self.delay)
        
        self.processing = False
    
    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM API（需要实现）"""
        # 这里应该是实际的 API 调用
        # 示例：await openai.ChatCompletion.acreate(...)
        return f"Response for: {prompt[:50]}..."


# ============================================================================
# 6. 监控与分析
# ============================================================================

class LLMMetrics:
    """LLM 性能指标收集器"""
    
    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "latencies": [],
            "errors": 0
        }
    
    def record_request(
        self, 
        tokens: int, 
        cost: float, 
        latency: float,
        cache_hit: bool = False
    ):
        """记录请求指标"""
        self.metrics["total_requests"] += 1
        self.metrics["total_tokens"] += tokens
        self.metrics["total_cost"] += cost
        self.metrics["latencies"].append(latency)
        
        if cache_hit:
            self.metrics["cache_hits"] += 1
        else:
            self.metrics["cache_misses"] += 1
    
    def record_error(self):
        """记录错误"""
        self.metrics["errors"] += 1
    
    def get_summary(self) -> dict:
        """获取指标摘要"""
        total = self.metrics["total_requests"]
        if total == 0:
            return {}
        
        return {
            "total_requests": total,
            "total_tokens": self.metrics["total_tokens"],
            "total_cost": self.metrics["total_cost"],
            "avg_tokens_per_request": self.metrics["total_tokens"] / total,
            "avg_cost_per_request": self.metrics["total_cost"] / total,
            "cache_hit_rate": (
                self.metrics["cache_hits"] / total * 100
                if total > 0 else 0
            ),
            "avg_latency": np.mean(self.metrics["latencies"]),
            "p99_latency": np.percentile(self.metrics["latencies"], 99),
            "error_rate": self.metrics["errors"] / total * 100 if total > 0 else 0,
            "tokens_per_dollar": (
                self.metrics["total_tokens"] / self.metrics["total_cost"]
                if self.metrics["total_cost"] > 0 else 0
            )
        }
    
    def export_to_json(self, filepath: str):
        """导出指标到 JSON 文件"""
        with open(filepath, 'w') as f:
            json.dump(self.get_summary(), f, indent=2)


# ============================================================================
# 7. 完整示例
# ============================================================================

async def example_usage():
    """完整使用示例"""
    
    # 1. 初始化组件
    cache = SimpleMemoryCache(max_size=100)
    router = ModelRouter()
    budget_config = BudgetConfig(daily_limit=10.0)
    budget = BudgetManager(budget_config)
    metrics = LLMMetrics()
    
    # 2. 模拟一些请求
    test_prompts = [
        "写一个 Python 函数，实现快速排序",
        "总结这篇文章的主要内容",
        "今天天气怎么样？",
        "创建一个简单的故事",
    ]
    
    for i, prompt in enumerate(test_prompts):
        print(f"\n--- 请求 {i+1} ---")
        print(f"Prompt: {prompt[:50]}...")
        
        # Token 计数
        tokens = TokenCounter.count_tokens(prompt)
        print(f"Tokens: {tokens}")
        
        # 模型选择
        model = router.select_model(prompt, budget_mode=False)
        print(f"Selected model: {model}")
        
        # 估算成本
        estimated_cost = TokenCounter.estimate_cost(prompt, model=model)
        print(f"Estimated cost: ${estimated_cost:.4f}")
        
        # 预算检查
        if not budget.check_budget(estimated_cost):
            print("❌ 预算不足，跳过")
            continue
        
        # 检查缓存
        cached = cache.get(prompt, model)
        if cached:
            print(f"✅ 缓存命中")
            response = cached
            is_cache_hit = True
        else:
            print(f"❌ 缓存未命中")
            # 模拟 API 调用
            await asyncio.sleep(0.1)  # 模拟延迟
            response = f"Mock response from {model} for: {prompt[:30]}..."
            is_cache_hit = False
            
            # 存入缓存
            cache.set(prompt, model, response)
        
        # 记录花费
        actual_cost = TokenCounter.estimate_cost(prompt, response, model)
        budget.record_spend(model, tokens + TokenCounter.count_tokens(response), actual_cost)
        
        # 记录指标
        metrics.record_request(
            tokens=tokens,
            cost=actual_cost,
            latency=0.1,
            cache_hit=is_cache_hit
        )
        
        print(f"Response: {response[:50]}...")
        print(f"Actual cost: ${actual_cost:.4f}")
    
    # 3. 输出摘要
    print("\n" + "="*50)
    print("摘要")
    print("="*50)
    print(json.dumps(metrics.get_summary(), indent=2))
    print("\n预算状态:")
    print(json.dumps(budget.get_stats(), indent=2))
    print("\n缓存统计:")
    print(json.dumps(cache.get_stats(), indent=2))


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())
