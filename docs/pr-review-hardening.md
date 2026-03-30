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

## Trial Rubric

Before expanding reviewer scope or adding a second AI reviewer, run a small trial on 5-10 low-risk PRs and score the current OpenHands reviewer with the same rubric each time.

Track these four metrics for every reviewed PR:

1. False positive rate
- Definition: comments that are technically incorrect, already addressed by the diff, or not actionable in context.
- Target for trial: keep this low enough that humans do not start ignoring the bot by default.

2. False negative rate
- Definition: important review findings later caught by humans, CI, or post-merge fixes that the reviewer missed.
- Target for trial: identify whether the bot is missing recurring classes of issues.

3. Useful comment rate
- Definition: percentage of comments that directly lead to a code change, clarification, or an accepted follow-up task.
- Target for trial: favor signal over volume; a smaller number of useful comments is better than many low-value comments.

4. Average repair rounds
- Definition: how many human or bot follow-up rounds are needed before the PR reaches an acceptable state.
- Target for trial: measure whether the reviewer is reducing or increasing iteration cost.

## Trial Execution

Use this lightweight process for each PR in the trial window:

1. Mark the PR with `review-this` and let OpenHands produce comment-only feedback.
2. Record the raw bot comments in the PR timeline or an external tracker.
3. After human review completes, classify each bot comment as one of:
- `useful`
- `false_positive`
- `non_actionable`
- `duplicate`
4. If humans, CI, or post-merge fixes catch a material issue the bot missed, log one `false_negative` entry for that issue class.
5. Record how many total repair rounds were needed before merge or close.

## Feedback Loop

Keep the feedback loop simple and explicit:

1. Add a short reviewer summary to each trial PR:
- `Bot comments: N`
- `Useful: N`
- `False positives: N`
- `False negatives discovered later: N`
- `Repair rounds: N`

2. If a bot comment is low-value, mark it in the PR discussion with a short reason:
- `incorrect`
- `duplicate`
- `out_of_scope`
- `not_actionable`

3. At the end of the 5-10 PR trial, summarize:
- recurring false-positive patterns
- recurring false-negative patterns
- whether useful comment rate is high enough to justify wider rollout
- whether average repair rounds went down, stayed flat, or increased

## Rollout Gate

Do not add a second reviewer or make the AI reviewer more prominent until the trial says it is helping.

A wider rollout is justified only if all of the following hold:

1. Humans still trust the comments enough to read them.
2. Useful comment rate is meaningfully higher than false-positive rate.
3. False negatives are not clustering around one obvious blind spot.
4. Average repair rounds are flat or improving.

If the trial fails these checks, keep the current reviewer advisory-only and tune prompts, trigger rules, or review scope before expanding.
