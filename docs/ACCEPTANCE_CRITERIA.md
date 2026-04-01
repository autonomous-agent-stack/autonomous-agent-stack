# Acceptance Criteria

This document defines **binding, machine-verifiable** gates that must pass
before any PR can merge and before the stack can be called "demo-ready".

---

## 1. Acceptance 门槛 (Must-Pass Gates)

### G1. Contract 模型完整性

| # | 条件 | 验证方式 |
|---|------|----------|
| G1.1 | `TaskStatus` 9 个枚举值全部可用 | `pytest tests/test_task_contract.py::TestTaskStatus` |
| G1.2 | `RunStatus` 7 个枚举值全部可用 | `pytest tests/test_run_contract.py::TestRunStatus` |
| G1.3 | `GateOutcome` 5 个枚举值全部可用 | `pytest tests/test_task_gate_contract.py` |
| G1.4 | `WorkerType` 4 个枚举值全部可用 | `pytest tests/test_worker_contract.py` |
| G1.5 | 所有 legacy 双向映射 roundtrip 正确 (JobStatus↔TaskStatus, HousekeeperTaskStatus↔TaskStatus, WorkerAvailabilityStatus↔WorkerStatus) | `pytest tests/test_task_contract.py::TestLegacyMapping tests/test_task_contract.py::TestHousekeeperTaskStatusMapping tests/test_worker_contract.py` |

### G2. 状态机合法性

| # | 条件 | 验证方式 |
|---|------|----------|
| G2.1 | `TaskStatus` 非法转换矩阵: 每个 `(current, target)` 不在合法表中的对, `is_valid_transition()` 必须返回 `False` | `pytest tests/test_illegal_transitions.py::TestTaskStatusIllegalTransitions` (81 个参数组合) |
| G2.2 | `RunStatus` 非法转换矩阵: 同上 | `pytest tests/test_illegal_transitions.py::TestRunStatusIllegalTransitions` (49 个参数组合) |
| G2.3 | 终态不可自转: `succeeded`, `rejected`, `cancelled` 对任意 target 返回 `False` | 包含在 G2.1 |
| G2.4 | `RunRecord.transition_to()` 对非法转换抛 `ValueError` | `pytest tests/test_illegal_transitions.py::TestRunRecordTransitionErrors` (12 个 case) |
| G2.5 | 无自转: 任何 `is_valid_transition(X, X)` 返回 `False` | 包含在 G2.1/G2.2 |

### G3. Gate 判决正确性

| # | 条件 | 验证方式 |
|---|------|----------|
| G3.1 | SUCCESS → ACCEPT | `pytest tests/test_gate_scenarios.py::TestGateSuccessScenario` |
| G3.2 | TIMEOUT → RETRY (未耗尽时) | `pytest tests/test_gate_scenarios.py::TestGateTimeoutScenario` |
| G3.3 | OVERREACH → REJECT | `pytest tests/test_gate_scenarios.py::TestGateOverreachScenario` |
| G3.4 | MISSING_ARTIFACTS → RETRY | `pytest tests/test_gate_scenarios.py::TestGateMissingArtifactsScenario` |
| G3.5 | NEEDS_HUMAN_CONFIRM → NEEDS_REVIEW | `pytest tests/test_gate_scenarios.py::TestGateHumanConfirmScenario` |
| G3.6 | Retry 耗尽 + 有 fallback_agent → FALLBACK | `pytest tests/test_retry_fallback_review.py::TestRetryRules::test_retry_exhaustion_upgrades_to_fallback` |
| G3.7 | Retry 耗尽 + 无 fallback_agent → NEEDS_REVIEW | `pytest tests/test_retry_fallback_review.py::TestRetryRules::test_retry_exhaustion_no_fallback_needs_review` |
| G3.8 | max_retries=0 直接走 FALLBACK/NEEDS_REVIEW | `pytest tests/test_retry_fallback_review.py::TestRetryBoundaryConditions` |

### G4. 连跑验收

| # | 条件 | 验证方式 |
|---|------|----------|
| G4.1 | 30 次连跑 100% 通过, 5 类故障 + success 全覆盖 | `python scripts/acceptance_run.py --runs 30 && echo $?` → exit 0 |
| G4.2 | 每次运行必须完成 8 个 lifecycle step | `pytest tests/test_acceptance_harness.py::TestAcceptanceSuite::test_all_lifecycle_steps_complete` |
| G4.3 | 6 种 fault type 全部出现 | `pytest tests/test_acceptance_harness.py::TestAcceptanceSuite::test_all_fault_types_covered` |

### G5. API 可用性

| # | 条件 | 验证方式 |
|---|------|----------|
| G5.1 | Console landing page 返回 200 含 "Control Plane Console" | `pytest tests/test_console.py::TestLandingPage` |
| G5.2 | 任务列表 + 状态过滤 | `pytest tests/test_console.py::TestTaskList` |
| G5.3 | Worker 列表 + heartbeat/metrics | `pytest tests/test_console.py::TestWorkerList` |
| G5.4 | Run detail + logs/artifacts/gate verdict | `pytest tests/test_console.py::TestRunDetail` |
| G5.5 | Approval approve/reject/retry/fallback 操作 | `pytest tests/test_console.py::TestApprovalActions` |

