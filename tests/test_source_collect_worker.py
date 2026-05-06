"""Tests for source_collect worker execution."""
from __future__ import annotations

import json
import os
from pathlib import Path

from autoresearch.shared.models import JobStatus, WorkerQueueItemRead, WorkerQueueName, WorkerTaskType, utc_now
from autoresearch.workers.mac.config import MacWorkerConfig
from autoresearch.workers.mac.executor import MacWorkerExecutor


def _run_source_collect(tmp_path: Path, payload: dict) -> tuple[WorkerQueueItemRead, object]:
    config = MacWorkerConfig(
        worker_id="source-worker-01",
        control_plane_base_url="http://127.0.0.1:8001",
        worker_name="Source Worker",
        host="test.local",
        housekeeping_root=tmp_path,
        dry_run=True,
    )
    now = utc_now()
    run = WorkerQueueItemRead(
        run_id="run_source_collect_001",
        queue_name=WorkerQueueName.HOUSEKEEPING,
        task_name="source_collect",
        task_type=WorkerTaskType.SOURCE_COLLECT,
        payload=payload,
        created_at=now,
        updated_at=now,
    )
    return run, MacWorkerExecutor(config).execute(run)


def _write_fake_xreach(bin_dir: Path, stdout: str, *, exit_code: int = 0) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "xreach"
    quoted_stdout = stdout.replace("'", "'\"'\"'")
    script.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' '{quoted_stdout}'\n"
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    os.chmod(script, 0o755)


def test_source_collect_x_bookmarks_uses_xreach_and_builds_content_kb_payload(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bin_dir = tmp_path / "bin"
    _write_fake_xreach(
        bin_dir,
        json.dumps(
            {
                "items": [
                    {
                        "id": "123",
                        "text": "Agent note worth saving",
                        "createdAt": "Wed May 06 10:00:00 +0000 2026",
                        "user": {"screenName": "alice", "name": "Alice"},
                    }
                ]
            }
        ),
    )
    monkeypatch.setenv("PATH", str(bin_dir))

    _, outcome = _run_source_collect(
        tmp_path,
        {
            "source_kind": "x_bookmarks",
            "limit": 1,
            "max_pages": 1,
            "title": "整理 X 书签",
            "request_text": "帮我整理一下 X 书签",
        },
    )

    assert outcome.status == JobStatus.COMPLETED
    assert outcome.result["collector"] == "xreach"
    assert outcome.result["item_count"] == 1
    assert outcome.result["source_urls"] == ["https://twitter.com/alice/status/123"]
    artifact_path = Path(outcome.result["artifact_path"])
    metadata_path = Path(outcome.result["metadata_path"])
    assert "Agent note worth saving" in artifact_path.read_text(encoding="utf-8")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["collector"] == "xreach"
    assert metadata["limit"] == 1
    assert outcome.result["content_kb_payload"]["subtitle_text_path"] == str(artifact_path)
    assert outcome.metrics["defer_completion_until"] == "content_kb_ingest"


def test_source_collect_fixture_path_takes_precedence_over_xreach(
    tmp_path: Path,
    monkeypatch,
) -> None:
    fixture = tmp_path / "bookmarks.json"
    fixture.write_text(
        json.dumps({"items": [{"title": "Fixture item", "url": "fixture://item", "text": "offline"}]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))

    _, outcome = _run_source_collect(
        tmp_path,
        {
            "source_kind": "x_bookmarks",
            "fixture_path": str(fixture),
        },
    )

    assert outcome.status == JobStatus.COMPLETED
    assert outcome.result["collector"] == "fixture"
    assert outcome.result["source_urls"] == ["fixture://item"]


def test_source_collect_x_bookmarks_fails_when_xreach_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))

    _, outcome = _run_source_collect(tmp_path, {"source_kind": "x_bookmarks"})

    assert outcome.status == JobStatus.FAILED
    assert outcome.result["error_kind"] == "collector_missing"
    assert outcome.result["collector"] == "xreach"


def test_source_collect_x_bookmarks_classifies_xreach_auth_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bin_dir = tmp_path / "bin"
    _write_fake_xreach(
        bin_dir,
        "Error: GraphQL Error: Could not authenticate you",
        exit_code=1,
    )
    monkeypatch.setenv("PATH", str(bin_dir))

    _, outcome = _run_source_collect(tmp_path, {"source_kind": "x_bookmarks"})

    assert outcome.status == JobStatus.FAILED
    assert outcome.error == "X 书签采集器 xreach 鉴权失败，无法读取书签。"
    assert outcome.result["error_kind"] == "collector_auth_failed"
    assert outcome.result["exit_reason"] == "collector_auth_failed"
    assert outcome.result["collector"] == "xreach"
    assert "重新完成 xreach 登录" in outcome.result["telegram_hint"]
    assert "Could not authenticate you" in outcome.result["collector_error"]
    assert outcome.metrics["error_kind"] == "collector_auth_failed"


def test_source_collect_x_bookmarks_fails_on_invalid_collector_json(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bin_dir = tmp_path / "bin"
    _write_fake_xreach(bin_dir, "{not-json")
    monkeypatch.setenv("PATH", str(bin_dir))

    _, outcome = _run_source_collect(tmp_path, {"source_kind": "x_bookmarks"})

    assert outcome.status == JobStatus.FAILED
    assert outcome.result["error_kind"] == "collector_invalid_json"


def test_source_collect_x_bookmarks_fails_on_empty_collector_result(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bin_dir = tmp_path / "bin"
    _write_fake_xreach(bin_dir, json.dumps({"items": []}))
    monkeypatch.setenv("PATH", str(bin_dir))

    _, outcome = _run_source_collect(tmp_path, {"source_kind": "x_bookmarks"})

    assert outcome.status == JobStatus.FAILED
    assert outcome.result["error_kind"] == "collector_empty"
