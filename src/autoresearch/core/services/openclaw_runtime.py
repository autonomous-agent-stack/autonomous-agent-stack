from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bridge.api import BridgeAPI

from autoresearch.agent_protocol.models import ExecutionPolicy, JobSpec
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.shared.models import OpenClawSessionEventAppendRequest
from autoresearch.shared.openclaw_runtime_contract import (
    OpenClawRuntimeJobSpec,
    OpenClawRuntimeResult,
)


class OpenClawRuntimeContractError(ValueError):
    """Raised when the runtime request is invalid or cannot be routed safely."""


class OpenClawRuntimeExecutionError(RuntimeError):
    """Raised when a resolved runtime action fails during execution."""


@dataclass(frozen=True)
class ResolvedOpenClawSkill:
    skill_dir: Path
    manifest_path: Path
    manifest: dict[str, Any]
    matched_by: str


class OpenClawRuntimeService:
    def __init__(
        self,
        *,
        repo_root: Path,
        workspace_root: Path,
        openclaw_service: OpenClawCompatService,
    ) -> None:
        self._repo_root = repo_root.resolve()
        self._workspace_root = workspace_root.resolve()
        self._openclaw_service = openclaw_service
        self._bridge = BridgeAPI(
            skill_base_path=self._workspace_root,
            enable_security_scan=True,
        )

    def build_agent_job_spec(self, spec: OpenClawRuntimeJobSpec) -> JobSpec:
        return JobSpec(
            run_id=spec.job_id,
            agent_id="openclaw_runtime",
            mode="runtime_only",
            task=f"OpenClaw runtime action: {spec.action}",
            policy=ExecutionPolicy(
                allowed_paths=[],
                max_changed_files=0,
                max_patch_lines=0,
                cleanup_on_success=True,
                retain_workspace_on_failure=True,
            ),
            metadata={
                "model_provider": "openclaw_runtime",
                "runtime_action": spec.action,
                "openclaw_runtime": spec.model_dump(mode="json"),
            },
        )

    async def execute(self, spec: OpenClawRuntimeJobSpec) -> OpenClawRuntimeResult:
        self._require_session(spec.session_id)
        if spec.action == "send_message":
            return self._send_message(spec)
        if spec.action == "run_skill":
            return await self._run_skill(spec)
        raise OpenClawRuntimeContractError(f"unsupported runtime action: {spec.action}")

    def _send_message(self, spec: OpenClawRuntimeJobSpec) -> OpenClawRuntimeResult:
        updated = self._openclaw_service.append_event(
            spec.session_id,
            OpenClawSessionEventAppendRequest(
                role=spec.role,
                content=spec.content or "",
                metadata={
                    **dict(spec.metadata),
                    "openclaw_runtime": {
                        "action": spec.action,
                        "job_id": spec.job_id,
                    },
                },
            ),
        )
        event = dict(updated.events[-1])
        return OpenClawRuntimeResult(
            job_id=spec.job_id,
            action=spec.action,
            session_id=spec.session_id,
            summary="session event appended",
            event_id=str(event.get("event_id") or ""),
            result=event,
            metadata={"event_count": len(updated.events)},
        )

    async def _run_skill(self, spec: OpenClawRuntimeJobSpec) -> OpenClawRuntimeResult:
        resolved_skill = self._resolve_skill(spec.skill_id or "")
        entry_path = self._resolve_entry_point(resolved_skill)
        skill = await self._load_skill(entry_path)
        result = await self._execute_skill(
            skill=skill,
            payload=spec.input if spec.input is not None else {},
            credentials=spec.credentials,
        )

        status_event = self._openclaw_service.append_event(
            spec.session_id,
            OpenClawSessionEventAppendRequest(
                role="status",
                content=f"runtime skill completed: {resolved_skill.manifest.get('id') or resolved_skill.skill_dir.name}",
                metadata={
                    "openclaw_runtime": {
                        "action": spec.action,
                        "job_id": spec.job_id,
                        "selector": spec.skill_id,
                        "matched_by": resolved_skill.matched_by,
                    },
                },
            ),
        )
        event = dict(status_event.events[-1])

        return OpenClawRuntimeResult(
            job_id=spec.job_id,
            action=spec.action,
            session_id=spec.session_id,
            summary=f"skill executed: {resolved_skill.manifest.get('id') or resolved_skill.skill_dir.name}",
            event_id=str(event.get("event_id") or ""),
            skill_id=str(resolved_skill.manifest.get("id") or resolved_skill.skill_dir.name),
            result=self._json_safe_value(result),
            metadata={
                "matched_by": resolved_skill.matched_by,
                "skill_dir": str(resolved_skill.skill_dir),
                "entry_point": str(entry_path),
            },
        )

    def _require_session(self, session_id: str) -> None:
        session = self._openclaw_service.get_session(session_id)
        if session is None:
            raise OpenClawRuntimeContractError(f"session not found: {session_id}")

    def _resolve_skill(self, selector: str) -> ResolvedOpenClawSkill:
        skills_root = self._workspace_root / "skills"
        if not skills_root.exists():
            raise OpenClawRuntimeContractError(f"skills directory not found: {skills_root}")

        normalized_selector = self._normalize_selector(selector)
        if not normalized_selector:
            raise OpenClawRuntimeContractError("run_skill requires skill_id")

        matches: list[ResolvedOpenClawSkill] = []
        for manifest_path in sorted(skills_root.glob("*/skill.json")):
            skill_dir = manifest_path.parent.resolve()
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if not isinstance(manifest, dict):
                continue

            selectors = (
                ("id", manifest.get("id")),
                ("name", manifest.get("name")),
                ("dirname", skill_dir.name),
            )
            for matched_by, candidate in selectors:
                if self._normalize_selector(candidate) == normalized_selector:
                    matches.append(
                        ResolvedOpenClawSkill(
                            skill_dir=skill_dir,
                            manifest_path=manifest_path.resolve(),
                            manifest=manifest,
                            matched_by=matched_by,
                        )
                    )
                    break

        if not matches:
            raise OpenClawRuntimeContractError(f"skill not found: {selector}")

        unique_matches: dict[Path, ResolvedOpenClawSkill] = {}
        for item in matches:
            unique_matches.setdefault(item.skill_dir, item)

        if len(unique_matches) > 1:
            conflict_paths = ", ".join(str(path.name) for path in sorted(unique_matches))
            raise OpenClawRuntimeContractError(
                f"ambiguous skill selector: {selector} ({conflict_paths})"
            )

        return next(iter(unique_matches.values()))

    def _resolve_entry_point(self, resolved_skill: ResolvedOpenClawSkill) -> Path:
        entry_point = str(resolved_skill.manifest.get("entry_point") or "").strip()
        if not entry_point:
            raise OpenClawRuntimeContractError(
                f"skill entry_point missing: {resolved_skill.manifest_path}"
            )

        skill_dir = resolved_skill.skill_dir.resolve()
        resolved_entry = (skill_dir / entry_point).resolve()
        try:
            resolved_entry.relative_to(skill_dir)
        except ValueError as exc:
            raise OpenClawRuntimeContractError(
                f"skill entry_point escapes skill directory: {entry_point}"
            ) from exc

        if not resolved_entry.is_file():
            raise OpenClawRuntimeContractError(
                f"skill entry_point not found: {resolved_entry}"
            )
        return resolved_entry

    async def _load_skill(self, entry_path: Path) -> Any:
        try:
            return await self._bridge.skill_loader.load_skill(str(entry_path))
        except Exception as exc:
            raise OpenClawRuntimeExecutionError(
                f"failed to load skill entry point {entry_path}: {exc}"
            ) from exc

    async def _execute_skill(
        self,
        *,
        skill: Any,
        payload: Any,
        credentials: dict[str, Any],
    ) -> Any:
        callable_owner = skill
        if not hasattr(callable_owner, "execute") and not hasattr(callable_owner, "main"):
            get_skill = getattr(callable_owner, "get_skill", None)
            if callable(get_skill):
                callable_owner = await self._bridge._call_maybe_async(get_skill)

        try:
            if hasattr(callable_owner, "execute"):
                return await self._bridge._call_maybe_async(
                    callable_owner.execute,
                    payload,
                    credentials=credentials,
                )
            if hasattr(callable_owner, "main"):
                return await self._bridge._call_maybe_async(callable_owner.main)
        except Exception as exc:
            raise OpenClawRuntimeExecutionError(f"skill execution failed: {exc}") from exc

        raise OpenClawRuntimeExecutionError(
            "loaded skill does not expose execute(...) or main(...)"
        )

    @staticmethod
    def _normalize_selector(value: Any) -> str:
        if value is None:
            return ""
        return unicodedata.normalize("NFKC", str(value)).strip().casefold()

    @classmethod
    def _json_safe_value(cls, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Path):
            return str(value)
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, dict):
            return {str(key): cls._json_safe_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [cls._json_safe_value(item) for item in value]
        return repr(value)
