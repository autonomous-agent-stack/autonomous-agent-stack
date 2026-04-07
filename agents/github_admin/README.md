# GitHub Admin Agent

Dry-run first GitHub repository migration workflow for Codex.

Current slice:
- inventory public repositories for configured owners
- build a transfer plan toward a target owner or org
- annotate repos that should be skipped or manually reviewed
- write artifacts under `artifacts/github_admin/YYYY-MM-DD/run_XXX/`

Not in scope yet:
- executing repository transfer
- mutating collaborators
- accepting invitations

All mutating actions stay gated behind future human approval.
