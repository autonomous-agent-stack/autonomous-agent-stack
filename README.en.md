# Autonomous Agent Stack

An engineering repository for multi-agent orchestration, workflow triggering, self-integration verification, and zero-trust hardening.

## Runtime Requirements

- Python baseline: `3.11+`
- This repo verifies in CI: `3.11`, `3.12`
- If your local default `python3` is below 3.11, install 3.11+ before running `make setup`

## Why It's Easier to Get Started

Referencing the ClawX experience, this repository unifies the three most common beginner pain points into a single entry point.

| Common Pain Point | Current Approach |
| --- | --- |
| Too many startup commands, don't know which to run first | `make setup -> make doctor -> make start` |
| Scattered error messages, slow to diagnose | `scripts/doctor.py` unified health check with next-step suggestions |
| Documentation differs from actual entry points | README, Makefile, and startup scripts use the same command set |

## 3-Minute Quick Start

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack
# Ensure Python 3.11+ is being used
make setup
make doctor
make doctor-linux
make start
```

After startup, access:
- `http://127.0.0.1:8001/health`
- `http://127.0.0.1:8001/docs`
- `http://127.0.0.1:8001/panel`

To enable Telegram notifications and Mini App approvals, set at least these 4 environment variables:

```bash
AUTORESEARCH_TELEGRAM_BOT_TOKEN=...
AUTORESEARCH_TELEGRAM_ALLOWED_UIDS=YourTelegramUID
AUTORESEARCH_PANEL_JWT_SECRET=random-long-string
AUTORESEARCH_PANEL_BASE_URL=https://your-panel-domain/api/v1/panel/view
```

If you also want notification cards to include `Mini App` buttons, add:

```bash
AUTORESEARCH_TELEGRAM_MINI_APP_URL=https://your-panel-domain/api/v1/panel/view
```

If you want to mount upstream OpenClaw inspections as Planner's optional low-noise tasks, add these 3 variables:

```bash
AUTORESEARCH_UPSTREAM_WATCH_URL=https://github.com/openclaw/openclaw.git
AUTORESEARCH_UPSTREAM_WATCH_WORKSPACE_ROOT=/Volumes/AI_LAB/ai_lab/workspace
AUTORESEARCH_UPSTREAM_WATCH_MAX_COMMITS=5
```

Current code prioritizes `AUTORESEARCH_TELEGRAM_BOT_TOKEN`; the old variable `TELEGRAM_BOT_TOKEN` is still compatible but deprecated.

## Linux Remote Nodes

If you're preparing Linux as an "execution plane" for real OpenHands, the most stable first step is not to copy Mac/Colima, but to use `host` runtime directly.

Minimal path:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
make setup
OPENHANDS_RUNTIME=host make doctor-linux
OPENHANDS_RUNTIME=host make start
```

For more complete landing checklist, environment variable recommendations, and remote usage patterns:

- [Linux Remote Worker Guide](./docs/linux-remote-worker.md)
- [cc-switch Usage Guide](./docs/cc-switch-usage.md)
- [OpenHands Controlled Backend Integration](./docs/openhands-cli-integration.md)

## Common Commands

```bash
make help
make setup
make doctor
make doctor-linux
make start
make test-quick
make ai-lab
make ai-lab-check
make ai-lab-setup
make masfactory-flight
make masfactory-flight GOAL="Detect current M1 CPU core count"
make masfactory-flight GOAL="Detect current M1 CPU core count" WATCH=1
make openhands-dry-run
make openhands OH_TASK="Please scan /opt/workspace/src/autoresearch/core and fix TODOs with tests."
make openhands-controlled-dry-run
make openhands-controlled OH_TASK="Create src/demo_math.py with add(a,b), then run validation."
make openhands-demo OH_BACKEND=mock OH_TASK="Create src/demo_math.py with add(a,b)."
make agent-run AEP_AGENT=openhands AEP_TASK="Create src/demo_math.py with add(a,b)."
make hygiene-check
make review-gates-local
```

`make hygiene-check` writes results to `logs/audit/prompt_hygiene/report.txt` and `logs/audit/prompt_hygiene/report.json`.

`make openhands` calls `scripts/openhands_start.sh` (CLI direct mode), injecting `DIFF_ONLY=1` and `MAX_FILES_PER_STEP=3` execution constraints by default. For real boundaries, see [ARCHITECTURE.md](./ARCHITECTURE.md) as the master diagram and [memory/SOP/MASFactory_Strict_Execution_v1.md](./memory/SOP/MASFactory_Strict_Execution_v1.md) for the execution checklist.

The current launcher prioritizes reading root directory `ai_lab.env`. In `host` mode, it prioritizes finding standalone tool venvs like `./.masfactory_runtime/tools/openhands-cli-py312/bin/openhands`, automatically generating `agent_settings.json` in the local OpenHands home. `ai-lab` mode calls containerized `openhands` by default. The default template uses `--exp --headless` because locally verified `OpenHands CLI 1.5.0` can auto-terminate on this path, making it more suitable as a pipeline worker:

```bash
RUNTIME=process \
SANDBOX_VOLUMES=/your/workspace:/workspace:rw \
openhands --exp --headless -t "your task"
```

During actual execution, the launcher first `cd`s to the target worktree, then starts the CLI, so OpenHands workspace aligns with the current task directory. To switch back to the old "prompt as position argument" mode, explicitly set `OPENHANDS_HEADLESS=0`. To explicitly disable `--exp`, set `OPENHANDS_EXPERIMENTAL=0`. `OPENHANDS_JSON=1` only applies to CLI versions that explicitly support this flag. Current local verification with `OpenHands CLI 1.5.0` doesn't include it by default. For real `ai-lab` container chain, besides container `openhands` itself, the current shell needs access permissions to the configured Docker/Colima socket. `sandbox/ai-lab/Dockerfile` also locks to the same `OpenHands CLI 1.5.0` to avoid drift to unverified new versions on container cold start.

`launch_ai_lab.sh` also explicitly recognizes `DOCKER_HOST=unix://...` style Colima sockets. If current config points to a Colima socket inaccessible to the current user, it attempts safe fallback: with external disk Colima store, it uses repo's built-in `scripts/colima-external.sh`, otherwise falls back directly to the current user's own `~/.colima/<profile>/docker.sock` instead of directly relaxing host socket permissions. The current user fallback branch also explicitly mounts `/Volumes/AI_LAB` into Colima. If you don't want to touch the existing default profile, use an independent profile directly, e.g., `COLIMA_PROFILE=ai-lab bash ./scripts/launch_ai_lab.sh status`.

