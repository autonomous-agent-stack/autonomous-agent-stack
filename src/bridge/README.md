# Bridge API - OpenClaw 与外部系统的双向桥梁

## 概述

Bridge API 提供了 OpenClaw 与外部系统（如 Codex、外部 Skill）之间的双向通信能力，支持安全的任务委派和动态 Skill 加载。

## 核心功能

### 1. 双向鉴权与凭证解耦

通过 `CredentialsRef` 实现敏感凭证的解耦管理：

```python
from src.bridge.api import BridgeAPI, CredentialsRef

# 创建凭证引用
ref = CredentialsRef(ref_id="my_token", ref_type="token")

# 注册凭证
bridge = BridgeAPI()
bridge.register_credentials("my_token", {"token": "secret_token_123"})
```

### 2. 任务接收与委派

支持三种任务类型：

#### Direct 任务（直接处理）
```python
task = {
    "task_id": "task_001",
    "task_type": "direct",
    "payload": {"action": "echo", "message": "Hello"},
}

result = await bridge.receive_task(task)
```

#### Codex 任务（委派给 Codex）
```python
task = {
    "task_id": "task_002",
    "task_type": "codex",
    "credentials_ref": {"ref_id": "codex_token", "ref_type": "token"},
    "payload": {"task_id": "codex_001", "action": "execute"},
}

result = await bridge.receive_task(task)
```

#### Skill 任务（委派给外部 Skill）
```python
task = {
    "task_id": "task_003",
    "task_type": "skill",
    "payload": {"skill_path": "skills/my_skill.py"},
}

result = await bridge.receive_task(task)
```

### 3. 动态 Skill 加载

自动加载外部 Skill，并强制进行安全扫描：

```python
from src.bridge.skill_loader import SkillLoader

loader = SkillLoader(
    base_path=Path("skills"),
    enable_security_scan=True,
    strict_mode=False,
)

# 加载 Skill（会自动进行安全扫描）
skill = await loader.load_skill("my_skill.py")
result = await skill.execute(payload)
```

### 4. 安全审计

SecurityAuditor 会自动检测 Skill 中的危险操作：

- **危险导入**：`os`, `subprocess`, `eval`, `requests`, `urllib`, `socket` 等
- **危险函数**：`eval()`, `exec()`, `__import__()`, `compile()` 等
- **AppleDouble 文件**：macOS 系统生成的 `._*` 文件

```python
from src.bridge.skill_loader import SecurityAuditor

auditor = SecurityAuditor(strict_mode=False)
result = auditor.audit_skill(Path("skills/my_skill"))

print(result["summary"])
# {"critical": 0, "high": 2, "medium": 1}
```

### 5. AppleDouble 文件清理

自动清理 macOS 生成的 `._*` 文件：

```python
from src.bridge.skill_loader import AppleDoubleCleaner

AppleDoubleCleaner.clean(Path("skills"))
# 清理了 5 个 AppleDouble 文件
```

## 架构设计

```
┌─────────────┐
│  OpenClaw   │
└─────┬───────┘
      │ Task
      ▼
┌─────────────┐     ┌──────────────┐
│  Bridge API │────▶│ Credentials  │
│             │     │    Store     │
└─────┬───────┘     └──────────────┘
      │
      ├──────────┬────────────┐
      │          │            │
      ▼          ▼            ▼
┌─────────┐ ┌────────┐ ┌──────────┐
│ Direct  │ │ Codex  │ │  Skill   │
│ Handler │ │ Client │ │  Loader  │
└─────────┘ └────────┘ └──────┬───┘
                           │
                   ┌───────┴───────┐
                   │ Security Audit│
                   │  + Clean      │
                   └───────────────┘
```

## 安全特性

1. **凭证解耦**：敏感凭证不直接传递，通过引用 ID 间接访问
2. **强制安全扫描**：加载 Skill 前必须通过安全审计
3. **AppleDouble 清理**：自动清理 macOS 系统文件
4. **AST 静态分析**：基于抽象语法树的代码审计，无需执行代码

