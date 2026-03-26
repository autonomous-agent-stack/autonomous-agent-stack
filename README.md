# 多话题路由网关

## 项目概述

这是一个 Telegram 多话题路由网关系统，支持智能消息分发、原话镜像备份和动态路由管理。

## 核心功能

### 1. 路由表管理 (RouteTable)
- ✅ 管理话题映射配置
- ✅ 支持动态添加/更新/删除路由
- ✅ 自动计算备份话题 ID
- ✅ 路由启用/禁用控制

### 2. 话题路由器 (TopicRouter)
- ✅ 根据消息类型智能路由到指定话题
- ✅ 支持消息镜像到备份话题
- ✅ 广播消息到多个话题
- ✅ 手动镜像功能

### 3. 消息镜像 (MessageMirror)
- ✅ 原话镜像到备份话题
- ✅ 批量镜像支持
- ✅ 镜像统计和监控

### 4. 环境防御 (AppleDoubleCleaner)
- ✅ 清理 macOS AppleDouble 文件
- ✅ 防止文件系统污染

## 项目结构

```
autonomous-agent-stack/
├── src/
│   ├── gateway/
│   │   ├── __init__.py
│   │   ├── route_table.py       # 路由表
│   │   ├── topic_router.py      # 话题路由器
│   │   └── message_mirror.py    # 消息镜像
│   └── security/
│       ├── __init__.py
│       └── apple_double_cleaner.py  # 环境清理
├── tests/
│   ├── gateway/
│   │   ├── test_route_table.py
│   │   ├── test_message_mirror.py
│   │   ├── test_topic_router.py
│   │   └── test_integration.py
│   └── run_tests.py
└── README.md
```

## 安装依赖

```bash
# 安装 pytest
pip install pytest pytest-asyncio

# 或者使用 uv
uv pip install pytest pytest-asyncio
```

## 快速开始

### 基本使用

```python
from src.gateway.topic_router import TopicRouter
from src.security.apple_double_cleaner import AppleDoubleCleaner

# 1. 环境清理（必须）
AppleDoubleCleaner.clean()

# 2. 初始化路由器
router = TopicRouter()

# 3. 路由消息
result = await router.route_message(
    message_type="intelligence",
    text="市场情报：某公司计划发布新产品",
    mirror=True  # 启用镜像备份
)

print(result)
# {
#     "status": "success",
#     "chat_id": -1001234567890,
#     "thread_id": 10,
#     "message_id": 1234,
#     "mirrored": true,
#     "backup_message_id": 5678
# }
```

### 自定义路由

```python
from src.gateway.route_table import RouteTable
from src.gateway.topic_router import TopicRouter

# 创建自定义路由表
route_table = RouteTable()

# 添加新路由
route_table.add_route(
    message_type="urgent",
    chat_id=-1001111111111,
    thread_id=50,
    description="紧急通知话题"
)

# 使用自定义路由表
router = TopicRouter(route_table=route_table)
```

### 广播消息

```python
router = TopicRouter()

# 广播到所有启用的路由
result = await router.broadcast_message("重要通知")

# 广播到指定类型
result = await router.broadcast_message(
    "特定通知",
    message_types=["intelligence", "content"]
)
```

### 手动镜像

```python
router = TopicRouter()

# 手动镜像消息
result = await router.mirror_message(
    source_chat_id=-1001234567890,
    source_thread_id=10,
    target_chat_id=-1001234567890,
    target_thread_id=110,
    text="需要备份的重要内容"
)
```

## 默认路由配置

| 消息类型 | 群组 ID | 话题 ID | 描述 | 备份话题 ID |
|---------|---------|---------|------|------------|
| intelligence | -1001234567890 | 10 | 市场情报话题 | 110 |
| content | -1001234567890 | 20 | 内容实验室话题 | 120 |
| security | -1009876543210 | None | 系统审计群组 | 无 |

## 运行测试

```bash
# 运行所有测试
python tests/run_tests.py

# 运行特定测试文件
pytest tests/gateway/test_route_table.py -v

# 运行特定测试用例
pytest tests/gateway/test_route_table.py::TestRouteTable::test_get_route_success -v

# 查看测试覆盖率
pytest tests/ --cov=src/gateway --cov-report=html
```

