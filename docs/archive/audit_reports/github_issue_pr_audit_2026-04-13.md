# GitHub Issue / PR 核查报告
**生成时间（UTC）**: 2026-04-13T01:20:23Z
**仓库**: `autonomous-agent-stack/autonomous-agent-stack`（`gh repo view` 默认上游；本地 `origin` 可能指向 fork）
**数据来源**: `gh issue list` / `gh pr list` JSON，PR 富集字段含 `statusCheckRollup`、`reviews`、`reviewDecision`。
**原始导出**（与本报告同目录）:
- [gh_open_issues_2026-04-13.json](gh_open_issues_2026-04-13.json)
- [gh_open_prs_2026-04-13.json](gh_open_prs_2026-04-13.json)
- [gh_open_prs_enriched_2026-04-13.json](gh_open_prs_enriched_2026-04-13.json)

---

## 总览

- **Open issues**: 9
- **Open PRs**: 24（Draft: 8）

### 阻塞：与 base 冲突（需 rebase/解决冲突）

| PR | Base | Head | Draft | Mergeable | Merge state | CI 摘要 | Review |
|---|------|------|-------|-------------|-------------|---------|--------|
| [66](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/66) | `main` | `feat/worker-schedules` | 否 | CONFLICTING | DIRTY | —（无 rollup 或陈旧） | — |
| [65](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/65) | `main` | `feat/windows-main-chain` | 否 | CONFLICTING | DIRTY | —（无 rollup 或陈旧） | — |
| [62](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/62) | `main` | `feat/single-machine-aas-ready-for-req4` | 否 | CONFLICTING | DIRTY | —（无 rollup 或陈旧） | — |
| [47](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/47) | `main` | `codex/github-assistant-api-control-plane` | 否 | CONFLICTING | DIRTY | FAIL: lint-test-audit (3.11) (CI); lint-test-audit (3.12) (CI) | — |
| [45](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/45) | `main` | `fix/ruff-baseline-clean` | 否 | CONFLICTING | DIRTY | —（无 rollup 或陈旧） | — |
| [31](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/31) | `feat/agent-contract-and-routing-foundation` | `feat/minimal-repo-agent-docs-demo` | 否 | CONFLICTING | DIRTY | FAIL: lint-test-audit (3.11) (CI); lint-test-audit (3.12) (CI) | — |
| [30](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/30) | `feat/live-run-remediation` | `feat/minimal-standby-worker` | 否 | CONFLICTING | DIRTY | —（无 rollup 或陈旧） | — |
| [27](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/27) | `main` | `codex/consolidate-housekeeper-entrypoints` | 否 | CONFLICTING | DIRTY | FAIL: lint-test-audit (3.11) (CI); lint-test-audit (3.12) (CI) | — |
| [25](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/25) | `main` | `codex/personal-openclaw-housekeeper-v0` | 否 | CONFLICTING | DIRTY | FAIL: lint-test-audit (3.11) (CI); lint-test-audit (3.12) (CI) | — |
| [11](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/11) | `main` | `codex/worker-orchestration-e2e` | 否 | CONFLICTING | DIRTY | FAIL: lint-test-audit (3.11) (CI); lint-test-audit (3.11) (CI)… | — |

### 可合并但 CI 未绿（lint-test-audit 等失败或 UNSTABLE）

| PR | Base | Head | Draft | Mergeable | Merge state | CI 摘要 | Review |
|---|------|------|-------|-------------|-------------|---------|--------|
| [67](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/67) | `main` | `codex/windows-parity-minimal-baseline` | 否 | MERGEABLE | UNSTABLE | FAIL: lint-test-audit (3.11) (CI); lint-test-audit (3.11) (CI)… | — |
| [32](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/32) | `main` | `codex/pr29-routing-foundation-clean` | 否 | MERGEABLE | UNSTABLE | FAIL: lint-test-audit (3.11) (CI); lint-test-audit (3.12) (CI) | — |
| [29](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/29) | `main` | `feat/agent-contract-and-routing-foundation` | 否 | MERGEABLE | UNSTABLE | FAIL: lint-test-audit (3.11) (CI); lint-test-audit (3.12) (CI) | — |
| [19](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/19) | `codex/docs-cc-switch-workstation` | `codex/housekeeper-video-agent-rfc` | 否 | MERGEABLE | UNSTABLE | FAIL: lint-test-audit (3.11) (CI); lint-test-audit (3.11) (CI)… | — |
| [15](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/15) | `main` | `fix/issue-12-malu-landing-page` | 否 | MERGEABLE | UNSTABLE | FAIL: lint-test-audit (3.11) (CI); lint-test-audit (3.11) (CI)… | — |
| [7](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/7) | `codex/openhands-controlled-backend` | `codex/pr-review-hardening` | 否 | MERGEABLE | UNSTABLE | FAIL: lint-test-audit (3.10) (CI); lint-test-audit (3.10) (CI)… | — |

