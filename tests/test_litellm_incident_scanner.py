from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "security" / "check_litellm_incident.py"
)


def _run_scanner(cwd: Path):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(proc.stdout or "{}")
    return proc.returncode, payload


def test_scanner_detects_compromised_version_in_requirements(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("litellm==1.82.8\nfastapi==0.115.0\n", encoding="utf-8")
    rc, payload = _run_scanner(tmp_path)

    assert rc == 1
    assert payload["lockfile_hits"]
    assert any(hit["version"] == "1.82.8" for hit in payload["lockfile_hits"])


def test_scanner_passes_clean_workspace(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("fastapi==0.115.0\n", encoding="utf-8")
    rc, payload = _run_scanner(tmp_path)

    assert payload["lockfile_hits"] == []
    assert payload["risk_installed"] is False
    assert rc in {0, 1}
