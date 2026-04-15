from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def test_new_process_driver_scaffolds_expected_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    script = Path(__file__).resolve().parents[1] / "scripts" / "new_process_driver.py"
    completed = subprocess.run(
        [sys.executable, str(script), "demo_driver", "--root", str(repo_root)],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["agent_id"] == "demo_driver"

    manifest = repo_root / "configs" / "agents" / "demo_driver.yaml"
    adapter = repo_root / "drivers" / "demo_driver_adapter.sh"
    test_file = repo_root / "tests" / "test_demo_driver_adapter.py"
    snippet = repo_root / "docs" / "agent-snippets" / "demo_driver.md"

    assert manifest.exists()
    assert adapter.exists()
    assert test_file.exists()
    assert snippet.exists()

    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest_payload["id"] == "demo_driver"
    assert manifest_payload["entrypoint"] == "drivers/demo_driver_adapter.sh"
