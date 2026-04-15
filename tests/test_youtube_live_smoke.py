from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scripts.youtube_live_smoke import _probe_failure
from autoresearch.core.services.youtube_errors import YouTubeAgentError
from autoresearch.shared.models import YouTubeFailedStage, YouTubeFailureKind


class _FakeModel:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def model_dump(self, *, mode: str = "json") -> dict[str, object]:
        assert mode == "json"
        return self._payload


class _FakeService:
    def __init__(self, *, error: YouTubeAgentError | None = None) -> None:
        self._error = error

    def subscribe(self, request) -> SimpleNamespace:
        return SimpleNamespace(subscription_id="ytsub_probe")

    def check_subscription(self, subscription_id: str, request) -> None:
        if self._error is not None:
            raise self._error

    def list_runs(self, *, subscription_id: str, kind) -> list[_FakeModel]:
        return [
            _FakeModel(
                {
                    "run_id": "ytrun_probe",
                    "failure_kind": "network_failure",
                    "failed_stage": "discovery",
                    "reason": "controlled connectivity probe failed",
                }
            )
        ]


def test_probe_failure_marks_missing_url_as_not_observed_live(tmp_path: Path) -> None:
    report: dict[str, object] = {}

    _probe_failure(
        report,
        db_path=tmp_path / "youtube-live-smoke.sqlite3",
        expected_kind=YouTubeFailureKind.NETWORK_FAILURE,
        url=None,
    )

    probe = report["failure_probes"][0]
    assert probe["probe_attempted"] is False
    assert probe["observation_status"] == "implemented_not_observed_live"
    assert probe["evidence"] == {}
    assert "No probe URL was provided" in probe["notes"][0]


def test_probe_failure_records_attempt_evidence_for_live_observation(tmp_path: Path) -> None:
    report: dict[str, object] = {}
    captured: dict[str, object] = {}

    def service_factory(
        db_path: Path,
        *,
        timeout_seconds: float = 120.0,
        fetcher_extra_args: list[str] | None = None,
    ) -> _FakeService:
        captured["db_path"] = db_path
        captured["timeout_seconds"] = timeout_seconds
        captured["fetcher_extra_args"] = fetcher_extra_args
        return _FakeService(
            error=YouTubeAgentError(
                YouTubeFailureKind.NETWORK_FAILURE,
                "failed to establish a new connection",
                retryable=True,
                failed_stage=YouTubeFailedStage.DISCOVERY,
            )
        )

    _probe_failure(
        report,
        db_path=tmp_path / "youtube-live-smoke.sqlite3",
        expected_kind=YouTubeFailureKind.NETWORK_FAILURE,
        url="https://www.youtube.com/watch?v=demo123",
        fetcher_extra_args=["--source-address", "203.0.113.1"],
        notes=["Connectivity probe uses a bind-address override for a single yt-dlp attempt."],
        service_factory=service_factory,
    )

    probe = report["failure_probes"][0]
    assert captured["fetcher_extra_args"] == ["--source-address", "203.0.113.1"]
    assert probe["probe_attempted"] is True
    assert probe["observation_status"] == "observed_live"
    assert probe["evidence"]["attempt"]["fetcher_extra_args"] == ["--source-address", "203.0.113.1"]
    assert probe["evidence"]["error"]["error_kind"] == "network_failure"
    assert probe["evidence"]["stored_run"]["failed_stage"] == "discovery"
