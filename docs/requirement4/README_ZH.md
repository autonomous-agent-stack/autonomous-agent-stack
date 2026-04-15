# requirement-4 中文文档导航

## 文档定位

这是一份给中文工程同事的 requirement-4 导航文档。

它的作用不是定义业务规则，而是告诉你：

- 当前 requirement-4 到底做到哪一步了
- 先看哪几份文档
- 新人应该按什么顺序开始
- 哪些事情在 2 天试运行范围内，哪些不在

---

## 一句话结论

当前 requirement-4 的仓库口径是：

- **2 天压缩试运行方案**
- **先手动触发，后考虑 schedule**
- **工程可执行，但不是 production complete**

不要把当前仓库理解成：

- 已经做完生产版 requirement-4
- 已经完成所有模块的 Windows 同等支持
- 已经因为有 schedule 就可以跳过人工审核

---

## 先看哪 3 份文档

如果你是第一次接 requirement-4，先看这 3 份：

1. [ACTION_PLAN_WHEN_ASSETS_ARRIVE_ZH.md](/Volumes/AI_LAB/Github/autonomous-agent-stack/docs/requirement4/ACTION_PLAN_WHEN_ASSETS_ARRIVE_ZH.md)
作用：
定义 2 天 pilot 的主口径、主范围、主验收标准。

2. [BRANCH_A_B_IMPLEMENTATION_BEST_PRACTICES_ZH.md](/Volumes/AI_LAB/Github/autonomous-agent-stack/docs/requirement4/BRANCH_A_B_IMPLEMENTATION_BEST_PRACTICES_ZH.md)
作用：
告诉你分支 A / 分支 B 具体怎么做，尤其是小白如何按 prompt 和命令一步步执行。

3. [../aas-claude-ecc-excel-best-practice-report.md](/Volumes/AI_LAB/Github/autonomous-agent-stack/docs/aas-claude-ecc-excel-best-practice-report.md)
作用：
解释为什么 requirement-4 必须走 deterministic + auditable 的路线，以及 Claude Code CLI + ECC 应该放在哪条链上。

---

## 当前主范围

2 天内只做：

- 业务资产 readiness review
- deterministic requirement-4 实现
- CLI 封装
- 单机版 AAS 基线验证
- Telegram 手动触发
- AAS 调 CLI 试运行
- 输出人工可审核材料

2 天内不做：

- 多模板支持
- 多规则版本并存
- 自动审批
- production schedule
- 大规模并发
- production complete 声明

---

## 两条分支怎么理解

### 分支 A：开发维护链

分支 A 负责：

- 看资产够不够
- 看契约硬不硬
- 做 deterministic 实现
- 做 fixture / golden 验证
- 把结果封装成 CLI

如果你是实现 requirement-4 业务逻辑的人，主要看分支 A。

### 分支 B：单机运行链

分支 B 负责：

- 单机版 AAS 安装与验证
- Telegram 接入与调试
- AAS 调起分支 A 的 CLI
- 做一次手动触发试运行

如果你是做接入、联调、运行闭环的人，主要看分支 B。

---

## 新手推荐起步顺序

推荐直接按这个顺序走：

1. 看 [ACTION_PLAN_WHEN_ASSETS_ARRIVE_ZH.md](/Volumes/AI_LAB/Github/autonomous-agent-stack/docs/requirement4/ACTION_PLAN_WHEN_ASSETS_ARRIVE_ZH.md)
2. 看 [BRANCH_A_B_IMPLEMENTATION_BEST_PRACTICES_ZH.md](/Volumes/AI_LAB/Github/autonomous-agent-stack/docs/requirement4/BRANCH_A_B_IMPLEMENTATION_BEST_PRACTICES_ZH.md)
3. 跑 `make setup`
4. 跑 `make doctor`
5. 确认 4 类业务资产已落盘
6. 先执行分支 A 的 Prompt A1
7. 只有在 `ready_for_pilot` 时，才继续 Prompt A2 / A3
8. CLI 本地跑通后，再交给分支 B 接 AAS + Telegram

---

## 如果你只负责分支 A

直接跳到：

- [BRANCH_A_B_IMPLEMENTATION_BEST_PRACTICES_ZH.md](/Volumes/AI_LAB/Github/autonomous-agent-stack/docs/requirement4/BRANCH_A_B_IMPLEMENTATION_BEST_PRACTICES_ZH.md)

重点看：

- `2.9 小白推荐执行顺序`
- `Prompt A1`
- `Prompt A2`
- `Prompt A3`
- `2.11 分支 A 执行时的最小命令清单`

---

## 如果你只负责分支 B

直接跳到：

- [BRANCH_A_B_IMPLEMENTATION_BEST_PRACTICES_ZH.md](/Volumes/AI_LAB/Github/autonomous-agent-stack/docs/requirement4/BRANCH_A_B_IMPLEMENTATION_BEST_PRACTICES_ZH.md)

重点看：

- `3. 分支 B 最佳实践：单机运行链`
- `4. 两分支之间的交接点`
- `5. 常见失败模式`
- `7. 检查清单`

---

## 当前边界要记住

当前仓库已经明确写出以下边界：

- requirement-4 仍然不是 production complete
- 原生 Windows 目前只覆盖最小主链，不代表全仓 parity
- requirement-4 虽然已有单机 schedule 主链，但仍不应跳过人工审核
- schedule 不在这次 2 天 pilot 的关键路径

---

## 补充文档

还可以按需看这些补充材料：

- [CONFIDENTIAL_ASSET_STORAGE_DECISION_ZH.md](/Volumes/AI_LAB/Github/autonomous-agent-stack/docs/requirement4/CONFIDENTIAL_ASSET_STORAGE_DECISION_ZH.md)
- [IMPLEMENTATION_READY_CHECKLIST.md](/Volumes/AI_LAB/Github/autonomous-agent-stack/docs/requirement4/IMPLEMENTATION_READY_CHECKLIST.md)
- [NEXT_STEP_ONCE_BUSINESS_ASSETS_ARRIVE.md](/Volumes/AI_LAB/Github/autonomous-agent-stack/docs/requirement4/NEXT_STEP_ONCE_BUSINESS_ASSETS_ARRIVE.md)
- [CLAUDE_CODE_BEST_PRACTICES_ZH.md](/Volumes/AI_LAB/Github/autonomous-agent-stack/docs/requirement4/CLAUDE_CODE_BEST_PRACTICES_ZH.md)

这些文档现在是补充说明，不是 requirement-4 的主口径真源。