## 测试覆盖

### 单元测试 (Unit Tests)
- ✅ RouteTable: 15 个测试用例
- ✅ MessageMirror: 10 个测试用例
- ✅ TopicRouter: 12 个测试用例

### 集成测试 (Integration Tests)
- ✅ 完整路由工作流
- ✅ 动态路由管理
- ✅ 混合状态广播
- ✅ 手动镜像工作流
- ✅ 错误处理
- ✅ 并发路由
- ✅ 备份路由计算
- ✅ 安全清理
- ✅ 路由更新
- ✅ 路由列表完整性

**总计：47+ 个测试用例**

## 日志规范

系统使用结构化日志，便于调试和监控：

```
[Router-Gate] Topic router initialized
[Router-Gate] RouteTable initialized with 3 routes
[Router-Gate] Routing message to: intelligence -> -1001234567890:10
[Router-Gate] Mirror enabled, backing up to: 110
[Router-Gate] Message mirrored: 1234 -> -1001234567890:110 (ID: 5678)
[Router-Gate] Route validation passed
[Security] Starting AppleDouble cleanup in: /path/to/dir
[Security] Cleanup complete: 3 files removed
```

## API 参考

### RouteTable

```python
class RouteTable:
    def get_route(message_type: str) -> Optional[Dict]
    def add_route(message_type, chat_id, thread_id, description) -> bool
    def update_route(message_type, **kwargs) -> bool
    def disable_route(message_type) -> bool
    def enable_route(message_type) -> bool
    def list_routes() -> List[Dict]
    def get_backup_route(message_type) -> Optional[Dict]
```

### TopicRouter

```python
class TopicRouter:
    async def route_message(message_type, text, mirror=False, sender_id=None) -> Dict
    async def mirror_message(source_chat_id, source_thread_id, target_chat_id, target_thread_id, text) -> Dict
    async def broadcast_message(text, message_types=None) -> Dict
    def get_router_stats() -> Dict
    def add_route(message_type, chat_id, thread_id, description) -> bool
```

### MessageMirror

```python
class MessageMirror:
    async def mirror_to_backup(original_message, backup_chat_id, backup_thread_id) -> Dict
    async def batch_mirror(messages, backup_chat_id, backup_thread_id) -> Dict
    def get_mirror_stats() -> Dict
```

### AppleDoubleCleaner

```python
class AppleDoubleCleaner:
    @staticmethod
    def clean(directory=".") -> int
    @staticmethod
    def check(directory=".") -> int
```

## 配置说明

### 环境变量（可选）

```bash
# Telegram Bot Token（如果需要实际发送消息）
export TELEGRAM_BOT_TOKEN="your_bot_token_here"

# 日志级别
export LOG_LEVEL="INFO"
```

### 路由配置

路由配置可以通过以下方式管理：

1. **代码配置**：使用默认路由或自定义 RouteTable
2. **文件配置**（未来支持）：从 JSON/YAML 文件加载
3. **动态配置**：运行时添加/修改路由

## 安全考虑

1. **环境清理**：所有路由操作前强制执行 AppleDouble 清理
2. **路由验证**：启动时验证所有路由配置的有效性
3. **错误处理**：所有 API 都有完善的错误处理和日志记录
4. **类型检查**：严格验证 chat_id 和 thread_id 的类型

## 性能优化

1. **异步操作**：所有 I/O 操作都是异步的
2. **批量处理**：支持批量镜像，减少 API 调用
3. **连接池**（未来）：复用 Telegram Bot 连接

## 未来计划

- [ ] 支持从文件加载路由配置
- [ ] 实现实际的 Telegram Bot API 集成
- [ ] 添加消息重试机制
- [ ] 支持路由优先级
- [ ] 添加 Web UI 管理界面
- [ ] 支持消息模板
- [ ] 添加性能监控和指标

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

MIT License

## 作者

Agent-1: 架构师（Topic Router）

---

**注意**：当前版本使用模拟模式，不会实际发送 Telegram 消息。要启用实际发送，需要配置真实的 Telegram Bot Token。
