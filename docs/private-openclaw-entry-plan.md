# 私人版 OpenClaw 入口 - 实施计划

> **时间**: 2026-03-31 14:07
> **状态**: 🔥 火即执行
> **模式**: 🔥 火力全开 × 10

---

## 🎯 目标

### 值得做：私人管家入口

**只补这些能力**:
- ✅ Personal agent persona
- ✅ 个人偏好/ ❌ 任务解释与汇报
- ✅ 给调度中心发任务
- ✅ 帮你审批高风险动作

### 不跑偏：保持主线定位

**主线**: "可治理的 AI 调度中枢"
- 控制平面仍然是主航道
- 私人管家只是入口层

---

## 📋 实施步骤

### Phase 1: 创建 Personal Agent Persona

**定义**: personal-agent-persona.md

```yaml
name: "Your Personal Assistant"
role: "Personal Agent"
tone: "友好、专业、高效"
capabilities:
  - 理解自然语言任务
  - 翻译成标准任务单
  - 汇报执行结果
```

---

### Phase 2: 个人偏好/上下文记忆

**存储**: personal-preferences.yaml

```yaml
user:
  name: "Your Name"
  timezone: "Asia/Shanghai"
  preferred_worker: "linux"
  working_hours: "09:00-18:00"

preferences:
  notification: true
  auto_approve_safe_tasks: false
  require_approval_for:
    - system_write
    - large_file_operations
```

---

### Phase 3: 任务解释与翻译

**输入**: 自然语言任务

**输出**: 标准任务单

**示例**:
```json
{
  "task_type": "data_extraction",
  "params": {
    "source": "https://example.com/data",
    "format": "json",
    "worker": "linux_worker"
  }
}
```

---

### Phase 4: 与控制平面集成

**接口**: REST API

```python
# 私人管家 -> 控制平面
POST /api/v1/tasks
{
  "user": "user_id",
  "natural_language_task": "帮我抓取昨天的销售数据",
  "translated_task_spec": {...}
}
```

---

### Phase 5: 高风险动作审批

**审批流程**:
1. 私人管家识别高风险任务
2. 暂停任务，通知用户
3. 等待用户审批
4. 获得批准后继续

---

## 🚀 18 天计划整合

### Day 5-6: 最小控制台（已有）

**新增**: 私人管家面板
- 任务输入
- 个人偏好配置
- 审批队列

---

### Day 13-14: 真实闭环（已有）

**新增**: 私人管家入口
- 自然语言任务
- 任务解释
- 结果汇报

---

## 📊 架构

```
┌─────────────────────────────────────┐
│         你（自然语言）              │
└──────────────┬──────────────────────┘
               ↓
┌───────────────────────────────────────┐
│     私人管家入口（新增）           │
│  - Personal Agent Persona         │
│  - 个人偏好/上下文记忆            │
│  - 任务解释与翻译               │
│  - 高风险动作审批               │
└──────────────┬──────────────────────┘
               ↓
┌───────────────────────────────────────┐
│     控制平面（主航道）            │
│  - 任务调度                     │
│  - Worker 管理                   │
│  - Gate 判定                     │
└──────────────┬──────────────────────┘
               ↓
┌───────────────────────────────────────┐
│     Workers（执行层）              │
│  - OpenHands/Codex                 │
│  - Linux worker                   │
│  - Mac worker                    │
│  │
│  - Windows+影刀 worker              │
└──────────────────────────────────────┘
```

---

## ⚠️ 边界线

### ✅ 不算跑偏

- ✅ 控制平面仍然是主航道
- ✅ Workers 仍然是执行核心
- ✅ gate/rules 仍然是治理核心
- ✅ 私人管家只是入口层

### ❌ 会跑偏

- ❌ 把控制平面降级为配角
- ❌ 把"私人管家"做成主叙事
- ❌ 重造 OpenClaw 的核心能力
- ❌ 失去"可治理的 AI 调度中枢"定位

---

## 💡 关键原则

> **你的项目主线应该还是"可治理的 AI 调度中枢"。**
> **私人版 OpenClaw 只能是这个中枢的一个入口，不该反过来吞掉中枢。**

---

## 🎯 成功标准

### 不算跑偏

- ✅ 控制平面功能完整
- ✅ Workers 正常工作
- ✅ Gate 仍然有效
- ✅ 私人管家只是增强体验

### 会跑偏

- ❌ 控制平面功能简化
- ❌ Workers 能力受限
- ⚠️ Gate 规则被绕过
- ❌ 项目重心变成"个人助理产品"

---

## 📚 相关文档

**主愿景**: [VISION-ADJUSTMENT.md](../VISION-ADJUSTMENT.md)
**18 天计划**: [18-DAY-SPRINT.md](../18-DAY-SAPRINT.md)
**OpenClaw 迁移**: [openclaw-replacement-migration-playbook.md](../openclaw-replacement-migration-playbook.md)

---

**创建者**: srxly888-creator
**时间**: 2026-03-31 14:07
**状态**: ✅ 边界线明确
**标签**: #私人管家 #OpenClaw #边界线 #入口设计
