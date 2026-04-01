# Worker Gap Analysis

Linux / Win / Fake worker 与 unified contract 的精确差距清单，
以及 acceptance → integration 的迁移计划。

---

## 1. Linux Worker 要补的字段和协议

### 当前生产代码

生产 `LinuxSupervisorService` 使用 `linux_supervisor_contract.py` 定义的状态枚举：

| 生产枚举 | 值 |
|----------|----|
| `LinuxSupervisorTaskStatus` | QUEUED / RUNNING / COMPLETED / FAILED (4个) |
| `LinuxSupervisorConclusion` | SUCCEEDED / STALLED_NO_PROGRESS / TIMED_OUT / MOCK_FALLBACK / ASSERTION_FAILED / INFRA_ERROR / UNKNOWN (7个) |

生产 `ControlPlaneService` 使用 `housekeeper_contract.py`：

| 生产枚举 | 值 |
|----------|----|
| `HousekeeperTaskStatus` | CREATED / CLARIFICATION_REQUIRED / APPROVAL_REQUIRED / QUEUED / RUNNING / COMPLETED / FAILED / REJECTED (8个) |
| `HousekeeperBackendKind` | MANAGER_AGENT / LINUX_SUPERVISOR / WIN_YINGDAO / OPENCLAW_RUNTIME (4个) |

### 缺少的 unified 字段

| 统一字段 | 生产对应 | 差距 |
|----------|---------|------|
| `TaskStatus.PENDING` | `CREATED` | 名称不同（bridge 已存在） |
| `TaskStatus.SUCCEEDED` | `COMPLETED` | 名称不同（bridge 已存在） |
| `TaskStatus.CANCELLED` | 无 | 生产无取消流程 |
| `TaskStatus.NEEDS_REVIEW` | `CLARIFICATION_REQUIRED` | 语义不同（bridge 映射了） |
| `RunStatus` 7 个值 | 无 | 生产无 RunRecord 概念 |
| `RunStatus.LEASED` | 无 | 生产无 lease 步骤 |
| `WorkerRegistration.allowed_actions` | 无 | 生产不跟踪 |
| `WorkerRegistration.metrics` | 无 | 生产不跟踪 |
| `WorkerRegistration.timeout_defaults` | 无 | 生产用硬编码阈值 |
| `WorkerRegistration.max_concurrent_tasks` | 无 | 生产不跟踪 |
| `WorkerRegistration.registered_at` | 无 | 生产不跟踪 |

### 要补的协议

1. **Run lifecycle protocol** — 生产 `LinuxSupervisorService` 直接从 QUEUED→RUNNING→COMPLETED/FAILED，没有 LEASED 状态。需要：
   - 在 `run_once()` 中加入 lease acquire/release 步骤
   - 将 `LinuxSupervisorTaskStatusRead` 映射到 `RunStatus`（QUEUED→LEASED→RUNNING→SUCCEEDED/FAILED）

2. **Heartbeat protocol** — 生产写 JSON 文件到磁盘（`heartbeat.json`、`supervisor_heartbeat.json`），但格式是 `LinuxSupervisorTaskHeartbeatRead`，不是 `WorkerHeartbeat`。需要：
   - 新增 heartbeat sender 将 `WorkerHeartbeat` 推送给 control plane
   - 或者让 `WorkerRegistryService` 读取时转换为 `WorkerHeartbeat`

3. **Gate protocol** — 生产没有 gate evaluation 步骤。任务完成后直接写 `summary.json`，不经过 `make_gate_verdict()`。需要：
   - 在 `_finalize_task()` 后调用 `make_gate_verdict()`
   - 将 verdict 写入 summary，用 action 驱动 retry/fallback/needs_review

4. **Worker registration protocol** — 生产 worker 是硬编码在 `WorkerRegistryService.list_workers()` 里的。需要：
   - 支持动态注册（`register()` / `unregister()`）
   - 将 `WorkerRegistrationRead` 扩展为 `WorkerRegistration`

5. **Metrics protocol** — 生产不采集 CPU/内存指标。需要：
   - 在 heartbeat 循环中采集 `psutil` 指标
   - 填充 `WorkerMetrics` 字段

