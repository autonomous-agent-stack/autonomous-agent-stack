from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Callable
from urllib.parse import urlparse

from autoresearch.shared.media_job_contract import (
    MediaJobEventRead,
    MediaJobMode,
    MediaJobPostprocess,
    MediaJobRead,
    MediaJobRequest,
    MediaJobStatus,
    MediaTargetBucket,
)
from autoresearch.shared.models import utc_now
from autoresearch.shared.store import Repository, create_resource_id

_TOKEN_TO_YTDLP = {
    "{title}": "%(title)s",
    "{id}": "%(id)s",
    "{uploader}": "%(uploader)s",
    "{upload_date}": "%(upload_date)s",
}
_URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)


class MediaJobService:
    def __init__(
        self,
        *,
        repository: Repository[MediaJobRead],
        event_repository: Repository[MediaJobEventRead],
        media_root: Path,
        allowed_domains: set[str],
        yt_dlp_bin: str = "yt-dlp",
        ffmpeg_bin: str = "ffmpeg",
        command_runner: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self._repository = repository
        self._event_repository = event_repository
        self._media_root = media_root
        self._allowed_domains = {item.lower().strip() for item in allowed_domains if item.strip()}
        self._yt_dlp_bin = yt_dlp_bin
        self._ffmpeg_bin = ffmpeg_bin
        self._command_runner = command_runner or self._run_command

    def create(self, request: MediaJobRequest) -> MediaJobRead:
        now = utc_now()
        job = MediaJobRead(
            job_id=create_resource_id("mediajob"),
            url=request.url,
            mode=request.mode,
            target_bucket=request.target_bucket,
            filename_template=request.filename_template,
            postprocess=request.postprocess,
            status=MediaJobStatus.QUEUED,
            created_at=now,
            updated_at=now,
            metadata=request.metadata,
        )
        self._ensure_directories()
        self._record_event(job_id=job.job_id, stage="created", status=job.status.value, detail=request.url)
        return self._repository.save(job.job_id, job)

    def get(self, job_id: str) -> MediaJobRead | None:
        return self._repository.get(job_id)

    def list(self) -> list[MediaJobRead]:
        return self._repository.list()

    def execute(self, job_id: str) -> MediaJobRead:
        job = self._require_job(job_id)
        running = job.model_copy(update={"status": MediaJobStatus.RUNNING, "updated_at": utc_now(), "error": None})
        self._repository.save(running.job_id, running)
        self._record_event(job_id=job.job_id, stage="running", status="running", detail=job.mode.value)

        try:
            metadata = self._probe_metadata(running.url)
            output_files = self._execute_job(running=running, metadata=metadata)
            completed = running.model_copy(
                update={
                    "status": MediaJobStatus.COMPLETED,
                    "updated_at": utc_now(),
                    "output_files": output_files,
                    "title": metadata.get("title"),
                    "duration_seconds": self._coerce_int(metadata.get("duration")),
                    "uploader": metadata.get("uploader"),
                    "subtitle_path": self._find_suffix(output_files, {".srt", ".vtt"}),
                    "metadata_path": self._metadata_path_for_job(running).as_posix(),
                    "error": None,
                }
            )
            self._write_metadata_file(completed=completed, metadata=metadata)
            self._record_event(job_id=job.job_id, stage="completed", status="completed", detail="ok")
            return self._repository.save(completed.job_id, completed)
        except Exception as exc:
            failed = running.model_copy(
                update={"status": MediaJobStatus.FAILED, "updated_at": utc_now(), "error": str(exc)}
            )
            self._record_event(job_id=job.job_id, stage="failed", status="failed", detail=str(exc))
            return self._repository.save(failed.job_id, failed)

    def parse_telegram_task(self, text: str) -> MediaJobRequest | None:
        normalized = text.strip()
        if not normalized:
            return None
        parts = normalized.split(maxsplit=1)
        explicit_mode = None
        url = normalized
        if len(parts) == 2 and parts[0].lower() in {"video", "audio", "subtitle", "metadata"}:
            explicit_mode = MediaJobMode(parts[0].lower())
            url = parts[1].strip()
        if not _URL_RE.match(url):
            return None
        if explicit_mode is None and not self.is_supported_url(url):
            return None
        mode = explicit_mode or MediaJobMode.VIDEO
        bucket = {
            MediaJobMode.AUDIO: MediaTargetBucket.AUDIO,
            MediaJobMode.VIDEO: MediaTargetBucket.VIDEO,
            MediaJobMode.SUBTITLE: MediaTargetBucket.SUBTITLES,
            MediaJobMode.METADATA: MediaTargetBucket.META,
        }[mode]
        postprocess = {
            MediaJobMode.AUDIO: MediaJobPostprocess.MP3,
            MediaJobMode.VIDEO: MediaJobPostprocess.MP4,
            MediaJobMode.SUBTITLE: MediaJobPostprocess.NONE,
            MediaJobMode.METADATA: MediaJobPostprocess.NONE,
        }[mode]
        return MediaJobRequest(
            url=url,
            mode=mode,
            target_bucket=bucket,
            filename_template="{title}-{id}",
            postprocess=postprocess,
        )

    def is_supported_url(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return any(host == domain or host.endswith(f".{domain}") for domain in self._allowed_domains)

    def _execute_job(self, *, running: MediaJobRead, metadata: dict[str, object]) -> list[str]:
        output_dir = self._bucket_dir(running.target_bucket)
        output_template = output_dir / f"{self._translate_template(running.filename_template)}.%(ext)s"
        commands = self._build_commands(running=running, output_template=output_template)
        for command in commands:
            result = self._command_runner(command)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "media command failed")

        output_files = sorted(path.as_posix() for path in output_dir.glob("*") if path.is_file())
        if running.mode is MediaJobMode.METADATA:
            output_files = []
        return output_files

    def _build_commands(self, *, running: MediaJobRead, output_template: Path) -> list[list[str]]:
        url = running.url
        template = output_template.as_posix()
        if running.mode is MediaJobMode.AUDIO:
            return [[self._yt_dlp_bin, "-x", "--audio-format", "mp3", "-o", template, url]]
        if running.mode is MediaJobMode.VIDEO:
            return [[self._yt_dlp_bin, "-f", "mp4/best", "-o", template, url]]
        if running.mode is MediaJobMode.SUBTITLE:
            return [[self._yt_dlp_bin, "--skip-download", "--write-auto-sub", "--write-sub", "--sub-langs", "all", "-o", template, url]]
        if running.mode is MediaJobMode.METADATA:
            return []
        raise ValueError(f"unsupported media mode: {running.mode}")

    def _probe_metadata(self, url: str) -> dict[str, object]:
        result = self._command_runner([self._yt_dlp_bin, "--dump-single-json", "--skip-download", url])
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "failed to probe media metadata")
        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError("invalid media metadata payload") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("invalid media metadata payload")
        return payload

    def _write_metadata_file(self, *, completed: MediaJobRead, metadata: dict[str, object]) -> None:
        metadata_path = self._metadata_path_for_job(completed)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    def _metadata_path_for_job(self, job: MediaJobRead) -> Path:
        return self._bucket_dir(MediaTargetBucket.META) / f"{job.job_id}.json"

    def _record_event(self, *, job_id: str, stage: str, status: str, detail: str) -> None:
        event = MediaJobEventRead(
            event_id=create_resource_id("mediaevt"),
            job_id=job_id,
            stage=stage,
            status=status,
            detail=detail,
            created_at=utc_now(),
        )
        self._event_repository.save(event.event_id, event)

    def _bucket_dir(self, bucket: MediaTargetBucket) -> Path:
        return self._media_root / bucket.value

    def _ensure_directories(self) -> None:
        for bucket in MediaTargetBucket:
            (self._media_root / bucket.value).mkdir(parents=True, exist_ok=True)
        (self._media_root / "jobs").mkdir(parents=True, exist_ok=True)

    def _translate_template(self, template: str) -> str:
        return "-".join(_TOKEN_TO_YTDLP[token] for token in template.split("-"))

    @staticmethod
    def _find_suffix(paths: list[str], suffixes: set[str]) -> str | None:
        for path in paths:
            if Path(path).suffix.lower() in suffixes:
                return path
        return None

    @staticmethod
    def _coerce_int(value: object) -> int | None:
        try:
            if value is None:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    def _require_job(self, job_id: str) -> MediaJobRead:
        job = self.get(job_id)
        if job is None:
            raise KeyError(f"media job not found: {job_id}")
        return job

    @staticmethod
    def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, text=True, capture_output=True, check=False)
