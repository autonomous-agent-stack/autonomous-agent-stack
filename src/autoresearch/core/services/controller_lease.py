from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping


_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CONTROLLER_STATE_FILE = _REPO_ROOT / ".masfactory_runtime" / "telegram-poller" / "active_controller.json"
DEFAULT_CONTROLLER_LEASE_SECONDS = 30
CONTROLLER_STATUS_ONLINE = "online"
CONTROLLER_STATUS_OFFLINE = "offline"
CONTROLLER_STATUS_STALE = "stale"


@dataclass(frozen=True)
class ControllerLeaseSnapshot:
    active_controller: str | None
    controller_name: str | None
    execution_role: str | None
    runtime_host: str | None
    should_poll: bool
    reason: str | None
    updated_at: int | None
    lease_ttl_seconds: int
    lease_expires_at: int | None
    lease_age_seconds: int | None
    controller_status: str
    status_signal: str | None
    task_risk_profile: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean_string(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    normalized = str(value).strip()
    if not normalized:
        return None
    try:
        return int(float(normalized))
    except (TypeError, ValueError):
        return None


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    return bool(value)


def resolve_controller_lease_seconds(raw: Any = None) -> int:
    candidate = raw
    if candidate is None:
        candidate = os.getenv("AUTORESEARCH_CONTROLLER_LEASE_SECONDS")
    value = _coerce_int(candidate)
    if value is None or value <= 0:
        return DEFAULT_CONTROLLER_LEASE_SECONDS
    return value


def resolve_controller_state_path(configured: str | None = None) -> Path:
    candidate = str(configured or "").strip()
    if not candidate:
        candidate = str(os.getenv("AUTORESEARCH_TELEGRAM_ACTIVE_CONTROLLER_FILE", "")).strip()
    if not candidate:
        candidate = str(os.getenv("TELEGRAM_ACTIVE_CONTROLLER_FILE", "")).strip()
    return Path(candidate).expanduser().resolve() if candidate else DEFAULT_CONTROLLER_STATE_FILE


def read_controller_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def write_controller_state(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def evaluate_controller_state(
    payload: Mapping[str, Any] | None,
    *,
    now_ts: int | None = None,
    default_lease_seconds: int | None = None,
) -> ControllerLeaseSnapshot:
    source = dict(payload or {})
    lease_ttl_seconds = resolve_controller_lease_seconds(
        source.get("lease_ttl_seconds") if default_lease_seconds is None else default_lease_seconds
    )
    updated_at = _coerce_int(source.get("updated_at"))
    lease_age_seconds = None
    lease_expires_at = None
    if updated_at is not None:
        current_ts = updated_at if now_ts is None else now_ts
        lease_age_seconds = max(0, current_ts - updated_at)
        lease_expires_at = updated_at + lease_ttl_seconds

    active_controller = _clean_string(source.get("active_controller"))
    controller_name = _clean_string(source.get("controller_name"))
    should_poll = _coerce_bool(source.get("should_poll"))

    if updated_at is None:
        controller_status = CONTROLLER_STATUS_OFFLINE
    elif lease_age_seconds is not None and lease_age_seconds > lease_ttl_seconds:
        controller_status = CONTROLLER_STATUS_STALE
    elif not should_poll:
        controller_status = CONTROLLER_STATUS_OFFLINE
    elif active_controller and controller_name and active_controller != controller_name:
        controller_status = CONTROLLER_STATUS_OFFLINE
    else:
        controller_status = CONTROLLER_STATUS_ONLINE

    return ControllerLeaseSnapshot(
        active_controller=active_controller,
        controller_name=controller_name,
        execution_role=_clean_string(source.get("execution_role")),
        runtime_host=_clean_string(source.get("runtime_host")),
        should_poll=should_poll,
        reason=_clean_string(source.get("reason")),
        updated_at=updated_at,
        lease_ttl_seconds=lease_ttl_seconds,
        lease_expires_at=lease_expires_at,
        lease_age_seconds=lease_age_seconds,
        controller_status=controller_status,
        status_signal=_clean_string(source.get("status_signal")),
        task_risk_profile=_clean_string(source.get("task_risk_profile")),
    )