### Draft（不宜合并）

| PR | Base | Head | Draft | Mergeable | Merge state | CI 摘要 | Review |
|---|------|------|-------|-------------|-------------|---------|--------|
| [36](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/36) | `main` | `codex/youtube-subtitle-summary-agent` | 是 | CONFLICTING | DIRTY | FAIL: lint-test-audit (3.11) (CI); lint-test-audit (3.12) (CI) | — |
| [24](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/24) | `main` | `feat/housekeeper-media-rfc-main` | 是 | CONFLICTING | DIRTY | FAIL: lint-test-audit (3.11) (CI); lint-test-audit (3.12) (CI) | — |
| [23](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/23) | `main` | `codex/ci-lint-debt-cleanup` | 是 | CONFLICTING | DIRTY | FAIL: lint-test-audit (3.11) (CI); lint-test-audit (3.11) (CI)… | — |
| [22](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/22) | `main` | `codex/housekeeper-media-mainline` | 是 | CONFLICTING | DIRTY | FAIL: lint-test-audit (3.11) (CI); lint-test-audit (3.12) (CI) | — |
| [21](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/21) | `main` | `feat/stable-remote-exec` | 是 | CONFLICTING | DIRTY | FAIL: lint-test-audit (3.11) (CI); lint-test-audit (3.12) (CI) | — |
| [17](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/17) | `main` | `codex/pr3-promotion-state-consistency` | 是 | CONFLICTING | DIRTY | FAIL: lint-test-audit (3.11) (CI); lint-test-audit (3.12) (CI) | — |
| [16](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/16) | `main` | `codex/auto-upgrade/you-are-openhands-operating-as-a-constra-20260330T062728Z` | 是 | MERGEABLE | UNSTABLE | FAIL: lint-test-audit (3.11) (CI); lint-test-audit (3.11) (CI)… | — |
| [10](https://github.com/autonomous-agent-stack/autonomous-agent-stack/pull/10) | `main` | `codex/auto-upgrade/admin-health-20260328172500` | 是 | MERGEABLE | UNSTABLE | FAIL: lint-test-audit (3.11) (CI); lint-test-audit (3.11) (CI)… | — |

---

## Open Issues 清单

| # | 更新 | 标题 |
|---|------|------|
| [68](https://github.com/autonomous-agent-stack/autonomous-agent-stack/issues/68) | 2026-04-12 | Backport shared WhatsApp / channel orchestration primitives from downstream enterprise fork |
| [63](https://github.com/autonomous-agent-stack/autonomous-agent-stack/issues/63) | 2026-04-09 | 字段逐项填写指南：docs/admin-view-field-guide.md 没用带链接 |
| [41](https://github.com/autonomous-agent-stack/autonomous-agent-stack/issues/41) | 2026-04-05 | Track OpenClaw as a separate runtime adapter lane |
| [38](https://github.com/autonomous-agent-stack/autonomous-agent-stack/issues/38) | 2026-04-05 | Investigate Codex full-auto bwrap compatibility on current Linux host |
| [35](https://github.com/autonomous-agent-stack/autonomous-agent-stack/issues/35) | 2026-04-04 | follow-up: make subtitle track selection deterministic |
| [34](https://github.com/autonomous-agent-stack/autonomous-agent-stack/issues/34) | 2026-04-04 | follow-up: document /api/v1/subtitle/offline as trusted dev-only endpoint |
| [28](https://github.com/autonomous-agent-stack/autonomous-agent-stack/issues/28) | 2026-03-31 | Deprecate legacy housekeeper schema aliases |
| [26](https://github.com/autonomous-agent-stack/autonomous-agent-stack/issues/26) | 2026-03-31 | Consolidate parallel housekeeper implementations |
| [12](https://github.com/autonomous-agent-stack/autonomous-agent-stack/issues/12) | 2026-03-30 | Chaos Run: 玛露遮瑕膏落地页商业化压力测试 |

---

## Issue 跟进建议（模板）

- 核对标题/描述是否仍有效；是否与其它 Issue 重复。
- 补 **labels** / **assignee**，避免长期无标签堆积。

---

## PR 下一步（可执行）

1. **冲突桶**：对 `main`（或目标 base）rebase，解决冲突后再跑 CI。
2. **CI 红桶**：打开 Actions 中 `lint-test-audit` 失败日志，修 ruff/black/pytest 后 push。
3. **Draft**：确认范围后 mark ready 或关闭过时 PR。

---

## 完成标准（计划核对）

- [x] Open issues + open PRs 清单含链接
- [x] 每个 open PR 标注 Draft、合并阻塞类型、CI rollup 摘要
- [x] 给出可执行下一步（rebase / 修 CI / 关闭或 ready）