---

## 2. Win Worker 要满足的契约

### 当前状态

`win_yingdao` worker 在 `WorkerRegistryService` 中硬编码为 `"implemented": False`，状态永远 `OFFLINE`。没有生产实现代码。

`FakeWinYingdaoWorker` 仅模拟了 4 种 outcome：success / form_not_found / network_error / needs_review。

### Run Lifecycle 契约

```
QUEUED → LEASED → RUNNING → SUCCEEDED | FAILED | NEEDS_REVIEW
```

Win worker 必须实现：
1. **接受 Task 派发** — 从 control plane 接收 `Task` 对象
2. **Lease acquire** — 确认接受任务，状态转 LEASED
3. **执行** — 调用 Yingdao RPA SDK / UI automation，状态转 RUNNING
4. **产出 RunRecord** — 包含 `run_id`、`task_id`、`worker_id`、timing、attempt
5. **状态回报** — 完成时汇报 SUCCEEDED / FAILED / NEEDS_REVIEW
6. **Gate 接受** — 让 gate 评估产出，接受 verdict

### Artifact 契约

| Artifact | 必须 | 说明 |
|----------|------|------|
| 执行日志 | 是 | 格式化的操作步骤记录 |
| 截图 | 条件 | form_fill / needs_review 时必须有截图 |
| 表单数据 | 条件 | 成功时返回填入的字段值 |
| Yingdao 响应 | 条件 | API/flow 执行的返回数据 |

Artifact 结构必须匹配 `TaskArtifact` 模型：
```python
class TaskArtifact(StrictModel):
    name: str
    path: str | None
    content_type: str
    size_bytes: int | None
    metadata: dict[str, Any]
```

### Heartbeat 契约

Win worker 必须以 `heartbeat_interval_sec`（默认 30s）频率发送 `WorkerHeartbeat`：

```python
class WorkerHeartbeat(StrictModel):
    worker_id: str
    status: WorkerStatus          # online / busy / degraded / offline
    metrics: WorkerMetrics        # cpu / memory / active_tasks / completed
    active_task_ids: list[str]
    errors: list[str]
    metadata: dict[str, Any]
```

必须满足：
- 执行任务时 status = BUSY
- 空闲时 status = ONLINE
- 网络异常时 status = DEGRADED（heartbeat 可送达但质量下降）
- 完全断连时 status = OFFLINE（由 control plane 通过 heartbeat timeout 推断）

### Worker Type 特有字段

```python
worker_type = WorkerType.WIN_YINGDAO
capabilities = ["yingdao_flow", "form_fill", "structured_data_entry", "erp_form_fill"]
allowed_actions = [EXECUTE_TASK, FILL_FORM, RUN_FLOW, CAPTURE_SCREENSHOT]
backend_kind = "win_yingdao"
max_concurrent_tasks = 1  # RPA 通常单线程
```

### 错误处理契约

必须覆盖至少 5 种 Yingdao 特有故障：

| 错误码 | retryable | gate outcome |
|--------|-----------|-------------|
| `FORM_NOT_FOUND` | True | TIMEOUT (元素定位失败) |
| `NETWORK_ERROR` | True | TIMEOUT |
| `PERMISSION_DENIED` | False | NEEDS_HUMAN_CONFIRM |
| `FLOW_STEP_FAILED` | True | TIMEOUT |
| `CONTRACT_ERROR` | False | NEEDS_HUMAN_CONFIRM |

---

## 3. Fake Worker vs Real Worker 差距清单

### FakeLinuxWorker vs 真实 LinuxSupervisorService

