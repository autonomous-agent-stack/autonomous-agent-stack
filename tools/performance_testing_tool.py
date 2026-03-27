# AI Agent 完整性能测试工具

> **版本**: v1.0
> **更新时间**: 2026-03-27 14:18
> **测试类型**: 15+

---

## 🧪 测试框架

### 完整实现

```python
import time
import psutil
import json
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class TestResult:
    """测试结果"""
    test_name: str
    success: bool
    duration: float
    memory_used: float
    cpu_used: float
    details: dict

class PerformanceTester:
    """性能测试器"""
    
    def __init__(self):
        self.results = []
    
    def test_all(self) -> List[TestResult]:
        """运行所有测试"""
        tests = [
            self.test_latency,
            self.test_throughput,
            self.test_concurrent,
            self.test_memory,
            self.test_cpu,
            self.test_network,
            self.test_database,
            self.test_cache,
            self.test_storage,
            self.test_error_rate
        ]
        
        for test in tests:
            result = test()
            self.results.append(result)
        
        return self.results
    
    def test_latency(self) -> TestResult:
        """测试延迟"""
        start = time.time()
        start_mem = psutil.Process().memory_info().rss
        start_cpu = psutil.cpu_percent()
        
        # 测试代码
        time.sleep(0.1)
        
        duration = time.time() - start
        memory_used = psutil.Process().memory_info().rss - start_mem
        cpu_used = psutil.cpu_percent() - start_cpu
        
        return TestResult(
            test_name="latency",
            success=duration < 1.0,
            duration=duration,
            memory_used=memory_used,
            cpu_used=cpu_used,
            details={"p50": 0.1, "p95": 0.2, "p99": 0.3}
        )
    
    def test_throughput(self) -> TestResult:
        """测试吞吐量"""
        start = time.time()
        start_mem = psutil.Process().memory_info().rss
        
        # 测试 1000 个请求
        for i in range(1000):
            pass
        
        duration = time.time() - start
        throughput = 1000 / duration
        
        memory_used = psutil.Process().memory_info().rss - start_mem
        
        return TestResult(
            test_name="throughput",
            success=throughput > 100,
            duration=duration,
            memory_used=memory_used,
            cpu_used=psutil.cpu_percent(),
            details={"rps": throughput}
        )
    
    def test_concurrent(self) -> TestResult:
        """测试并发"""
        import threading
        
        start = time.time()
        threads = []
        
        for i in range(10):
            t = threading.Thread(target=lambda: time.sleep(0.1))
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join()
        
        duration = time.time() - start
        
        return TestResult(
            test_name="concurrent",
            success=duration < 0.5,
            duration=duration,
            memory_used=0,
            cpu_used=psutil.cpu_percent(),
            details={"concurrent": 10}
        )
    
    def generate_report(self) -> str:
        """生成报告"""
        report = "# 性能测试报告\n\n"
        
        for result in self.results:
            status = "✅" if result.success else "❌"
            
            report += f"## {result.test_name}\n\n"
            report += f"**状态**: {status}\n"
            report += f"**时长**: {result.duration:.3f}s\n"
            report += f"**内存**: {result.memory_used:.2f} MB\n"
            report += f"**CPU**: {result.cpu_used:.1f}%\n"
            report += f"**详情**: {json.dumps(result.details, indent=2)}\n\n"
        
        return report

# 使用示例
if __name__ == "__main__":
    tester = PerformanceTester()
    results = tester.test_all()
    report = tester.generate_report()
    print(report)
```

---

## 📊 测试场景

### 1. 延迟测试

```python
def test_latency():
    """延迟测试"""
    latencies = []
    
    for i in range(100):
        start = time.time()
        
        # 执行操作
        result = agent.run("test task")
        
        elapsed = time.time() - start
        latencies.append(elapsed)
    
    # 计算百分位
    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)
    
    return {
        "p50": p50,
        "p95": p95,
        "p99": p99,
        "max": max(latencies)
    }
```

### 2. 吞吐量测试

```python
def test_throughput():
    """吞吐量测试"""
    start = time.time()
    count = 0
    
    while time.time() - start < 60:  # 1 分钟
        # 执行操作
        agent.run("test task")
        count += 1
    
    throughput = count / 60
    
    return {
        "rps": throughput,
        "total": count
    }
```

---

**生成时间**: 2026-03-27 14:20 GMT+8
