# PR Review Hardening (OpenHands + Quality Gates)

This repository now uses a two-layer review setup:

1. AI first-pass reviewer (comment-only)
- Workflow: `.github/workflows/pr-review-by-openhands.yml`
- Trigger:
  - Required: PR label `review-this`
  - Optional: reviewer request for `OPENHANDS_REVIEWER_HANDLE` (repo variable)
- Safety defaults:
  - `pull_request` event (not `pull_request_target`)
  - Skip fork PRs (`head.repo.full_name == github.repository`)
  - Minimal permissions (`contents: read`, `pull-requests: write`, `issues: write`)
  - Human merge remains mandatory
  - OpenHands action pinned to full commit SHA
  - OpenHands extensions pinned to full commit SHA
- Required check policy:
  - Do not mark this workflow as required while it is on-demand (`review-this` / optional reviewer request trigger).
  - Keep it advisory, not merge-blocking.

2. Hard quality gates for reviewer core
- Workflow: `.github/workflows/quality-gates.yml`
- Checks:
  - `mypy` (typed consistency)
  - `bandit` (security anti-patterns)
  - `semgrep` (rule-based bug/security checks)
  - Trigger includes `merge_group` for merge queue compatibility.

## One-time repository setup

1. Add Actions secret:
- `LLM_API_KEY`

2. Create label:
- `review-this`

3. Optional repository variables:
- `OPENHANDS_REVIEW_MODEL`
- `OPENHANDS_REVIEW_STYLE` (`standard` or `roasted`)
- `OPENHANDS_LLM_BASE_URL`
- `OPENHANDS_REVIEWER_HANDLE` (optional reviewer login; leave empty to run label-only)

4. Configure merge protection on `main`
- Pick one as primary control plane: ruleset or branch protection (avoid duplicate management drift).
- Require pull request before merge
- Require status checks:
  - Use job names/check contexts (not workflow filenames)
  - `CI / lint-test-audit` (main CI line; matrix variants may appear in UI)
  - `Quality Gates / reviewer-gates`
- Require review from Code Owners
- Restrict direct pushes to `main`

## Notes

- `CODEOWNERS` is in `.github/CODEOWNERS` and should be kept in sync with maintainers.
- Repository-specific review policy is in `.agents/skills/custom-codereview-guide.md`.
- If merge queue is enabled, keep both `CI` and `Quality Gates` workflows listening on `merge_group`.
