from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from autoresearch.core.services.media_jobs import MediaJobService
from autoresearch.shared.media_job_contract import MediaJobMode, MediaJobRequest, MediaTargetBucket
from autoresearch.shared.store import InMemoryRepository


class _FakeRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        if "--dump-single-json" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout='{"title":"Demo","id":"abc123","uploader":"alice","duration":12}',
                stderr="",
            )

        output_template = command[command.index("-o") + 1]
        output_path = (
            output_template.replace("%(title)s", "Demo")
            .replace("%(id)s", "abc123")
            .replace("%(uploader)s", "alice")
            .replace("%(upload_date)s", "20260331")
            .replace("%(ext)s", "mp3" if "-x" in command else "mp4")
        )
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("media", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


def _service(tmp_path: Path, runner: _FakeRunner | None = None) -> MediaJobService:
    return MediaJobService(
        repository=InMemoryRepository(),
        event_repository=InMemoryRepository(),
        media_root=tmp_path / "media",
        allowed_domains={"youtube.com", "youtu.be", "bilibili.com"},
        command_runner=runner or _FakeRunner(),
    )


def test_media_job_service_parses_explicit_and_bare_urls(tmp_path: Path) -> None:
    service = _service(tmp_path)

    explicit = service.parse_telegram_task("audio https://youtu.be/demo")
    assert explicit is not None
    assert explicit.mode is MediaJobMode.AUDIO
    assert explicit.target_bucket is MediaTargetBucket.AUDIO

    bare = service.parse_telegram_task("https://www.youtube.com/watch?v=demo")
    assert bare is not None
    assert bare.mode is MediaJobMode.VIDEO

    assert service.parse_telegram_task("https://example.com/article") is None


def test_media_job_service_executes_with_whitelisted_template_and_writes_metadata(tmp_path: Path) -> None:
    runner = _FakeRunner()
    service = _service(tmp_path, runner=runner)
    job = service.create(
        MediaJobRequest(
            url="https://youtu.be/demo",
            mode=MediaJobMode.AUDIO,
            target_bucket=MediaTargetBucket.AUDIO,
            filename_template="{title}-{id}",
        )
    )

    completed = service.execute(job.job_id)

    assert completed.status.value == "completed"
    assert completed.title == "Demo"
    assert completed.uploader == "alice"
    assert completed.metadata_path is not None
    assert Path(completed.metadata_path).exists()
    assert completed.output_files
    assert Path(completed.output_files[0]).exists()
    assert len(runner.commands) == 2


def test_media_job_request_rejects_unapproved_template_tokens() -> None:
    with pytest.raises(ValueError):
        MediaJobRequest(
            url="https://youtu.be/demo",
            mode=MediaJobMode.VIDEO,
            target_bucket=MediaTargetBucket.VIDEO,
            filename_template="{title}-{badtoken}",
        )
