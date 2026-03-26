# 多话题分流与技能实装任务规划

> 创建时间：2026-03-26 09:10
> 分支：feature/topic-routing-gateway
> 时间限制：120 分钟

---

## 📋 任务矩阵

### [架构师] Agent-1

**职责**：多话题路由网关（Topic-Aware Gateway）
**文件**：`src/gateway/topic_router.py`, `src/gateway/route_table.py`
**任务**：
1. ✅ 路由映射逻辑（chat_id + message_thread_id）
2. ✅ 原话镜像功能（A 话题 → B 话题备份）
3. ✅ 动态路由选择

---

### [情报官] Agent-2

**职责**：市场监控数据定向投递
**文件**：`src/skills/intelligence_router.py`
**任务**：
1. ✅ 自动识别情感和意图
2. ✅ 动态选择投递目标
3. ✅ MCP 工具：topic_router_utility

---

### [视觉专家] Agent-3

**职责**：图片分析结果投递
**文件**：`src/vision/content_router.py`
**任务**：
1. ✅ 内容话题投递
2. ✅ JSON 卡片权重调整
3. ✅ 视觉字段突出

---

### [安全审计员] Agent-4

**职责**：审计日志投递与安全隔离
**文件**：`src/security/audit_router.py`
**任务**：
1. ✅ 物理清理日志投递
2. ✅ Token 脱敏
3. ✅ 审计群组隔离

---

## 🎯 路由映射契约

```python
# 路由表
ROUTE_TABLE = {
    "intelligence": {
        "chat_id": -1001234567890,
        "thread_id": 10,
        "description": "市场情报话题"
    },
    "content": {
        "chat_id": -1001234567890,
        "thread_id": 20,
        "description": "内容实验室话题"
    },
    "security": {
        "chat_id": -1009876543210,  # 独立审计群
        "thread_id": None,  # 无话题
        "description": "系统审计群组"
    }
}
```

---

## 📊 执行计划

### 阶段 1：并发启动（0-10 分钟）

**启动 4 个子代理**：
1. Agent-1（架构师）→ 路由网关
2. Agent-2（情报官）→ 意图识别
3. Agent-3（视觉专家）→ 内容投递
4. Agent-4（安全审计员）→ 审计隔离

---

### 阶段 2：并行开发（10-100 分钟）

**任务分配**：

**Agent-1**：
- src/gateway/topic_router.py（路由逻辑）
- src/gateway/route_table.py（路由表）
- src/gateway/message_mirror.py（原话镜像）

**Agent-2**：
- src/skills/intelligence_router.py（情报投递）
- src/skills/utils/intent_classifier.py（意图分类）
- src/skills/topic_router_utility.py（MCP 工具）

**Agent-3**：
- src/vision/content_router.py（内容投递）
- src/vision/card_formatter.py（卡片格式化）
- src/vision/weight_adjuster.py（权重调整）

**Agent-4**：
- src/security/audit_router.py（审计投递）
- src/security/token_sanitizer.py（Token 脱敏）
- src/security/audit_logger.py（审计日志）

---

### 阶段 3：集成测试（100-120 分钟）

**任务**：
1. ✅ 运行 234 个测试用例
2. ✅ 修复失败测试
3. ✅ 生成审计日志
4. ✅ 提交代码

---

## 🔒 环境防御

### 预检机制

**强制调用**：
```python
from src.security.apple_double_cleaner import AppleDoubleCleaner

AppleDoubleCleaner.clean()  # 所有分流任务启动前
```

---

### 安全隔离

**Token 脱敏**：
```python
# 审计日志
{
    "timestamp": "2026-03-26T09:10:00Z",
    "action": "token_access",
    "status": "success",
    "token": "***REDACTED***"  # 脱敏
}
```

---

## 📊 交付清单

### 代码模块

- [ ] `src/gateway/topic_router.py`（路由网关）
- [ ] `src/gateway/route_table.py`（路由表）
- [ ] `src/gateway/message_mirror.py`（原话镜像）
- [ ] `src/skills/intelligence_router.py`（情报投递）
- [ ] `src/skills/topic_router_utility.py`（MCP 工具）
- [ ] `src/vision/content_router.py`（内容投递）
- [ ] `src/vision/card_formatter.py`（卡片格式化）
- [ ] `src/security/audit_router.py`（审计投递）
- [ ] `src/security/token_sanitizer.py`（Token 脱敏）

---

### 测试要求

- [ ] 234 个测试用例全绿
- [ ] 新增测试覆盖新功能
- [ ] 审计日志完整

---

### 日志规范

**格式**：
```python
logger.info("[Router-Gate] ...")
```

**示例**：
```python
logger.info("[Router-Gate] Routing message to topic: intelligence")
logger.info("[Router-Gate] Mirror message to backup thread")
logger.info("[Router-Gate] Token sanitized for audit log")
```

---

## 🚀 启动命令

```bash
# 创建分支
cd /Volumes/PS1008/Github/autonomous-agent-stack
git checkout -b feature/topic-routing-gateway

# 启动 4 个子代理
# （通过 sessions_spawn）
```

---

**创建时间**：2026-03-26 09:10
**预计完成**：2026-03-26 11:10