| 维度 | FakeLinuxWorker | 真实 LinuxSupervisorService |
|------|----------------|---------------------------|
| **执行方式** | 内存中返回固定 dict | `subprocess.Popen` 起子进程 |
| **返回类型** | `dict[str, Any]` (3 key) | `LinuxSupervisorTaskSummaryRead` (~20 field) |
| **文件系统** | 无 I/O | 创建目录、写 JSON (task/status/heartbeat/summary)、收集 stdout/stderr/artifact |
| **Heartbeat** | 返回本地对象，不发不存 | 定时写 `heartbeat.json` + `supervisor_heartbeat.json` |
| **Lease** | 无 | 无（需要补） |
| **Timeout** | 值存储但未使用 | `time.monotonic()` 跟踪，超时 SIGTERM→SIGKILL |
| **Stall 检测** | 无 | progress signature (file mtime/count 对比) |
| **AEP 集成** | 无 | 解析 `summary.json`、`events.ndjson`、`RunSummary` |
| **队列管理** | 无 | `enqueue_task()`、`run_once()`、`run_forever()`、orphan repair |
| **Artifacts** | `{"files_changed": 2}` | stdout.log, stderr.log, aep_summary.json, promotion.patch |
| **进程信息** | 无 | PID、return code、signal handling |
| **耗时** | 瞬时 (0s) | 真实 wall-clock `duration_seconds` |
| **Metrics** | 硬编码 (cpu=35/5) | 无采集（需要补） |
| **错误结构** | `{"code", "message", "retryable", "suggested_action"}` | `conclusion` enum + `message` string |
| **Gate** | 由 harness 外部调用 `make_gate_verdict()` | 不调用 gate（需要补） |

### FakeWinYingdaoWorker vs 真实 Win/Yingdao Worker

| 维度 | FakeWinYingdaoWorker | 真实 Win Worker (待建) |
|------|---------------------|---------------------|
| **存在** | 测试代码 | 不存在 (`"implemented": False`) |
| **执行方式** | 内存中返回固定 dict | 需调用 Yingdao RPA SDK / UI automation |
| **表单操作** | 返回 `{"forms_filled": 1}` | 需真实 DOM/API 交互 |
| **截图** | 返回假路径 `/tmp/partial.png` | 需真实截图写入 |
| **网络** | 硬编码 `network_error` | 需真实 HTTP/RPC 调用 |
| **Flow** | 返回 `{"flow_completed": True}` | 需真实 Yingdao flow 编排 |
| **Heartbeat** | 返回本地对象 | 需定时推送给 control plane |
| **Lease** | 无 | 需实现 |
| **Gate** | 无 | 需实现 |
| **Metrics** | 硬编码 (cpu=25/2, mem=1024) | 需真实系统指标 |

### Fake Worker 通用缺失

两个 fake worker 都缺少：

1. **错误恢复** — 无 retry 逻辑，无 fallback 切换
2. **资源限制** — 无 OOM / disk full / CPU throttle 检测
3. **并发控制** — `max_concurrent_tasks=1` 但未强制
4. **状态持久化** — 进程重启后所有状态丢失
5. **分布式协调** — 无 lease、无 heartbeat 接收端
6. **安全控制** — 无 scope check、无 allowed_actions 校验
7. **审计日志** — `_execution_log` 是内存 list，不持久化

---

## 4. Acceptance → Integration 迁移计划

### 当前状态

423+ tests 全部基于内存中的 Pydantic 模型，不涉及：
- 真实进程执行
- 文件系统 I/O
- 数据库读写 (SQLite)
- HTTP 调用
- 网络通信

### 迁移分类

#### A. 保持为 unit test（不需要迁移）

这些测试验证纯粹的逻辑规则，不依赖任何后端：

| 测试文件 | 内容 | 原因 |
|---------|------|------|
| `test_task_contract.py` | TaskStatus 枚举、legacy 映射 | 纯模型逻辑 |
| `test_run_contract.py` | RunStatus 枚举、transition table | 纯状态机 |
| `test_worker_contract.py` | WorkerType、WorkerStatus、映射 | 纯模型逻辑 |
| `test_task_gate_contract.py` | GateOutcome、GateAction 映射 | 纯决策逻辑 |
| `test_illegal_transitions.py` | 81+49 参数化非法转换 | 纯状态机验证 |
| `test_gate_scenarios.py` | 5 种 gate outcome 场景 | 纯决策验证 |
| `test_retry_fallback_review.py` | retry 耗尽 / fallback / review 规则 | 纯规则验证 |

这些 test ~240 个，验证契约不变量，保持现状。

#### B. 迁移为 integration test（需要真实后端）

