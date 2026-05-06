# Stage 1 Done

阶段一目标是把仓库收成一条稳定主线，而不是继续叠功能。这个目标已经完成，可以作为后续开发的冻结基线。

## 已完成

- 唯一主入口固定为 `src/autoresearch/api/main.py`
- `openclaw`、`gateway_telegram`、`panel`、`admin`、`webauthn` 路由统一由主应用装配
- `/telegram/webhook` 兼容入口与 `/api/v1/gateway/telegram/webhook` 收为同一处理链
- 集中式 `settings.py` 配置面建立完成，主线运行逻辑不再依赖散落的 `os.getenv`
- `panel` 路由恢复挂载，核心健康检查和安全测试路径恢复可用
- `mirofish` prediction gate 改为显式 feature flag，默认关闭
- 测试态 `AUTORESEARCH_API_DB_PATH` 已强制指向临时 SQLite，避免污染开发机数据
- 测试 collect 与核心回归已恢复为可运行状态

## 当前基线的边界

- 本阶段只解决“挂载/启动/鉴权/collect/核心回归”问题
- 不包含三层记忆、Mini App 审批、GLM-V、多 agent 聚合、在线 skills 市场
- 历史兼容以 HTTP 路径连续性为主，不保留旧 workflow 分叉语义

## 已知未收口项

以下模块仍保留直接环境变量读取，暂未并入阶段一配置主线：

- `src/autoresearch/api/routers/webauthn.py`
- `src/autoresearch/core/services/group_access.py`
- `src/autoresearch/core/services/claude_agents.py`
- `src/autoresearch/core/services/telegram_image_downloader.py`
- `src/autoresearch/core/services/panel_audit.py`
- `src/autoresearch/core/auth/middleware.py`
- `src/autoresearch/core/cache/redis_cache.py`
- `src/autoresearch/core/evolution_manager.py`
- `src/autoresearch/core/services/hitl_approval.py`
- `src/autoresearch/core/services/tool_registry.py`
- `src/autoresearch/llm/*.py`
- `src/gateway/*.py`

## 建议的后续顺序

- 阶段二-A：`identity/session/scope` 数据模型与 SQLite 落库接口
- 阶段二-B：三层记忆 contract
- 阶段三：GLM-V 与 macOS STT 适配器
- 阶段四：审批流与 Git 策略
- 阶段五：skills 在线更新与受控并发
