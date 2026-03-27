"""Bridge API core implementation.

Provides:
- credentials reference model and in-memory credential registry
- task router for direct / codex / skill task types
- unified cleanup hook for Bridge resources
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import inspect
import logging

from .codex_client import CodexClient
from .skill_loader import SkillLoader

logger = logging.getLogger("agent_stack.bridge.api")


def _now_iso() -> str:
    return datetime.now().isoformat()


@dataclass
class CredentialsRef:
    """Reference object that decouples tasks from raw secrets."""

    ref_id: str
    ref_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict for API payloads."""
        return {
            "ref_id": self.ref_id,
            "ref_type": self.ref_type,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CredentialsRef":
        """Deserialize from dict payload."""
        return cls(
            ref_id=str(data.get("ref_id", "")),
            ref_type=str(data.get("ref_type", "")),
            metadata=dict(data.get("metadata") or {}),
            created_at=str(data.get("created_at") or _now_iso()),
        )


class BridgeAPI:
    """OpenClaw bridge facade for task routing and secure execution."""

    def __init__(
        self,
        codex_endpoint: str | None = None,
        skill_base_path: Path | None = None,
        enable_security_scan: bool = True,
    ) -> None:
        self.codex_endpoint = codex_endpoint or "http://localhost:8000"
        self.enable_security_scan = enable_security_scan
        self._credentials_store: dict[str, dict[str, Any]] = {}

        self.codex_client = CodexClient(endpoint=self.codex_endpoint)
        self.skill_loader = SkillLoader(
            base_path=Path(skill_base_path or Path.cwd()),
            enable_security_scan=enable_security_scan,
            strict_mode=False,
        )

        logger.info("[Agent-Stack-Bridge] Bridge API initialized")

    def register_credentials(
        self,
        ref_id: str,
        credentials: dict[str, Any],
        ref_type: str = "token",
        metadata: dict[str, Any] | None = None,
    ) -> CredentialsRef:
        """Register credentials and return an immutable reference."""
        if not ref_id:
            raise ValueError("ref_id is required")

        self._credentials_store[ref_id] = dict(credentials)
        return CredentialsRef(
            ref_id=ref_id,
            ref_type=ref_type,
            metadata=dict(metadata or {}),
        )

    async def receive_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """Validate, resolve credentials and route task execution."""
        self._validate_task(task)

        task_id = str(task["task_id"])
        task_type = str(task["task_type"])
        payload = dict(task["payload"])
        credentials = self._resolve_credentials(task.get("credentials_ref"))

        logger.info(f"[Agent-Stack-Bridge] Task received from OpenClaw: {task_id}")

        if task_type == "direct":
            return await self._handle_direct(task_id, payload)
        if task_type == "codex":
            return await self._handle_codex(task_id, payload, credentials)
        if task_type == "skill":
            return await self._handle_skill(task_id, payload, credentials)

        return {
            "status": "error",
            "task_id": task_id,
            "error": f"Unknown task type: {task_type}",
            "timestamp": _now_iso(),
        }

    async def cleanup(self) -> None:
        """Release bridge resources."""
        await self.skill_loader.cleanup()
        if self.codex_client.is_authenticated():
            await self.codex_client.logout()

    def _validate_task(self, task: dict[str, Any]) -> None:
        required_fields = ("task_id", "task_type", "payload")
        for field_name in required_fields:
            if field_name not in task:
                raise ValueError(f"Missing required field: {field_name}")

    def _resolve_credentials(self, credentials_ref: Any) -> dict[str, Any] | None:
        if not credentials_ref:
            return None

        if isinstance(credentials_ref, CredentialsRef):
            ref = credentials_ref
        elif isinstance(credentials_ref, dict):
            ref = CredentialsRef.from_dict(credentials_ref)
        else:
            raise ValueError("credentials_ref must be a dict or CredentialsRef")

        if ref.ref_id not in self._credentials_store:
            raise ValueError(f"Credentials ref not found: {ref.ref_id}")
        return self._credentials_store[ref.ref_id]

    async def _handle_direct(self, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        action = payload.get("action")

        if action == "echo":
            return {
                "status": "success",
                "task_id": task_id,
                "result": {"echo": payload.get("message", "")},
                "timestamp": _now_iso(),
            }

        if action == "health_check":
            return {
                "status": "success",
                "task_id": task_id,
                "result": {
                    "status": "healthy",
                    "bridge_version": "0.1.0",
                    "security_scan": self.enable_security_scan,
                },
                "timestamp": _now_iso(),
            }

        return {
            "status": "error",
            "task_id": task_id,
            "error": f"Unknown direct task action: {action}",
            "timestamp": _now_iso(),
        }

    async def _handle_codex(
        self,
        task_id: str,
        payload: dict[str, Any],
        credentials: dict[str, Any] | None,
    ) -> dict[str, Any]:
        try:
            if not self.codex_client.is_authenticated():
                if credentials is None:
                    return {
                        "status": "error",
                        "task_id": task_id,
                        "error": "Missing credentials for codex task",
                        "timestamp": _now_iso(),
                    }
                await self.codex_client.login(credentials)

            result = await self.codex_client.delegate_task(payload)
            return {
                "status": "success",
                "task_id": task_id,
                "result": result,
                "timestamp": _now_iso(),
            }
        except Exception as exc:
            return {
                "status": "error",
                "task_id": task_id,
                "error": str(exc),
                "timestamp": _now_iso(),
            }

    async def _handle_skill(
        self,
        task_id: str,
        payload: dict[str, Any],
        credentials: dict[str, Any] | None,
    ) -> dict[str, Any]:
        skill_path = payload.get("skill_path")
        if not skill_path:
            return {
                "status": "error",
                "task_id": task_id,
                "error": "Missing skill_path in payload",
                "timestamp": _now_iso(),
            }

        try:
            skill = await self.skill_loader.load_skill(str(skill_path))
            execution_input = payload.get("input", payload)

            if hasattr(skill, "execute"):
                result = await self._call_maybe_async(
                    skill.execute, execution_input, credentials=credentials
                )
            elif hasattr(skill, "main"):
                result = await self._call_maybe_async(skill.main)
            else:
                result = {"loaded": True}

            return {
                "status": "success",
                "task_id": task_id,
                "result": result,
                "timestamp": _now_iso(),
            }
        except Exception as exc:
            return {
                "status": "error",
                "task_id": task_id,
                "error": str(exc),
                "timestamp": _now_iso(),
            }

    async def _call_maybe_async(self, fn, *args, **kwargs):
        """Call sync/async callables with simple signature compatibility."""
        try:
            result = fn(*args, **kwargs)
        except TypeError:
            if "credentials" in kwargs:
                kwargs = dict(kwargs)
                kwargs.pop("credentials")
                result = fn(*args, **kwargs)
            else:
                raise

        if inspect.isawaitable(result):
            return await result
        return result
