#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from autoresearch.core.repositories.youtube import SQLiteYouTubeRepository
from autoresearch.core.services.youtube_agent import YouTubeAgentService
from autoresearch.core.services.youtube_digest import YouTubeDigestService
from autoresearch.core.services.youtube_errors import YouTubeAgentError
from autoresearch.core.services.youtube_fetcher import YouTubeFetcher
from autoresearch.shared.models import (
    YouTubeDigestCreateRequest,
    YouTubeFailureKind,
    YouTubeQuestionRequest,
    YouTubeSubscriptionCheckRequest,
    YouTubeSubscriptionCreateRequest,
    YouTubeTranscriptCreateRequest,
)


def _run_step(summary: dict[str, Any], step_name: str, fn) -> Any:
    started = time.perf_counter()
    try:
        value = fn()
        duration_seconds = round(time.perf_counter() - started, 3)
        summary["steps"].append(
            {
                "step": step_name,
                "status": "ok",
                "duration_seconds": duration_seconds,
                "result": _json_ready(value),
            }
        )
        return value
    except YouTubeAgentError as exc:
        duration_seconds = round(time.perf_counter() - started, 3)
        summary["steps"].append(
            {
                "step": step_name,
                "status": "error",
                "duration_seconds": duration_seconds,
                "error_kind": exc.failure_kind.value,
                "failed_stage": exc.failed_stage.value if exc.failed_stage else None,
                "reason": exc.reason,
                "retryable": exc.retryable,
                "details": exc.details,
            }
        )
        raise


