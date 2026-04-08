# Architecture

[English](ARCHITECTURE.md) | **简体中文**

本页是当前架构的中文导读，服务于中文入口和中文贡献协作。

权威、最完整、随实现演进同步维护的版本仍然是 [ARCHITECTURE.md](ARCHITECTURE.md)。如果两者出现不一致，请以英文版为准，并同步修正本页。

## 这个仓库现在是什么

`autonomous-agent-stack` 现在的主线已经不是“放任 Agent 直接改仓库”的实验集合，而是一套受控的自治执行控制面，用来完成以下事情：

- 发现并选择有边界的仓库改动机会
- 在隔离环境中执行改动
- 对补丁进行验证
- 在晋升门再次检查约束
- 最终产出补丁产物或草稿合并请求

核心意思很简单：Agent 可以提议和执行，但不能天然拥有仓库、分支图和发布权。

## 当前主路径

```text
规划器 -> Worker 合约 -> 隔离执行 -> 验证门 -> 晋升门 -> 补丁产物 / 草稿合并请求
```

当前稳定主线对应的系统组件是：

1. `AutoResearchPlannerService` 选择一个有边界的改动候选。
2. 它生成 `OpenHandsWorkerJobSpec`、`ControlledExecutionRequest` 和 AEP `JobSpec`。
3. `OpenHandsWorkerService` 把任务翻译成严格的补丁式执行合约。
4. `OpenHandsControlledBackendService` 或 `AgentExecutionRunner` 在隔离工作区中执行。
5. 验证命令和策略检查对结果进行收口。
6. `GitPromotionGateService` 重新检查 clean base、writer lease、approval、runtime artifact 和草稿合并请求前置条件。
7. 最终只会落到两种安全结果：
   - 人类可审阅的补丁产物
   - 通过晋升门后的草稿合并请求

## 核心约束

### 1. 脑手分离

- Planner 负责找下一件值得做的事
- Worker 只在隔离环境中产出补丁候选
- Promotion Gate 决定结果能否升级为补丁产物或草稿合并请求

OpenHands、Codex 和其他执行器在这里都是“手”，不是控制面本身。

### 2. 默认补丁式执行

默认模式下，自治执行只能产出 patch，不能直接接管 git 变更。

当前 worker prompt 明确禁止：

- `git add`
- `git commit`
- `git push`
- `git merge`
- `git rebase`
- `git reset`
- `git checkout`

### 3. 更严格规则优先

AEP 层采用 deny-wins 合并规则：

- `forbidden_paths` 取并集
- `allowed_paths` 取交集
- 网络权限取更严格者
- 工具白名单取交集
- 变更文件数、补丁行数、超时时间等限制取更小值

这保证了宽松请求不能覆盖更严格的默认安全边界。

### 4. 可变状态单写者

`WriterLeaseService` 是可变控制面操作的单写者锁。

它用于最容易发生并发危险的路径，例如：

- git 晋升收口
- managed skill promotion
- approval 相关的状态变更

拿不到 lease 时，系统应当阻断，而不是猜测。

### 5. 运行时产物不能晋升

运行时或控制面产物不能混入源码变更。

当前重点拒绝前缀包括：

- `logs/`
- `.masfactory_runtime/`
- `memory/`
- `.git/`

这个规则同时存在于 AEP patch filtering 和 git promotion gate。

### 6. 升级前必须满足干净基线

当前至少有两条路径会对 dirty repo 直接拒绝：

- `OpenHandsControlledBackendService` 下的 OpenHands CLI 执行
- `GitPromotionGateService` 下的草稿合并请求升级

这样做是为了避免把无关本地改动误判成 agent 输出。

## 物理与沙箱拓扑

当前实现把运行环境本身也视为架构的一部分，而不只是运维细节。

- 主机：MacBook Air M1
- 容器运行时：Colima / Docker
- 仓库路径：`/Volumes/AI_LAB/Github/autonomous-agent-stack`
- `ai-lab` 可写目录：
  - `/Volumes/AI_LAB/ai_lab/workspace`
  - `/Volumes/AI_LAB/ai_lab/logs`
  - `/Volumes/AI_LAB/ai_lab/.cache`

概念上的执行层次是：

```text
Mac 主机源码仓库
  -> Colima / Docker
    -> ai-lab 外置可写目录
      -> 隔离执行工作区
        -> 隔离晋升 worktree
```

## 关键代码入口

如果你准备从代码层面理解这条主路径，优先看这些文件：

- `src/autoresearch/core/services/autoresearch_planner.py`
- `src/autoresearch/core/services/openhands_worker.py`
- `src/autoresearch/core/services/openhands_controlled_backend.py`
- `src/autoresearch/executions/runner.py`
- `src/autoresearch/core/services/git_promotion_gate.py`
- `src/autoresearch/core/services/writer_lease.py`

## 延伸阅读

- [README.zh-CN.md](README.zh-CN.md)：中文首页入口
- [WHY_AAS.zh-CN.md](WHY_AAS.zh-CN.md)：为什么做这套系统
- [docs/rfc/README.zh-CN.md](docs/rfc/README.zh-CN.md)：RFC 索引与架构演进
- [ARCHITECTURE.md](ARCHITECTURE.md)：英文权威架构全文
