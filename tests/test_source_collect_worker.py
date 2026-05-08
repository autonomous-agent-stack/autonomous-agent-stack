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


def _write_fake_xreach_auth_extract_success(bin_dir: Path) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "xreach"
    marker = bin_dir / ".xreach-authed"
    bookmarks = json.dumps({"items": [{"id": "456", "text": "Recovered bookmark", "user": {"screenName": "bob"}}]})
    script.write_text(
        "#!/bin/sh\n"
        f"MARKER='{marker}'\n"
        "if [ \"$1\" = 'auth' ] && [ \"$2\" = 'check' ]; then\n"
        "  [ -f \"$MARKER\" ] && exit 0\n"
        "  echo 'Error: GraphQL Error: Could not authenticate you'\n"
        "  exit 1\n"
        "fi\n"
        "if [ \"$1\" = 'auth' ] && [ \"$2\" = 'browsers' ]; then\n"
        "  echo 'browser=chrome, profile=Default'\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = 'auth' ] && [ \"$2\" = 'extract' ]; then\n"
        "  : > \"$MARKER\"\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = 'bookmarks' ]; then\n"
        f"  printf '%s\\n' '{bookmarks}'\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
        encoding="utf-8",
    )
    os.chmod(script, 0o755)


def _write_fake_xreach_bookmarks_auth_retry_success(bin_dir: Path) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "xreach"
    marker = bin_dir / ".xreach-refreshed"
    bookmarks = json.dumps({"items": [{"id": "789", "text": "Retried bookmark", "user": {"screenName": "chen"}}]})
    script.write_text(
        "#!/bin/sh\n"
        f"MARKER='{marker}'\n"
        "if [ \"$1\" = 'auth' ] && [ \"$2\" = 'check' ]; then\n"
        "  echo '✓ Authenticated'\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = 'auth' ] && [ \"$2\" = 'browsers' ]; then\n"
        "  echo 'browser=chrome, profile=Default'\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = 'auth' ] && [ \"$2\" = 'extract' ]; then\n"
        "  : > \"$MARKER\"\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = 'bookmarks' ]; then\n"
        "  if [ -f \"$MARKER\" ]; then\n"
        f"    printf '%s\\n' '{bookmarks}'\n"
        "    exit 0\n"
        "  fi\n"
        "  echo 'Error: GraphQL Error: Could not authenticate you'\n"
        "  exit 1\n"
        "fi\n"
        "exit 1\n",
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


def test_source_collect_x_bookmarks_reports_delta_since_previous_collection(
    tmp_path: Path,
    monkeypatch,
) -> None:
    previous_dir = tmp_path / "artifacts" / "source_collect" / "run_previous"
    previous_dir.mkdir(parents=True)
    previous_dir.joinpath("metadata.json").write_text(
        json.dumps(
            {
                "collector": "xreach",
                "source_kind": "x_bookmarks",
                "item_count": 1,
                "source_urls": ["https://twitter.com/alice/status/111"],
            }
        ),
        encoding="utf-8",
    )
    bin_dir = tmp_path / "bin"
    _write_fake_xreach(
        bin_dir,
        json.dumps(
            {
                "items": [
                    {"id": "111", "text": "Known bookmark", "user": {"screenName": "alice"}},
                    {"id": "222", "text": "Fresh bookmark", "user": {"screenName": "alice"}},
                ]
            }
        ),
    )
    monkeypatch.setenv("PATH", str(bin_dir))

    _, outcome = _run_source_collect(
        tmp_path,
        {
            "source_kind": "x_bookmarks",
            "request_text": "上次整理X书签后有新的么",
        },
    )

    assert outcome.status == JobStatus.COMPLETED
    assert outcome.result["item_count"] == 2
    assert outcome.result["previous_source_collect_run_id"] == "run_previous"
    assert outcome.result["new_item_count"] == 1
    assert outcome.result["known_item_count"] == 1
    assert outcome.result["new_source_urls"] == ["https://twitter.com/alice/status/222"]
    assert "发现新增 1 条 X 书签" in outcome.result["answer"]
    content_payload = outcome.result["content_kb_payload"]
    assert content_payload["source_collect_new_item_count"] == 1
    assert content_payload["source_collect_known_item_count"] == 1
    assert content_payload["source_collect_previous_run_id"] == "run_previous"
    metadata = json.loads(Path(outcome.result["metadata_path"]).read_text(encoding="utf-8"))
    assert metadata["new_item_count"] == 1
    assert metadata["answer"] == outcome.result["answer"]


def test_source_collect_x_bookmarks_ignores_fixture_baseline_for_xreach(
    tmp_path: Path,
    monkeypatch,
) -> None:
    fixture_previous = tmp_path / "artifacts" / "source_collect" / "run_fixture_previous"
    fixture_previous.mkdir(parents=True)
    fixture_previous.joinpath("metadata.json").write_text(
        json.dumps(
            {
                "collector": "fixture",
                "source_kind": "x_bookmarks",
                "item_count": 2,
                "source_urls": ["fixture://aas/source-smoke/known-001"],
            }
        ),
        encoding="utf-8",
    )
    real_previous = tmp_path / "artifacts" / "source_collect" / "run_real_previous"
    real_previous.mkdir(parents=True)
    real_previous.joinpath("metadata.json").write_text(
        json.dumps(
            {
                "collector": "xreach",
                "source_kind": "x_bookmarks",
                "item_count": 1,
                "source_urls": ["https://twitter.com/alice/status/111"],
            }
        ),
        encoding="utf-8",
    )
    bin_dir = tmp_path / "bin"
    _write_fake_xreach(
        bin_dir,
        json.dumps(
            {
                "items": [
                    {"id": "111", "text": "Known bookmark", "user": {"screenName": "alice"}},
                    {"id": "222", "text": "Fresh bookmark", "user": {"screenName": "alice"}},
                ]
            }
        ),
    )
    monkeypatch.setenv("PATH", str(bin_dir))

    _, outcome = _run_source_collect(
        tmp_path,
        {
            "source_kind": "x_bookmarks",
            "request_text": "上次整理X书签后有新的么",
        },
    )

    assert outcome.status == JobStatus.COMPLETED
    assert outcome.result["collector"] == "xreach"
    assert outcome.result["previous_source_collect_run_id"] == "run_real_previous"
    assert outcome.result["new_item_count"] == 1
    assert outcome.result["new_source_urls"] == ["https://twitter.com/alice/status/222"]


def test_source_collect_x_bookmarks_detail_followup_uses_previous_delta_context(
    tmp_path: Path,
    monkeypatch,
) -> None:
    previous_dir = tmp_path / "artifacts" / "source_collect" / "run_previous_delta"
    previous_dir.mkdir(parents=True)
    artifact_path = previous_dir / "normalized_subtitle.txt"
    artifact_path.write_text(
        "# source_collect x_bookmarks\n\n"
        "## 1. X bookmark by @alice\n"
        "Source: https://twitter.com/alice/status/111\n"
        "Author: Alice\n"
        "Created: Wed May 06 10:00:00 +0000 2026\n"
        "Known bookmark\n\n"
        "## 2. X bookmark by @alice\n"
        "Source: https://twitter.com/alice/status/222\n"
        "Author: Alice\n"
        "Created: Wed May 06 10:05:00 +0000 2026\n"
        "Fresh bookmark detail\n",
        encoding="utf-8",
    )
    previous_dir.joinpath("metadata.json").write_text(
        json.dumps(
            {
                "collector": "xreach",
                "source_kind": "x_bookmarks",
                "item_count": 2,
                "previous_item_count": 1,
                "previous_source_collect_run_id": "run_baseline",
                "new_item_count": 1,
                "new_source_urls": ["https://twitter.com/alice/status/222"],
                "source_urls": [
                    "https://twitter.com/alice/status/111",
                    "https://twitter.com/alice/status/222",
                ],
                "artifact_path": str(artifact_path),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))

    _, outcome = _run_source_collect(
        tmp_path,
        {
            "source_kind": "x_bookmarks",
            "request_text": "新增的x书签详情是什么",
        },
    )

    assert outcome.status == JobStatus.COMPLETED
    assert outcome.result["collector"] == "context_lookup"
    assert outcome.result["source_collect_context_run_id"] == "run_previous_delta"
    assert outcome.result["previous_source_collect_run_id"] == "run_baseline"
    assert outcome.result["new_item_count"] == 1
    assert outcome.result["new_source_urls"] == ["https://twitter.com/alice/status/222"]
    assert outcome.result["new_items"][0]["text"] == "Fresh bookmark detail"
    assert "Fresh bookmark detail" in outcome.result["answer"]
    content_payload = outcome.result["content_kb_payload"]
    assert content_payload["source_collect_detail_lookup"] is True
    assert content_payload["source_collect_context_run_id"] == "run_previous_delta"
    assert content_payload["source_collect_new_items"][0]["url"] == "https://twitter.com/alice/status/222"


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


def test_source_collect_x_bookmarks_uses_known_path_when_worker_path_misses_xreach(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bin_dir = tmp_path / "known-bin"
    _write_fake_xreach(bin_dir, json.dumps({"items": [{"text": "Known path bookmark"}]}))
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    monkeypatch.setenv("AUTORESEARCH_XREACH_KNOWN_PATHS", str(bin_dir / "xreach"))

    _, outcome = _run_source_collect(tmp_path, {"source_kind": "x_bookmarks"})

    assert outcome.status == JobStatus.COMPLETED
    assert outcome.result["collector"] == "xreach"
    assert outcome.result["xreach_path_repair_status"] == "path_repaired"


def test_source_collect_x_bookmarks_pauses_for_setup_recovery_when_xreach_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    monkeypatch.setenv("AUTORESEARCH_XREACH_DISABLE_KNOWN_PATHS", "1")

    _, outcome = _run_source_collect(tmp_path, {"source_kind": "x_bookmarks"})

    assert outcome.status == JobStatus.RUNNING
    assert outcome.error is None
    assert outcome.result["error_kind"] == "xreach_setup_required"
    assert outcome.result["failure_kind"] == "dependency_missing"
    assert outcome.result["collector"] == "xreach"
    assert outcome.result["can_self_repair"] is True
    assert "install_xreach" in outcome.result["next_actions"]
    assert outcome.metrics["worker_pause_reason"] == "xreach_setup_required"


def test_source_collect_x_bookmarks_classifies_xreach_auth_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bin_dir = tmp_path / "bin"
    _write_fake_xreach(
        bin_dir,
        "Error: GraphQL Error: Could not authenticate you\nAuth Token: secret-token\nCT0: secret-ct0",
        exit_code=1,
    )
    monkeypatch.setenv("PATH", str(bin_dir))

    _, outcome = _run_source_collect(tmp_path, {"source_kind": "x_bookmarks"})

    assert outcome.status == JobStatus.RUNNING
    assert outcome.error is None
    assert outcome.result["error_kind"] == "collector_auth_required"
    assert outcome.result["exit_reason"] == "collector_auth_required"
    assert outcome.result["collector"] == "xreach"
    assert "Hermes" in outcome.result["telegram_hint"]
    assert "Could not authenticate you" in outcome.result["collector_error"]
    assert "secret-token" not in outcome.result["collector_error"]
    assert "secret-ct0" not in outcome.result["collector_error"]
    assert "secret-token" not in json.dumps(outcome.result["xreach_auth_attempts"])
    assert "secret-ct0" not in json.dumps(outcome.result["xreach_auth_attempts"])
    assert outcome.metrics["error_kind"] == "collector_auth_required"
    assert outcome.metrics["worker_pause_reason"] == "xreach_auth_required"


def test_source_collect_x_bookmarks_recovers_when_xreach_auth_extract_succeeds(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bin_dir = tmp_path / "bin"
    _write_fake_xreach_auth_extract_success(bin_dir)
    monkeypatch.setenv("PATH", str(bin_dir))

    _, outcome = _run_source_collect(tmp_path, {"source_kind": "x_bookmarks"})

    assert outcome.status == JobStatus.COMPLETED
    assert outcome.result["collector"] == "xreach"
    assert outcome.result["item_count"] == 1
    assert outcome.result["source_urls"] == ["https://twitter.com/bob/status/456"]


def test_source_collect_x_bookmarks_refreshes_auth_when_check_passes_but_bookmarks_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bin_dir = tmp_path / "bin"
    _write_fake_xreach_bookmarks_auth_retry_success(bin_dir)
    monkeypatch.setenv("PATH", str(bin_dir))

    _, outcome = _run_source_collect(tmp_path, {"source_kind": "x_bookmarks"})

    assert outcome.status == JobStatus.COMPLETED
    assert outcome.result["collector"] == "xreach"
    assert outcome.result["item_count"] == 1
    assert outcome.result["source_urls"] == ["https://twitter.com/chen/status/789"]


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