### G6. Bridge Coverage (Linux Supervisor → Unified Contracts)

| # | 条件 | 验证方式 |
|---|------|----------|
| G6.1 | All 7 LinuxSupervisorConclusion values map to correct GateOutcome | `pytest tests/test_linux_supervisor_bridge.py::TestConclusionToGateOutcome` |
| G6.2 | Summary produces valid GateChecks for succeeded/failed/mock scenarios | `pytest tests/test_linux_supervisor_bridge.py::TestSummaryToGateChecks` |
| G6.3 | All 7 conclusions map to correct RunStatus | `pytest tests/test_linux_supervisor_bridge.py::TestConclusionToRunStatus` |
| G6.4 | Summary → RunRecord conversion preserves all fields | `pytest tests/test_linux_supervisor_bridge.py::TestSummaryToRunRecord` |
| G6.5 | Heartbeat → WorkerHeartbeat for idle/running/stopped/offline | `pytest tests/test_linux_supervisor_bridge.py::TestHeartbeatConversion` |
| G6.6 | Heartbeat → WorkerRegistration produces LINUX type | `pytest tests/test_linux_supervisor_bridge.py::TestHeartbeatToRegistration` |
| G6.7 | Full chain: summary → gate_outcome → gate_checks → make_gate_verdict → verdict for all 7 conclusions | `pytest tests/test_linux_supervisor_bridge.py::TestFullChainEndToEnd` |

---

## 2. Fail-Fast 条件

以下任一条件为真时, **立即中断** 流水线, 不继续后续步骤:

### F1. Lint/Format

| # | 条件 | 触发 |
|---|------|------|
| F1.1 | `ruff check` 返回非零 | **FAIL FAST** — 不跑测试 |
| F1.2 | `black --check` 返回非零 | **FAIL FAST** — 不跑测试 |

### F2. 导入完整性

| # | 条件 | 触发 |
|---|------|------|
| F2.1 | `from autoresearch.shared.task_contract import Task, TaskStatus, is_valid_transition` 失败 | **FAIL FAST** — 合约不可导入 |
| F2.2 | `from autoresearch.shared.run_contract import RunRecord, RunStatus` 失败 | **FAIL FAST** |
| F2.3 | `from autoresearch.shared.task_gate_contract import GateVerdict, make_gate_verdict` 失败 | **FAIL FAST** |
| F2.4 | `from autoresearch.shared.worker_contract import WorkerRegistration, WorkerStatus` 失败 | **FAIL FAST** |
| F2.5 | `from autoresearch.testing.fake_workers import FakeLinuxWorker, FailureCategory, FAILURE_TAXONOMY` 失败 | **FAIL FAST** |

### F3. 状态机不变量

| # | 条件 | 触发 |
|---|------|------|
| F3.1 | 终态自转不抛异常 | `RunRecord(status=RunStatus.SUCCEEDED).transition_to(RunStatus.RUNNING)` 必须抛 `ValueError`, 否则 **FAIL FAST** |
| F3.2 | `is_valid_transition(TaskStatus.SUCCEEDED, TaskStatus.RUNNING)` 返回 `True` | **FAIL FAST** — 终态不应允许转换 |
| F3.3 | `is_valid_transition(TaskStatus.FAILED, TaskStatus.PENDING)` 返回 `True` | **FAIL FAST** — 不允许回退到 PENDING |

### F4. Gate 核心规则

| # | 条件 | 触发 |
|---|------|------|
| F4.1 | `make_gate_verdict(GateOutcome.SUCCESS).action != GateAction.ACCEPT` | **FAIL FAST** — success 必须映射到 accept |
| F4.2 | `make_gate_verdict(GateOutcome.OVERREACH).action != GateAction.REJECT` | **FAIL FAST** — overreach 必须映射到 reject |
| F4.3 | `make_gate_verdict(GateOutcome.TIMEOUT, retry_attempt=3, max_retries=3, fallback_agent_id="fb").action != GateAction.FALLBACK` | **FAIL FAST** — 耗尽必须升级 |

### F5. Acceptance Harness

| # | 条件 | 触发 |
|---|------|------|
| F5.1 | `scripts/acceptance_run.py --runs 30` exit code ≠ 0 | **FAIL FAST** — 验收不通过 |
| F5.2 | 任一 fault type 0% pass rate | **FAIL FAST** — 某类故障完全无法处理 |

---

## 3. PR Merge Checklist

以下每一项 **必须 ✓** 才允许 merge:

### 代码质量

- [ ] `ruff check` 在 `CORE_LINT_PATHS` 上零错误
- [ ] `black --check` 在 `CORE_LINT_PATHS` 上零错误
- [ ] 无新引入的 `# type: ignore` 或 `# noqa` 除非有注释说明原因
- [ ] `pip-audit` 零新增高危 CVE (已 suppress 的不算)

### 测试

