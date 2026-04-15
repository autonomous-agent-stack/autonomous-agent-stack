# Deterministic Job Best Practice: Claude Code CLI + ECC + AAS

> **Decision date:** 2026-04-07
> **Status:** Active
> **Applies to:** Requirement 4 (Excel / statistics / commission) and any deterministic computation scenario

---

## Core Principle

> **LLM owns understanding and code generation; deterministic programs own computation.**

Claude Code CLI develops and maintains fixed programs. ECC enforces engineering rigor. AAS governs runtime execution, validation, and audit.

---

## System Roles

### AAS — Governance Layer

AAS already provides the strongest foundation for deterministic jobs:

- Task protocol (`JobSpec` -> adapter -> validation -> promotion)
- Isolated workspace execution
- Allowed / forbidden paths
- Validation gate
- Artifact output
- Human review / approval
- Promotion / summary closure
- Audit log with run_id, timestamps, file hashes

### Claude Code CLI — Program Developer

Claude Code CLI is used **only during development**, not during production runtime:

- Write `sales_summary.py`, `commission_calc.py`, `anomaly_check.py`
- Write unit tests and regression tests
- Write field mappers
- Write rule configuration templates
- Maintain programs when rules change

It is NOT a "commission calculation engine" that reasons fresh on every upload.

### ECC — Engineering Reinforcement

Do NOT install the full ECC package. Cherry-pick only:

**Commands:**
- `/plan` — decompose business logic into modules
- `/tdd` — write tests first
- `/code-review` — catch edge cases, precision issues, null handling
- `/verify` — run sample data, compare expected results
- `/test-coverage` — enforce coverage

**Rules:**
- common coding style
- testing (80% minimum)
- security (no hardcoded paths/secrets)
- performance

**Skills (subset):**
- python-patterns
- python-testing
- verification-loop
- search-first
- cost-aware-llm-pipeline

---

## Anti-patterns

### Do NOT

| Anti-pattern | Why |
|---|---|
| Let Claude calculate final numbers at runtime | Non-deterministic, non-auditable |
| Install all 108 ECC skills | Noise, interference, cost |
| Put business rules in prompts | Rules drift, no version control |
| Guess column names without confirmation | Excel headers are inconsistent |
| Auto-issue final commission without human sign-off | Client trust, legal risk |
| Build a fancy UI before test coverage | Wrong priority |

### DO

| Practice | Why |
|---|---|
| One job type = one fixed entry point | Predictable, testable |
| Rules in versioned YAML files | Traceable, auditable |
| Field mapping = suggest then confirm | Prevent silent mismatches |
| Every run produces result + summary + audit log | Full traceability |
| Human review gate before final export | Trust and safety |
| Test suite before any UI | Correctness first |

---

## Business Layer Decomposition

### Layer 1: Input Standardization

Constrain input to known templates:

- Sales detail table
- Payment/receipt table
- Personnel mapping table
- Commission rule table

### Layer 2: Fixed Processing Programs

Modular, not monolithic:

```
jobs/
  excel_loader.py        # Parse and validate input
  column_mapper.py        # Map columns with confirmation
  sales_summary.py        # Aggregate sales data
  commission_calc.py      # Apply rules, compute commission
  anomaly_check.py        # Flag outliers and inconsistencies
  export_writer.py        # Generate output files
  run_sales_summary.py    # Entry point
  run_commission_calc.py  # Entry point
  run_reconciliation.py   # Entry point
```

### Layer 3: Rule Configuration

Rules change frequently. Keep them in files, not in prompts:

```
rules/
  commission/
    v1.yaml   # 2026-Q1 rules
    v2.yaml   # 2026-Q2 rules
    v3.yaml
```

Each rule file contains:

- Commission rates
- Region rules
- Channel rules
- Personnel mappings
- Anomaly thresholds
- Valid date range
- Change log

### Layer 4: Runtime Governance (AAS)

AAS manages the full lifecycle:

1. User uploads file(s)
2. AAS creates `JobSpec` with job type + input paths + rule version
3. AAS runs fixed program in isolated workspace
4. Validator checks output schema and sanity
5. Artifacts stored: result table + anomaly table + run summary
6. Human review gate
7. Confirmed export

---

## Required Output Per Run

Every execution must produce three artifacts:

### 1. Result Tables

- Summary table
- Commission table
- Anomaly table

### 2. Run Summary

- Rule version used
- Input files involved
- Field mappings applied
- Anomaly items flagged
- Program version / git sha

### 3. Audit Record

- `run_id`
- Timestamp
- Input file hash(es)
- Output file hash(es)
- Program version
- Rule version
- Operator who confirmed

---

## Development Workflow

### Phase 1: Build Programs (Claude Code CLI + ECC)

```
/plan          -> Decompose "sales summary / commission calc" into modules
/tdd           -> Write test data and expected outputs first
[write code]   -> Claude generates fixed programs
/code-review   -> Catch edge cases, precision, nulls, duplicates
/verify        -> Run sample data, compare expected results
/test-coverage -> Ensure 80%+ coverage
```

Goal: Freeze business logic into programs and rules, not prompts.

### Phase 2: Run Programs (AAS Only)

```
Upload -> JobSpec -> Select job type -> Run fixed program
       -> Validate -> Store artifacts -> Human review -> Export
```

Goal: Runtime does NOT depend on Claude's free-form reasoning.

---

## Docker / Deployment Guidance

### What runs in the container

- AAS API
- Fixed processing programs (`jobs/`)
- Rule files (`rules/`)
- Sample data for smoke tests
- Log / artifact directories

### What does NOT need to run in the container

- Claude Code CLI (used during development only)
- ECC tools (used during development only)

For client delivery: container runs fixed programs. Claude is a development tool, not a runtime dependency.

---

## Most Common Pitfalls

1. **Letting Claude become the calculation engine** — LLM output is non-deterministic. Never for financial computation.
2. **Full ECC install** — Too heavy. Cherry-pick.
3. **No rule versioning** — Commission rules will change. Without versions, chaos.
4. **No sample test dataset** — Client changes a rule, you have nothing to validate against.
5. **Mixing "anomaly explanation" with "result decision"** — LLM can explain anomalies; LLM must not decide outcomes.

---

## Six Rules (Condensed)

1. Claude Code CLI generates and maintains fixed programs; it does NOT compute results at runtime.
2. ECC is used selectively — commands/rules/skills — to make programs correct, tested, and reviewed.
3. AAS governs runtime: isolation, validation, audit, human review.
4. Commission formulas and statistical methods must be configurable and versioned.
5. Every run produces result tables + anomaly tables + summary + audit log.
6. Phase 1 always retains human confirmation; no auto-issuance of final figures.

---

## Task Type Mapping

For AAS integration, this maps to a new `WorkerTaskType`:

```python
DETERMINISTIC_JOB = "deterministic_job"
```

Payload structure:

```json
{
  "job_type": "commission_calc",
  "input_files": ["/workspace/uploads/sales_2026_q1.xlsx"],
  "rule_version": "v2",
  "output_dir": "/workspace/artifacts/run_xxx/",
  "metadata": {
    "session_key": "...",
    "actor_user_id": "..."
  }
}
```

This reuses the same worker queue + sticky session infrastructure from the 3-cut implementation.

---

## References

- 3-cut implementation: commit `af87f56` on `codex/openclaw-runtime-adapter-v1-impl`
- Worker queue design: `docs/decisions/mac-standby-worker-runtime-v1.md`
- Telegram ingress: `docs/decisions/telegram-youtube-autoflow-ingress-v1.md`
