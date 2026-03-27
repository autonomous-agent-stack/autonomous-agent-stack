---
name: custom-codereview-guide
description: Repository-specific guardrails for OpenHands PR review
triggers:
  - /codereview
---

# Autonomous Agent Stack - Review Guardrails

You are the first-pass reviewer. Keep this workflow comment-only and focus on actionable issues.

## Review Decisions

- APPROVE only low-risk changes (docs-only, tests-only, non-runtime config edits).
- COMMENT for risky logic changes, design ambiguity, or missing tests.
- REQUEST CHANGES for security boundary violations or regression risk.

## Must-Check Areas

1. Security boundaries
- No bypass of guardrails in `src/security/`, `src/gatekeeper/`, or execution adapters.
- No unsafe command execution paths (`shell=True`, untrusted command composition, hidden runtime writes).
- No weakening of access checks in panel, webhook, gateway, or auth paths.

2. Review-loop integrity
- Diff review must remain comment-only; no autonomous merge, no hidden approval logic.
- Reviewer output should include concrete file/line pointers and minimal reproduction guidance.

3. Reliability and test coverage
- Runtime-path changes should include tests in `tests/`.
- Changes touching workflow/runner code should include failure-path assertions.

4. Repository conventions
- Keep edits scoped and avoid unrelated churn.
- Respect existing linting/formatting conventions.
- Prefer explicit contracts and typed structures where practical.

## Output Style

- Prioritize high-severity issues first.
- Keep comments concise, specific, and actionable.
- Avoid duplicate comments when the same issue appears repeatedly.
