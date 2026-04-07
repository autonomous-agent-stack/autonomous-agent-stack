from __future__ import annotations

import os
from pathlib import Path
import subprocess

from autoresearch.github_assistant.models import AssistantConfig, ExecutionPlan, GitHubIssue, PreparedWorkspace


class AssistantExecutorRunner:
    def __init__(self, *, repo_root: Path) -> None:
        self._repo_root = repo_root

    def run(
        self,
        *,
        prepared: PreparedWorkspace,
        run_dir: Path,
        issue: GitHubIssue,
        plan: ExecutionPlan,
        assistant: AssistantConfig,
    ) -> None:
        prompt_text = self._build_prompt(issue=issue, plan=plan)
        prompt_path = run_dir / "executor_prompt.md"
        issue_path = run_dir / "issue.json"
        plan_path = run_dir / "plan.md"
        prompt_path.write_text(prompt_text, encoding="utf-8")

        command, extra_env = self._command_for_adapter(
            assistant=assistant,
            prepared=prepared,
            run_dir=run_dir,
            issue=issue,
            prompt_text=prompt_text,
            prompt_path=prompt_path,
            plan_path=plan_path,
            issue_path=issue_path,
        )
        env = {
            **os.environ,
            "ASSISTANT_WORKSPACE": str(prepared.execution_workspace_dir),
            "ASSISTANT_RUN_DIR": str(run_dir),
            "ASSISTANT_ISSUE_NUMBER": str(issue.number),
            "ASSISTANT_ISSUE_URL": issue.url,
            "ASSISTANT_REPO": issue.repo,
            "ASSISTANT_PROMPT": prompt_text,
            "ASSISTANT_PROMPT_PATH": str(prompt_path),
            **assistant.executor.env,
            **extra_env,
        }
        completed = subprocess.run(
            command,
            cwd=prepared.execution_workspace_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=assistant.executor.timeout_seconds,
            env=env,
        )
        (run_dir / "executor.stdout.log").write_text(completed.stdout, encoding="utf-8")
        (run_dir / "executor.stderr.log").write_text(completed.stderr, encoding="utf-8")
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout or "executor failed").strip())

    def is_configured(self, assistant: AssistantConfig) -> bool:
        adapter = assistant.executor.adapter
        if adapter in {"codex", "openhands"}:
            return True
        return bool(assistant.executor.command)

    def _command_for_adapter(
        self,
        *,
        assistant: AssistantConfig,
        prepared: PreparedWorkspace,
        run_dir: Path,
        issue: GitHubIssue,
        prompt_text: str,
        prompt_path: Path,
        plan_path: Path,
        issue_path: Path,
    ) -> tuple[list[str], dict[str, str]]:
        placeholders = {
            "workspace": str(prepared.execution_workspace_dir),
            "run_dir": str(run_dir),
            "issue_number": str(issue.number),
            "issue_url": issue.url,
            "repo": issue.repo,
            "plan_path": str(plan_path),
            "issue_path": str(issue_path),
            "prompt": prompt_text,
            "prompt_path": str(prompt_path),
        }
        adapter = assistant.executor.adapter

        if assistant.executor.command:
            return ([item.format(**placeholders) for item in assistant.executor.command], {})

        if adapter == "codex":
            binary = assistant.executor.binary or "codex"
            return (
                [
                    binary,
                    "exec",
                    "-C",
                    placeholders["workspace"],
                    placeholders["prompt"],
                ],
                {},
            )

        if adapter == "openhands":
            return (
                [
                    "bash",
                    str((self._repo_root / "scripts" / "openhands_start.sh").resolve()),
                    placeholders["prompt"],
                ],
                {
                    "OPENHANDS_WORKSPACE": placeholders["workspace"],
                    "OPENHANDS_RUNTIME": os.environ.get("OPENHANDS_RUNTIME", "host"),
                },
            )

        raise RuntimeError(
            f"assistant.executor.command is required for adapter={adapter}"
        )

    @staticmethod
    def _build_prompt(*, issue: GitHubIssue, plan: ExecutionPlan) -> str:
        lines = [
            "Resolve the GitHub issue inside the provided workspace.",
            "",
            f"Repo: {issue.repo}",
            f"Issue: #{issue.number} - {issue.title or '(untitled)'}",
            f"URL: {issue.url}",
            "",
            "Issue body:",
            issue.body.strip() or "(empty)",
            "",
            "Execution plan:",
            f"- Branch: {plan.branch_name}",
            f"- Commit message: {plan.commit_message}",
            f"- Allowed paths: {', '.join(plan.allowed_paths) or '(none)'}",
            f"- Validator commands: {', '.join(plan.validator_commands) or '(none)'}",
            "",
            "Constraints:",
            "- Keep the patch narrow.",
            "- Stay inside allowed paths.",
            "- Update tests when needed.",
            "- Leave branch / PR operations to the outer control plane.",
        ]
        return "\n".join(lines).strip() + "\n"
