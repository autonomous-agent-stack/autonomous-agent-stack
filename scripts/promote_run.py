#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from autoresearch.core.services.git_promotion_gate import GitPromotionCreateRequest, GitPromotionService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote a ready AEP run into a git branch and draft PR payload")
    parser.add_argument("--run-id", required=True, help="AEP run id under .masfactory_runtime/runs/<run_id>")
    parser.add_argument("--base-ref", default="main", help="git base ref for the promotion branch")
    parser.add_argument("--branch-prefix", default="codex/auto-upgrade", help="branch prefix")
    parser.add_argument("--title", default=None, help="draft PR title override")
    parser.add_argument("--body", default="", help="draft PR body override")
    parser.add_argument("--commit-message", default=None, help="git commit message override")
    parser.add_argument("--validator-cmd", action="append", default=[], help="validator command to run in the clean worktree")
    parser.add_argument("--push", action="store_true", help="push the branch to the configured remote")
    parser.add_argument("--open-draft-pr", action="store_true", help="run gh pr create --draft after push")
    parser.add_argument("--keep-worktree", action="store_true", help="keep the temporary worktree after completion")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    service = GitPromotionService(repo_root=repo_root)
    record = service.promote(
        GitPromotionCreateRequest(
            run_id=args.run_id,
            base_ref=args.base_ref,
            branch_prefix=args.branch_prefix,
            title=args.title,
            body=args.body,
            commit_message=args.commit_message,
            validator_commands=args.validator_cmd,
            push_branch=args.push,
            open_draft_pr=args.open_draft_pr,
            keep_worktree=args.keep_worktree,
            metadata={"entrypoint": "scripts/promote_run.py"},
        )
    )
    print(json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0 if record.status == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