| 当前测试 | 迁移目标 | 需要的真实组件 |
|---------|---------|--------------|
| `test_acceptance_harness.py` 的 30 连跑 | `tests/integration/test_acceptance_linux.py` | 真实 `LinuxSupervisorService` + SQLite + subprocess |
| `test_fake_workers.py::FakeLinuxWorker` 的 execute | `tests/integration/test_linux_execute.py` | 真实子进程执行、文件系统 I/O |
| `test_fake_workers.py::HeartbeatSimulation` | `tests/integration/test_heartbeat_file.py` | 真实 heartbeat.json 写入/读取 |
| `test_fake_workers.py::LeaseManager` | `tests/integration/test_lease_real.py` | 真实 WriterLeaseService 或分布式 lease |
| `test_acceptance_harness.py::TestAcceptancePerFaultType` | `tests/integration/test_fault_injection.py` | 真实 fault injection (kill -9, timeout, disk full) |
| `test_console.py` 的 approval 操作 | `tests/integration/test_approval_flow.py` | 真实 ApprovalStoreService + ControlPlaneService |
| `test_console.py` 的 task/worker 列表 | `tests/integration/test_task_worker_api.py` | 真实 WorkerRegistryService + SQLite |

#### C. 新增 integration test（当前没有覆盖）

| 测试 | 验证内容 | 优先级 |
|------|---------|--------|
| `test_control_plane_dispatch.py` | ControlPlaneService → LinuxSupervisorService 真实派发 | P0 |
| `test_linux_supervisor_lifecycle.py` | enqueue → run_once → summary 全流程 | P0 |
| `test_aep_runner_lifecycle.py` | AgentExecutionRunner.run_job() 全流程 | P0 |
| `test_heartbeat_timeout_detection.py` | heartbeat 断失 → worker 转 OFFLINE | P1 |
| `test_orphan_task_repair.py` | supervisor 重启后修复 RUNNING task | P1 |
| `test_gate_after_real_execution.py` | 真实执行后 gate evaluation | P1 |
| `test_win_yingdao_lifecycle.py` | Win worker 全流程（实现后） | P2 |
| `test_concurrent_dispatch.py` | 多 worker 并发派发 + lease 竞争 | P2 |
| `test_artifact_collection.py` | 真实 artifact 文件收集 | P2 |

#### D. 迁移时机

| 阶段 | 前置条件 | 动作 |
|------|---------|------|
| Phase 1 | LinuxSupervisorService 可本地启动 | 将 FakeLinuxWorker 的 9 个 execute test 改为调用真实 service |
| Phase 2 | unified contract 接入生产代码 | 将 acceptance harness 改为走 control plane → supervisor 真实路径 |
| Phase 3 | Win worker 实现 | 将 FakeWinYingdaoWorker 的 8 个 test 改为真实 worker |
| Phase 4 | 网络可用 | 将 HeartbeatSimulation / LeaseManager 改为网络 heartbeat + 分布式 lease |

### 关键风险

1. **双重模型维护** — 生产用 `housekeeper_contract` + `linux_supervisor_contract`，测试用 `task_contract` + `run_contract`。在 unified contract 接入生产之前，两套模型会持续分叉。
2. **Gate 不在生产路径** — `make_gate_verdict()` 只在测试和 harness 中被调用。真实执行完成后不会走 gate。
3. **RunStatus 不在生产路径** — `RunRecord.transition_to()` 只在测试中被调用。真实路径没有 run-level 状态机。
4. **Heartbeat 是文件轮询** — 不是推送协议。`WorkerRegistryService.list_workers()` 每次调用都读磁盘文件，不适合高频监控。

---

## 5. Linux Supervisor Bridge（已实现）

`src/autoresearch/shared/linux_supervisor_bridge.py` 提供 6 个纯函数，将
`LinuxSupervisor` 的生产输出形状映射到 unified contract 类型。
**不修改任何生产服务或 unified contract 模型。**

### 函数清单

