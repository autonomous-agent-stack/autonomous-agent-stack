# 状态与发布说明 (Status & Release Notes)

最后更新：2026-03-26  
目标版本：MVP 集成版（基于 main 分支）

本文件用于客观记录 Autonomous Agent Stack 的真实工程进度与可用性判定，仅基于代码落点与实机验证结果编写。

## 🟢 核心已验证 (Implemented & Verified)

以下模块已在代码层面存在完整链路，且基础逻辑跑通：

- SQLite 仓储与会话层：OpenClawCompat 接口已实现，对话、评估记录支持断电持久化。
- Docker 动态沙盒：能够将代码路由至容器执行，AppleDouble (`._*`) 清理器代码已实装。
- Telegram 网关：Webhook 连通，支持 `/status` 指令返回短效 JWT 魔法链接。
- 零信任面板：JWT 验签与 Telegram UID 白名单逻辑已在路由层生效，基础浅色看板 UI 可用。
- 静态安全扫描 (AST)：拦截 `os.system` 等高危操作的双通道审计脚本已就绪。
- 知识图谱 (Micro-GraphRAG)：基于纯 Python + SQLite 的三元组存储已实现，玛露红线词汇（平替、代工厂）断言逻辑已就绪。

## 🟡 部分实现 / 简化版 (Partially Implemented / Mocked)

以下模块骨架已搭好，但在生产环境中采用了简化逻辑，尚未达成严格意义上的闭环：

- WebAuthn 生物识别：`/api/v1/auth/webauthn` 路由和前后端拦截器代码存在，但当前包含模拟（Mock）放行逻辑，未强制打通所有设备的真实指纹/面容硬件校验。
- P4 自主集成协议 (OpenSage)：发现、生成适配器并测试的流程骨架已写好，但“在沙盒中自主修复并热更新”的链路目前偏向于半自动化，需人为介入辅助。

## 🟠 仍待验证 (Pending Environment Validation)

由于当前开发环境存在限制，以下状态仅基于代码推演，缺乏稳定的实机运行证据：

- 并发稳定性：Deer-flow 并发控制与事件总线在应对高并发真实 API 回调时的稳定性，尚需实弹压测。
- 生态插件真实收益：P3 阶段的 OpenViking（Token 压缩）与 MiroFish（预测闸门）已作为插件挂载，但在长文本真实业务场景下的 Token 节约率尚无确切数据支撑。
- 全量测试通过率：代码库中包含大量测试用例，但在无特定环境配置的机器上直接执行，可能会因为依赖缺失或路径问题产生报错。

## 📝 下一步行动建议

1. 环境对齐：在目标 M1 宿主机上建立干净的 `venv`，全量安装 `requirements.txt` 并跑通 `pytest`，获取真实的测试覆盖率和通过率报告。
2. 红线实弹测试：向 Telegram 网关发送一张竞品截图或文案，验证视觉解析 + Micro-GraphRAG + Gatekeeper 拦截的完整业务链路是否按预期阻断“工厂化词汇”。
3. 移除 WebAuthn Mock：当准备好真正的生产部署时，清理 `webauthn.py` 中的模拟代码，对接真实的外部可信硬件配置。

## 🔎 参考入口

- OpenClaw 兼容服务：`src/autoresearch/core/services/openclaw_compat.py`
- 面板鉴权：`src/autoresearch/core/services/panel_access.py`
- 面板路由：`src/autoresearch/api/routers/panel.py`
- Telegram 网关：`src/autoresearch/api/routers/gateway_telegram.py`
- WebAuthn 简化路由：`src/autoresearch/api/routers/webauthn.py`
- 动态工具合成：`src/orchestrator/mcp_context.py`
- 沙盒清理：`src/orchestrator/sandbox_cleaner.py`
- 静态安全审计：`src/gatekeeper/static_analyzer.py`