## 日志规范

所有日志使用统一前缀 `[Agent-Stack-Bridge]`：

```
[Agent-Stack-Bridge] Bridge API initialized
[Agent-Stack-Bridge] Task received from OpenClaw: task_001
[Agent-Stack-Bridge] Delegating task to Codex
[Agent-Stack-Bridge] Security audit completed: {'critical': 0, 'high': 1, 'medium': 0}
[Agent-Stack-Bridge] Skill loaded: my_skill.py
[Agent-Stack-Bridge] Task completed: task_001
```

## 测试覆盖

共 28 个测试用例，覆盖：

- ✅ CredentialsRef 创建与序列化
- ✅ Bridge API 初始化与任务验证
- ✅ 直接任务处理（echo、health_check）
- ✅ 凭证注册与解析
- ✅ Codex 登录、认证与任务委派
- ✅ 安全审计（安全代码、危险导入、危险函数、语法错误）
- ✅ AppleDouble 文件清理（单层、嵌套）
- ✅ Skill 加载（简单 Skill、含 AppleDouble 文件、不存在的 Skill）
- ✅ 完整工作流集成测试

运行测试：
```bash
pytest tests/test_bridge_api.py -v
```

## 使用示例

### 完整工作流

```python
import asyncio
from pathlib import Path
from src.bridge.api import BridgeAPI

async def main():
    # 1. 初始化 Bridge API
    bridge = BridgeAPI(
        codex_endpoint="http://localhost:8000",
        skill_base_path=Path("skills"),
        enable_security_scan=True,
    )

    # 2. 注册 Codex 凭证
    bridge.register_credentials("codex_token", {
        "token": "my_codex_token"
    })

    # 3. 接收并处理任务
    task = {
        "task_id": "demo_001",
        "task_type": "direct",
        "payload": {"action": "health_check"},
    }

    result = await bridge.receive_task(task)
    print(result)

    # 4. 清理资源
    await bridge.cleanup()

asyncio.run(main())
```

## 文件结构

```
src/bridge/
├── __init__.py          # 模块导出
├── api.py               # Bridge API 核心实现
├── skill_loader.py      # Skill 动态加载器 + 安全审计
└── codex_client.py      # Codex 对接客户端

tests/
└── test_bridge_api.py   # 28 个测试用例
```

## 配置选项

### BridgeAPI

- `codex_endpoint`: Codex 服务端点（可选）
- `skill_base_path`: Skill 基础路径（默认：当前目录）
- `enable_security_scan`: 是否启用安全扫描（默认：True）

### SkillLoader

- `base_path`: Skill 基础路径
- `enable_security_scan`: 是否启用安全扫描（默认：True）
- `strict_mode`: 严格模式（安全扫描失败则拒绝加载，默认：False）

### SecurityAuditor

- `strict_mode`: 严格模式（发现危险操作立即失败，默认：True）

## 扩展性

Bridge API 设计为可扩展架构，可以轻松添加：

1. **新的任务类型**：在 `receive_task()` 中添加新的路由逻辑
2. **新的外部系统**：实现类似 `CodexClient` 的客户端类
3. **新的安全检查**：在 `SecurityAuditor` 中添加新的检测规则
4. **新的 Skill 加载策略**：在 `SkillLoader` 中自定义加载逻辑

## 限制与注意事项

1. **凭证存储**：当前实现在内存中存储凭证，生产环境应使用加密存储
2. **Codex 集成**：当前为模拟实现，需要接入真实的 Codex API
3. **并发安全**：凭证存储未加锁，高并发场景需要注意线程安全
4. **网络安全**：Codex 通信未加密，生产环境应使用 HTTPS

## 版本历史

- **v0.1.0** (2026-03-26)
  - ✨ 初始版本
  - ✨ 支持 Direct、Codex、Skill 三种任务类型
  - ✨ 实现安全审计和 AppleDouble 清理
  - ✨ 28 个测试用例，100% 通过率
