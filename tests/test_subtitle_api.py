from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from autoresearch.api.main import app as main_app
from autoresearch.api.routers import subtitle_offline
from subtitle_offline.contract import MediaJobContractSubtitle, SubtitleJobStatus, SubtitleOutputFormat
from autoresearch.shared.models import utc_now


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(subtitle_offline.router)
    return TestClient(app)


def _contract(*, title: str, output_path: str, status: SubtitleJobStatus = SubtitleJobStatus.DONE) -> MediaJobContractSubtitle:
    now = utc_now()
    return MediaJobContractSubtitle(
        url="offline-fixture",
        title=title,
        output_path=output_path,
        output_format=SubtitleOutputFormat.SRT,
        status=status,
        metadata={"stub": True},
        raw_subtitle_path=None,
        created_at=now,
        updated_at=now,
    )


def test_subtitle_offline_endpoint_returns_done_contract(monkeypatch, tmp_path: Path) -> None:
    def _fake_run_subtitle_job(*, raw_path: Path, output_dir: Path, output_format: SubtitleOutputFormat):
        assert raw_path == Path("tests/fixtures/subtitles/basic-webvtt.vtt")
        assert output_dir == tmp_path / "artifacts"
        assert output_format is SubtitleOutputFormat.TXT
        return _contract(title=raw_path.stem, output_path=(output_dir / "basic-webvtt_clean.txt").as_posix())

    monkeypatch.setattr(subtitle_offline, "run_subtitle_job", _fake_run_subtitle_job)

    with _build_client() as client:
        response = client.post(
            "/api/v1/subtitle/offline",
            json={
                "input_path": "tests/fixtures/subtitles/basic-webvtt.vtt",
                "output_dir": str(tmp_path / "artifacts"),
                "output_format": "txt",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "done"
    assert payload["title"] == "basic-webvtt"


def test_subtitle_online_endpoint_uses_fetch_subtitle(monkeypatch, tmp_path: Path) -> None:
    def _fake_fetch_subtitle(*, youtube_url: str, output_dir: str | Path, output_format: SubtitleOutputFormat, yt_dlp_bin: str):
        assert youtube_url == "https://www.youtube.com/watch?v=demo"
        assert Path(output_dir) == tmp_path / "artifacts"
        assert output_format is SubtitleOutputFormat.SRT
        assert yt_dlp_bin == "yt-dlp"
        return _contract(title="remote-demo", output_path=(Path(output_dir) / "remote-demo_clean.srt").as_posix())

    monkeypatch.setattr(subtitle_offline, "fetch_subtitle", _fake_fetch_subtitle)

    with _build_client() as client:
        response = client.post(
            "/api/v1/subtitle/online",
            json={
                "url": "https://www.youtube.com/watch?v=demo",
                "output_dir": str(tmp_path / "artifacts"),
                "output_format": "srt",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "done"
    assert payload["title"] == "remote-demo"


def test_main_app_mounts_subtitle_router() -> None:
    assert any(route.path == "/api/v1/subtitle/offline" for route in main_app.routes)
    assert any(route.path == "/api/v1/subtitle/online" for route in main_app.routes)
