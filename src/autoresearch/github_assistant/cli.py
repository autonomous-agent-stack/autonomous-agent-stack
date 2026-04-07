from __future__ import annotations

import argparse
import json
from pathlib import Path

from autoresearch.github_assistant.service import GitHubAssistantService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local-first GitHub assistant template CLI")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Assistant template repository root (default: current directory)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="Validate gh auth, configs, prompts, and repo access")

    triage_parser = subparsers.add_parser("triage", help="Triage a managed GitHub issue")
    triage_parser.add_argument("repo", help="Managed repo full name or unique short name")
    triage_parser.add_argument("issue_number", type=int, help="Issue number in the managed repo")

    execute_parser = subparsers.add_parser("execute", help="Execute a managed GitHub issue")
    execute_parser.add_argument("repo", help="Managed repo full name or unique short name")
    execute_parser.add_argument("issue_number", type=int, help="Issue number in the managed repo")

    review_parser = subparsers.add_parser("review-pr", help="Review a managed pull request")
    review_parser.add_argument("repo", help="Managed repo full name or unique short name")
    review_parser.add_argument("pr_number", type=int, help="Pull request number in the managed repo")

    release_parser = subparsers.add_parser("release-plan", help="Build a release plan from merged PRs")
    release_parser.add_argument("repo", help="Managed repo full name or unique short name")
    release_parser.add_argument("--version", default=None, help="Optional target version label")
    release_parser.add_argument("--limit", type=int, default=10, help="How many merged PRs to include")

    schedule_parser = subparsers.add_parser("schedule", help="Run scheduled issue triage")
    schedule_subparsers = schedule_parser.add_subparsers(dest="schedule_command", required=True)
    schedule_subparsers.add_parser("run", help="Triage repos configured for scheduled scanning")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    service = GitHubAssistantService(repo_root=Path(args.repo_root).resolve())

    if args.command == "doctor":
        checks, ok = service.doctor()
        for check in checks:
            line = f"[{check.status.value}] {check.name}: {check.detail}"
            if check.hint:
                line += f" | hint: {check.hint}"
            print(line)
        return 0 if ok else 1

    if args.command == "triage":
        run_dir, triage = service.triage(args.repo, args.issue_number)
        print(
            json.dumps(
                {
                    "run_dir": str(run_dir),
                    "triage": triage.model_dump(mode="json"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.command == "execute":
        run_dir = service.execute(args.repo, args.issue_number)
        summary_path = run_dir / "summary.json"
        print(
            json.dumps(
                {
                    "run_dir": str(run_dir),
                    "summary_path": str(summary_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.command == "review-pr":
        run_dir, review = service.review_pr(args.repo, args.pr_number)
        print(
            json.dumps(
                {
                    "run_dir": str(run_dir),
                    "review": review.model_dump(mode="json"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.command == "release-plan":
        run_dir, release_plan = service.release_plan(
            args.repo,
            version=args.version,
            limit=args.limit,
        )
        print(
            json.dumps(
                {
                    "run_dir": str(run_dir),
                    "release_plan": release_plan.model_dump(mode="json"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.command == "schedule" and args.schedule_command == "run":
        result = service.schedule_run()
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0

    parser.error("unknown command")
    return 2