def _json_ready(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _target_summary(name: str, url: str) -> dict[str, Any]:
    return {
        "target": name,
        "url": url,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "steps": [],
    }


def _build_service(
    db_path: Path,
    *,
    timeout_seconds: float = 120.0,
    fetcher_extra_args: list[str] | None = None,
) -> YouTubeAgentService:
    return YouTubeAgentService(
        repository=SQLiteYouTubeRepository(db_path=db_path),
        repo_root=ROOT,
        fetcher=YouTubeFetcher(
            command_timeout_seconds=timeout_seconds,
            command_extra_args=fetcher_extra_args,
        ),
        digest_service=YouTubeDigestService(),
    )


def _set_observation_status(probe: dict[str, Any], status: str) -> None:
    probe["observation_status"] = status
    probe["status"] = status


def _probe_failure(
    report: dict[str, Any],
    *,
    db_path: Path,
    expected_kind: YouTubeFailureKind,
    url: str | None,
    timeout_seconds: float = 120.0,
    fetcher_extra_args: list[str] | None = None,
    notes: list[str] | None = None,
    service_factory: Callable[..., YouTubeAgentService] = _build_service,
) -> None:
    probe: dict[str, Any] = {
        "expected_error_kind": expected_kind.value,
        "url": url,
        "probe_attempted": False,
        "observation_status": "not_started",
        "evidence": {},
        "notes": list(notes or []),
    }
    report.setdefault("failure_probes", []).append(probe)

    if not url:
        _set_observation_status(probe, "implemented_not_observed_live")
        probe["reason"] = "no probe URL provided for this failure kind"
        probe["notes"].append("No probe URL was provided, so no live attempt was executed.")
        return

    probe["probe_attempted"] = True
    probe["evidence"]["attempt"] = {
        "timeout_seconds": timeout_seconds,
        "fetcher_extra_args": list(fetcher_extra_args or []),
    }
    service = service_factory(
        db_path,
        timeout_seconds=timeout_seconds,
        fetcher_extra_args=fetcher_extra_args,
    )
    started = time.perf_counter()
    subscription = service.subscribe(
        YouTubeSubscriptionCreateRequest(
            source_url=url,
            auto_fetch_transcript=False,
            auto_digest=False,
            metadata={"probe_failure_kind": expected_kind.value},
        )
    )
    probe["subscription_id"] = subscription.subscription_id
    probe["evidence"]["subscription"] = {
        "subscription_id": subscription.subscription_id,
        "source_url": url,
    }
    try:
        service.check_subscription(
            subscription.subscription_id,
            YouTubeSubscriptionCheckRequest(limit=1, metadata={"probe_failure_kind": expected_kind.value}),
        )
        _set_observation_status(probe, "implemented_not_observed_live")
        probe["reason"] = "probe completed without the expected failure"
        probe["notes"].append("A single live attempt completed without reproducing the target failure.")
    except YouTubeAgentError as exc:
        probe["duration_seconds"] = round(time.perf_counter() - started, 3)
        probe["observed_error_kind"] = exc.failure_kind.value
        probe["failed_stage"] = exc.failed_stage.value if exc.failed_stage else None
        probe["reason"] = exc.reason
        probe["retryable"] = exc.retryable
        probe["details"] = exc.details
        probe["evidence"]["error"] = {
            "error_kind": exc.failure_kind.value,
            "failed_stage": exc.failed_stage.value if exc.failed_stage else None,
            "reason": exc.reason,
            "retryable": exc.retryable,
            "details": exc.details,
        }
        _set_observation_status(
            probe,
            "observed_live" if exc.failure_kind == expected_kind else "observed_unexpected_failure",
        )
        latest_run = service.list_runs(
            subscription_id=subscription.subscription_id,
            kind=None,
        )
        if latest_run:
            probe["stored_run"] = _json_ready(latest_run[0])
            probe["evidence"]["stored_run"] = probe["stored_run"]
        return

    probe["duration_seconds"] = round(time.perf_counter() - started, 3)
    latest_run = service.list_runs(subscription_id=subscription.subscription_id, kind=None)
    if latest_run:
        probe["stored_run"] = _json_ready(latest_run[0])
        probe["evidence"]["stored_run"] = probe["stored_run"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a live YouTube smoke flow against real URLs.")
    parser.add_argument("--channel-url", required=True)
    parser.add_argument("--playlist-url", required=True)
    parser.add_argument("--video-url", required=True)
    parser.add_argument("--allow-live", action="store_true", help="Explicitly allow the live network smoke run.")
    parser.add_argument("--db-path", default=str((ROOT / "artifacts" / "youtube" / "youtube-live-smoke.sqlite3").resolve()))
    parser.add_argument("--output-dir", default=str((ROOT / "artifacts" / "youtube" / "live-smoke").resolve()))
    parser.add_argument("--question", default="What is this video mainly about?")
    parser.add_argument("--probe-video-unavailable-url")
    parser.add_argument("--probe-extractor-failure-url")
    parser.add_argument("--probe-network-url")
    parser.add_argument("--probe-network-bind-address", default="203.0.113.1")
    parser.add_argument("--probe-rate-limited-url")
    parser.add_argument("--probe-timeout-url")
    parser.add_argument("--probe-timeout-seconds", type=float, default=0.01)
    args = parser.parse_args()

    if not args.allow_live and os.getenv("AUTORESEARCH_YOUTUBE_LIVE") != "1":
        print("Refusing to run live smoke without --allow-live or AUTORESEARCH_YOUTUBE_LIVE=1", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    db_path = Path(args.db_path).resolve()
    repository = SQLiteYouTubeRepository(db_path=db_path)
    service = _build_service(db_path)

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db_path": str(Path(args.db_path).resolve()),
        "targets": [],
    }

    for target_name, url in [
        ("channel", args.channel_url),
        ("playlist", args.playlist_url),
        ("video", args.video_url),
    ]:
        summary = _target_summary(target_name, url)
        report["targets"].append(summary)
        digest_path: Path | None = None
        try:
            subscription = _run_step(
                summary,
                "create_subscription",
                lambda: service.subscribe(YouTubeSubscriptionCreateRequest(source_url=url)),
            )
            check_result = _run_step(
                summary,
                "manual_check",
                lambda: service.check_subscription(
                    subscription.subscription_id,
                    YouTubeSubscriptionCheckRequest(limit=3),
                ),
            )
            candidate_video_id = (
                (check_result.new_video_ids or check_result.discovered_video_ids or [None])[0]
            )
            if not candidate_video_id:
                raise YouTubeAgentError(
                    check_result.run.failure_kind or YouTubeFailureKind.NO_NEW_VIDEOS_FOUND,
                    check_result.run.reason or "manual check returned no candidate video id",
                )

            video = _run_step(
                summary,
                "fetch_metadata",
                lambda: service.refresh_video_metadata(candidate_video_id),
            )
            _run_step(
                summary,
                "fetch_transcript",
                lambda: service.fetch_transcript(
                    video.video_id,
                    YouTubeTranscriptCreateRequest(),
                ),
            )
            digest = _run_step(
                summary,
                "build_digest",
                lambda: service.generate_digest(
                    video.video_id,
                    YouTubeDigestCreateRequest(),
                ),
            )
            digest_path = output_dir / f"{target_name}-{video.video_id}.md"
            digest_path.write_text(digest.content, encoding="utf-8")
            summary["digest_path"] = str(digest_path)
            _run_step(
                summary,
                "ask",
                lambda: service.ask_video(
                    video.video_id,
                    YouTubeQuestionRequest(question=args.question),
                ),
            )
        except YouTubeAgentError:
            pass

        summary["objects"] = {
            "subscriptions": len(repository.list_subscriptions()),
            "videos": len(repository.list_videos()),
            "transcripts": len(repository.list_transcripts()),
            "digests": len(repository.list_digests()),
            "runs": len(repository.list_runs()),
        }
        summary["finished_at"] = datetime.now(timezone.utc).isoformat()

    _probe_failure(
        report,
        db_path=db_path,
        expected_kind=YouTubeFailureKind.VIDEO_UNAVAILABLE,
        url=args.probe_video_unavailable_url,
    )
    _probe_failure(
        report,
        db_path=db_path,
        expected_kind=YouTubeFailureKind.YT_DLP_EXTRACTOR_FAILURE,
        url=args.probe_extractor_failure_url,
    )
    _probe_failure(
        report,
        db_path=db_path,
        expected_kind=YouTubeFailureKind.NETWORK_FAILURE,
        url=args.probe_network_url,
        fetcher_extra_args=(
            ["--source-address", args.probe_network_bind_address]
            if args.probe_network_url
            else None
        ),
        notes=(
            [
                "Connectivity probe uses a bind-address override for a single yt-dlp attempt.",
                f"Configured bind address: {args.probe_network_bind_address}",
            ]
            if args.probe_network_url
            else None
        ),
    )
    _probe_failure(
        report,
        db_path=db_path,
        expected_kind=YouTubeFailureKind.RATE_LIMITED,
        url=args.probe_rate_limited_url,
        notes=[
            "Rate-limit probe is intentionally a single safe attempt.",
            "No retry loop is used to force or simulate rate limiting.",
        ],
    )
    _probe_failure(
        report,
        db_path=db_path,
        expected_kind=YouTubeFailureKind.TIMEOUT_FAILURE,
        url=args.probe_timeout_url,
        timeout_seconds=args.probe_timeout_seconds,
    )

    report_path = output_dir / f"live-smoke-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nreport_path={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
