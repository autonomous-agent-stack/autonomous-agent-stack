# 18 天冲刺计划 - 可治理的 AI 调度中枢

> **目标时间**: 18 天
> **目标**: 做出"能跑的控制平面 + 2 到 3 个 worker + 1 条闭环业务流"
> **不是**: 18 天做出"无需人类干预、还能自我进化的超级智能体"
> **而是**: 18 天造出一个能调度 Mac/Linux/Win+影刀的受控自治底座 v0

---

## 🎯 18 天目标

### 到第 18 天，拿到这 4 个结果

1. **一个统一任务面板**
   - 任务列表、worker 列表、run 详情、人工审批页

2. **三类执行节点里至少两类跑通**
   - linux_worker ✅
   - win_yingdao_worker ✅
   - mac_worker（可选，第三个补上）

3. **一条真实闭环流程跑通**
   - 抓数据 → 清洗 → 影刀录入 → 生成结果回传

4. **一套最小自优化**
   - 只优化路由/重试/参数，不碰权限和规则

### 核心理念

```
一句任务 → 控制平面分发 → worker 执行 →
回传日志/截图/结果 → gate 判定 → 必要时人工接管
```

---

## 📅 18 天排期

### Day 1-2: 收缩范围，冻结目标

**别再做"大而全"**

**只保留三条主线**:
- JobSpec
- DriverResult
- decision

**目标**: 1 条 demo 流程
- 抓数据
- 清洗
- 影刀录入
- 生成结果回传

**只干三件事**:
1. 定义统一任务 schema
2. 定义 worker 注册 schema
3. 定义统一 run 状态机

**状态机**:
- queued
- leased
- running
- succeeded
- failed
- needs_review

**复用现有**: control-plane / AEP 思想（JobSpec → driver adapter → validators → decision）

---

### Day 3-4: 把 AEP 改成"跨机器协议"

**最关键的一步**

**新增三个 driver**:
- linux_worker
- mac_worker
- win_yingdao_worker

**统一输入**:
- task id
- task type
- params
- allowed actions
- timeout
- artifact path

**统一输出**:
- status
- stdout/stderr
- screenshots
- structured result
- error type
- suggested next action

**最土但最稳的方式**:
- HTTP pull task
- HTTP post result
- 或 polling + webhook

**复用现有**: remote wrapper、heartbeat、result fetch、failure taxonomy

---

### Day 5-6: 做最小控制台

**只做 4 个页面**:
1. 任务列表
2. worker 列表
3. run 详情
4. 人工审批页

**run 详情页必须看到**:
- 谁接单
- 什么时候开始
- 日志
- 截图
- 产物
- decision

**目的**: 不是"好看"，而是调 bug 不会崩

---

### Day 7-8: 先打通 Linux worker

**Linux 最容易先通**

**三类能力**:
- shell command
- python script
- file artifact upload

**示例任务**:
- 拉取网页数据
- 清洗 CSV
- 生成 JSON/Excel
- 回传产物

**目标**: Linux worker 成为最稳的执行器

**只要 Linux worker 跑通，整个控制平面就算活了**

---

### Day 9-10: 接 Windows + 影刀 worker

**只做一件事**: 把影刀当执行器，不把它当大脑

**worker 只暴露几个固定 action**:
- run_flow(flow_id, inputs)
- get_run_status(run_id)
- get_artifacts(run_id)
- cancel_run(run_id)

**返回**:
- 执行状态
- 截图
- 影刀流程日志
- 输出文件

**不要先做**: "自然语言生成影刀流程"

**18 天版只需要**: 控制平面调用已有影刀流程

**这是天差地别**: 前者会炸，后者能上线

---

### Day 11-12: 把 gate 从 patch gate 泛化成 task gate

**改成更通用的 task gate**

**判定维度只保留 5 个**:
1. 是否成功
2. 是否越权
3. 是否超时
4. 是否缺关键产物
5. 是否需要人工确认

**输出决策**:
- accept
- retry
- fallback
- needs_review

**别搞**: 十几种复杂决策树

**这就够了**

---

### Day 13-14: 打通第一条真实闭环

**找一条你真会用的流程，别做假 demo**

**示例**:
1. Linux 抓取表格/订单/报表
2. Linux 清洗成标准格式
3. Windows+影刀录入老系统
4. Linux 或 Mac 生成回执和日报
5. 控制平面汇总并通知你

**只打一条**
- 18 天不需要"平台"
- 只需要一条持续可复跑的闭环

---

### Day 15-16: 做最小自优化

**注意**: 不是"自我进化"，只是自动调参

**只允许优化这三类**:
- 哪类任务优先派给哪个 worker
- 失败后 retry 还是 fallback
- timeout / retry_count / backoff

**不要允许它自动改**:
- ❌ 权限模型
- ❌ gate 规则
- ❌ worker 白名单
- ❌ 外部系统写入规则

**原则**: 让它优化调度策略，别优化系统宪法

**实现**:
- 记录每类 task 在不同 worker 上的成功率/耗时
- 下一次优先派给历史最优 worker
- 连续失败则自动降级到人工审批

---

### Day 17-18: 压测、演示、收口

**最后两天只干三件事**:
1. 连跑 20 到 50 次任务
2. 故意制造 5 类失败
3. 录一段完整 demo

**验证的不是**: "它是不是超级智能体"

**验证的是**:
1. 有任务来时会不会跑 ✅
2. 失败时会不会乱 ✅
3. 越权时会不会停 ✅
4. 人工接管时会不会顺 ✅

**只要这四个答案是"会、不会、会、会"，你这 18 天就值了**

---

## ⚠️ 哪些先砍

### 18 天内先别碰这些

- ❌ 自我修改主控制平面
- ❌ 自动创建/修改技能市场
- ❌ 多 agent 自由辩论
- ❌ 长期记忆人格化
- ❌ 自动融资式"公司治理幻想"
- ❌ 全渠道入口（Telegram/网页/语音全上）

**原因**: 这些都很诱人，但都会拖死节奏

---

## ✅ 哪些必须保留

### 必须保留的只有这些

- ✅ AEP / JobSpec 思路
- ✅ driver adapter
- ✅ validators / gate
- ✅ isolated run artifact
- ✅ heartbeat / timeout / failure taxonomy
- ✅ human_review 分支

**原因**: 这些正是仓库当前最成熟的硬骨架

---

## 💡 18 天定义

### 不是

```
18 天造出超级智能体
```

### 而是

```
18 天造出一个能调度 Mac/Linux/Win+影刀的受控自治底座 v0
```

### 这个目标够狠，也够真实

---

## 🎯 最适合的口号

### 现在的项目最适合的口号不是

```
"无需人类干预，自我进化"
```

### 而是

```
"18 天做出一个可治理的 AI 调度中枢。"
```

### 这个真有机会成

---

## 📊 总结

### 核心原则

1. **借现有骨架** - AEP + control-plane
2. **快速迭代** - 18 天，不是 18 个月
3. **真实闭环** - 一条能跑的流程
4. **最小优化** - 只优化调度，不优化宪法
5. **可治理** - 有边界、可追踪、可审计

### 成功标准

- ✅ 能跑的控制平面
- ✅ 2-3 个 worker
- ✅ 1 条闭环业务流
- ✅ 最小自优化

---

**制定者**: srxly888-creator
**时间**: 2026-03-31 13:41
**期限**: 18 天
**标签**: #18天冲刺 #AI调度中枢 #控制平面
