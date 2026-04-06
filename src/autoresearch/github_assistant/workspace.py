from __future__ import annotations

import shutil
from pathlib import Path

from autoresearch.github_assistant.gh import GhCliGateway
from autoresearch.github_assistant.models import PreparedWorkspace


class LocalWorkspaceManager:
    def __init__(self, *, github: GhCliGateway, workspace_root: Path) -> None:
        self._github = github
        self._workspace_root = workspace_root

    def prepare(self, *, repo: str, run_id: str) -> PreparedWorkspace:
        root = self._workspace_root / run_id
        source_repo_dir = root / "source"
        execution_workspace_dir = root / "workspace"
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        self._github.clone_repo(repo, source_repo_dir)
        shutil.copytree(source_repo_dir, execution_workspace_dir, symlinks=True)
        return PreparedWorkspace(
            source_repo_dir=source_repo_dir,
            execution_workspace_dir=execution_workspace_dir,
        )

    def cleanup(self, prepared: PreparedWorkspace) -> None:
        root = prepared.source_repo_dir.parent
        shutil.rmtree(root, ignore_errors=True)
