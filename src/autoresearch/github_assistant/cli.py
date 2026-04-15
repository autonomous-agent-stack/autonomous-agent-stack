from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess

from autoresearch.github_assistant.config import initialize_profile, resolve_profile
from autoresearch.github_assistant.gh import GhCliGateway
from autoresearch.github_assistant.service import GitHubAssistantServiceRegistry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local-first GitHub assistant template CLI")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Assistant template repository root (default: current directory)",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="GitHub assistant profile id (defaults to default_profile or implicit default)",
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
    schedule_run_parser = schedule_subparsers.add_parser("run", help="Triage repos configured for scheduled scanning")
    schedule_run_parser.add_argument(
        "--all-profiles",
        action="store_true",
        help="Run scheduled triage for every configured profile",
    )

    profile_parser = subparsers.add_parser("profile", help="Manage GitHub assistant profiles")
    profile_subparsers = profile_parser.add_subparsers(dest="profile_command", required=True)
    profile_subparsers.add_parser("list", help="List configured GitHub assistant profiles")
    profile_init_parser = profile_subparsers.add_parser("init", help="Create a new profile scaffold")
    profile_init_parser.add_argument("profile_id", help="New profile identifier")
    profile_init_parser.add_argument("--display-name", default=None, help="Optional display name")
    profile_init_parser.add_argument(
        "--source-profile",
        default=None,
        help="Optional source profile to copy from (defaults to current/default profile)",
    )
    profile_doctor_parser = profile_subparsers.add_parser("doctor", help="Run doctor for one or all profiles")
    profile_doctor_parser.add_argument("--all", action="store_true", help="Run doctor for all profiles")

    auth_parser = subparsers.add_parser("auth", help="Run gh auth commands inside a profile context")
    auth_subparsers = auth_parser.add_subparsers(dest="auth_command", required=True)
    auth_subparsers.add_parser("status", help="Show gh auth status for the selected profile")
    auth_subparsers.add_parser("login", help="Run gh auth login for the selected profile")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    registry = GitHubAssistantServiceRegistry(repo_root=repo_root)

    if args.command == "profile":
        if args.profile_command == "list":
            default_profile = registry.default_profile_id()
            print(
                json.dumps(
                    {
                        "default_profile": default_profile,
                        "profiles": [
                            {
                                "id": profile.id,
                                "display_name": profile.display_name,
                                "root": str(profile.root),
                                "github_host": profile.github_host,
                                "gh_config_dir": str(profile.gh_config_dir),
                                "is_default": profile.id == default_profile,
                            }
                            for profile in registry.list_profiles()
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        if args.profile_command == "init":
            profile = initialize_profile(
                repo_root,
                args.profile_id,
                display_name=args.display_name,
                source_profile_id=args.source_profile or args.profile,
            )
            print(
                json.dumps(
                    {
                        "profile_id": profile.id,
                        "display_name": profile.display_name,
                        "root": str(profile.root),
                        "github_host": profile.github_host,
                        "gh_config_dir": str(profile.gh_config_dir),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        if args.profile_command == "doctor":
            target_profiles = registry.list_profiles() if args.all else [registry.get(args.profile).profile]
            reports = [registry.get(profile.id).doctor_report().model_dump(mode="json") for profile in target_profiles]
            print(json.dumps({"profiles": reports}, ensure_ascii=False, indent=2))
            return 0

    if args.command == "auth":
        profile = resolve_profile(repo_root, args.profile)
        gh_env = {"GH_CONFIG_DIR": str(profile.gh_config_dir)} if profile.explicit else {}
        gateway = GhCliGateway(
            repo_root=repo_root,
            env=gh_env,
            github_host=profile.github_host,
        )
        if args.auth_command == "status":
            ok, detail = gateway.auth_probe()
            print(
                json.dumps(
                    {
                        "profile_id": profile.id,
                        "profile_display_name": profile.display_name,
                        "github_host": profile.github_host,
                        "gh_config_dir": str(profile.gh_config_dir),
                        "ok": ok,
                        "active_login": gateway.current_login(),
                        "detail": detail,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0 if ok else 1
        if args.auth_command == "login":
            completed = subprocess.run(
                gateway.build_auth_command("login"),
                cwd=repo_root,
                check=False,
                env={**os.environ, **gh_env},
            )
            return completed.returncode

    service = registry.get(args.profile)

    if args.command == "doctor":
        report = service.doctor_report()
        print(f"Profile: {report.profile_id} ({report.profile_display_name})")
        for check in report.checks:
            line = f"[{check.status.value}] {check.name}: {check.detail}"
            if check.hint:
                line += f" | hint: {check.hint}"
            print(line)
        return 0 if report.ok else 1

    if args.command == "triage":
        run_dir, triage = service.triage(args.repo, args.issue_number)
        print(
            json.dumps(
                {
                    "profile_id": service.profile.id,
                    "profile_display_name": service.profile.display_name,
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
                    "profile_id": service.profile.id,
                    "profile_display_name": service.profile.display_name,
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
                    "profile_id": service.profile.id,
                    "profile_display_name": service.profile.display_name,
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
                    "profile_id": service.profile.id,
                    "profile_display_name": service.profile.display_name,
                    "run_dir": str(run_dir),
                    "release_plan": release_plan.model_dump(mode="json"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.command == "schedule" and args.schedule_command == "run":
        if args.all_profiles:
            result = {
                "profiles": [
                    registry.get(profile.id).schedule_run().model_dump(mode="json")
                    for profile in registry.list_profiles()
                ]
            }
        else:
            result = service.schedule_run().model_dump(mode="json")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    parser.error("unknown command")
    return 2
