# AI Agent 性能基准测试

> **版本**: v1.0
> **更新时间**: 2026-03-27
> **测试场景**: 10+

---

## 📊 基准测试框架

### 测试指标

| 指标 | 说明 | 目标值 |
|------|------|--------|
| **响应时间** | 首次响应时间 | < 2s |
| **吞吐量** | 每秒请求数 | > 100/s |
| **准确率** | 任务成功率 | > 90% |
| **成本效率** | 每千次调用成本 | < $0.5 |
| **并发能力** | 并发用户数 | > 100 |

---

## 🧪 基准测试代码

```python
"""
AI Agent 性能基准测试
"""

import time
import asyncio
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass
import matplotlib.pyplot as plt

@dataclass
class BenchmarkResult:
    """基准测试结果"""
    test_name: str
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    success_rate: float
    throughput: float
    errors: List[str]

class AgentBenchmark:
    """Agent 基准测试"""
    
    def __init__(self, agent):
        self.agent = agent
        self.results = []
    
    def run_test(
        self,
        test_name: str,
        tasks: List[str],
        warmup_runs: int = 3,
        test_runs: int = 10
    ) -> BenchmarkResult:
        """
        运行测试
        
        Args:
            test_name: 测试名称
            tasks: 测试任务列表
            warmup_runs: 预热次数
            test_runs: 测试次数
        """
        # 1. 预热
        print(f"🔥 预热中 ({warmup_runs} 次)...")
        for _ in range(warmup_runs):
            for task in tasks:
                self.agent.run(task)
        
        # 2. 正式测试
        print(f"📊 正式测试中 ({test_runs} 次)...")
        times = []
        errors = []
        success_count = 0
        
        start_time = time.time()
        
        for i in range(test_runs):
            for task in tasks:
                try:
                    task_start = time.time()
                    result = self.agent.run(task)
                    task_time = time.time() - task_start
                    
                    times.append(task_time)
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Run {i+1}: {str(e)}")
        
        total_time = time.time() - start_time
        
        # 3. 计算指标
        avg_time = statistics.mean(times) if times else 0
        min_time = min(times) if times else 0
        max_time = max(times) if times else 0
        success_rate = success_count / (test_runs * len(tasks))
        throughput = (test_runs * len(tasks)) / total_time
        
        result = BenchmarkResult(
            test_name=test_name,
            total_time=total_time,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            success_rate=success_rate,
            throughput=throughput,
            errors=errors
        )
        
        self.results.append(result)
        
        return result
    
    async def run_concurrent_test(
        self,
        test_name: str,
        tasks: List[str],
        concurrent_users: int = 10
    ) -> BenchmarkResult:
        """
        并发测试
        
        Args:
            test_name: 测试名称
            tasks: 测试任务
            concurrent_users: 并发用户数
        """
        print(f"🚀 并发测试中 ({concurrent_users} 用户)...")
        
        times = []
        errors = []
        success_count = 0
        
        async def worker(task: str):
            nonlocal success_count
            
            try:
                start = time.time()
                result = await self.agent.async_run(task)
                elapsed = time.time() - start
                
                times.append(elapsed)
                success_count += 1
                
            except Exception as e:
                errors.append(str(e))
        
        # 启动并发任务
        start_time = time.time()
        
        coroutines = []
        for task in tasks:
            for _ in range(concurrent_users):
                coroutines.append(worker(task))
        
        await asyncio.gather(*coroutines)
        
        total_time = time.time() - start_time
        
        # 计算指标
        avg_time = statistics.mean(times) if times else 0
        min_time = min(times) if times else 0
        max_time = max(times) if times else 0
        success_rate = success_count / (len(tasks) * concurrent_users)
        throughput = success_count / total_time
        
        result = BenchmarkResult(
            test_name=f"{test_name}_concurrent_{concurrent_users}",
            total_time=total_time,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            success_rate=success_rate,
            throughput=throughput,
            errors=errors
        )
        
        self.results.append(result)
        
        return result
    
    def generate_report(self) -> str:
        """生成报告"""
        report = "# Agent 性能基准测试报告\n\n"
        report += f"> **测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        report += "---\n\n"
        
        for result in self.results:
            report += f"## {result.test_name}\n\n"
            report += f"| 指标 | 数值 |\n"
            report += f"|------|------|\n"
            report += f"| **平均响应时间** | {result.avg_time:.3f}s |\n"
            report += f"| **最小响应时间** | {result.min_time:.3f}s |\n"
            report += f"| **最大响应时间** | {result.max_time:.3f}s |\n"
            report += f"| **总耗时** | {result.total_time:.2f}s |\n"
            report += f"| **成功率** | {result.success_rate*100:.1f}% |\n"
            report += f"| **吞吐量** | {result.throughput:.2f} req/s |\n"
            
            if result.errors:
                report += f"\n**错误数**: {len(result.errors)}\n"
            
            report += "\n---\n\n"
        
        return report
    
    def plot_results(self, output_file: str = "benchmark_results.png"):
        """绘制结果图表"""
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # 1. 响应时间对比
        test_names = [r.test_name for r in self.results]
        avg_times = [r.avg_time for r in self.results]
        
        axes[0, 0].bar(test_names, avg_times, color='skyblue')
        axes[0, 0].set_title('平均响应时间')
        axes[0, 0].set_ylabel('时间 (s)')
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # 2. 成功率对比
        success_rates = [r.success_rate * 100 for r in self.results]
        
        axes[0, 1].bar(test_names, success_rates, color='lightgreen')
        axes[0, 1].set_title('成功率')
        axes[0, 1].set_ylabel('成功率 (%)')
        axes[0, 1].tick_params(axis='x', rotation=45)
        axes[0, 1].set_ylim(0, 100)
        
        # 3. 吞吐量对比
        throughputs = [r.throughput for r in self.results]
        
        axes[1, 0].bar(test_names, throughputs, color='lightcoral')
        axes[1, 0].set_title('吞吐量')
        axes[1, 0].set_ylabel('请求/秒')
        axes[1, 0].tick_params(axis='x', rotation=45)
        
        # 4. 响应时间分布
        axes[1, 1].boxplot([
            [r.min_time, r.avg_time, r.max_time]
            for r in self.results
        ], labels=test_names)
        axes[1, 1].set_title('响应时间分布')
        axes[1, 1].set_ylabel('时间 (s)')
        axes[1, 1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300)
        print(f"✅ 图表已保存到 {output_file}")


# 使用示例
if __name__ == "__main__":
    from your_agent import YourAgent
    
    # 创建 Agent
    agent = YourAgent(model="claude-3-opus-20240229")
    
    # 创建基准测试
    benchmark = AgentBenchmark(agent)
    
    # 测试任务
    tasks = [
        "什么是 Python？",
        "如何学习编程？",
        "推荐一些 AI 学习资源"
    ]
    
    # 1. 单用户测试
    result1 = benchmark.run_test(
        test_name="单用户测试",
        tasks=tasks,
        warmup_runs=3,
        test_runs=10
    )
    
    # 2. 并发测试
    result2 = asyncio.run(benchmark.run_concurrent_test(
        test_name="并发测试",
        tasks=tasks,
        concurrent_users=10
    ))
    
    # 生成报告
    report = benchmark.generate_report()
    with open("benchmark_report.md", 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 绘制图表
    benchmark.plot_results()
    
    print("\n📊 基准测试完成！")
```

---

## 📈 标准测试场景

### 场景 1: 简单问答

**测试内容**: 100 个简单问题

**预期结果**:
- 平均响应时间: < 1s
- 成功率: > 98%
- 吞吐量: > 50/s

### 场景 2: 复杂推理

**测试内容**: 50 个复杂问题

**预期结果**:
- 平均响应时间: < 5s
- 成功率: > 90%
- 吞吐量: > 10/s

### 场景 3: 工具调用

**测试内容**: 100 次工具调用

**预期结果**:
- 平均响应时间: < 3s
- 成功率: > 95%
- 吞吐量: > 20/s

### 场景 4: 多轮对话

**测试内容**: 20 个多轮对话（每轮 5 次）

**预期结果**:
- 平均响应时间: < 2s
- 成功率: > 95%
- 吞吐量: > 30/s

### 场景 5: 并发压力

**测试内容**: 100 并发用户

**预期结果**:
- 平均响应时间: < 3s
- 成功率: > 90%
- 吞吐量: > 100/s

---

**生成时间**: 2026-03-27 13:15 GMT+8
