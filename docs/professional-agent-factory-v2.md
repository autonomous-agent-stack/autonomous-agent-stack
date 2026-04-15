# 🚀 专业 Agent 工厂 - 影刀能力底座 + Agent 模板

> **时间**: 2026-03-31 14:20
> **状态**: 🔥 火力全开 × 10
> **核心**: 做专业 agent 工厂，不是万能 agent

---

## 🎯 核心定位

### 从

**错误目标**: 一个通用型、什么都能操作的超级 agent

### 到

**正确定位**: 一个能批量生产、分发、治理专业 agent 的 control plane

---

## 💡 为什么可行？

### 现有基础

1. **OpenClow 成熟 runtime**
   - Gateway / agent runtime
   - Skills 体系
   - 远程节点能力

2. **影刀 API/SDK 文档**
   - 可编程接口
   - 标准化流程调用

3. **Paperclip 公开定位**
   - 带自己的 agents 进来
   - 统一目标、预算、治理、看板
   - 不要求所有 agent 长成一个模样

---

## 🏭️ 两层架构

### 第一层：影刀能力底座

#### 统一封装（平台能力）

**核心接口**:
```yaml
run_flow(flow_id, inputs)
get_run_status(run_id)
get_artifacts(run_id)
cancel_run(run_id)
list_available_flows()
```

**功能**:
- 流程执行
- 状态查询
- 产物获取
- 任务取消
- 流程列表

---

### 第二层：专业 Agent 模板

#### Agent Package 定义（5 样东西）

**1. 能力声明**
- 它会什么、不会什么
- 边界清晰

**2. 执行适配器**
- 我调用哪个影刀 flow
- 我需要哪些输入
- 我怎么处理错误

**3. 任务表单 / 输入 schema**
- 输入格式要求
- 必填/可选字段
- 验证规则

**4. 策略与边界**
- 哪些动作允许
- 哪些必须审批
- 禁止某些操作

**5. 结果 schema**
- 交付什么产物
- 日志格式
- 截图要求
- 状态定义

---

## 📦 专业 Agent 列表

### 可分享的专业 Agent 模板

#### 1. 表单录入 Agent
**能力**: 把标准化数据喂给影刀流程

**输入**: CSV/JSON/Excel
**调用**: 影刀流程
**产物**: 录入成功回执

**适用**: ERP/财务/客服后台录入

**定义**:
- 能力声明：录入标准化数据
- 执行适配器：表单录入技能
- 任务表单：数据字段映射
- 策略：数据验证、错误重试
- 结果：录入成功确认

---

#### 2. 对账 Agent
**能力**: Linux 清洗数据 + Win+影刀回填 + 生成回执

**输入**: 原始数据
**调用**: Linux worker + 影刀流程
**产物**: 核对回执

**定义**:
- 能力声明：数据清洗 + 回填
- 执行适配器：data_pipeline 技能
- 任务表单：数据清洗规则
- 策略：回填策略、异常处理

---

#### 3. 店铺巡检 Agent
**能力**: OpenClow/浏览器抓数 + 影刀补全桌面端动作

**输入**: 工铺要求
**调用**: OpenClow + 影刀流程
**产物**: 工铺状态报告

**定义**:
- 能力声明：数据采集 + 分析
- 执行适配器：browser_agent 技能
- 任务表单：巡检清单
- 策略：异常处理、告警

---

#### 4. 报表 Agent
**能力**: 抓取、清洗、生成、投递一条龙

**输入**: 报表需求
**调用**: OpenClow + Linux worker + Win+影刀
**产物**: 投递结果

**定义**:
- 能力声明：报表生成
- 执行适配器：report_generator 技能
- 任务表单：报表规则
- 策略：多渠道投递

---

#### 5. 客服工单 Agent
**能力**: 分类、摘要、分流、后台操作

**输入**: 工单信息
**调用**: OpenClow + 影刀流程
**产物**: 处理结果

**定义**:
- 能力声明：工单处理
- 执行适配器：ticket_router 技能
- 任务表单：工单状态机
- 策略：分流规则、升级条件

---

## ⚠️ 边界

### ✅ 应该做

**专业 Agent 工厂**:
- ✅ 批量生产专业 agent
- ✅ 易复制、易修改、可分享
- ✅ 版本控制、权限控制

**专业 Agent 包**:
- ✅ 明确的能力边界
- ✅ 清晰的输入输出
- ✅ 标准的审批规则

### ❌ 不应该先做

**通用型影刀 Agent**（第一版）:
- ❌ "万能 agent"
- ❌ 边界不清
- ❌ 难维护
- ❌ 难分享

---

## 🎯 更新后的 18 天目标

### 保留的核心

- ✅ 一个任务队列
- **一个 worker 注册表**
- **一个 run 状态机**
- **一个最小控制台**
- **OpenClow worker**（新增）
- **Linux worker**
- **Win+影刀 worker**
- **task gate**
- **至少一条真实闭环**

### 新增的内容

- **影刀能力底座**
- **专业 Agent 模板**（5 个）
- **Agent Package 规范**
- **专业 Agent 工厂**

---

## 🚀 实施计划（18 天）

### Day 1-2: 收缩范围
- 定义统一任务 schema（支持 OpenClow worker）
- 定义 Agent Package 规范（5 样组件）
- 定义影刀能力底座接口

### Day 3-4: 跨机器协议
- 实现 openclaw_agent driver
- 实现 yingdao_skill 底座接口
- 实现 mac_worker 底座接口

### Day 5-6: 最小控制台
- 任务列表（各类 agent）
- Worker 列表（OpenClow、Linux、Mac、Win+影刀）
- Run 详情
- 人工审批页（高风险动作）

### Day 7-8: Linux worker + 影刀底座
- Shell command
- Python script
- File upload
- **影刀能力底座调用**

### Day 9-10: Win+影刀 worker
- **影刀能力底座调用**
- 调用已有影刀流程
- 指定流程执行

### Day 11-12: task gate
- 泛化 patch gate 为 task gate
- 新增影刀专用判定规则

### Day 13-14: 真实闭环
- 表单录入 Agent 测试
- 对账 Agent 测试
- 工铺巡检 Agent 测试

### Day 15-16: 最小自优化
- 优化路由策略
- 优化失败恢复

### Day 17-18: 压测、演示、收口
- 完整 demo
- 专业 Agent 展示

---

## 📊 成功标准

### 能做（5 个指标）

1. **可追踪** - 任务从下达到完成是否可追踪
2. **【可恢复】 - 任务失败后是否可恢复
3. **可复制】 - Agent Package 易复制
4. **可分享】 - Agent Package 易分享
- **可治理** - 权限、边界清晰

### 不算跑偏

- ✅ 控制平面功能完整
- ✅ Workers 正常工作
- ✅ Gate 仍然有效
- ✅ 专业 Agent 可复用

---

## 💡 一句话收口

> **你该做的不是"一个万能影刀 agent"，而是"一个能批量生产、分发、治理专业影刀 agent 的 control plane"。**

---

## 📚 相关文档

**更新文档**:
- [18-DAY-SPRINT.md](./18-DAY-SPRINT.md) - 更新中
- [VISION-ADJUSTMENT.md](./VISION-ADJUSTMENT.md)
- [openclaw-replacement-migration-playbook.md](./openclaw-replacement-migration-playbook.md)

---

**整理者**: srxly888-creator
**时间**: 2026-03-31 14:20
**状态**: ✅ 专业 Agent 工厂概念已整合
**标签**: #专业Agent #影刀 #AgentPackage #工场 #18天计划
