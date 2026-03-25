# 🤝 贡献指南

感谢你对 **Autonomous Agent Stack** 的兴趣！我们欢迎所有形式的贡献。

---

## 📋 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [提交信息规范](#提交信息规范)
- [Pull Request 流程](#pull-request-流程)

---

## 行为准则

### 我们的承诺

为了营造开放和友好的环境，我们承诺：

- 使用包容性语言
- 尊重不同的观点和经验
- 优雅地接受建设性批评
- 关注对社区最有利的事情
- 对其他社区成员表示同理心

---

## 如何贡献

### 报告 Bug

如果你发现了 bug，请创建 [GitHub Issue](https://github.com/srxly888-creator/autonomous-agent-stack/issues) 并包含：

1. **清晰的标题**
2. **复现步骤**
3. **预期行为**
4. **实际行为**
5. **环境信息**（Python 版本、操作系统等）
6. **日志/截图**（如果适用）

### 建议新功能

如果你有新功能的想法：

1. 先查看 [Issues](https://github.com/srxly888-creator/autonomous-agent-stack/issues) 确保没有被提出过
2. 创建新 Issue，详细描述：
   - 功能描述
   - 使用场景
   - 可能的实现方式

### 改进文档

文档改进包括：

- 修正拼写/语法错误
- 添加缺失的文档
- 改进现有文档的清晰度
- 添加更多示例

---

## 开发流程

### 1. Fork 仓库

```bash
# 在 GitHub 上 Fork 仓库
# 然后克隆你的 Fork
git clone https://github.com/your-username/autonomous-agent-stack.git
cd autonomous-agent-stack
```

### 2. 创建分支

```bash
# 创建特性分支
git checkout -b feature/your-feature-name

# 或修复分支
git checkout -b fix/your-bug-fix
```

### 3. 设置开发环境

```bash
# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install pytest black flake8

# 运行测试
pytest tests/
```

### 4. 进行更改

- 编写代码
- 添加测试
- 更新文档

### 5. 提交更改

```bash
git add .
git commit -m "feat: 添加新功能 X"
git push origin feature/your-feature-name
```

### 6. 创建 Pull Request

在 GitHub 上创建 Pull Request，填写 PR 模板。

---

## 代码规范

### Python 代码

遵循 [PEP 8](https://pep8.org/) 规范：

```python
# 好的示例
def evaluate_task(task_id: str, config: dict) -> dict:
    """
    评估任务

    Args:
        task_id: 任务 ID
        config: 配置字典

    Returns:
        评估结果字典
    """
    result = {
        "task_id": task_id,
        "status": "completed",
        "score": 0.95
    }
    return result
```

### 代码风格工具

```bash
# 格式化代码
black src/

# 检查代码风格
flake8 src/

# 运行测试
pytest tests/ -v
```

### 类型注解

使用类型注解提高代码可读性：

```python
from typing import Dict, List, Optional

def process_data(
    data: List[Dict[str, str]],
    threshold: Optional[float] = None
) -> Dict[str, float]:
    """处理数据"""
    pass
```

---

## 提交信息规范

我们遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

### 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type（必需）

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更改
- `style`: 代码格式（不影响功能）
- `refactor`: 重构（不添加功能或修复 bug）
- `test`: 添加/修改测试
- `chore`: 构建过程或辅助工具的变动

### 示例

```bash
# 新功能
git commit -m "feat(api): 添加 Generator API"

# Bug 修复
git commit -m "fix(evaluator): 修复 SQLite 连接池问题"

# 文档
git commit -m "docs(readme): 更新安装指南"

# 重构
git commit -m "refactor(core): 优化评估逻辑"
```

---

## Pull Request 流程

### PR 标题

使用与提交信息相同的格式：

```
feat(api): 添加 Generator API 实现
```

### PR 描述

PR 描述应包含：

1. **更改类型**（新功能/Bug 修复/文档等）
2. **更改描述**
3. **相关 Issue**（如果有）
4. **测试方法**
5. **截图**（如果适用）

### 示例 PR 描述

```markdown
## 更改类型
- [x] 新功能
- [ ] Bug 修复
- [ ] 文档改进
- [ ] 代码重构

## 描述
添加 Generator API 实现，支持基于 LLM 的变体生成。

## 相关 Issue
Closes #123

## 测试方法
1. 运行 `pytest tests/test_generator_api.py`
2. 手动测试 API 端点

## 截图
（如果适用）
```

### 代码审查

所有 PR 都需要至少一位维护者的审查。

审查者会检查：

- 代码质量
- 测试覆盖率
- 文档完整性
- 提交信息规范

---

## 测试规范

### 单元测试

每个新功能都应包含单元测试：

```python
# tests/test_new_feature.py
from src.module import new_function

def test_new_function():
    result = new_function("input")
    assert result == "expected_output"
```

### 测试覆盖率

保持测试覆盖率在 80% 以上：

```bash
# 运行测试并生成覆盖率报告
pytest --cov=src tests/
```

---

## 文档规范

### README.md

- 清晰的项目描述
- 安装指南
- 快速开始
- 使用示例

### API 文档

- 所有公共 API 都应有文档字符串
- 使用 Google 风格的文档字符串

```python
def create_evaluation(
    task_name: str,
    config_path: str,
    evaluator_command: Optional[Dict] = None
) -> str:
    """
    创建评估任务

    Args:
        task_name: 任务名称
        config_path: 配置文件路径
        evaluator_command: 自定义评估器命令（可选）

    Returns:
        任务 ID

    Raises:
        ValueError: 如果 task_name 为空
    """
    pass
```

---

## 发布流程

### 版本号

遵循 [Semantic Versioning](https://semver.org/)：

- MAJOR: 不兼容的 API 更改
- MINOR: 向后兼容的功能添加
- PATCH: 向后兼容的 bug 修复

### 发布步骤

1. 更新版本号
2. 更新 CHANGELOG.md
3. 创建 Git tag
4. 推送到 GitHub
5. 发布 Release

---

## 获取帮助

- **GitHub Issues**: https://github.com/srxly888-creator/autonomous-agent-stack/issues
- **文档**: https://github.com/srxly888-creator/autonomous-agent-stack#readme

---

## 许可证

通过贡献代码，你同意你的代码将根据 MIT 许可证授权。

---

**感谢你的贡献！** 🎉
