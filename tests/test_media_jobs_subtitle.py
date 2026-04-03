from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from autoresearch.core.services.media_jobs_subtitle import (
    MacSubtitleJobService,
    clean_subtitle_file,
    run_subtitle_job,
)
from autoresearch.shared.media_job_contract_subtitle import (
    MediaJobContractSubtitle,
    SubtitleJobStatus,
    SubtitleOutputFormat,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "subtitles"
FIXTURE_FILES = sorted(path for path in FIXTURE_DIR.iterdir() if path.is_file())


class _FakeSubtitleRunner:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        if "--dump-single-json" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout='{"title":"Demo Clip","id":"abc123","duration":42,"automatic_captions":{"en":[{"ext":"vtt"}],"zh-Hant":[{"ext":"vtt"}]}}',
                stderr="",
            )

        subtitle_path = self.output_dir / "Demo Clip-abc123.en.srt"
        subtitle_path.parent.mkdir(parents=True, exist_ok=True)
        subtitle_path.write_text(
            "1\n 00:00:00,000 --> 00:00:01,000 \n Hello world \n\n\n2\n00:00:01,500 --> 00:00:02,000\n Again \n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


class _PartialSuccessSubtitleRunner(_FakeSubtitleRunner):
    def __call__(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        if "--dump-single-json" in command:
            return super().__call__(command)
        output_template = self.output_dir / "Demo Clip-abc123.en.srt"
        output_template.parent.mkdir(parents=True, exist_ok=True)
        output_template.write_text(
            "1\n00:00:00,000 --> 00:00:01,000\nRecovered subtitle\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(
            command,
            1,
            stdout="",
            stderr="ERROR: Unable to download video subtitles for 'ab-en': HTTP Error 429: Too Many Requests",
        )


def test_fixture_inventory_contains_seven_samples() -> None:
    assert len(FIXTURE_FILES) == 7


@pytest.mark.parametrize("fixture_file", FIXTURE_FILES, ids=lambda path: path.name)
def test_run_subtitle_job_offline_fixture_to_srt(fixture_file: Path, tmp_path: Path) -> None:
    job = run_subtitle_job(fixture_file, tmp_path / "out", output_format=SubtitleOutputFormat.SRT)

    assert isinstance(job, MediaJobContractSubtitle)
    assert job.status is SubtitleJobStatus.DONE
    assert job.url == "offline-fixture"
    assert job.title == fixture_file.stem
    assert job.metadata == {
        "source_kind": "offline-fixture",
        "fixture_name": fixture_file.name,
        "duration_seconds": None,
        "language": None,
        "lang_tracks": [],
    }
    output_path = Path(job.output_path)
    assert output_path.exists()
    assert output_path.suffix == ".srt"
    assert output_path.read_text(encoding="utf-8").strip() != ""


@pytest.mark.parametrize("fixture_file", FIXTURE_FILES, ids=lambda path: path.name)
def test_run_subtitle_job_offline_fixture_to_txt(fixture_file: Path, tmp_path: Path) -> None:
    job = run_subtitle_job(fixture_file, tmp_path / "out", output_format=SubtitleOutputFormat.TXT)

    assert job.status is SubtitleJobStatus.DONE
    output_path = Path(job.output_path)
    content = output_path.read_text(encoding="utf-8")
    assert output_path.suffix == ".txt"
    assert content.strip() != ""
    assert "-->" not in content
    assert "WEBVTT" not in content


def test_clean_subtitle_file_normalizes_srt_blocks(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.srt"
    raw_path.write_text(
        "1\n 00:00:00,000 --> 00:00:01,000 \n Hello world \n\n\n2\n00:00:01,500 --> 00:00:02,000\n Again \n",
        encoding="utf-8",
    )

    out_path = tmp_path / "raw_clean.srt"
    clean_subtitle_file(raw_path, out_path, output_format=SubtitleOutputFormat.SRT)

    assert out_path.read_text(encoding="utf-8") == (
        "1\n00:00:00,000 --> 00:00:01,000\nHello world\n\n"
        "2\n00:00:01,500 --> 00:00:02,000\nAgain\n"
    )


def test_clean_subtitle_file_can_emit_plain_text(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.vtt"
    raw_path.write_text(
        "WEBVTT\n\ncaption-1\n00:00:00.000 --> 00:00:01.000 align:start\nHello world\n",
        encoding="utf-8",
    )

    out_path = tmp_path / "raw_clean.txt"
    clean_subtitle_file(raw_path, out_path, output_format=SubtitleOutputFormat.TXT)

    assert out_path.read_text(encoding="utf-8") == "Hello world\n"


def test_fetch_subtitle_returns_done_contract_with_clean_path(tmp_path: Path) -> None:
    output_dir = tmp_path / "subtitles"
    runner = _FakeSubtitleRunner(output_dir)
    service = MacSubtitleJobService(command_runner=runner)

    result = service.fetch_subtitle("https://www.youtube.com/watch?v=demo", output_dir)

    assert result.status is SubtitleJobStatus.DONE
    assert result.title == "Demo Clip"
    assert result.metadata == {
        "source_kind": "yt-dlp",
        "video_id": "abc123",
        "duration_seconds": 42,
        "language": "en",
        "lang_tracks": ["en", "zh-Hant"],
    }
    assert result.raw_subtitle_path is not None
    assert Path(result.raw_subtitle_path).exists()
    assert Path(result.output_path).exists()
    assert Path(result.output_path).name.endswith("_clean.srt")
    assert len(runner.commands) == 2


def test_fetch_subtitle_fails_for_unsupported_domain(tmp_path: Path) -> None:
    service = MacSubtitleJobService()

    result = service.fetch_subtitle("https://example.com/video", tmp_path)

    assert result.status is SubtitleJobStatus.FAILED
    assert result.error is not None
    assert "allowlist" in result.error


def test_fetch_subtitle_tolerates_partial_ytdlp_success_when_srt_exists(tmp_path: Path) -> None:
    output_dir = tmp_path / "subtitles"
    runner = _PartialSuccessSubtitleRunner(output_dir)
    service = MacSubtitleJobService(command_runner=runner)

    result = service.fetch_subtitle("https://www.youtube.com/watch?v=demo", output_dir)

    assert result.status is SubtitleJobStatus.DONE
    assert result.output_path
    assert Path(result.output_path).exists()
    assert result.metadata == {
        "source_kind": "yt-dlp",
        "video_id": "abc123",
        "duration_seconds": 42,
        "language": "en",
        "lang_tracks": ["en", "zh-Hant"],
        "download_warning": "ERROR: Unable to download video subtitles for 'ab-en': HTTP Error 429: Too Many Requests",
    }


def test_fetch_subtitle_prefers_downloaded_track_language_over_video_language(tmp_path: Path) -> None:
    class _MismatchedLanguageRunner(_FakeSubtitleRunner):
        def __call__(self, command: list[str]) -> subprocess.CompletedProcess[str]:
            if "--dump-single-json" in command:
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout='{"title":"Demo Clip","id":"abc123","duration":42,"language":"zh-Hant","automatic_captions":{"en":[{"ext":"vtt"}],"zh-Hant":[{"ext":"vtt"}]}}',
                    stderr="",
                )
            subtitle_path = self.output_dir / "Demo Clip-abc123.en.srt"
            subtitle_path.parent.mkdir(parents=True, exist_ok=True)
            subtitle_path.write_text(
                "1\n00:00:00,000 --> 00:00:01,000\nRecovered subtitle\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    output_dir = tmp_path / "subtitles"
    service = MacSubtitleJobService(command_runner=_MismatchedLanguageRunner(output_dir))

    result = service.fetch_subtitle("https://www.youtube.com/watch?v=demo", output_dir)

    assert result.status is SubtitleJobStatus.DONE
    assert result.metadata["language"] == "en"
    assert result.metadata["lang_tracks"] == ["en", "zh-Hant"]
