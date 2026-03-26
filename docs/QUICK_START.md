# 🚀 快速启动指南

## 30 秒启动

```bash
# 1. 进入项目目录
cd /Volumes/PS1008/Github/autonomous-agent-stack

# 2. 验证模块
python3 << 'EOF'
from memory.session_store import SessionStore
from executors.claude_cli_adapter import ClaudeCLIAdapter
from opensage.tool_synthesizer import ToolSynthesizer
from opensage.topology_engine import TopologyEngine
print("✅ 所有模块导入成功！")
EOF

# 3. 查看文档
cat docs/BLITZ_INTEGRATION_REPORT.md
```

---

## 5 分钟上手

### 1. 连贯对话

```python
import asyncio
from memory.session_store import SessionStore

async def test_chat():
    store = SessionStore()
    
    # 创建会话
    session_id = await store.create_session("user_001")
    
    # 保存历史
    await store.save_history(session_id, "user", "你好")
    await store.save_history(session_id, "assistant", "你好！有什么可以帮助你的？")
    
    # 加载上下文
    context = await store.load_context(session_id)
    
    print(f"✅ 会话 ID: {session_id}")
    print(f"✅ 上下文消息数: {len(context)}")
    
asyncio.run(test_chat())
```

### 2. Claude CLI 执行

```python
import asyncio
from executors.claude_cli_adapter import ClaudeCLIAdapter

async def test_claude():
    adapter = ClaudeCLIAdapter()
    
    # 执行任务
    result = await adapter.execute("解释什么是 Agent")
    
    print(f"✅ 执行成功: {result[:100]}...")
    
asyncio.run(test_claude())
```

### 3. 工具合成

```python
import asyncio
from opensage.tool_synthesizer import ToolSynthesizer

async def test_synthesize():
    synthesizer = ToolSynthesizer()
    
    # 合成工具
    tool = await synthesizer.synthesize(
        task_description="计算斐波那契数列",
        code_snippet="""
def execute(n):
    if n <= 1:
        return n
    return execute(n-1) + execute(n-2)
"""
    )
    
    print(f"✅ 工具名称: {tool.name}")
    print(f"✅ 是否有效: {tool.is_valid}")
    
asyncio.run(test_synthesize())
```

### 4. 拓扑生成

```python
import asyncio
from opensage.topology_engine import TopologyEngine

async def test_topology():
    engine = TopologyEngine()
    
    # 生成拓扑
    graph = await engine.generate_topology(
        "分析数据。生成报告。发送通知。",
        available_agents=["agent_1", "agent_2"]
    )
    
    # 获取执行顺序
    order = engine.get_execution_order()
    
    print(f"✅ 节点数: {len(engine.nodes)}")
    print(f"✅ 执行顺序: {order}")
    
asyncio.run(test_topology())
```

---

## 环境要求

- Python 3.11+
- SQLite3（内置）
- Claude CLI（可选，用于实际执行）

---

## 常见问题

### Q: 模块导入失败？

```bash
# 确保在项目根目录
cd /Volumes/PS1008/Github/autonomous-agent-stack

# 添加 src 到 PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Q: Claude CLI 不可用？

```bash
# 检查 Claude CLI
which claude

# 如果未安装，跳过 Claude 相关测试
# 其他模块仍然可用
```

### Q: 如何查看系统状态？

```python
from bridge.unified_router import UnifiedRouter

router = UnifiedRouter()
status = router.get_status()

print(status)
```

---

## 下一步

1. **查看完整文档**: `docs/BLITZ_INTEGRATION_REPORT.md`
2. **运行测试**: `python3 tests/test_blitz_integration.py`
3. **查看示例**: `examples/` 目录

---

**创建时间**: 2026-03-26 10:33 GMT+8
