# ⚡ v2.0 异构算力全量跃迁 - 任务分配矩阵

**版本**: v2.0-distributed-genesis
**执行时间**: 2026-03-26 11:21 - 14:21 (180 分钟)
**算力矩阵**: 1x Codex + 2x GLM-5 + 3x GLM-4.7

---

## 📊 Agent 职责矩阵

### 🧠 Agent 1: Codex (架构总师)

**目标**: PostgreSQL + Redis 持久化与总线升级

**任务清单**:
1. 引入 asyncpg 和 redis-py
2. 实现基于 Redis Pub/Sub 的全局事件总线
3. 重写 src/memory/session_store.py（分布式支持）

**交付文件**:
- `src/memory/distributed_session_store.py`
- `src/bridge/event_bus.py`
- `requirements.txt` (新增依赖)

**验收标准**:
- Redis Pub/Sub 可跨节点通信
- Session 数据支持分布式共享

---

### 🛡️ Agent 2: GLM-5 (首席安全官)

**目标**: WebAuthn 物理锁实装

**任务清单**:
1. 引入 webauthn 库
2. 实现 FIDO2 注册与断言逻辑
3. 建立高危指令拦截器

**交付文件**:
- `src/security/hardware_lock.py`
- `src/security/webauthn_handler.py`
- `src/bridge/interceptor.py`

**验收标准**:
- 高危指令触发 FaceID/TouchID 验证
- 未授权操作被阻断

---

### 🧩 Agent 3: GLM-5 (演化专家)

**目标**: 可插拔技能市场

**任务清单**:
1. 实现 src/opensage/skill_registry.py
2. 支持远端 Skill 下载（.zip / .py）
3. AST 审计 + 签名校验
4. 动态挂载机制

**交付文件**:
- `src/opensage/skill_registry.py`
- `src/opensage/skill_loader.py`
- `src/opensage/skill_validator.py`

**验收标准**:
- 可从 URL 下载 Skill
- Skill 通过 AST 审计后自动挂载

---

### 📡 Agent 4: GLM-4.7 (通信网关)

**目标**: WebSocket 实时遥测管道

**任务清单**:
1. 增加 WebSocket 端点
2. 打包系统遥测数据（CPU/内存/心跳/日志）
3. 100ms 频率广播

**交付文件**:
- `src/bridge/websocket_telemetry.py`
- `src/bridge/telemetry_collector.py`

**验收标准**:
- WebSocket 连接成功
- 前端接收到实时遥测数据

---

### 🎨 Agent 5: GLM-4.7 (视觉呈现)

**目标**: 实时看板增强

**任务清单**:
1. 接入 WebSocket 数据流
2. 增加实时波形图（心跳 / Token 消耗）
3. 增加"物理锁授权请求"弹窗
4. 浅色背景 + 极简 UI

**交付文件**:
- `frontend/src/components/RealtimeDashboard.jsx`
- `frontend/src/components/WebAuthnModal.jsx`
- `frontend/src/hooks/useTelemetry.js`

**验收标准**:
- 看板显示实时波形图
- 物理锁弹窗正常工作

---

### 🛠️ Agent 6: GLM-4.7 (质量控制)

**目标**: 集成与部署对齐

**任务清单**:
1. 编写 Alembic 数据库迁移脚本
2. 编写 blitz_v2_start.sh
3. 整合所有 Agent 代码
4. 输出全绿 pytest 测试报告

**交付文件**:
- `alembic/versions/001_initial.py`
- `scripts/blitz_v2_start.sh`
- `tests/test_v2_integration.py`

**验收标准**:
- 一键启动 PG/Redis + 服务
- 所有测试通过

---

## 🎯 验收标准（Definition of Done）

### 功能验收

1. ✅ **实时看板**
   - 前端显示心电图般的实时波形
   - 不再是 3 秒刷新的静态数据

2. ✅ **WebAuthn 物理锁**
   - 高危指令触发验证
   - FaceID/TouchID 授权

3. ✅ **一键启动**
   - blitz_v2_start.sh 自动拉起 PG/Redis
   - 完整微服务环境

### 性能验收

- WebSocket 延迟 < 100ms
- Redis Pub/Sub 延迟 < 10ms
- PostgreSQL 查询 < 50ms

### 质量验收

- 所有 pytest 测试通过
- 代码覆盖率 > 80%
- 无高危安全漏洞

---

## 📊 执行时间表

| 阶段 | 时间 | 任务 |
|------|------|------|
| **准备** | 0-5 分钟 | 创建规范文件 |
| **核心开发** | 5-155 分钟 | 6 个 Agent 并行 |
| **集成测试** | 155-175 分钟 | 全链路测试 |
| **验收报告** | 175-180 分钟 | 输出报告 |

---

## 🔧 技术栈

### 后端
- PostgreSQL 15+
- Redis 7+
- asyncpg
- redis-py
- webauthn

### 前端
- React 18
- D3.js / Recharts
- WebSocket API

### 部署
- Docker Compose
- Alembic
- pytest

---

**创建时间**: 2026-03-26 11:21 GMT+8
**预计完成**: 2026-03-26 14:21 GMT+8
**状态**: 🟡 准备中
