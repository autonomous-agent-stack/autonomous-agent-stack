# Project Health

[Simplified Chinese](project-health.zh-CN.md)

This document records the current release-health baseline for Autonomous Agent Stack. It is meant to replace guesswork from external reports with facts that can be verified inside this checkout.

## Current Baseline

- The project has maintained entry documentation: `README.md`, `docs/README.md`, `docs/architecture.md`, `WHY_AAS.md`, and `CONTRIBUTING.md`.
- The active product direction is an evergreen governed agent control plane, with `/api/v2/*` as the current development surface and `/api/v1/*` retained as compatibility shims.
- The repository has CI workflows for focused linting, tests, documentation checks, dependency audit, Windows startup, and reviewer quality gates.
- The local source tree includes focused regression tests under `tests/` and GA-specific checks under `tests/ga/`.
- The GA evidence files currently report `passed` with `missing_total: 0` in `ga_gap_report.md`.

## Release Health Boundaries

- Runtime state should live under `artifacts/`, logs, caches, or operator-configured paths, not under source packages.
- SQLite files, generated runtime databases, and local audit stores are runtime artifacts and should not be tracked as source.
- Public docs should use repo-relative paths or `AAS_*` environment variables instead of developer-machine absolute paths.
- Active public docs should remain language-separated: English canonical `.md` files and Simplified Chinese `.zh-CN.md` mirrors where maintained.
- The package metadata in `pyproject.toml` should match the README positioning: AAS is a governed control plane, not only a generic orchestration framework.

## Residual Risks

- Some historical reports remain outside `docs/archive/**`; they are useful records but should not override `docs/architecture.md`.
- Several AI Lab and operator scripts still contain machine-specific defaults by design. They should be handled in a separate operator-runtime cleanup, not mixed into the public release-health gate.
- Full repository-wide linting is not yet enforced; CI still uses focused paths for practical compatibility.
- Runtime health depends on local credentials and service configuration for live integrations, so release checks should distinguish missing credentials from missing implementation.

## Validation

Use these checks for release-health changes:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_check_pr_bilingual.py tests/test_repo_hygiene.py -q
PYTHONPATH=src .venv/bin/python -m pytest tests/ga/test_release_gate.py -q
git ls-files '*.sqlite' '*.sqlite3'
```