| 函数 | 输入 | 输出 | 用途 |
|------|------|------|------|
| `supervisor_conclusion_to_gate_outcome()` | `LinuxSupervisorConclusion` | `GateOutcome` | 7 种 conclusion → 5 种 outcome |
| `supervisor_summary_to_gate_checks()` | `LinuxSupervisorTaskSummaryRead` | `list[GateCheck]` | 从 summary 提取 5 项 gate check |
| `supervisor_conclusion_to_run_status()` | `LinuxSupervisorConclusion` | `RunStatus` | 7 种 conclusion → 3 种 run status |
| `supervisor_summary_to_run_record()` | `LinuxSupervisorTaskSummaryRead` | `BridgeRunRecord` | summary → 带 timing/artifacts 的 run record |
| `supervisor_heartbeat_to_worker_heartbeat()` | `LinuxSupervisorProcessHeartbeatRead` + `LinuxSupervisorProcessStatusRead` | `WorkerHeartbeat` | 进程心跳 → 统一心跳 |
| `supervisor_heartbeat_to_worker_registration()` | 同上 | `WorkerRegistration` | 进程心跳 → worker 注册信息 |

### Gate Check 规则

| check_id | 通过条件 | 失败 severity |
|----------|---------|---------------|
| `aep_final_status` | `ready_for_promotion` 或 `promoted` | critical |
| `process_exit` | returncode ∈ {0, 2, None} | critical |
| `agent_completed` | conclusion == SUCCEEDED | critical |
| `no_mock_fallback` | `used_mock_fallback == False` | warning |
| `artifacts_present` | `bool(artifacts)` | warning |

### Conclusion 映射表

| LinuxSupervisorConclusion | GateOutcome | RunStatus | GateAction (default) |
|---------------------------|-------------|-----------|---------------------|
| SUCCEEDED | SUCCESS | SUCCEEDED | ACCEPT |
| TIMED_OUT | TIMEOUT | FAILED | RETRY |
| STALLED_NO_PROGRESS | TIMEOUT | FAILED | RETRY |
| MOCK_FALLBACK | MISSING_ARTIFACTS | FAILED | RETRY |
| ASSERTION_FAILED | OVERREACH | FAILED | REJECT |
| INFRA_ERROR | NEEDS_HUMAN_CONFIRM | FAILED | NEEDS_REVIEW |
| UNKNOWN | NEEDS_HUMAN_CONFIRM | NEEDS_REVIEW | NEEDS_REVIEW |

### Heartbeat 状态推导

使用与 `worker_registry.py` 一致的阈值：

- `process_status == "stopped"` → `OFFLINE`
- heartbeat age > 120s → `OFFLINE`
- `process_status == "running"` + fresh → `BUSY`
- `process_status == "idle"` + fresh → `ONLINE`

### 测试覆盖

43 个测试在 `tests/test_linux_supervisor_bridge.py`，7 个 test class：

1. `TestConclusionToGateOutcome` — 7 parametrized
2. `TestSummaryToGateChecks` — 6 tests (succeeded/failed/mock/empty artifacts/bad returncode/None returncode)
3. `TestConclusionToRunStatus` — 7 parametrized
4. `TestSummaryToRunRecord` — 4 tests (fields/error/unknown/result_data)
5. `TestHeartbeatConversion` — 6 tests (idle/running/stopped/stale/very_stale/metadata)
6. `TestHeartbeatToRegistration` — 4 tests (type/backend/capabilities/max_concurrent)
7. `TestFullChainEndToEnd` — 9 tests (all 7 conclusions + retry exhaustion + no fallback)

CI 路径已包含在 `.github/workflows/ci.yml` 的 `CORE_LINT_PATHS` 和 `CORE_TEST_PATHS` 中。
验收门已包含在 `docs/ACCEPTANCE_CRITERIA.md` 的 G6 gate 中（G6.1–G6.7）。

### 接入优先级建议

```
1. 将 make_gate_verdict() 接入 LinuxSupervisorService._finalize_task()
   → 让真实执行结果走 gate 决策

2. 将 RunRecord 接入 ControlPlaneService._execute()
   → 让 run 有真实的状态生命周期

3. 将 WorkerHeartbeat 接入 WorkerRegistryService
   → 统一 heartbeat 格式，替换硬编码阈值

4. 将 is_valid_transition() 接入 task status 变更点
   → 让非法转换在生产中抛异常而非静默通过

5. 动态 worker 注册
   → 替换硬编码的 list_workers()
```
