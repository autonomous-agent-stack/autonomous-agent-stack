# 多智能体系统快速参考手册

> **版本**: v0.1
> **日期**: 2026-03-25
> **状态**: 🚧 进行中

---

## 📋 目录

1. [架构模式速查](#架构模式速查)
2. [算法实现模板](#算法实现模板)
3. [代码片段库](#代码片段库)
4. [常见问题排查](#常见问题排查)
5. [性能调优清单](#性能调优清单)

---

## 架构模式速查

### 1. 协作模式选择指南

| 场景 | 推荐模式 | 关键优势 | 实现难度 |
|------|---------|---------|---------|
| **顺序处理任务** | Pipeline | 流程清晰，易于调试 | ⭐⭐ |
| **专家协作** | Hierarchical | 责任明确，便于管理 | ⭐⭐⭐ |
| **实时协作** | Mesh | 低延迟，去中心化 | ⭐⭐⭐⭐ |
| **复杂任务分解** | Fractal | 自然表达，支持并行 | ⭐⭐⭐⭐⭐ |

### 2. 通信协议选择

| 特性 | 同步 | 异步 | 消息队列 | 发布订阅 |
|------|------|------|---------|---------|
| **实时性** | 高 | 中 | 低 | 低 |
| **可靠性** | 中 | 中 | 高 | 中 |
| **扩展性** | 低 | 中 | 高 | 高 |
| **复杂度** | 低 | 低 | 中 | 中 |
| **适用场景** | 简单请求 | 事件驱动 | 任务队列 | 广播通知 |

### 3. 共识算法选择

| 算法 | 一致性 | 性能 | 容错 | 适用场景 |
|------|-------|------|------|---------|
| Raft | 强 | 中 | f < N/2 | 通用分布式系统 |
| Paxos | 强 | 低 | f < N/2 | 金融系统 |
| Gossip | 最终 | 高 | f < N | 大规模P2P |
| PBFT | 强 | 低 | f < N/3 | 区块链联盟链 |

---

## 算法实现模板

### 模板1：基础Agent类

```python
from abc import ABC, abstractmethod
from typing import Dict, Any
import asyncio

class BaseAgent(ABC):
    """Agent基类"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.state = {}
        self.message_queue = asyncio.Queue()
    
    @abstractmethod
    async def process_message(self, message: Dict) -> Any:
        """处理消息（抽象方法）"""
        pass
    
    async def start(self):
        """启动Agent"""
        while True:
            message = await self.message_queue.get()
            try:
                result = await self.process_message(message)
                await self.send_response(message, result)
            except Exception as e:
                await self.send_error(message, e)
            finally:
                self.message_queue.task_done()
    
    async def send_response(self, message: Dict, result: Any):
        """发送响应"""
        # 实现消息发送逻辑
        pass
    
    async def send_error(self, message: Dict, error: Exception):
        """发送错误"""
        # 实现错误发送逻辑
        pass
    
    async def receive(self, message: Dict):
        """接收消息"""
        await self.message_queue.put(message)
```

### 模板2：编排器Agent

```python
from typing import List, Dict
import asyncio

class OrchestratorAgent(BaseAgent):
    """编排器Agent"""
    
    def __init__(self, agent_id: str, workers: List[BaseAgent]):
        super().__init__(agent_id)
        self.workers = {w.agent_id: w for w in workers}
        self.task_queue = asyncio.Queue()
        self.active_tasks = {}
    
    async def process_message(self, message: Dict) -> Dict:
        """处理任务请求"""
        task_id = message['task_id']
        task_type = message['task_type']
        task_input = message['input']
        
        # 选择合适的worker
        worker = self._select_worker(task_type)
        
        # 分配任务
        self.active_tasks[task_id] = {
            'worker': worker.agent_id,
            'status': 'assigned',
            'start_time': asyncio.get_event_loop().time()
        }
        
        # 发送任务给worker
        await worker.receive({
            'type': 'task',
            'task_id': task_id,
            'input': task_input
        })
        
        return {'task_id': task_id, 'status': 'assigned'}
    
    def _select_worker(self, task_type: str) -> BaseAgent:
        """选择worker（简单的负载均衡）"""
        # 实现更复杂的worker选择策略
        available_workers = [
            w for w in self.workers.values()
            if not self._is_busy(w.agent_id)
        ]
        
        if not available_workers:
            raise RuntimeError("无可用worker")
        
        # 简单轮询
        return available_workers[0]
    
    def _is_busy(self, worker_id: str) -> bool:
        """检查worker是否忙碌"""
        for task in self.active_tasks.values():
            if task['worker'] == worker_id and task['status'] == 'assigned':
                return True
        return False
```

### 模板3：工作流引擎

```python
from typing import Dict, List
import asyncio
from collections import defaultdict

class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self):
        self.workflows = {}
        self.execution_history = []
    
    def register_workflow(self, workflow_def: Dict):
        """注册工作流"""
        workflow_id = workflow_def['id']
        
        # 构建依赖图
        tasks = workflow_def['tasks']
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        for task in tasks:
            task_id = task['id']
            in_degree[task_id] = len(task.get('depends_on', []))
            
            for dep in task.get('depends_on', []):
                graph[dep].append(task_id)
        
        # 拓扑排序
        task_order = self._topological_sort(tasks, in_degree, graph)
        
        self.workflows[workflow_id] = {
            'definition': workflow_def,
            'task_order': task_order
        }
    
    def _topological_sort(self, tasks: List[Dict], in_degree: Dict, graph: Dict) -> List[str]:
        """拓扑排序（Kahn算法）"""
        queue = [task['id'] for task in tasks if in_degree[task['id']] == 0]
        sorted_order = []
        
        while queue:
            task_id = queue.pop(0)
            sorted_order.append(task_id)
            
            for neighbor in graph[task_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(sorted_order) != len(tasks):
            raise ValueError("检测到循环依赖")
        
        return sorted_order
    
    async def execute_workflow(self, workflow_id: str, inputs: Dict) -> Dict:
        """执行工作流"""
        if workflow_id not in self.workflows:
            raise ValueError(f"工作流不存在: {workflow_id}")
        
        workflow = self.workflows[workflow_id]
        task_order = workflow['task_order']
        definition = workflow['definition']
        tasks = {t['id']: t for t in definition['tasks']}
        
        completed = set()
        results = {}
        
        # 执行任务
        for task_id in task_order:
            task = tasks[task_id]
            
            # 检查依赖
            if not all(dep in completed for dep in task.get('depends_on', [])):
                continue
            
            # 执行任务
            print(f"执行任务: {task['name']}")
            result = await self._execute_task(task, inputs, results)
            
            completed.add(task_id)
            results[task_id] = result
        
        return results
    
    async def _execute_task(self, task: Dict, inputs: Dict, previous_results: Dict) -> Any:
        """执行单个任务"""
        # 解析输入
        task_inputs = self._resolve_inputs(task.get('inputs', {}), inputs, previous_results)
        
        # 执行任务（这里简化，实际应调用Agent）
        print(f"  输入: {task_inputs}")
        await asyncio.sleep(0.5)  # 模拟执行
        
        return {
            'status': 'success',
            'output': f"Result of {task['name']}"
        }
    
    def _resolve_inputs(self, inputs: Dict, workflow_inputs: Dict, previous_results: Dict) -> Dict:
        """解析输入（支持变量引用）"""
        resolved = {}
        
        for key, value in inputs.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                # 变量引用
                var_path = value[2:-1]
                parts = var_path.split('.')
                
                if parts[0] == 'inputs':
                    resolved[key] = workflow_inputs.get(parts[1])
                elif parts[0] == 'tasks':
                    task_id = parts[1]
                    output_key = parts[3] if len(parts) > 3 else None
                    task_result = previous_results.get(task_id, {})
                    resolved[key] = task_result.get(output_key) if output_key else task_result
            else:
                resolved[key] = value
        
        return resolved
```

---

## 代码片段库

### 片段1：消息传递（基于Redis）

```python
import redis
import json
import asyncio
from typing import Dict, Callable

class RedisMessageBus:
    """基于Redis的消息总线"""
    
    def __init__(self, redis_url: str = 'redis://localhost:6379'):
        self.redis = redis.from_url(redis_url)
        self.subscribers = {}
        self.channels = {}
    
    async def publish(self, channel: str, message: Dict):
        """发布消息"""
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.redis.publish(channel, json.dumps(message))
        )
    
    async def subscribe(self, channel: str, callback: Callable):
        """订阅频道"""
        pubsub = self.redis.pubsub()
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: pubsub.subscribe(channel)
        )
        
        self.channels[channel] = pubsub
        self.subscribers[channel] = callback
        
        # 启动监听任务
        asyncio.create_task(self._listen(channel, pubsub, callback))
    
    async def _listen(self, channel: str, pubsub, callback: Callable):
        """监听频道"""
        while True:
            message = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: pubsub.get_message(timeout=1)
            )
            
            if message and message['type'] == 'message':
                data = json.loads(message['data'])
                await callback(data)
```

### 片段2：分布式锁（基于Redis）

```python
import redis
import uuid
import time

class DistributedLock:
    """分布式锁"""
    
    def __init__(self, redis_client: redis.Redis, lock_key: str, timeout: int = 10):
        self.redis = redis_client
        self.lock_key = lock_key
        self.timeout = timeout
        self.lock_id = str(uuid.uuid4())
        self.acquired = False
    
    def acquire(self, blocking: bool = True, blocking_timeout: int = None) -> bool:
        """获取锁"""
        end_time = time.time() + blocking_timeout if blocking_timeout else 0
        
        while True:
            # 尝试获取锁
            acquired = self.redis.set(
                self.lock_key,
                self.lock_id,
                nx=True,
                ex=self.timeout
            )
            
            if acquired:
                self.acquired = True
                return True
            
            if not blocking:
                return False
            
            if blocking_timeout and time.time() >= end_time:
                return False
            
            time.sleep(0.1)
    
    def release(self) -> bool:
        """释放锁"""
        if not self.acquired:
            return False
        
        # Lua脚本保证原子性
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        result = self.redis.eval(
            lua_script,
            1,
            self.lock_key,
            self.lock_id
        )
        
        if result == 1:
            self.acquired = False
            return True
        
        return False
```

### 片段3：重试装饰器

```python
import asyncio
import functools
from typing import Callable, Any

def retry(max_attempts: int = 3, 
          base_delay: float = 1.0,
          max_delay: float = 60.0,
          jitter: bool = True):
    """重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_error = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    
                    # 最后一次失败，不重试
                    if attempt == max_attempts:
                        break
                    
                    # 计算延迟
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    if jitter:
                        delay = delay * (0.5 + asyncio.get_random() * 0.5)
                    
                    print(f"重试 {attempt}/{max_attempts}, 延迟 {delay:.2f}秒")
                    await asyncio.sleep(delay)
            
            raise last_error
        return wrapper
    return decorator

# 使用示例
@retry(max_attempts=3, base_delay=1.0)
async def unreliable_operation():
    import random
    if random.random() < 0.7:  # 70%概率失败
        raise ValueError("模拟失败")
    return "成功"
```

### 片段4：断路器装饰器

```python
import time
from enum import Enum
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = 'closed'
    OPEN = 'open'
    HALF_OPEN = 'half_open'

class CircuitBreaker:
    """断路器"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
    
    def __call__(self, func: Callable) -> Callable:
        """装饰器"""
        def wrapper(*args, **kwargs) -> Any:
            # 检查断路器状态
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise CircuitBreakerOpenError("断路器打开")
            
            try:
                result = func(*args, **kwargs)
                
                # 成功，重置断路器
                if self.state == CircuitState.HALF_OPEN:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                
                return result
            
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                # 检查是否应该打开断路器
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                
                raise e
        
        return wrapper

class CircuitBreakerOpenError(Exception):
    """断路器打开异常"""
    pass

# 使用示例
breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)

@breaker
def risky_operation():
    import random
    if random.random() < 0.7:
        raise ValueError("操作失败")
    return "成功"
```

### 片段5：任务编排（DAG）

```python
from typing import Dict, List, Set
from collections import defaultdict, deque

class TaskScheduler:
    """任务调度器（基于DAG）"""
    
    def __init__(self):
        self.tasks = {}
        self.dependencies = defaultdict(list)
        self.in_degree = defaultdict(int)
        self.completed = set()
    
    def add_task(self, task_id: str, task_func: Callable, dependencies: List[str] = None):
        """添加任务"""
        self.tasks[task_id] = task_func
        self.in_degree[task_id] = len(dependencies or [])
        
        for dep in (dependencies or []):
            self.dependencies[dep].append(task_id)
    
    async def execute(self) -> Dict[str, Any]:
        """执行所有任务（按拓扑顺序）"""
        # 找到所有入度为0的任务
        queue = deque([task_id for task_id, degree in self.in_degree.items() if degree == 0])
        results = {}
        
        while queue:
            task_id = queue.popleft()
            
            # 执行任务
            print(f"执行任务: {task_id}")
            result = await self.tasks[task_id]()
            results[task_id] = result
            self.completed.add(task_id)
            
            # 更新依赖该任务的其他任务
            for dependent in self.dependencies[task_id]:
                self.in_degree[dependent] -= 1
                if self.in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # 检查是否有循环依赖
        if len(self.completed) != len(self.tasks):
            raise RuntimeError("检测到循环依赖")
        
        return results

# 使用示例
import asyncio

async def task_a():
    await asyncio.sleep(1)
    return "Result A"

async def task_b():
    await asyncio.sleep(2)
    return "Result B"

async def task_c():
    await asyncio.sleep(1)
    return "Result C"

async def task_d():
    await asyncio.sleep(1)
    return "Result D"

async def main():
    scheduler = TaskScheduler()
    
    # 添加任务
    scheduler.add_task('A', task_a, [])
    scheduler.add_task('B', task_b, [])
    scheduler.add_task('C', task_c, ['A'])
    scheduler.add_task('D', task_d, ['B', 'C'])
    
    # 执行
    results = await scheduler.execute()
    print(f"任务结果: {results}")

asyncio.run(main())
```

---

## 常见问题排查

### 问题1：任务卡住，无响应

**可能原因**：
1. 死锁（循环等待）
2. 依赖任务未完成
3. 网络超时
4. Agent崩溃

**排查步骤**：
```python
# 1. 检查任务状态
def check_task_status(executor: WorkflowExecutor, workflow_id: str):
    status = executor.get_workflow_status(workflow_id)
    
    for task_id, task_info in status['tasks'].items():
        if task_info['status'] == 'running':
            print(f"任务 {task_id} 正在运行")
            # 检查运行时间
            if task_info.get('start_time'):
                duration = time.time() - task_info['start_time']
                if duration > 300:  # 5分钟
                    print(f"  警告: 任务运行时间过长 ({duration}秒)")
        elif task_info['status'] == 'failed':
            print(f"任务 {task_id} 失败: {task_info.get('error')}")
        elif task_info['status'] == 'pending':
            print(f"任务 {task_id} 等待中")
            # 检查依赖
            task = executor.workflows[workflow_id]['tasks'][task_id]
            if task.depends_on:
                print(f"  依赖: {task.depends_on}")

# 2. 检查Agent健康状态
async def check_agent_health(agents: Dict[str, BaseAgent]):
    for agent_id, agent in agents.items():
        try:
            # 发送心跳消息
            await agent.receive({'type': 'heartbeat'})
            print(f"Agent {agent_id}: 健康")
        except Exception as e:
            print(f"Agent {agent_id}: 异常 - {e}")

# 3. 检查网络连接
async def check_network_connectivity():
    try:
        response = await httpx.get('https://api.example.com/health', timeout=5)
        if response.status_code == 200:
            print("网络连接正常")
        else:
            print(f"网络连接异常: {response.status_code}")
    except Exception as e:
        print(f"网络连接失败: {e}")
```

**解决方案**：
- 添加任务超时机制
- 实现心跳检测
- 添加任务重试逻辑
- 实现断路器模式

### 问题2：消息丢失

**可能原因**：
1. 队列溢出
2. 消息序列号错乱
3. 网络分区
4. 消费者崩溃

**排查步骤**：
```python
# 1. 检查消息队列大小
def check_queue_size(redis_client: redis.Redis, queue_name: str):
    size = redis_client.llen(queue_name)
    print(f"队列 {queue_name} 大小: {size}")
    
    if size > 1000:
        print("  警告: 队列积压过多")
        # 查看积压消息
        sample = redis_client.lrange(queue_name, 0, 9)
        print(f"  样本消息: {sample}")

# 2. 检查消息确认率
class MessageTracker:
    def __init__(self):
        self.sent = 0
        self.acked = 0
        self.lost = 0
    
    def record_sent(self):
        self.sent += 1
    
    def record_acked(self):
        self.acked += 1
    
    def record_lost(self):
        self.lost += 1
    
    def get_stats(self):
        total = self.sent
        if total == 0:
            return {'sent': 0, 'acked': 0, 'lost': 0, 'ack_rate': 0}
        
        ack_rate = self.acked / total
        loss_rate = self.lost / total
        
        return {
            'sent': self.sent,
            'acked': self.acked,
            'lost': self.lost,
            'ack_rate': ack_rate,
            'loss_rate': loss_rate
        }

# 3. 检查消息序列号
def check_message_sequencing(messages: List[Dict]):
    seq_numbers = [msg['seq'] for msg in messages]
    
    # 检查是否有重复
    duplicates = [seq for seq in seq_numbers if seq_numbers.count(seq) > 1]
    if duplicates:
        print(f"发现重复序列号: {set(duplicates)}")
    
    # 检查是否有缺失
    expected = list(range(min(seq_numbers), max(seq_numbers) + 1))
    missing = set(expected) - set(seq_numbers)
    if missing:
        print(f"发现缺失序列号: {missing}")
    
    # 检查是否乱序
    if seq_numbers != sorted(seq_numbers):
        print("发现乱序消息")
        # 找出乱序位置
        for i in range(1, len(seq_numbers)):
            if seq_numbers[i] < seq_numbers[i-1]:
                print(f"  乱序位置: {i-1} → {i} ({seq_numbers[i-1]} → {seq_numbers[i]})")
```

**解决方案**：
- 实现消息持久化
- 添加消息确认机制
- 实现消息去重
- 使用可靠消息队列（如RabbitMQ、Kafka）

### 问题3：性能瓶颈

**可能原因**：
1. 串行执行任务
2. 数据库查询慢
3. 网络延迟
4. CPU密集型任务

**排查步骤**：
```python
import time
import asyncio

# 1. 任务执行时间分析
class PerformanceProfiler:
    def __init__(self):
        self.task_times = {}
    
    async def profile_task(self, task_id: str, task_func):
        """分析任务执行时间"""
        start_time = time.time()
        result = await task_func()
        end_time = time.time()
        
        duration = end_time - start_time
        self.task_times[task_id] = duration
        
        print(f"任务 {task_id} 执行时间: {duration:.3f}秒")
        
        return result
    
    def get_report(self):
        """生成性能报告"""
        sorted_tasks = sorted(self.task_times.items(), 
                            key=lambda x: x[1], 
                            reverse=True)
        
        report = []
        for task_id, duration in sorted_tasks:
            report.append(f"{task_id}: {duration:.3f}秒")
        
        return "\n".join(report)

# 2. 并行度分析
async def analyze_parallelism(executor: WorkflowExecutor, workflow_id: str):
    """分析并行度"""
    workflow = executor.workflows[workflow_id]
    tasks = workflow['tasks']
    
    # 构建依赖图
    in_degree = {}
    for task_id in tasks:
        in_degree[task_id] = len(tasks[task_id].depends_on)
    
    # 分层
    layers = []
    remaining = set(tasks.keys())
    
    while remaining:
        layer = []
        for task_id in list(remaining):
            if all(dep not in remaining for dep in tasks[task_id].depends_on):
                layer.append(task_id)
                remaining.remove(task_id)
        
        if not layer:
            raise RuntimeError("检测到循环依赖")
        
        layers.append(layer)
    
    print(f"工作流分层 (共{len(layers)}层):")
    for i, layer in enumerate(layers):
        print(f"  第{i+1}层: {layer} (可并行)")
    
    # 计算最大并行度
    max_parallelism = max(len(layer) for layer in layers)
    print(f"\n最大并行度: {max_parallelism}")

# 3. 资源使用分析
import psutil

def monitor_resources():
    """监控资源使用"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()
    disk_info = psutil.disk_usage('/')
    
    print(f"CPU使用率: {cpu_percent}%")
    print(f"内存使用: {memory_info.percent}% ({memory_info.used / 1024**3:.2f}GB / {memory_info.total / 1024**3:.2f}GB)")
    print(f"磁盘使用: {disk_info.percent}% ({disk_info.used / 1024**3:.2f}GB / {disk_info.total / 1024**3:.2f}GB)")
```

**解决方案**：
- 实现任务并行执行
- 添加连接池
- 使用缓存
- 优化数据库查询
- 考虑使用更快的模型

---

## 性能调优清单

### 1. 通信优化

- [ ] **使用消息批处理**
  ```python
  async def batch_publish(messages: List[Dict]):
      # 将多条消息合并发送
      await redis.publish('agent_channel', json.dumps(messages))
  ```

- [ ] **压缩大消息**
  ```python
  import gzip
  compressed = gzip.compress(json.dumps(message).encode('utf-8'))
  ```

- [ ] **使用二进制协议**（如Protocol Buffers、MessagePack）

- [ ] **实现连接池**
  ```python
  import httpx
  client = httpx.AsyncClient(limits=httpx.Limits(max_connections=50))
  ```

### 2. 任务调度优化

- [ ] **识别可并行任务**
  ```python
  # 分析依赖图，找出无依赖关系的任务
  parallel_tasks = find_independent_tasks(tasks)
  ```

- [ ] **使用线程池/进程池**（CPU密集型任务）
  ```python
  from concurrent.futures import ThreadPoolExecutor
  with ThreadPoolExecutor(max_workers=4) as executor:
      results = list(executor.map(func, tasks))
  ```

- [ ] **限制并发度**
  ```python
  semaphore = asyncio.Semaphore(10)
  async def limited_task():
      async with semaphore:
          return await task()
  ```

- [ ] **实现任务优先级**
  ```python
  import heapq
  priority_queue = []
  heapq.heappush(priority_queue, (priority, task))
  ```

### 3. 缓存优化

- [ ] **使用内存缓存**
  ```python
  from functools import lru_cache
  
  @lru_cache(maxsize=1024)
  def cached_function(arg):
      return expensive_computation(arg)
  ```

- [ ] **使用Redis缓存**
  ```python
  async def get_cached(key: str):
      cached = await redis.get(key)
      if cached:
          return json.loads(cached)
      return None
  
  async def set_cached(key: str, value: Any, ttl: int = 3600):
      await redis.setex(key, ttl, json.dumps(value))
  ```

- [ ] **实现查询结果缓存**
  ```python
  class QueryCache:
      def __init__(self, redis_client):
          self.redis = redis_client
      
      async def get(self, query: str, params: Dict):
          cache_key = f"query:{hash(query)}:{hash(str(params))}"
          cached = await self.redis.get(cache_key)
          if cached:
              return json.loads(cached)
          return None
      
      async def set(self, query: str, params: Dict, result: Any, ttl: int = 3600):
          cache_key = f"query:{hash(query)}:{hash(str(params))}"
          await self.redis.setex(cache_key, ttl, json.dumps(result))
  ```

### 4. 数据库优化

- [ ] **使用索引**
  ```sql
  CREATE INDEX idx_task_status ON tasks(status);
  CREATE INDEX idx_task_created ON tasks(created_at);
  ```

- [ ] **使用批量插入**
  ```python
  # 不好的做法（多次查询）
  for data in batch:
      await db.insert(data)
  
  # 好的做法（批量插入）
  await db.insert_batch(batch)
  ```

- [ ] **使用连接池**
  ```python
  import asyncpg
  pool = await asyncpg.create_pool(
      'postgresql://user:pass@localhost/db',
      min_size=5,
      max_size=20
  )
  ```

### 5. 监控与告警

- [ ] **监控关键指标**
  - 任务执行时间
  - 消息延迟
  - 资源使用率
  - 错误率

- [ ] **设置告警阈值**
  ```python
  if task_duration > 30:
      send_alert(f"任务超时: {task_id}")
  
  if error_rate > 0.05:
      send_alert(f"错误率过高: {error_rate:.2%}")
  ```

- [ ] **实现健康检查**
  ```python
  async def health_check():
      checks = {
          'redis': check_redis(),
          'database': check_database(),
          'agents': check_agents()
      }
      
      return all(checks.values()), checks
  ```

---

## 📚 参考资源

### 官方文档
- [LangChain Documentation](https://python.langchain.com/docs/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [OpenAI API](https://platform.openai.com/docs)
- [Redis Documentation](https://redis.io/docs/)

### 开源项目
- [AutoGen](https://github.com/microsoft/autogen)
- [CrewAI](https://github.com/joaomdmoura/crewAI)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [OpenClaw](https://github.com/srxly888-creator/openclaw)

### 论文
- "ReAct: Synergizing Reasoning and Acting in Language Models"
- "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models"
- "Swarm Intelligence: From Natural to Artificial Systems"
- "Multi-Agent Reinforcement Learning: A Selective Overview"

---

**版本**: v0.1
**最后更新**: 2026-03-25
**作者**: 小lin 🤖
**状态**: 🚧 进行中
