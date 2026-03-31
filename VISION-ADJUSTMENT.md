# Autonomous Agent Stack - 愿景调整

> **调整时间**: 2026-03-31 13:37
> **调整原因**: 基于 ARCHITECTURE.md 和 AEP v0 的现实定位

---

## 🎯 新愿景

### 从

**旧愿景**: 无需人类干预的自我进化超级智能体网络

### 到

**新愿景**: 一个受控的 agent execution control plane，统一调度代码 agent、Linux worker、Mac worker、Windows RPA worker

---

## 💡 为什么调整？

### 现实定位（基于 ARCHITECTURE.md）

截至 2026-03-31，autonomous-agent-stack 的"稳定主干"是一个：

- ✅ **有边界的 control plane**
- ✅ **隔离执行环境**（isolated workspace）
- ✅ **验证与 promotion gate**
- ✅ **受控自治**（不是自由生长）

### 核心特征

- ❌ **不是**: 自我进化超级体
- ✅ **而是**: 受控自动化平台
- ❌ **不是**: 自主编织
- ✅ **而是**: 可治理的执行控制平面

### 当前成熟能力

- ✅ JobSpec
- ✅ driver adapter
- ✅ isolated workspace
- ✅ validation gate
- ✅ promotion gate
- ✅ Draft PR / patch artifact 输出

**结论**: 这些能力解决的是"怎么安全地让 agent 干活"，不是"怎么让 agent 自己变聪明并长期自治"。

---

## 🚀 可行 Roadmap（6 个 Phase）

### Phase 0: 停止追"自我进化"

**目标**: 调整项目叙事

**从**:
```
无需人类干预的自我进化超级智能体网络
```

**到**:
```
一个受控的 agent execution control plane，
统一调度代码 agent、Linux worker、Mac worker、Windows RPA worker
```

**原因**: 产品生死线。ARCHITECTURE.md 明确要信 current stable spine，不是旧的 aspirational stack diagrams。

---

### Phase 1: 把 AEP 变成"统一 worker 协议"

**目标**: 让 AEP 不只驱动 OpenHands/Codex/本地脚本，也能驱动异构执行节点。

**新增 3 类 driver**:
- `mac_worker`
- `linux_worker`
- `win_yingdao_worker`

**统一输入**:
- task spec
- policy
- timeout
- artifact path
- result schema

**统一输出**:
- stdout/stderr
- 截图/录屏/产物
- 结构化 result
- heartbeat/events
- success/failure 分类

**适配**: 沿用 AEP 现有的 run folder 约定和 driver_result.json 合同。

---

### Phase 2: 把"patch gate"推广成"task gate"

**目标**: 泛化验证和 promotion 机制。

**任务类型**:
- 代码任务: 输出 promotion patch / Draft PR
- Linux 任务: 输出日志、文件、服务状态
- Mac 任务: 输出浏览器截图、表格、报告
- Windows+影刀: 输出流程执行记录、截图、Excel、系统回执

**统一判断**:
- 是否超预算
- 是否越权
- 是否产物完整
- 是否命中 forbidden paths / forbidden tools
- 是否需要 human_review

**结果**: 从"代码 agent"变成"智能底座"。

---

### Phase 3: 做真正的远程 worker

**基础**: ARCHITECTURE.md 已有 offline remote hardening layer:
- RemoteTaskSpec
- RemoteRunRecord
- RemoteRunSummary
- 模拟 remote adapter
- failure taxonomy
- day/night runtime config

**实施方案**:
- 每台机器跑轻量 agent daemon
- 定时 heartbeat
- 轮询或长连领取任务
- 回传 events / summary / artifacts
- 支持取消、超时、中断恢复

**顺序**: Linux → Mac → Windows+影刀
**原因**: Windows 桌面自动化不确定性最大。

---

### Phase 4: 引入"人类在环"的审批点

**目标**: 保留少量审批点（提速，不是保守）。

**3 个审批点**:
1. 高风险任务首次执行
2. 影响外部系统写入的任务
3. agent 提议修改自己的配置/策略/driver 时

**实施**: 扩展现有的 human_review 终态/分支到异构任务。

---

### Phase 5: 有限自优化

**注意**: 不是"自我进化"，而是有限自优化。

**允许自动优化**:
- ✅ prompt 模板
- ✅ tool routing
- ✅ timeout / retry 参数
- ✅ worker 选择策略
- ✅ 失败恢复策略
- ✅ 某些技能的 manifest

**禁止自动优化**:
- ❌ promotion gate 规则
- ❌ forbidden paths
- ❌ 权限模型
- ❌ 金融/外部系统写权限
- ❌ 主控制平面的核心代码

**原则**: 可以让它优化手脚，但别让它改宪法。

---

### Phase 6: 连续自治

**前提**: 前 5 个 Phase 都稳定。

**能力**:
- 周期性目标
- 自动分解任务树
- 成本预算器
- 多 worker 协同
- 失败后自主重规划

**定位**: 勉强配叫"半自治系统"。离"超级智能体"有距离，但能创造真实产值。

---

## 📊 成败标准

### 别用"会不会自我进化"判断

### 用这 5 个指标判断:

1. **可追踪性**
   - 一个任务从下达到完成，是否可追踪

2. **可恢复性**
   - 一个任务失败后，是否可恢复

3. **协同稳定性**
   - 多个 worker 并行时，是否不打架

4. **可审计性**
   - 涉及外部系统时，是否可审计

5. **硬边界**
   - 修改系统自身时，是否有硬边界

**如果这 5 个过了，项目就不是玩具了。**

---

## 🎯 总结

### 这仓库不适合
- ❌ 直接冲"超级智能体神话"

### 这仓库非常适合
- ✅ 改造成"AI 调度中枢"

### 它已具备
- ✅ bounded control plane
- ✅ isolated execution
- ✅ validation gate
- ✅ promotion gate
- ✅ AEP driver model
- ✅ offline remote hardening 的雏形

### 这些是做"多机、多执行器、可治理自治系统"的硬骨架。

---

## 💡 建议

**不是"放弃愿景"，而是:**

- **前 6 天**: 做控制平面
- **中 6 天**: 做异构 worker
- **后 6 天**: 做有限自优化

---

**调整者**: srxly888-creator
**时间**: 2026-03-31 13:37
**标签**: #愿景调整 #roadmap #控制平面