- [ ] `pytest -q ${CORE_TEST_PATHS}` 零失败
- [ ] 423+ tests 全部 pass (不减少)
- [ ] 新增代码有对应测试文件
- [ ] `scripts/acceptance_run.py --runs 30` exit 0

### 合约

- [ ] 新增 TaskStatus/RunStatus 枚举值时, 必须同时更新 `_VALID_TRANSITIONS` / `_RUN_TRANSITIONS` 和对应映射
- [ ] 新增 GateOutcome 时, 必须同时更新 `_DEFAULT_OUTCOME_ACTION` 和 `make_gate_verdict()`
- [ ] 新增 WorkerType 时, 必须同时更新 legacy 映射和 worker_registry
- [ ] 修改状态转换表时, 必须同步更新 `tests/test_illegal_transitions.py`

### 文档

- [ ] API schema 变更同步到 `docs/offline-demo.md`
- [ ] 新增 endpoint 同步到 `docs/offline-demo.md` endpoint 表
- [ ] 状态机变更同步到 lifecycle diagram

### 架构

- [ ] 未引入第二套编排系统 (只有 control plane)
- [ ] Housekeeper 未直接执行业务逻辑 (走 control plane dispatch)
- [ ] 高风险操作未绕过 approval gate
- [ ] 无模糊路由 (无 package 匹配时返回 clarification_required)

---

## 4. Demo-Ready 最小标准

以下条件全部满足时, 可宣布 "demo-ready":

### DR1. 离线演示可运行

| # | 标准 | 验证命令 |
|---|------|----------|
| DR1.1 | `scripts/demo_offline.py` 5 个场景全部 PASS, exit 0 | `PYTHONPATH=src python scripts/demo_offline.py` |
| DR1.2 | `scripts/acceptance_run.py --runs 30` 100% pass rate | `PYTHONPATH=src python scripts/acceptance_run.py --runs 30` |
| DR1.3 | 无需网络、无需 Docker、无需 API key 即可运行上述两个脚本 | 断网测试 |

### DR2. Console 可交互

| # | 标准 | 验证方式 |
|---|------|----------|
| DR2.1 | `uvicorn autoresearch.api.app:app` 启动无错 | `PYTHONPATH=src uvicorn autoresearch.api.app:app --port 8000` |
| DR2.2 | 浏览器访问 `http://localhost:8000/api/v1/console/` 可见 landing page | 手动 or `curl` |
| DR2.3 | 任务列表可按状态过滤 | 点击 status 按钮 |
| DR2.4 | Worker 列表显示 status/capability/heartbeat age | 页面可见 |
| DR2.5 | 输入 run-001 可查看 run detail (logs + artifacts + gate verdict) | 页面交互 |
| DR2.6 | Approval 页面可 approve/reject, 状态实时变化 | 页面交互 |

### DR3. 合约模型正确

| # | 标准 | 验证命令 |
|---|------|----------|
| DR3.1 | `pytest tests/test_task_contract.py tests/test_worker_contract.py tests/test_run_contract.py tests/test_task_gate_contract.py` 全绿 | pytest |
| DR3.2 | `pytest tests/test_illegal_transitions.py tests/test_gate_scenarios.py tests/test_retry_fallback_review.py` 全绿 | pytest |
| DR3.3 | `pytest tests/test_fake_workers.py tests/test_acceptance_harness.py` 全绿 | pytest |

### DR4. CI 绿

| # | 标准 | 验证方式 |
|---|------|----------|
| DR4.1 | GitHub Actions CI `lint-test-audit` job 在 Python 3.11 + 3.12 matrix 全绿 | `gh run list --limit 1` |
| DR4.2 | `pip-audit` 步骤通过 (已知 suppress 不算) | CI log |

### DR5. 文档完整

| # | 标准 |
|---|------|
| DR5.1 | `docs/offline-demo.md` 包含 quick start, endpoint 表, fault injection 表, 决策逻辑说明 |
| DR5.2 | 本文件 (`docs/ACCEPTANCE_CRITERIA.md`) 存在且与实际验证命令一致 |
| DR5.3 | `CLAUDE.md` hard rules 与本文件不冲突 |

---

## 快速验证命令

```bash
# 一次性验证所有 demo-ready 标准
set -e
echo "=== DR1: Offline demos ==="
PYTHONPATH=src python scripts/demo_offline.py
PYTHONPATH=src python scripts/acceptance_run.py --runs 30

echo "=== DR3: Contract tests ==="
PYTHONPATH=src pytest tests/test_task_contract.py \
  tests/test_worker_contract.py \
  tests/test_run_contract.py \
  tests/test_task_gate_contract.py \
  tests/test_illegal_transitions.py \
  tests/test_gate_scenarios.py \
  tests/test_retry_fallback_review.py \
  tests/test_fake_workers.py \
  tests/test_acceptance_harness.py \
  tests/test_console.py \
  -q

echo "=== DR4: Lint ==="
ruff check src/autoresearch/shared/ src/autoresearch/testing/ src/autoresearch/api/routers/console.py
black --check src/autoresearch/shared/ src/autoresearch/testing/ src/autoresearch/api/routers/console.py

echo "=== ALL DEMO-READY CHECKS PASSED ==="
```
