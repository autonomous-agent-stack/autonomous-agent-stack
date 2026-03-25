# E5 日志补全 - 快速参考

## 🚀 快速开始

### AppleDouble 清理（重点功能）

```python
from src.adapters.opensage_adapter import AppleDoubleCleaner

cleaner = AppleDoubleCleaner()

# 清理列表中的 macOS 元数据文件
files = ["doc.pdf", "._doc.pdf", ".DS_Store", "image.jpg"]
cleaned, stats = cleaner.clean_list(files)

# 输出日志（自动）：
# {"node": "executor", "action": "appledouble_cleanup", "files_removed": 2, ...}

print(cleaned)  # ['doc.pdf', 'image.jpg']
```

### 使用图编排引擎

```python
from src.orchestrator.graph_engine import GraphEngine, GraphNode, NodeType

engine = GraphEngine("my_workflow")

def my_task(inputs):
    return {"result": "done"}

engine.add_node(GraphNode(
    id="task1",
    type=NodeType.EXECUTOR,
    handler=my_task
))

results = engine.execute()  # 自动记录所有日志
```

### 使用 Docker 沙盒

```python
from src.orchestrator.tool_synthesis import ToolSynthesis

synthesizer = ToolSynthesis()

result = synthesizer.execute_script(
    script_content="print('hello')",
    input_data={"key": "value"}
)

print(result.success)    # True
print(result.duration_ms)  # 1500
```

## 📋 日志格式速查

### AppleDouble 清理日志
```json
{
  "timestamp": "2026-03-25T23:44:54Z",
  "level": "INFO",
  "node": "executor",
  "action": "appledouble_cleanup",
  "files_removed": 2,
  "duration_ms": 0,
  "files": ["._file1.txt", ".DS_Store"]
}
```

### 节点执行日志
```json
{
  "timestamp": "2026-03-25T23:45:00Z",
  "level": "INFO",
  "node": "executor",
  "action": "execute_node_started",
  "node_id": "task1",
  "attempt": 1
}
```

### Docker 沙盒日志
```json
{
  "timestamp": "2026-03-25T23:46:00Z",
  "level": "INFO",
  "node": "docker_sandbox",
  "action": "execute",
  "image": "python:3.11-slim",
  "success": true,
  "duration_ms": 1500
}
```

### 错误重试日志
```json
{
  "timestamp": "2026-03-25T23:47:00Z",
  "level": "WARNING",
  "node": "executor",
  "action": "retry_attempt",
  "attempt": 2,
  "max_attempts": 3,
  "error_type": "ValueError",
  "delay_ms": 2000
}
```

## 🔍 检测的文件模式

| 模式 | 说明 | 示例 |
|------|------|------|
| `._*` | AppleDouble 文件 | `._document.pdf` |
| `.DS_Store` | macOS Finder 设置 | `.DS_Store` |

## 📂 文件结构

```
src/
├── orchestrator/
│   ├── structured_logger.py      # 日志工具
│   ├── graph_engine.py            # 图引擎
│   └── tool_synthesis.py          # 沙盒执行
└── adapters/
    └── opensage_adapter.py        # 适配器（含 AppleDouble 清理）

tests/
└── test_structured_logging.py     # 测试套件

docs/
├── E5-logging-implementation-report.md    # 详细报告
├── E5-completion-summary.md               # 完成摘要
└── E5-quick-reference.md                  # 本文档
```

## 🧪 测试命令

```bash
# 完整测试
python3 tests/test_structured_logging.py

# 测试 AppleDouble 清理
python3 -c "
from src.adapters.opensage_adapter import AppleDoubleCleaner
cleaner = AppleDoubleCleaner()
cleaned, stats = cleaner.clean_list(['a.txt', '._a.txt', '.DS_Store'])
print('Removed:', stats['files_removed'])
print('Cleaned:', cleaned)
"

# 测试日志输出
python3 -c "
from src.orchestrator.structured_logger import get_logger
logger = get_logger('test')
logger.info(node='test', action='test', value=123)
"
```

## 📊 日志级别

| 级别 | 用途 | 示例 |
|------|------|------|
| DEBUG | 详细信息 | 节点添加、脚本准备 |
| INFO | 正常操作 | 启动、完成、成功 |
| WARNING | 警告 | 重试、验证失败 |
| ERROR | 错误 | 执行失败、超时 |

## 🎯 重点功能清单

- ✅ AppleDouble 清理拦截（`._*` 和 `.DS_Store`）
- ✅ 节点执行耗时（自动计时）
- ✅ Docker 沙盒生命周期日志
- ✅ 错误重试记录
- ✅ JSON 格式输出
- ✅ UTC 时间戳
- ✅ 性能优化（不阻塞主流程）

## 💡 常见用法

### 1. 清理文件列表
```python
cleaner = AppleDoubleCleaner()
cleaned, stats = cleaner.clean_list(files)
```

### 2. 清理字典键
```python
cleaner = AppleDoubleCleaner()
cleaned, stats = cleaner.clean_dict(data_dict)
```

### 3. 清理目录
```python
cleaner = AppleDoubleCleaner()
stats = cleaner.clean_directory("/path/to/dir")
```

### 4. 使用 OpenSage 适配器
```python
from src.adapters.opensage_adapter import OpenSageAdapter

adapter = OpenSageAdapter()
cleaned = adapter.clean_appledouble(files)
result = adapter.parse_external_format(json_string)
```

## 🔧 配置选项

### DockerConfig
```python
DockerConfig(
    image="python:3.11-slim",      # Docker 镜像
    network_mode="none",            # 网络模式（隔离）
    timeout_seconds=30,             # 超时时间
    memory_limit="512m",            # 内存限制
    cpu_quota=50000                 # CPU 限制
)
```

### 重试配置
```python
{
    "max_attempts": 3,              # 最大重试次数
    "base_delay_ms": 1000,          # 基础延迟
}
```

## 📝 日志查询示例

```bash
# 查看 AppleDouble 清理日志
grep "appledouble_cleanup" app.log | jq '.'

# 统计清理的文件总数
grep "appledouble_cleanup" app.log | jq '.files_removed' | awk '{sum+=$1} END {print sum}'

# 查看失败的节点执行
grep '"action":"execute_node_failed"' app.log | jq '.'

# 查看 Docker 沙盒执行时间
grep '"node":"docker_sandbox"' app.log | jq '.duration_ms'
```

## ✅ 验证检查

- [ ] 日志输出为 JSON 格式
- [ ] AppleDouble 文件被正确清理
- [ ] 日志包含 files_removed 字段
- [ ] 日志包含 duration_ms 字段
- [ ] 时间戳为 UTC 格式
- [ ] 日志级别正确（DEBUG/INFO/WARNING/ERROR）

---

**最后更新**：2026-03-25
**版本**：1.0
**状态**：✅ 完成并测试通过
