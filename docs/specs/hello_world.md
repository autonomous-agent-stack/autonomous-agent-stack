# TaskSpec: hello_world

**Agent Type**: Validation / Pipeline Test  
**Risk Level**: None (只读操作)  
**Estimated Duration**: 30 秒

## 任务描述

一个简单的 "hello world" agent，用于验证 AAS 的完整执行管道是否正常工作。

## 目标

1. 扫描项目基础信息
2. 生成项目分析报告（只读）
3. 验证从 TaskSpec → Execution → Result 的完整流程

## 允许路径

```yaml
allowed_paths:
  - "README.md"
  - "setup.py"
  - "requirements.txt"
  - "pyproject.toml"
  - "package.json"
  - ".gitignore"
  - "LICENSE"
```

## 禁止路径

```yaml
forbidden_paths:
  - "secrets/"
  - ".env"
  - "*.key"
  - "*.pem"
```

## Agent Prompt

```python
PROMPT = """你是 AAS 系统验证助手。你的任务是扫描项目并生成一个简短的分析报告。

## 任务

1. 读取 README.md 获取项目名称和描述
2. 检测项目类型（Python/Node.js/Go/Rust/其他）
3. 检测主要依赖（从 requirements.txt / package.json 等）
4. 生成一个简短的 JSON 报告

## 输出格式

```json
{
  "project_name": "项目名称",
  "description": "项目描述",
  "project_type": "python|nodejs|go|rust|other",
  "main_dependencies": ["依赖1", "依赖2"],
  "file_count": 10,
  "has_tests": true,
  "has_ci": true
}
```

## 限制

- 只读取文件，不修改任何内容
- 不执行任何命令
- 不访问网络
"""
```

## 验证命令

```yaml
validation_commands:
  - name: "检查输出是有效 JSON"
    command: "echo '{result}' | python -m json.tool"
    error_on_failure: true
```

## 实现优先级

### 最小实现（今天就能跑）

```python
# src/autoresearch/agents/hello_world.py

import json
import os
from pathlib import Path

def hello_world_agent(repo_path: str) -> dict:
    """简单的 hello world agent"""
    result = {
        "project_name": Path(repo_path).name,
        "project_type": "unknown",
        "main_dependencies": [],
        "file_count": 0,
        "has_tests": False,
        "has_ci": False
    }
    
    # 检测项目类型
    if (Path(repo_path) / "requirements.txt").exists():
        result["project_type"] = "python"
        with open(Path(repo_path) / "requirements.txt") as f:
            result["main_dependencies"] = [
                line.split("==")[0].strip()
                for line in f
                if line.strip() and not line.startswith("#")
            ][:5]  # 只取前 5 个依赖
    elif (Path(repo_path) / "package.json").exists():
        result["project_type"] = "nodejs"
    
    # 统计文件数量
    result["file_count"] = sum(1 for _ in Path(repo_path).rglob("*") if _.is_file())
    
    # 检查是否有测试
    result["has_tests"] = (
        (Path(repo_path) / "tests").exists() or
        (Path(repo_path) / "test").exists() or
        any("test" in f.name for f in Path(repo_path).rglob("*.py"))
    )
    
    # 检查是否有 CI
    result["has_ci"] = (Path(repo_path) / ".github").exists()
    
    return result

# 使用示例
if __name__ == "__main__":
    import sys
    result = hello_world_agent(sys.argv[1] if len(sys.argv) > 1 else ".")
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

## 运行示例

```bash
# 快速测试
python -m autoresearch.agents.hello_world /path/to/repo

# 预期输出
{
  "project_name": "autonomous-agent-stack",
  "project_type": "python",
  "main_dependencies": [
    "fastapi",
    "pydantic",
    "anthropic",
    "openai",
    "pytest"
  ],
  "file_count": 245,
  "has_tests": true,
  "has_ci": true
}
```

## 集成到 AAS Pipeline

```python
# src/autoresearch/core/services/hello_world_worker.py

class HelloWorldWorkerService:
    """Hello world worker 服务"""
    
    def execute(self, job_spec: dict) -> dict:
        """执行 hello world 任务"""
        repo_path = job_spec["repo_path"]
        
        # 执行 agent
        result = hello_world_agent(repo_path)
        
        # 验证输出
        self._validate_result(result)
        
        return {
            "task_id": job_spec["task_id"],
            "status": "completed",
            "result": result,
            "metadata": {
                "agent": "hello_world",
                "duration_seconds": 0.5
            }
        }
    
    def _validate_result(self, result: dict):
        """验证结果格式"""
        assert "project_name" in result
        assert "project_type" in result
        assert isinstance(result.get("main_dependencies"), list)
```

## 成功标准

- [ ] 能在 30 秒内完成扫描
- [ ] 输出有效 JSON
- [ ] 不修改任何文件
- [ ] 能正确检测 Python/Node.js 项目
- [ ] 验证管道完整（TaskSpec → Worker → Result）

## 用途

1. **验证基础管道**：确保 AAS 的核心组件能协同工作
2. **新环境测试**：在新环境部署后快速验证
3. **开发调试**：开发其他 agent 时作为参考模板

---

**预计工作量**: 2-4 小时  
**风险等级**: 无  
**价值**: 建立信心，验证管道
