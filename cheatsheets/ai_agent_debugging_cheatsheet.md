# AI Agent 调试技巧速查表

> **版本**: v1.0
> **调试技巧**: 15+

---

## 🔍 快速调试

### 1. 日志记录

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def debug_agent(task: str):
    logger.debug(f"Input: {task}")
    
    result = llm.call(task)
    
    logger.debug(f"Output: {result}")
    
    return result
```

---

### 2. 打印中间结果

```python
def debug_workflow(task: str):
    # 1. 输入
    print(f"📥 Input: {task}")
    
    # 2. 处理
    thought = think(task)
    print(f"💭 Thought: {thought}")
    
    # 3. 行动
    action = act(thought)
    print(f"⚡ Action: {action}")
    
    # 4. 输出
    result = generate(action)
    print(f"📤 Output: {result}")
    
    return result
```

---

### 3. 性能分析

```python
import time
import cProfile

def profile_agent():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # 运行代码
    result = agent.run("test task")
    
    profiler.disable()
    
    # 打印统计
    profiler.print_stats(sort='cumulative')
    
    return result
```

---

### 4. 内存追踪

```python
import tracemalloc

def track_memory():
    tracemalloc.start()
    
    # 运行代码
    result = agent.run("test task")
    
    # 获取快照
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    for stat in top_stats[:10]:
        print(stat)
    
    return result
```

---

### 5. 异常追踪

```python
import traceback

def safe_run(task: str):
    try:
        return agent.run(task)
    except Exception as e:
        # 打印完整堆栈
        traceback.print_exc()
        
        # 记录到文件
        with open("errors.log", "a") as f:
            f.write(f"{time.time()}: {e}\n")
            f.write(traceback.format_exc())
        
        return f"Error: {e}"
```

---

## 📊 调试工具

### 1. 断点调试

```python
def debug_with_breakpoint(task: str):
    # 设置断点
    breakpoint()
    
    result = agent.run(task)
    
    return result
```

### 2. 交互式调试

```python
import pdb

def interactive_debug(task: str):
    result = agent.run(task)
    
    # 启动交互式调试
    pdb.set_trace()
    
    return result
```

### 3. 可视化调试

```python
def visualize_agent():
    # 创建可视化
    import graphviz
    
    dot = graphviz.Digraph()
    
    # 添加节点
    dot.node('input', 'Input')
    dot.node('llm', 'LLM')
    dot.node('output', 'Output')
    
    # 添加边
    dot.edge('input', 'llm')
    dot.edge('llm', 'output')
    
    # 渲染
    dot.render('agent_debug.gv', view=True)
```

---

## 🎯 调试清单

- [ ] 添加日志记录
- [ ] 打印中间结果
- [ ] 性能分析
- [ ] 内存追踪
- [ ] 异常追踪
- [ ] 断点调试
- [ ] 交互式调试
- [ ] 可视化调试

---

**生成时间**: 2026-03-27 14:49 GMT+8