`make openhands-controlled` follows the narrowest closed loop: create isolated workspace, execute OpenHands subtasks, run validation, output promotion patch and audit summary (doesn't directly pollute main repo).

`make agent-run` uses AEP v0 unified execution kernel: `JobSpec -> driver adapter -> patch gate -> decision`. OpenHands/Codex/local scripts can all be plugged in as drivers.

`make review-gates-local` runs the reviewer core module's `mypy + bandit + semgrep` locally, consistent with CI's `Quality Gates` process.

## Local CLI Switch Tool Boundaries

Tools like `cc-switch` are suitable for local development workbenches to switch between `Codex`, `OpenClaw`, `Claude Code` CLIs for manual debugging and prompt testing.

But they shouldn't replace this repo's main execution chain. What's really responsible for controlled execution here is `make agent-run`, `make openhands-controlled`, AEP runner, validator, and promotion gate.

If you want to integrate `cc-switch` into daily workflow, recommend using it only as a bypass workbench, don't rewrite `drivers/openhands_adapter.sh` or `scripts/openhands_start.sh` main logic. For detailed boundaries, see [cc-switch Usage Guide](./docs/cc-switch-usage.md).

## PR Review & Gates

- OpenHands first-pass review (comment-only): `.github/workflows/pr-review-by-openhands.yml`
  - Trigger: Default `review-this` label; optional reviewer trigger via `OPENHANDS_REVIEWER_HANDLE`
  - Security policy: `pull_request` event, internal branch PRs only (skip forks), minimal permissions, fixed action/extension SHA
  - Merge policy: Not set as required status check in on-demand mode (advisory reviewer only)
- Quality gates: `.github/workflows/quality-gates.yml`
  - Checks: `mypy + bandit + semgrep` (tool versions locked in `requirements-review.lock`)
  - Includes `merge_group` trigger, compatible with merge queue
- Repo required checks recommendation: `CI / lint-test-audit` + `Quality Gates / reviewer-gates`
- Trial run and feedback loop: See [PR Review Hardening](./docs/pr-review-hardening.md) under `Trial Rubric` and `Feedback Loop`

For complete landing instructions: [PR Review Hardening](./docs/pr-review-hardening.md)

If port conflicts:

```bash
PORT=8010 make start
```

## What You Can Do With It

- Trigger repository review tasks from Telegram
- Generate review reports with language distribution
- Generate prototypes for external repositories and advance promotion after secure-fetch
- Scan and execute local skills
- Run zero-trust hardening scripts and related verification scripts

## OpenHands Integration Boundaries (Important)

- "Easier to get started" refers to AAS's unified startup and troubleshooting flow: `make setup -> make doctor -> make start`.
- OpenHands docs' "easy switching" refers to switching under its internal SDK/workspace abstraction, not cross-platform fusion.
- This repository uses layered integration: AAS handles task routing, state, validation, and promotion; OpenHands only handles code execution within isolated workspace.

Narrowest path:

1. AAS sends task (controlled input contract)
2. OpenHands executes in isolated workspace
3. AAS runs validation gate
4. AAS outputs promotion patch and decides promote/reject

See: [OpenHands Controlled Backend Integration](./docs/openhands-cli-integration.md)
Protocol doc: [Agent Execution Protocol (AEP v0)](./docs/agent-execution-protocol.md)
If evaluating the layered relationship between "heavyweight Claude Code workstation" and OpenHands, plus Claude Code CLI's handling of Excel / sales statistics / commission distribution for strong-rule business landing, refer to [Claude Code CLI Business Case: Sales Statistics & Commission Tables](./docs/claude-code-excel-business-case.md).

## Claude Code CLI Integration

`autonomous-agent-stack` doesn't embed Claude Code CLI into the Python process, but treats it as a callable repository executor.

Most common invocation pattern:

1. Outer loop receives, categorizes, selects repo
2. Write task brief in target repo directory
3. `cd` to target repo
4. Call `claude -p` directly
5. Let Claude Code CLI read that repo's `CLAUDE.md` and docs to execute modifications

Minimal command paradigm:

```bash
cd /path/to/target-repo
claude -p "Please read CLAUDE.md and relevant docs first, then complete this task brief: .... Finally, only output files changed / verification / manual follow-up."
```

For more complete writing, see [Task Brief / Bridge Documentation Guide](./docs/task-brief-guide.md).

If using Claude Code CLI for strong-rule business development, e.g., "sales statistics tables / commission distribution tables / various Excel processing and statistics", directly refer to [Claude Code CLI Business Case: Sales Statistics & Commission Tables](./docs/claude-code-excel-business-case.md).

If using `autonomous-agent-stack` as long-running outer loop, this integration's focus isn't "calling some internal API", but "keeping execution boundaries at repository directory and task brief".

## Key Entry Points

- [API Main Entry](./src/autoresearch/api/main.py)
- [Workflow Engine](./src/workflow/workflow_engine.py)
- [Telegram Gateway (mainline)](./src/autoresearch/api/routers/gateway_telegram.py)
- [Telegram Webhook (legacy compatibility only)](./src/gateway/telegram_webhook.py)
- [Self-Integration Service](./src/autoresearch/core/services/self_integration.py)
- [Self-Integration Router](./src/autoresearch/api/routers/integrations.py)
- [Skill Registry](./src/opensage/skill_registry.py)
- [MASFactory Skeleton](./src/masfactory/graph.py)
- [MASFactory First Flight Example](./examples/masfactory_first_flight.py)

## GitHub Professional Assistant Template

The repo root now comes with a local-first GitHub assistant template skeleton:

- `assistant.yaml`
- `repos.yaml`
- `profiles.yaml` (optional, enable for multi-profile)
- `prompts/`
- `policies/default-policy.yaml`
- `./assistant`

This capability is now integrated into the main app path:

- `GET /api/v1/github-assistant/health`
- `GET /api/v1/github-assistant/doctor`
- `GET /api/v1/github-assistant/profiles`
- `POST /api/v1/github-assistant/triage`
- `POST /api/v1/github-assistant/execute`
- `POST /api/v1/github-assistant/review-pr`
- `POST /api/v1/github-assistant/release-plan`
- `POST /api/v1/github-assistant/schedule/run`

Meaning it's no longer just a local script template. After starting the API, you can call directly from Swagger or other control planes.

Common commands:

```bash
./assistant doctor
./assistant profile list
./assistant profile init work --display-name "Work"
./assistant auth status --profile work
./assistant triage owner/repo 123
./assistant execute owner/repo 123
./assistant review-pr owner/repo 456
./assistant release-plan owner/repo --version v1.2.3
./assistant schedule run
```

The current template defaults to pre-filling with GitHub context detected on this machine:

- Bot account: `nxs9bg24js-tech`
- Current managed repo example: `srxly888-creator/autonomous-agent-stack`

Executor adapter layer has 4 built-in modes:

- `shell`
- `codex`
- `openhands`
- `custom`

Among them, `assistant.yaml` currently defaults to using `codex` adapter.

Runtime supports overriding key configuration via environment variables:

- `GH_ASSISTANT_GITHUB_LOGIN`
- `GH_ASSISTANT_WORKSPACE_ROOT`
- `GH_ASSISTANT_EXECUTOR_ADAPTER`
- `GH_ASSISTANT_EXECUTOR_BINARY`
- `GH_ASSISTANT_EXECUTOR`

Ops recommendations:

- First check if `GET /api/v1/github-assistant/health` is `ok`
- Then check `GET /api/v1/github-assistant/doctor` for item-by-item check results
- If local machine `gh auth` fails, health degrades, real GitHub operation interfaces explicitly return `503`, won't fake success

Related docs:

- [Quickstart](./docs/github-assistant-quickstart.md)
- [Migration Guide](./docs/github-assistant-migration.md)
- [Repo Onboarding](./docs/github-assistant-onboarding.md)
- [Safety Rules](./docs/github-assistant-safety.md)

## Quick Troubleshooting

1. First run `make doctor`, check if any `FAIL`
2. For Linux remote execution nodes, first run `OPENHANDS_RUNTIME=host make doctor-linux`
3. If prompted Python version too low, switch to Python 3.11+ first, then run `make setup`
4. If port issue, run `PORT=8010 make start`
5. If import issue, confirm startup via `make start` (script auto-sets `PYTHONPATH=src`)

## 🎯 Inspirations

This project is inspired by 6 excellent open-source libraries:

### 1. **MASFactory** - Multi-Agent Orchestration Framework
**GitHub**: https://github.com/BUPT-GAMMA/MASFactory
**Stars**: 125+
**Inspirations**:
- ✅ 4-node graph structure (Planner/Generator/Executor/Evaluator)
- ✅ M1 local execution sandbox
- ✅ MCP gateway integration
- ✅ Visual monitoring dashboard

---

### 2. **deer-flow** - Concurrent Orchestration & Sandbox Isolation
**GitHub**: https://github.com/nxs9bg24js-tech/deer-flow
**Stars**: 45,000+
**Inspirations**:
- ✅ Multi-agent concurrent orchestration (Lead Agent + Sub-agents)
- ✅ Sandbox isolated execution (three-tier defense: L1/L2/L3)
- ✅ Persistent long-term memory
- ✅ Markdown Skills

---

### 3. **OpenSage** - Self-Evolving Agent
**Paper**: arXiv:2602.16891
**Website**: https://www.opensage-agent.ai/
**Inspirations**:
- ✅ Self-programming agent (Level 3 - AI auto-creation)
- ✅ Self-generating Agent Topology
- ✅ Dynamic Tool and Skill Synthesis
- ✅ Hierarchical, Graph-based Memory

---

### 4. **OpenClaw** - Multi-Channel Access & Skill System
**GitHub**: https://github.com/openclaw/openclaw
**Stars**: 1,000+
**Inspirations**:
- ✅ Multi-channel access (Telegram, Discord, Signal)
- ✅ Skill system (SKILL.md)
- ✅ Session management
- ✅ Memory system (MEMORY.md)

---

### 5. **OpenSpace** - SOP Evolution Engine
**GitHub**: https://github.com/HKUDS/OpenSpace
**Version**: v0.1.0
**Inspirations**:
- ✅ Self-evolving skill engine (smarter with use)
- ✅ Markdown SOP evolution (safe, readable, accumulative)
- ✅ AUTO-LEARN mechanism (auto-learn new skills)
- ✅ Network effects (collective wisdom sharing)

---

### 6. **AutoResearch** - Karpathy Loop
**GitHub**: https://github.com/karpathy/autoresearch
**Stars**: 48,800+
**Author**: Andrej Karpathy (former Tesla AI Director)
**Inspirations**:
- ✅ **Autonomous Experiment Loop**
  ```
  propose → train → evaluate → commit/revert → repeat
  ```
- ✅ Parallel exploration strategy (multi-branch parallel)
- ✅ Result-oriented (keep improvements, rollback failures)
- ✅ Infinite iteration (autonomous optimization)

---

### Integration Value

| Open Source Library | Core Value | Applied to This Project |
|---------------------|------------|-------------------------|
| **MASFactory** | Multi-agent orchestration | 4-node graph structure + MCP gateway |
| **deer-flow** | Concurrent orchestration + sandbox | Lead Agent + Docker sandbox |
| **OpenSage** | Self-evolution mechanism | OpenSage module + dynamic tool synthesis |
| **OpenClaw** | Channel access | Telegram Webhook + skill system |
| **OpenSpace** | SOP evolution engine | Markdown skill library + AUTO-LEARN |
| **AutoResearch** | Karpathy loop | Propose-Train-Evaluate-Repeat |

---

**Value Proposition**: "Build a super-agent network that self-optimizes through multiple channels without human intervention"

---

## Deep Dive Documentation

- [Quick Start Guide](./docs/QUICK_START.md)
- [Architecture Overview](./ARCHITECTURE.md)
- [Admin View Field Guide](./docs/admin-view-field-guide.md)
- [Status & Release Notes](./STATUS_AND_RELEASE_NOTES.md)
- [Workflow Engine Verification Report](./docs/WORKFLOW_ENGINE_VERIFICATION_REPORT.md)
- [Self-Integration Protocol](./docs/p4-self-integration-protocol.md)
- [Zero-Trust Implementation Plan](./docs/zero-trust-implementation-plan-v2.md)
