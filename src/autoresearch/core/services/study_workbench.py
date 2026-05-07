from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import json
import re
import shlex
import sqlite3
import subprocess
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


class StudyWorkbenchError(RuntimeError):
    pass


@dataclass(slots=True)
class StudyWorkbenchService:
    settings: Any
    state_db_path: Path
    artifact_root: Path

    def __post_init__(self) -> None:
        self.state_db_path = self.state_db_path.expanduser().resolve()
        self.artifact_root = self.artifact_root.expanduser().resolve()
        self.state_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self._initialize_state()

    def health(self) -> dict[str, Any]:
        vault = self._vault_dir()
        git_repo = self._git_repo_dir()
        checks = {
            "obsidian_vault": _path_check(vault, expect_dir=True),
            "goodnotes_inbox": _path_check(self.settings.goodnotes_inbox_dir, expect_dir=True),
            "goodnotes_backup_dirs": [_path_check(path, expect_dir=True) for path in self.settings.goodnotes_backup_dirs],
            "marginnote_inbox": _path_check(self.settings.marginnote_inbox_dir, expect_dir=True),
            "marginnote_export_dirs": [_path_check(path, expect_dir=True) for path in self.settings.marginnote_export_dirs],
            "git_repo": {
                **_path_check(git_repo, expect_dir=True),
                "is_git_repo": bool(git_repo and (git_repo / ".git").exists()),
            },
            "ocr": {
                "configured": bool(str(self.settings.ocr_command or "").strip()),
                "available": self._ocr_available(),
            },
        }
        required_ok = checks["obsidian_vault"]["exists"] and checks["git_repo"]["is_git_repo"]
        any_inbox = checks["goodnotes_inbox"]["exists"] or checks["marginnote_inbox"]["exists"]
        any_ingest_dir = bool(
            any(item["exists"] for item in checks["goodnotes_backup_dirs"])
            or any(item["exists"] for item in checks["marginnote_export_dirs"])
        )
        status = "ok" if required_ok and (any_inbox or any_ingest_dir) else "degraded"
        return {
            "status": status,
            "checks": checks,
            "review_inbox_relative_dir": self.settings.review_inbox_relative_dir,
            "git_push_enabled": bool(self.settings.git_push_enabled),
        }

    def prepare(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(payload or {})
        items = self._prepare_items(payload)
        if not items:
            raise StudyWorkbenchError("study_prepare found no study items")

        prepared: list[dict[str, Any]] = []
        for item in items:
            title = _safe_title(str(item.get("title") or "Study Note"))
            markdown = str(item.get("markdown") or item.get("content") or "").strip()
            if not markdown and item.get("markdown_path"):
                markdown = self._read_markdown_path(str(item["markdown_path"]))
            if not markdown:
                raise StudyWorkbenchError(f"study item has no markdown content: {title}")

            pdf_path = self.artifact_root / "prepare" / f"{_slugify(title)}.pdf"
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            pdf_path.write_bytes(_minimal_pdf([title, "", *markdown.splitlines()[:80]]))

            targets = _normalize_targets(item.get("targets") or payload.get("targets"))
            copies = self._copy_prepared_pdf(pdf_path=pdf_path, title=title, targets=targets)
            prepared.append(
                {
                    "title": title,
                    "artifact_pdf_path": str(pdf_path),
                    "copies": copies,
                    "targets": targets,
                }
            )

        return {
            "status": "prepared",
            "prepared_count": len(prepared),
            "prepared": prepared,
        }

    def ingest(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(payload or {})
        candidates = self._ingest_candidates(payload)
        files_written: list[str] = []
        imported: list[dict[str, Any]] = []
        skipped: list[dict[str, str]] = []
        degraded: list[dict[str, str]] = []

        for candidate in candidates:
            fingerprint = _file_fingerprint(candidate.path)
            if self._fingerprint_seen(fingerprint):
                skipped.append({"path": str(candidate.path), "reason": "already_processed"})
                continue

            extracted = self._extract_candidate(candidate)
            if extracted.degraded_reason:
                degraded.append({"path": str(candidate.path), "reason": extracted.degraded_reason})
                continue
            if not extracted.markdown.strip():
                degraded.append({"path": str(candidate.path), "reason": "empty_extracted_text"})
                continue

            output_path = self._write_obsidian_review_note(
                source_path=candidate.path,
                source_kind=candidate.source_kind,
                markdown=extracted.markdown,
                title=extracted.title,
            )
            self._record_fingerprint(fingerprint, source_path=candidate.path, output_path=output_path)
            files_written.append(str(output_path))
            imported.append(
                {
                    "source_path": str(candidate.path),
                    "source_kind": candidate.source_kind,
                    "output_path": str(output_path),
                    "title": extracted.title,
                }
            )

        result: dict[str, Any] = {
            "status": "completed" if files_written else ("degraded" if degraded else "skipped"),
            "scanned_count": len(candidates),
            "imported_count": len(imported),
            "skipped_count": len(skipped),
            "degraded_count": len(degraded),
            "files_written": files_written,
            "imported": imported,
            "skipped": skipped,
            "degraded": degraded,
        }
        if files_written:
            result["enqueue_git_sync"] = True
            result["git_sync_payload"] = {
                "paths": files_written,
                "message": "chore(study): sync study workbench notes",
            }
        return result

    def git_sync(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(payload or {})
        repo = self._git_repo_dir()
        if repo is None:
            raise StudyWorkbenchError("AUTORESEARCH_STUDY_GIT_REPO_DIR or Obsidian vault is required")
        repo = repo.resolve()
        if not (repo / ".git").exists():
            return {
                "status": "degraded",
                "reason": f"not a git repository: {repo}",
                "repo": str(repo),
            }

        requested_paths = [str(item) for item in payload.get("paths") or payload.get("changed_paths") or []]
        if not requested_paths:
            requested_paths = self._default_git_sync_paths(repo)
        allowlisted = self._allowlisted_repo_paths(repo=repo, paths=requested_paths)
        if not allowlisted:
            return {"status": "skipped", "reason": "no allowlisted paths to sync", "repo": str(repo)}

        rel_paths = [str(path.relative_to(repo)) for path in allowlisted]
        _run_git(repo, ["add", "--", *rel_paths])
        diff = _run_git(repo, ["diff", "--cached", "--name-only", "--", *rel_paths])
        changed = [line.strip() for line in diff.stdout.splitlines() if line.strip()]
        if not changed:
            return {"status": "skipped", "reason": "no changes to commit", "repo": str(repo), "paths": rel_paths}

        message = str(payload.get("message") or "chore(study): sync study workbench notes").strip()
        commit = _run_git(
            repo,
            [
                "-c",
                "user.name=AAS Study Workbench",
                "-c",
                "user.email=aas-study-workbench@users.noreply.github.com",
                "commit",
                "-m",
                message,
                "--",
                *rel_paths,
            ],
        )
        commit_sha = _run_git(repo, ["rev-parse", "HEAD"]).stdout.strip()
        pushed = False
        if bool(self.settings.git_push_enabled):
            _run_git(repo, ["push"])
            pushed = True
        return {
            "status": "completed",
            "repo": str(repo),
            "paths": changed,
            "commit_sha": commit_sha,
            "commit_stdout": commit.stdout.strip()[:2000],
            "pushed": pushed,
        }

    def _prepare_items(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        if isinstance(payload.get("items"), list):
            return [dict(item) for item in payload["items"] if isinstance(item, dict)]
        if payload.get("markdown_text") or payload.get("markdown") or payload.get("markdown_path"):
            return [
                {
                    "title": payload.get("title") or "Study Note",
                    "markdown": payload.get("markdown_text") or payload.get("markdown") or "",
                    "markdown_path": payload.get("markdown_path") or "",
                    "targets": payload.get("targets") or ["goodnotes", "marginnote"],
                }
            ]
        queue_path = self._vault_required() / "study" / "queue.json"
        if not queue_path.exists():
            return []
        raw = json.loads(queue_path.read_text(encoding="utf-8"))
        items = raw.get("items") if isinstance(raw, dict) else raw
        if not isinstance(items, list):
            return []
        limit = max(1, int(payload.get("limit") or 10))
        return [dict(item) for item in items[:limit] if isinstance(item, dict) and item.get("enabled", True)]

    def _read_markdown_path(self, raw_path: str) -> str:
        vault = self._vault_dir()
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            candidate = self._vault_required() / candidate
        candidate = candidate.resolve()
        if vault is not None and not _is_relative_to(candidate, vault):
            raise StudyWorkbenchError(f"markdown_path must stay inside the Obsidian vault: {candidate}")
        if not candidate.exists():
            raise StudyWorkbenchError(f"markdown_path not found: {candidate}")
        return candidate.read_text(encoding="utf-8")

    def _copy_prepared_pdf(self, *, pdf_path: Path, title: str, targets: list[str]) -> list[dict[str, str]]:
        copies: list[dict[str, str]] = []
        target_dirs: list[tuple[str, Path | None]] = [
            ("goodnotes", self.settings.goodnotes_inbox_dir),
            ("marginnote", self.settings.marginnote_inbox_dir),
        ]
        for target_name, inbox_dir in target_dirs:
            if target_name not in targets or inbox_dir is None:
                continue
            inbox = Path(inbox_dir).expanduser().resolve()
            inbox.mkdir(parents=True, exist_ok=True)
            destination = inbox / f"{_slugify(title)}.pdf"
            destination.write_bytes(pdf_path.read_bytes())
            copies.append({"target": target_name, "path": str(destination)})
        return copies

    def _ingest_candidates(self, payload: dict[str, Any]) -> list[IngestCandidate]:
        explicit = payload.get("sources") or payload.get("paths")
        if explicit:
            source_kind = str(payload.get("source_kind") or "goodnotes").strip() or "goodnotes"
            return [
                IngestCandidate(path=Path(str(item)).expanduser().resolve(), source_kind=source_kind)
                for item in explicit
            ]

        candidates: list[IngestCandidate] = []
        candidates.extend(self._scan_dirs(self.settings.goodnotes_backup_dirs, source_kind="goodnotes"))
        candidates.extend(self._scan_dirs(self.settings.marginnote_export_dirs, source_kind="marginnote"))
        return sorted(candidates, key=lambda item: str(item.path))

    def _scan_dirs(self, dirs: list[Path], *, source_kind: str) -> list[IngestCandidate]:
        extensions = {".pdf", ".md", ".txt"} if source_kind == "goodnotes" else {".md", ".txt", ".html", ".htm", ".opml"}
        candidates: list[IngestCandidate] = []
        for root in dirs:
            root_path = Path(root).expanduser().resolve()
            if not root_path.exists() or not root_path.is_dir():
                continue
            for path in root_path.rglob("*"):
                if path.is_file() and path.suffix.lower() in extensions:
                    if source_kind == "goodnotes" and path.suffix.lower() in {".md", ".txt"}:
                        if path.with_suffix(".pdf").exists():
                            continue
                    candidates.append(IngestCandidate(path=path.resolve(), source_kind=source_kind))
        return candidates

    def _extract_candidate(self, candidate: IngestCandidate) -> ExtractedStudyNote:
        suffix = candidate.path.suffix.lower()
        title = _safe_title(candidate.path.stem)
        if suffix in {".md", ".txt"}:
            return ExtractedStudyNote(title=title, markdown=_clean_markdown(candidate.path.read_text(encoding="utf-8")))
        if suffix in {".html", ".htm"}:
            return ExtractedStudyNote(title=title, markdown=_html_to_markdown(candidate.path.read_text(encoding="utf-8")))
        if suffix == ".opml":
            return ExtractedStudyNote(title=title, markdown=_opml_to_markdown(candidate.path.read_text(encoding="utf-8")))
        if suffix == ".pdf":
            sidecar = _find_sidecar_text(candidate.path)
            if sidecar is not None:
                return ExtractedStudyNote(title=title, markdown=_clean_markdown(sidecar.read_text(encoding="utf-8")))
            ocr = self._run_ocr(candidate.path)
            if ocr:
                return ExtractedStudyNote(title=title, markdown=_clean_markdown(ocr))
            return ExtractedStudyNote(title=title, markdown="", degraded_reason="ocr_unavailable")
        return ExtractedStudyNote(title=title, markdown="", degraded_reason="unsupported_extension")

    def _write_obsidian_review_note(
        self,
        *,
        source_path: Path,
        source_kind: str,
        markdown: str,
        title: str,
    ) -> Path:
        vault = self._vault_required()
        review_root = self._review_root(vault)
        day_dir = review_root / datetime.now(timezone.utc).date().isoformat()
        day_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(str(source_path).encode("utf-8")).hexdigest()[:10]
        output_path = (day_dir / f"{source_kind}-{_slugify(title)}-{digest}.md").resolve()
        if not _is_relative_to(output_path, review_root):
            raise StudyWorkbenchError("review note path escaped the review inbox")
        body = [
            "---",
            f"title: {json.dumps(title, ensure_ascii=False)}",
            f"source_kind: {source_kind}",
            f"source_path: {json.dumps(str(source_path), ensure_ascii=False)}",
            f"imported_at: {datetime.now(timezone.utc).isoformat()}",
            "---",
            "",
            markdown.strip(),
            "",
        ]
        output_path.write_text("\n".join(body), encoding="utf-8")
        return output_path

    def _default_git_sync_paths(self, repo: Path) -> list[str]:
        review_root = self._review_root(repo)
        if not review_root.exists():
            return []
        return [str(path) for path in review_root.rglob("*.md") if path.is_file()]

    def _allowlisted_repo_paths(self, *, repo: Path, paths: list[str]) -> list[Path]:
        review_root = self._review_root(repo)
        allowlisted: list[Path] = []
        for raw_path in paths:
            path = Path(raw_path).expanduser()
            if not path.is_absolute():
                path = repo / path
            resolved = path.resolve()
            if not _is_relative_to(resolved, repo):
                raise StudyWorkbenchError(f"git sync path is outside repo: {resolved}")
            if not _is_relative_to(resolved, review_root):
                raise StudyWorkbenchError(f"git sync path is outside review inbox: {resolved}")
            if resolved.exists():
                allowlisted.append(resolved)
        return allowlisted

    def _review_root(self, vault_or_repo: Path) -> Path:
        relative = Path(str(self.settings.review_inbox_relative_dir or "inbox_review"))
        if relative == Path(".") or relative.is_absolute() or ".." in relative.parts:
            raise StudyWorkbenchError("review inbox relative dir must be a safe relative path")
        return (vault_or_repo / relative).resolve()

    def _vault_dir(self) -> Path | None:
        raw = self.settings.obsidian_vault_dir
        return Path(raw).expanduser().resolve() if raw else None

    def _vault_required(self) -> Path:
        vault = self._vault_dir()
        if vault is None:
            raise StudyWorkbenchError("AUTORESEARCH_STUDY_OBSIDIAN_VAULT_DIR is required")
        return vault

    def _git_repo_dir(self) -> Path | None:
        raw = self.settings.git_repo_dir or self.settings.obsidian_vault_dir
        return Path(raw).expanduser().resolve() if raw else None

    def _ocr_available(self) -> bool:
        command = str(self.settings.ocr_command or "").strip()
        if not command:
            return False
        executable = shlex.split(command)[0]
        return bool(_which(executable))

    def _run_ocr(self, pdf_path: Path) -> str:
        command = str(self.settings.ocr_command or "").strip()
        if not command:
            return ""
        args = [*shlex.split(command), str(pdf_path)]
        try:
            completed = subprocess.run(args, capture_output=True, check=False, text=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired):
            return ""
        if completed.returncode != 0:
            return ""
        return completed.stdout.strip()

    def _initialize_state(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS study_workbench_fingerprints (
                    fingerprint TEXT PRIMARY KEY,
                    source_path TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    processed_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def _fingerprint_seen(self, fingerprint: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT fingerprint FROM study_workbench_fingerprints WHERE fingerprint = ?",
                (fingerprint,),
            ).fetchone()
        return row is not None

    def _record_fingerprint(self, fingerprint: str, *, source_path: Path, output_path: Path) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO study_workbench_fingerprints (
                    fingerprint,
                    source_path,
                    output_path,
                    processed_at
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    fingerprint,
                    str(source_path),
                    str(output_path),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.state_db_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection


@dataclass(frozen=True, slots=True)
class IngestCandidate:
    path: Path
    source_kind: str


@dataclass(frozen=True, slots=True)
class ExtractedStudyNote:
    title: str
    markdown: str
    degraded_reason: str | None = None


def _path_check(path: Path | None, *, expect_dir: bool) -> dict[str, Any]:
    if path is None:
        return {"configured": False, "exists": False, "path": None}
    resolved = Path(path).expanduser().resolve()
    return {
        "configured": True,
        "exists": resolved.exists() and (resolved.is_dir() if expect_dir else resolved.is_file()),
        "path": str(resolved),
    }


def _normalize_targets(value: Any) -> list[str]:
    if value is None:
        return ["goodnotes", "marginnote"]
    if isinstance(value, str):
        items = [item.strip().lower() for item in value.split(",")]
    else:
        items = [str(item).strip().lower() for item in value]
    targets = [item for item in items if item in {"goodnotes", "marginnote"}]
    return targets or ["goodnotes", "marginnote"]


def _safe_title(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    return normalized[:120] or "Study Note"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-")
    return slug[:80] or "study-note"


def _file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(str(path.resolve()).encode("utf-8"))
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_sidecar_text(pdf_path: Path) -> Path | None:
    for suffix in (".md", ".txt"):
        sidecar = pdf_path.with_suffix(suffix)
        if sidecar.exists() and sidecar.is_file():
            return sidecar
    return None


def _clean_markdown(value: str) -> str:
    lines = [line.rstrip() for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    compact: list[str] = []
    blank = False
    for line in lines:
        if not line.strip():
            if not blank:
                compact.append("")
            blank = True
            continue
        compact.append(line)
        blank = False
    return "\n".join(compact).strip()


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"p", "br", "li", "div", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def markdown(self) -> str:
        return _clean_markdown(" ".join(self.parts).replace("\n ", "\n"))


def _html_to_markdown(value: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(value)
    return parser.markdown()


def _opml_to_markdown(value: str) -> str:
    root = ET.fromstring(value)
    lines: list[str] = []

    def visit(node: ET.Element, depth: int = 0) -> None:
        text = str(node.attrib.get("text") or node.attrib.get("title") or "").strip()
        if text:
            lines.append(f"{'  ' * depth}- {text}")
        for child in list(node):
            if child.tag.lower().endswith("outline"):
                visit(child, depth + (1 if text else 0))

    body = root.find(".//body")
    start_nodes = list(body) if body is not None else list(root)
    for child in start_nodes:
        if child.tag.lower().endswith("outline"):
            visit(child, 0)
    return _clean_markdown("\n".join(lines))


def _minimal_pdf(lines: list[str]) -> bytes:
    escaped = [_pdf_text(line[:120]) for line in lines[:90]]
    text_ops = []
    y = 760
    for line in escaped:
        text_ops.append(f"BT /F1 10 Tf 50 {y} Td ({line}) Tj ET")
        y -= 14
    stream = "\n".join(text_ops).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{idx} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"
    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    pdf += b"0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode("ascii")
    pdf += (
        b"trailer\n"
        + f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii")
        + b"startxref\n"
        + str(xref_offset).encode("ascii")
        + b"\n%%EOF\n"
    )
    return pdf


def _pdf_text(value: str) -> str:
    cleaned = value.encode("latin-1", errors="replace").decode("latin-1")
    return cleaned.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _which(executable: str) -> str | None:
    if "/" in executable:
        return executable if Path(executable).exists() else None
    completed = subprocess.run(["/usr/bin/which", executable], capture_output=True, check=False, text=True)
    return completed.stdout.strip() if completed.returncode == 0 else None


def _run_git(cwd: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=False, text=True)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "git command failed").strip()
        raise StudyWorkbenchError(detail)
    return completed
