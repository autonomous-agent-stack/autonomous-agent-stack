# Contributing

[Simplified Chinese](CONTRIBUTING.zh-CN.md)

Thanks for contributing to Autonomous Agent Stack (AAS). The project is a governed control plane for long-running agents, so contribution quality is measured by correctness, safety, auditability, and clear documentation.

## Before You Start

Read these first:

- [README](README.md)
- [Architecture](docs/architecture.md)
- [Why AAS](WHY_AAS.md)
- [Documentation index](docs/README.md)

For architecture or governance changes, open or update an RFC under `docs/rfc/` before implementing a large design.

## Local Setup

```bash
git clone https://github.com/autonomous-agent-stack/autonomous-agent-stack.git
cd autonomous-agent-stack

make setup
make doctor
make test-quick
```

Optional checks:

```bash
make hygiene-check
make review-gates-local
make evergreen-demo
```

## Contribution Types

- Documentation fixes and examples.
- Focused bug fixes with regression tests.
- Runtime adapter improvements that preserve control-plane boundaries.
- Policy, approval, audit, and promotion hardening.
- RFCs for broader architecture changes.

Avoid broad refactors mixed with feature work. Keep pull requests small enough to review.

## Engineering Rules

- Prefer existing FastAPI routers, service patterns, shared models, and test helpers.
- Do not introduce a parallel control plane when an existing capability, runtime, task, approval, or audit path fits.
- Keep autonomous execution patch-only by default.
- Use SQLite-compatible defaults unless a task explicitly requires another store.
- Add focused tests for changed behavior.
- Update the nearest maintained docs when behavior changes.

## Documentation i18n

Active public docs are language-separated:

- English canonical docs use `.md`.
- Simplified Chinese mirrors use `.zh-CN.md`.
- Do not add inline bilingual blocks such as `Chinese:` / `English:` to active docs.
- When materially changing an active doc, update its matching language file in the same PR.
- Archived files under `docs/archive/**`, memory notes, test fixtures, and prompt templates are exempt.

Do not commit developer-machine paths in public docs. Use environment variables such as `AAS_REPO_ROOT`, `AAS_WORKSPACE_ROOT`, `AAS_LOG_ROOT`, `AAS_CACHE_ROOT`, or repository-relative links.

## Pull Requests

Before opening a PR:

```bash
git status --short
make test-quick
```

Include:

- purpose of the change,
- files or subsystem touched,
- validation run,
- known risks or follow-up work.

If the PR changes user-facing docs, keep the English and Simplified Chinese versions aligned.

## Review Expectations

Reviewers should focus on:

- behavioral regressions,
- policy bypass risk,
- missing tests,
- hard-coded local paths or secrets,
- stale documentation links,
- whether the change preserves the control-plane boundary.

Security-sensitive paths should bias toward rejection or explicit approval over silent fallback.

## Commit Style

Use clear, conventional prefixes when possible:

- `docs:`
- `fix:`
- `feat:`
- `test:`
- `refactor:`
- `chore:`

Prefer one coherent change per commit.
