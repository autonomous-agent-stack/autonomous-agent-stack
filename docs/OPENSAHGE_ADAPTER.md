# OpenSage 适配器使用指南

异构数据胶水层，提供数据解析、动态脚本生成、Docker 沙盒验证和适配器注册功能。

---

## 核心功能

| 功能 | 说明 |
|------|------|
| 解析错误检测 | 自动检测 JSON/Python/YAML 解析错误 |
| 动态脚本生成 | 基于错误类型生成清洗脚本 |
| Docker 沙盒验证 | 隔离环境验证脚本安全性 |
| AppleDouble 清理 | 过滤 macOS 元数据文件 |

---

## 快速开始

### 基本使用

```python
from lib.opensage_adapter import OpenSageAdapter

# 创建实例
adapter = OpenSageAdapter()

# 解析数据
result = adapter.parse_data(content, "json", "/path/to/file.json")

if result["success"]:
    print("解析成功")
else:
    for error in result["errors"]:
        print(f"错误: {error['message']} (行 {error['line']})")
```

### 命令行

```bash
# 解析文件
python lib/opensage_adapter.py data.json

# 列出已注册适配器
python lib/opensage_adapter.py --list-adapters
```

---

## 动态适配器生成

### 工作流程

```
输入数据 → 解析 → 捕获错误 → 生成脚本 → Docker 验证 → 注册复用
```

### 示例：处理损坏的 JSON

**输入**（有问题的 JSON）:
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Test",  // 注释
    }
  ],
}
```

**自动生成的清洗脚本**:
```python
#!/usr/bin/env python3
import re

def repair_json(raw_string):
    # 移除注释
    raw_string = re.sub(r'//.*?\n', '\n', raw_string)
    # 移除尾部逗号
    raw_string = re.sub(r',\s*([\]}])', r'\1', raw_string)
    return raw_string
```

**输出**（修复后的 JSON）:
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Test"
    }
  ]
}
```

### 生成 ETL 脚本

```python
adapter = OpenSageAdapter()

# 定义操作
operations = [
    {"type": "read", "path": "input.json"},
    {"type": "transform", "field": "name"},
    {"type": "write", "path": "output.json"}
]

# 生成脚本
script_name = adapter.generate_etl_script("python", operations)

# 执行脚本
adapter.script_generator.execute_script(script_name)
```

---

## Docker 沙盒验证

### 安全配置

```python
validator = DockerValidator()

# 自动添加的安全措施：
# --network=none      # 网络隔离
# --user=1000         # 非特权用户
# --timeout=10        # 超时保护
```

### 使用示例

```python
from lib.opensage_adapter import DockerValidator

validator = DockerValidator()

# 检查 Docker 可用性
if not validator.validate_docker_available():
    print("Docker 未运行")
    exit(1)

# 创建沙盒
container_id = validator.create_sandbox(
    image_name="python:3.11-slim",
    command="python script.py",
    timeout=60
)

# 运行沙盒
result = validator.run_sandbox(container_id)

if result["success"]:
    print("验证通过")
    print(result["stdout"])
else:
    print("验证失败:", result.get("error"))

# 清理
validator.cleanup()
```

### 构建沙盒镜像

```bash
docker build -f src/adapters/Dockerfile.sandbox -t opensage-sandbox .
```

---

## AppleDouble 清理机制

### 问题背景

macOS 会在压缩包中生成 `._` 开头的元数据文件（AppleDouble），这些文件会导致解析错误。

### 自动清理

```python
from lib.opensage_adapter import AppleDoubleCleaner

cleaner = AppleDoubleCleaner()

# 检测 AppleDouble 文件
files = cleaner.detect_appledouble_files("/path/to/directory")
print(f"发现 {len(files)} 个 AppleDouble 文件")

# 清理（dry_run=True 仅检测不删除）
count = cleaner.cleanup_appledouble("/path/to/directory", dry_run=False)
print(f"已清理 {count} 个文件")

# 查看已清理文件列表
cleaned = cleaner.get_cleaned_files()
```

### 拦截创建

```python
# 在文件创建时拦截 AppleDouble 文件
if cleaner.intercept_create("._meta.txt"):
    print("已拦截 AppleDouble 文件创建")
```

---

## 适配器注册表

### 注册适配器

```python
from lib.opensage_adapter import AdapterRegistry

registry = AdapterRegistry()

# 注册新适配器
config = registry.register(
    name="json_repair",
    version="1.0.0",
    supported_formats=["json"],
    handler=lambda x: repair_json(x),
    docker_image="python:3.11-slim"
)
```

### 查找和执行

```python
# 查找支持特定格式的适配器
adapters = registry.find_adapter("json")

# 执行适配器
result = registry.execute("json_repair", raw_data)

# 列出所有适配器
all_adapters = registry.list_adapters()
```

---

## 支持的错误类型

| 错误类型 | 说明 | 处理策略 |
|---------|------|---------|
| `JSONDecodeError` | JSON 格式错误 | 移除注释、修复引号、处理尾部逗号 |
| `SyntaxError` | Python 语法错误 | 语法修复 |
| `YAMLError` | YAML 解析错误 | 格式修复 |
| `apple_double_file` | macOS 元数据文件 | 过滤 `._` 开头的文件 |

---

## 环境验证

```python
adapter = OpenSageAdapter()

env_status = adapter.validate_environment()
print(f"Docker 可用: {env_status['docker_available']}")
print(f"Docker 守护进程: {env_status['docker_daemon_running']}")
```

---

## 工作空间清理

```python
# 清理工作空间中的 AppleDouble 文件
cleaned_count = adapter.cleanup_workspace("/path/to/workspace")
print(f"已清理 {cleaned_count} 个 AppleDouble 文件")
```

---

## 故障排查

### Docker 未运行

```bash
# 启动 Docker
open -a Docker

# 验证
docker ps
```

### 清理所有适配器

```python
import os
registry_file = "src/adapters/.adapter_registry.json"
if os.path.exists(registry_file):
    os.remove(registry_file)
```

---

## 文件结构

```
lib/
└── opensage_adapter.py      # 核心适配器

src/adapters/
├── opensage_adapter.py      # 完整实现
├── Dockerfile.sandbox       # 沙盒镜像
├── test_opensage_adapter.py # 测试
└── generated_adapters/      # 运行时生成的适配器
```
