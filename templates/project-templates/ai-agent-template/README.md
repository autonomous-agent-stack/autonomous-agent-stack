# AI Agent 项目模板

一个完整的 Python AI Agent 项目模板，包含配置管理、工具定义、测试和文档。

## 项目结构

```
ai-agent-template/
├── src/
│   ├── __init__.py
│   ├── agent.py          # Agent 核心逻辑
│   ├── tools.py          # 工具定义
│   ├── config.py         # 配置管理
│   └── utils.py          # 工具函数
├── tests/
│   ├── __init__.py
│   ├── test_agent.py     # Agent 测试
│   └── test_tools.py     # 工具测试
├── config/
│   ├── config.yaml       # 配置文件
│   └── config.example.yaml
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境
cp config/config.example.yaml config/config.yaml
vim config/config.yaml

# 运行 Agent
python src/main.py

# 运行测试
pytest tests/
```

## 功能特性

- **模块化设计**: 清晰的代码结构，易于扩展
- **配置管理**: 支持 YAML 配置文件
- **工具系统**: 灵活的工具定义和使用
- **测试覆盖**: 完整的单元测试和集成测试
- **类型提示**: Python 类型提示支持
- **日志记录**: 结构化日志输出

## 配置说明

编辑 `config/config.yaml` 文件来配置 Agent 行为：

```yaml
agent:
  name: "My Agent"
  model: "gpt-4"
  temperature: 0.7
  max_tokens: 1000

tools:
  - name: "web_search"
    enabled: true
  - name: "code_executor"
    enabled: false
```

## 扩展工具

在 `src/tools.py` 中添加新工具：

```python
def my_new_tool(input: str) -> str:
    """工具描述"""
    # 实现逻辑
    return result
```

## 许可证

MIT
