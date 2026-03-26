# 4 大 Agent 矩阵桥接任务规划

> 创建时间：2026-03-26 08:37
> 分支：feature/4-agent-matrix-bridge
> 时间限制：120 分钟

---

## 📋 任务矩阵

### [架构师] Agent-1

**职责**：Bridge API 深度贯通
**文件**：`src/bridge/api.py`, `src/bridge/skill_loader.py`
**任务**：
1. ✅ 双向鉴权（credentials_ref 解耦调用）
2. ✅ 动态加载（强制安全扫描）
3. ✅ 对接 Codex 登录与任务委派

---

### [情报官] Agent-2

**职责**：通用趋势监控 Skill
**文件**：`src/skills/market_pain_point_extractor.py`
**任务**：
1. ✅ MCP 工具实现
2. ✅ 关键词列表配置
3. ✅ 低质量噪音过滤
4. ✅ JSON 报告生成（SQLite）

---

### [视觉专家] Agent-3

**职责**：多模态视觉网关
**文件**：`src/vision/visual_gateway.py`
**任务**：
1. ✅ 图形质感转化
2. ✅ 数据截图解析
3. ✅ 结构化文案逻辑

---

### [安全审计员] Agent-4

**职责**：物理清理与 AST 审计
**文件**：`src/security/apple_double_cleaner.py`, `src/security/ast_auditor.py`
**任务**：
1. ✅ AppleDoubleCleaner.clean() 强制预检
2. ✅ AST 静态审计
3. ✅ WebAuthn 物理验证触发

---

## 🎯 执行计划

### 阶段 1：并发启动（0-10 分钟）

**启动 4 个子代理**：
1. Agent-1（架构师）→ Bridge API
2. Agent-2（情报官）→ Market Skill
3. Agent-3（视觉专家）→ Visual Gateway
4. Agent-4（安全审计员）→ Security Hooks

---

### 阶段 2：并行开发（10-100 分钟）

**任务分配**：

**Agent-1**：
- src/bridge/api.py（双向鉴权）
- src/bridge/skill_loader.py（动态加载）
- src/bridge/codex_client.py（Codex 对接）

**Agent-2**：
- src/skills/market_pain_point_extractor.py（MCP 工具）
- src/skills/config/keywords.json（关键词配置）
- src/skills/utils/noise_filter.py（噪音过滤）

**Agent-3**：
- src/vision/visual_gateway.py（视觉网关）
- src/vision/texture_analyzer.py（质感分析）
- src/vision/chart_parser.py（图表解析）

**Agent-4**：
- src/security/apple_double_cleaner.py（物理清理）
- src/security/ast_auditor.py（AST 审计）
- src/security/webauthn_trigger.py（物理验证）

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

AppleDoubleCleaner.clean()  # 所有任务启动前
```

---

### 高危授权

**触发条件**：
- 环境变量更新
- 敏感文件读取

**自动触发**：
```python
from src.security.webauthn_trigger import WebAuthnTrigger

WebAuthnTrigger.request_verification()  # 高危操作前
```

---

## 📊 交付清单

### 代码模块

- [ ] `src/bridge/api.py`（Bridge API）
- [ ] `src/bridge/skill_loader.py`（动态加载）
- [ ] `src/skills/market_pain_point_extractor.py`（市场监控）
- [ ] `src/vision/visual_gateway.py`（视觉网关）
- [ ] `src/security/apple_double_cleaner.py`（物理清理）
- [ ] `src/security/ast_auditor.py`（AST 审计）

---

### 测试要求

- [ ] 234 个测试用例全绿
- [ ] 新增测试覆盖新功能
- [ ] 审计日志完整

---

### 日志规范

**格式**：
```python
logger.info("[Agent-Stack-Bridge] ...")
```

**示例**：
```python
logger.info("[Agent-Stack-Bridge] Bridge API initialized")
logger.info("[Agent-Stack-Bridge] Skill loaded: market_pain_point_extractor")
logger.info("[Agent-Stack-Bridge] Security scan passed")
```

---

## 🚀 启动命令

```bash
# 创建分支
cd /Volumes/PS1008/Github/autonomous-agent-stack
git checkout -b feature/4-agent-matrix-bridge

# 启动 4 个子代理
# （通过 sessions_spawn）
```

---

**创建时间**：2026-03-26 08:37
**预计完成**：2026-03-26 10:37
