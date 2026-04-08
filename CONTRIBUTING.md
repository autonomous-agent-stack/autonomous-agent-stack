# 🤝 贡献指南

感谢你对 **Autonomous Agent Stack** 的兴趣！我们欢迎所有形式的贡献。

> **项目定位**: AAS 是一个受控的多智能体编排平台，强调 **零信任安全**、**patch-only 执行** 和 **可治理的 AI 调度**。
>
> **核心哲学**: Agent 不能直接修改代码库，必须经过验证和审批。

---

## 📋 目录

- [快速贡献](#快速贡献)
- [贡献类型](#贡献类型)
- [架构理解](#架构理解)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [RFC 流程](#rfc-流程)
- [提交信息规范](#提交信息规范)
- [Pull Request 流程](#pull-request-流程)

---

## 快速贡献

### 一键命令

```bash
# 克隆并设置
git clone https://github.com/srxly888-creator/autonomous-agent-stack.git
cd autonomous-agent-stack
make setup

# 健康检查
make doctor

# 运行测试
make test-quick

# 代码质量检查
make hygiene-check
```

### 新手友好的任务

标签 `good first issue` 的 issues 适合新手：
- [搜索 good first issue](https://github.com/srxly888-creator/autonomous-agent-stack/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)

---

## 贡献类型

| 类型 | 难度 | 说明 | 链接 |
|------|------|------|------|
| 📝 文档 | ⭐ | 修正错误、补充说明 | [文档贡献](#文档贡献) |
| 🐛 Bug 修复 | ⭐⭐ | 修复已知问题 | [Bug 报告](#bug-报告) |
| ✨ 新功能 | ⭐⭐⭐ | 添加新特性 | [功能提案](#功能提案) |
| 🏗️ RFC 设计 | ⭐⭐⭐⭐ | 架构设计文档 | [RFC 流程](#rfc-流程) |
| 🔧 核心架构 | ⭐⭐⭐⭐⭐ | 控制面/promotion 等核心 | 先讨论 |

---

## 架构理解

### 核心原则（必读！）

AAS 与其他 Agent 项目的关键区别：

1. **Brain 与 Hand 分离**
   - Planner 规划任务
   - Worker 在隔离环境执行
   - Promotion Gate 做最终决策

2. **Patch-Only 默认**
   - Agent 只能产出 patch，不能 `git commit`/`push`
   - 所有修改必须经过 validation + promotion

3. **Zero-Trust Invariants**
   - deny-wins 策略合并
   - single-writer lease
   - runtime artifacts 不进入 source

### 关键文件

| 文件 | 说明 |
|------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 权威架构文档 |
| [memory/SOP/MASFactory_Strict_Execution_v1.md](memory/SOP/MASFactory_Strict_Execution_v1.md) | 执行清单 |
| [docs/rfc/](docs/rfc/) | 架构演进 RFC |

### 架构演进路线

```
Phase 1 ✅: 单机 control plane + isolated execution
Phase 2 🚧: 分布式执行（Linux 控制面 + Mac worker）
Phase 3 📋: 多机异构池（Linux + Mac mini + MacBook）
Phase 4 📋: Federation 网络（分层互信联邦）
```

详见：[docs/rfc/README.md](docs/rfc/README.md)

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

## Bug 报告

如果你发现了 bug，请创建 [GitHub Issue](https://github.com/srxly888-creator/autonomous-agent-stack/issues) 并包含：

1. **清晰的标题**
2. **复现步骤**
3. **预期行为**
4. **实际行为**
5. **环境信息**（Python 版本、操作系统等）
6. **日志/截图**（如果适用）

---

## 功能提案

### 小功能

直接创建 Issue 描述：
- 功能描述
- 使用场景
- 预期效果

### 大功能（需要 RFC）

如果功能涉及架构变更，请先提交 RFC：

1. 阅读 [docs/rfc/](docs/rfc/) 了解现有 RFC
2. 创建新的 RFC 文档
3. 在 Discussions 中讨论
4. 等待 approval 后再实现

---

## 文档贡献

文档是最容易上手的贡献方式！

### 可以改进的文档

- [ ] README.md 的中英文翻译
- [ ] API 文档的补充
- [ ] 使用示例的添加
- [ ] 错别字修正
- [ ] 代码注释完善

### 提交方式

1. 直接编辑文件并提交 PR
2. 或在 Issues 中指出需要改进的地方

---

## RFC 流程

对于涉及架构变更的功能，必须先通过 RFC 流程：

### RFC 提交

1. 在 `docs/rfc/` 创建新文档：`rfc-XXX-title.md`
2. 使用 [RFC 模板](docs/rfc/README.md#rfc-模板)
3. 提交 PR
4. 在 Discussions 中发起讨论

### RFC 状态

- 📝 Draft: 草案讨论中
- 👀 Under Review: 正在 review
- ✅ Accepted: 已接受，等待实现
- 🚧 In Progress: 实现中
- ✅ Implemented: 已实现
- ❌ Rejected: 已拒绝

### 现有 RFC

- [Distributed Execution Model](docs/rfc/distributed-execution.md)
- [Three-Machine Architecture](docs/rfc/three-machine-architecture.md)
- [Federation Protocol](docs/rfc/federation-protocol.md)

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
# 一键安装（推荐）
make setup

# 或手动安装
pip install -r requirements.txt

# 运行健康检查
make doctor

# 运行测试
make test-quick
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

### 6. 运行检查

```bash
# 本地质量检查
make hygiene-check

# 运行 review gates
make review-gates-local
```

### 7. 创建 Pull Request

在 GitHub 上创建 Pull Request，填写 PR 模板。

---

## 代码规范

### AAS 特定规范

#### 零信任原则

1. **不在代码中硬编码密钥**
   ```python
   # ❌ 错误
   API_KEY = "sk-xxx"

   # ✅ 正确
   API_KEY = os.environ.get("API_KEY")
   if not API_KEY:
       raise ValueError("API_KEY is required")
   ```

2. **验证所有用户输入**
   ```python
   def process_path(user_path: str) -> Path:
       # 验证路径在允许范围内
       path = Path(user_path).resolve()
       allowed_root = Path("/allowed/root").resolve()
       if not str(path).startswith(str(allowed_root)):
           raise ValueError("Path outside allowed root")
       return path
   ```

3. **Agent 执行约束**
   - Agent 不能执行 `git commit`/`push`
   - Agent 只能编辑 `allowed_paths` 中的文件
   - 禁止访问 `forbidden_paths`

#### 不变性优先

```python
# ❌ 避免突变
def add_item(items, item):
    items.append(item)
    return items

# ✅ 返回新对象
def add_item(items, item):
    return items + [item]
```

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
make format  # 或 black src/

# 检查代码风格
make lint    # 或 flake8 src/

# 运行测试
make test     # 或 pytest tests/ -v

# 安全检查
make security-scan  # 或 bandit -r src/
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

### 文档分层

1. **对外入口文档**（README.md）
   - 面向新用户
   - 5 分钟能跑起来
   - 快速验证安装

2. **权威架构文档**（ARCHITECTURE.md）
   - 当前 checkout 的 canonical 描述
   - zero-trust invariants
   - 与历史文档冲突时以本文档为准

3. **专题设计文档 / RFC**（docs/rfc/）
   - 分布式执行
   - 三机架构
   - Federation 协议
   - 不混在 README 里

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

## AAS 特定测试指南

### 受控执行测试

测试 OpenHands/Agent 执行时，必须验证：

```python
def test_worker_cannot_git_commit():
    """验证 worker 不能执行 git commit"""
    worker_prompt = build_worker_prompt(task)

    # 检查 prompt 包含禁止命令
    assert "git commit" not in worker_prompt.lower()
    assert "git push" not in worker_prompt.lower()

    # 验证执行结果
    result = execute_in_isolation(worker_prompt)
    assert not result.contains_git_operations
```

### Promotion Gate 测试

```python
def test_promotion_gate_rejects_runtime_artifacts():
    """验证 promotion gate 拒绝 runtime artifacts"""
    patch = create_patch_with_runtime_artifacts()

    gate = GitPromotionGateService()
    result = gate.validate(patch)

    assert result.rejected
    assert "runtime artifacts" in result.reason
```

### 安全测试

```python
def test_forbidden_paths_are_respected():
    """验证 forbidden paths 被遵守"""
    policy = Policy(
        forbidden_paths=[".git", "logs/", ".masfactory_runtime/"]
    )

    worker = execute_worker(policy, task="modify .git/config")
    assert worker.rejected
    assert "forbidden path" in worker.reason.lower()
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

### 社区渠道

- **GitHub Issues**: 技术问题和 Bug 报告
- **GitHub Discussions**: 功能讨论和疑问
- **RFC PR**: 架构设计讨论

### 文档资源

| 文档 | 说明 |
|------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 权威架构文档 |
| [README.md](README.md) | 快速上手 |
| [docs/QUICK_START.md](docs/QUICK_START.md) | 详细启动指南 |
| [docs/linux-remote-worker.md](docs/linux-remote-worker.md) | Linux 远端节点部署 |
| [docs/rfc/](docs/rfc/) | 架构演进 RFC |

### 贡献资源

| 资源 | 说明 |
|------|------|
| [good first issue](https://github.com/srxly888-creator/autonomous-agent-stack/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) | 新手友好任务 |
| [help wanted](https://github.com/srxly888-creator/autonomous-agent-stack/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) | 需要帮助的任务 |
| [RFC 模板](docs/rfc/README.md#rfc-模板) | RFC 提交模板 |

---

## 许可证

通过贡献代码，你同意你的代码将根据 MIT 许可证授权。

---

## 我们的愿景

AAS 正在构建一个**更安全、更可靠的 AI Agent 基础设施**：

### 短期目标（Phase 1 ✅）
- 单机 control plane + isolated execution
- SQLite 权威状态 + artifact 分离
- GitHub Assistant、Telegram 集成

### 中期目标（Phase 2-3 🚧）
- 分布式执行（Linux + Mac worker）
- 多机异构池
- 心跳/租约/离线恢复

### 长期愿景（Phase 4 📋）
- 分层联邦网络
- 算力/worker/agent 分级共享
- 可治理的 AI 调度生态

### 欢迎加入

无论你是：
- 🔥 热爱 AI 的开发者
- 🏢 需要受控 AI 的企业
- 🎓 研究分布式系统的学者
- 💡 有新想法的创新者

我们都欢迎你的贡献！

让我们一起定义 AI Agent 的**安全标准**和**最佳实践**。

---

**再次感谢你的贡献！** 🎉🚀
