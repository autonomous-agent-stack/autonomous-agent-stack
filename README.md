# Autonomous Agent Stack

一个**受控的 agent execution control plane**，统一调度代码 agent、Linux worker、Mac worker、Windows RPA worker。

**核心理念**: 安全地让 agent 干活，而不是让 agent 自己变聪明并长期自治。

---

## 🎯 新愿景（2026-03-31 调整）

### 定位

**一个受控的 agent execution control plane**

统一调度：
- 代码 agent（OpenHands/Codex）
- Linux worker
- Mac worker
- Windows RPA worker（影刀）

### 核心特征

- ✅ **有边界的 control plane**
- ✅ **隔离执行环境**（isolated workspace）
- ✅ **验证与 promotion gate**
- ✅ **受控自治**（不是自由生长）

### 为什么不是"超级智能体"？

基于 ARCHITECTURE.md 和 AEP v0 的现实定位：

- ❌ 当前不现实："无需人类干预 + 自我进化"
- ✅ 现实可行："受控自动化平台"

**缺少的能力**:
- 长周期目标保持与优先级竞争机制
- 多环境真实执行闭环（不只是 repo patch）
- 结果驱动的自动评估与经验沉淀
- 安全可控的自修改机制
- 预算、权限、故障、审计下的持续运行

**现有的能力**（非常有价值）:
- JobSpec
- driver adapter
- isolated workspace
- validation gate
- promotion gate
- Draft PR / patch artifact 输出

**结论**: 这些解决的是"怎么安全地让 agent 干活"，不是"怎么让 agent 自己变聪明"。

---

## 🚀 Roadmap（6 个 Phase）

### Phase 0: 停止追"自我进化" ✅
- 调整项目叙事
- 从"超级智能体"到"受控控制平面"

### Phase 1: 统一 worker 协议
- 新增 mac_worker, linux_worker, win_yingdao_worker
- 统一输入/输出接口

### Phase 2: 推广 task gate
- 从"patch gate"到"task gate"
- 支持异构任务类型

### Phase 3: 远程 worker
- 真正的远程 worker daemon
- Linux → Mac → Windows

### Phase 4: 人类在环审批
- 3 个关键审批点
- 高风险任务首次执行
- 外部系统写入
- 修改自身配置

### Phase 5: 有限自优化
- 允许: prompt, routing, 参数
- 禁止: gate rules, permissions, core code

### Phase 6: 连续自治
- 周期性目标
- 自动任务分解
- 成本预算
- 多 worker 协同

---

## 📊 成败标准

### 不用"会不会自我进化"判断

### 用这 5 个指标:

1. **可追踪性** - 任务从下达到完成是否可追踪
2. **可恢复性** - 任务失败后是否可恢复
3. **协同稳定性** - 多 worker 并行时是否不打架
4. **可审计性** - 涉及外部系统时是否可审计
5. **硬边界** - 修改系统自身时是否有硬边界

**如果这 5 个过了，项目就不是玩具了。**

---

## 💡 核心优势

### 已具备的硬骨架

- ✅ bounded control plane
- ✅ isolated execution
- ✅ validation gate
- ✅ promotion gate
- ✅ AEP driver model
- ✅ offline remote hardening 雏形

### 这些是做"多机、多执行器、可治理自治系统"的硬骨架。

---

## 🔗 详细规划

**完整愿景调整文档**: [VISION-ADJUSTMENT.md](./VISION-ADJUSTMENT.md)

**Roadmap**: 见 VISION-ADJUSTMENT.md 的 6 个 Phase

---

## 📖 为什么现在更容易上手

参考 ClawX 的使用体验，这个仓库把新手最常见的三个问题做了统一入口。

| 常见痛点 | 现在的做法 |
| --- | --- |
| 启动命令太多，不知道先跑哪个 | `make setup -> make doctor -> make start` |
| 报错信息分散，定位慢 | `scripts/doctor.py` 统一体检并给出下一步建议 |
| 文档和实际入口不一致 | README、Makefile、启动脚本使用同一套命令 |

---

## 3 分钟上手

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack
make setup
make doctor
make start
```

启动后可访问：

- `http://127.0.0.1:8001/health`
- `http://127.0.0.1:8001/docs`
- `http://127.0.0.1:8001/panel`

---

## 🎯 你可以拿它做什么

- 从 Telegram 触发仓库审查任务
- 生成带语言分布的审查报告
- 为外部仓库生成 prototype，并在 secure-fetch 后推进 promotion
- 扫描并执行本地技能
- 运行零信任加固脚本和相关验证脚本

---

## ⚠️ 重要说明

### OpenHands 接入边界

- "更容易上手"指 AAS 的统一启动和排错流程
- OpenHands 文档里的"切换简单"指其内部 SDK/workspace 抽象下的切换
- 本仓库采用分层接法：AAS 负责任务路由、状态、校验与 promotion；OpenHands 只负责隔离 workspace 内的代码执行

### 最窄链路

1. AAS 下发 task（受控输入契约）
2. OpenHands 在隔离 workspace 执行
3. 输出 promotion patch 与审计摘要（不直接污染主仓库）

---

**最后更新**: 2026-03-31 13:37
**愿景调整**: ✅ 完成
**标签**: #控制平面 #AI调度 #受控自治
