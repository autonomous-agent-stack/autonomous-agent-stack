from __future__ import annotations

import json
from pathlib import Path

from scripts.replay_openhands_worker_requests import replay_requests


def test_replay_openhands_worker_requests_writes_summary_json(tmp_path: Path) -> None:
    input_path = tmp_path / "recorded_requests.json"
    output_path = tmp_path / "replay_results.json"
    input_path.write_text(
        json.dumps(
            [
                {
                    "job_id": "job-1",
                    "problem_statement": "Patch a subtitle-sidecar business surface test.",
                    "allowed_paths": ["apps/malu/**", "tests/apps/test_malu_landing_page.py"],
                    "test_command": "pytest -q tests/apps/test_malu_landing_page.py",
                    "metadata": {"language": "en"},
                },
                {
                    "job_id": "job-2",
                    "problem_statement": "This request should fail path validation.",
                    "allowed_paths": ["/etc/passwd"],
                    "test_command": "pytest -q tests/test_bad.py",
                },
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = replay_requests(input_path, output_path)

    assert output_path.exists()
    assert payload["total_requests"] == 2
    assert payload["ok_count"] == 1
    assert payload["error_count"] == 1

    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["results"][0]["status"] == "ok"
    assert report["results"][0]["pipeline_target"] == "draft_pr"
    assert report["results"][0]["worker_output_mode"] == "patch"
    assert report["results"][0]["language"] == "en"
    assert report["results"][0]["artifact_stub"] == "job-1-draft_pr.json"
    assert report["results"][1]["status"] == "error"
