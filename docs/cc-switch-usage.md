# cc-switch Usage Guide

这份说明只回答一个问题：

`cc-switch` 在这个仓库里该放哪，不该放哪。

## 一句话结论

`cc-switch` 适合放在本地开发工作台，不适合接管仓库的执行主链路。

更直接一点：

- 适合：给人用
- 不适合：给 AEP runner 当底盘

## 为什么

这个仓库的主价值已经不是“切换哪个 CLI 更方便”，而是把 agent 执行收进统一协议。

当前主链路已经包含这些关键环节：

1. `make agent-run` 进入 `scripts/agent_run.py`
2. 组装 `JobSpec`、`ValidatorSpec`、fallback 策略
3. 交给 `AgentExecutionRunner`
4. 在受控 workspace 中执行 adapter
5. 跑 validator
6. 生成 promotion patch
7. 决定 promote / reject / human_review

对 `openhands` 来说，这条链还进一步拆成：

- `configs/agents/openhands.yaml`
  定义 process adapter、默认 policy、allowed paths、patch/file 限额
- `drivers/openhands_adapter.sh`
  读取 AEP 环境变量，执行 OpenHands，并标准化为 `driver_result.json`
- `scripts/openhands_start.sh`
  负责 `host` / `ai-lab` runtime、workspace、settings、audit、启动参数

所以这里的核心诉求是：

- 可审计
- 可约束
- 可验证
- 可回放
- 可 promotion

这和“切换哪个 CLI/provider 更顺手”不是一层东西。

## 适合怎么用

推荐把 `cc-switch` 放在 Mac 控制面，作为开发者工作台。

典型用途：

- 手工切换 `Codex`、`OpenClaw`、`Claude Code` 等 CLI
- 做 prompt 试验
- 对比不同 provider 的回答或代码风格
- 人工复现某个 agent 行为
- 在正式进入 AEP 前先做低成本探索

这个定位下，`cc-switch` 是提效工具，不是执行协议的一部分。

## 不适合怎么用

不建议让 `cc-switch` 直接接管下面这些环节：

- `make agent-run`
- `make openhands-controlled`
- `AgentExecutionRunner`
- `drivers/openhands_adapter.sh`
- `scripts/openhands_start.sh`
- validation gate
- promotion gate
- Linux `OPENHANDS_RUNTIME=host` 执行链

原因很简单：

- 这些环节需要稳定的输入输出契约
- 需要固定的审计和 artifact 产出
- 需要可重复的 policy 约束
- 需要在失败时进入 fallback / human review

`cc-switch` 更像开发者侧的“入口切换器”，而不是执行侧的“受控协议层”。

## 推荐拓扑

最稳的做法是：

- Mac：控制面 + 工作台
- Linux：执行面

对应分工：

- Mac
  - Telegram
  - 审批
  - 面板
  - 本地 CLI 切换（`cc-switch`）
- Linux
  - OpenHands
  - pytest
  - patch 生成
  - promotion 前验证

这和当前仓库推荐的 Linux remote worker 方向是一致的。

## 推荐工作流

### 工作流 1：人工探索，再进入受控执行

1. 在 Mac 上用 `cc-switch` 选一个你要试的 CLI/provider
2. 手工验证 prompt、任务拆解、输出风格
3. 确认任务契约后，回到仓库主入口：

```bash
make agent-run AEP_AGENT=openhands AEP_TASK="Create apps/demo/lead_capture.py with tests."
```

### 工作流 2：Mac 调试，Linux 执行

1. Mac 上用 `cc-switch` 做人工调试
2. Linux 保持真实执行面：

```bash
OPENHANDS_RUNTIME=host make doctor-linux
OPENHANDS_RUNTIME=host make start
make agent-run AEP_AGENT=openhands AEP_TASK="Create apps/demo/lead_capture.py with tests."
```

### 工作流 3：只做旁路工具，不改主链

如果想给团队加一点便利，建议只加旁路入口，例如：

- `scripts/dev/with_cc_switch.sh`
- `make cli-shell`
- `make cli-check`

但这些入口应满足 4 条规则：

1. 给人用，不给 runner 用
2. 不参与 promotion
3. 不作为 CI 依赖
4. 不替换现有 adapter / launcher

## 风险提醒

如果把 `cc-switch` 误放到执行主链里，常见风险是：

- 执行输入输出不再稳定
- provider 切换把审计边界打散
- fallback 语义变模糊
- promotion 结果更难复现
- 线上故障时不容易定位是 runner 问题还是工作台问题

## 推荐边界

可以接，而且值得接。

但推荐边界很明确：

- `cc-switch` 负责开发者体验
- AEP / OpenHands controlled backend 负责受控执行

一句话说完：

`cc-switch` 可以做工作台，别做底盘。
