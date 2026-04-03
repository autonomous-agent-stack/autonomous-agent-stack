from __future__ import annotations

import json
from pathlib import Path

from autoresearch.agent_protocol.models import ExecutionPolicy
from scripts.standby_enqueue_job import main


def _write_manifest(repo_root: Path, agent_id: str = "openhands") -> None:
    manifests_dir = repo_root / "configs" / "agents"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": agent_id,
        "kind": "process",
        "entrypoint": f"drivers/{agent_id}_adapter.sh",
        "version": "0.1",
        "capabilities": ["write_repo"],
        "default_mode": "apply_in_workspace",
        "policy_defaults": ExecutionPolicy(
            allowed_paths=["src/**"],
            forbidden_paths=[".git/**"],
        ).model_dump(mode="json"),
    }
    (manifests_dir / f"{agent_id}.yaml").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_standby_enqueue_materializes_manual_fail_closed_job(tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "repo"
    standby_root = tmp_path / "standby"
    _write_manifest(repo_root, "openhands")

    exit_code = main(
        [
            "--repo-root",
            str(repo_root),
            "--standby-root",
            str(standby_root),
            "--agent",
            "openhands",
            "--task",
            "demo standby task",
            "--validator-cmd",
            "pytest -q tests/test_demo.py",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    queued_path = Path(output["queued_path"])
    assert queued_path.exists()

    envelope = json.loads(queued_path.read_text(encoding="utf-8"))
    assert envelope["metadata"] == {"source": "standby_enqueue_job"}
    assert envelope["job"]["agent_id"] == "openhands"
    assert envelope["job"]["mode"] == "apply_in_workspace"
    assert envelope["job"]["fallback"] == []
    assert envelope["job"]["policy"]["allowed_paths"] == ["src/**"]
    assert envelope["job"]["metadata"]["standby_mode"] == "manual_fail_closed"
    assert envelope["job"]["validators"] == [
        {
            "id": "cmd_1",
            "kind": "command",
            "command": "pytest -q tests/test_demo.py",
        }
    ]
