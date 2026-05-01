from __future__ import annotations

from pathlib import Path
from typing import Any

from autoresearch.core.services.butler_dispatch import ButlerDoctorCheck


def build_hermes_interactive_callback_check(
    *,
    api_db_path: Path,
    hermes_transport: Any | None,
    workers: list[Any],
    probe_gateway: bool,
) -> ButlerDoctorCheck:
    api_db_path_str = str(api_db_path.resolve())
    api_gateway_configured = hermes_transport is not None
    api_gateway_health_ok: bool | None = None
    api_gateway_error: str | None = None

    if api_gateway_configured and probe_gateway:
        try:
            api_gateway_health_ok = bool(hermes_transport.health_check())
        except Exception as exc:  # pragma: no cover - defensive around pluggable transports
            api_gateway_health_ok = False
            api_gateway_error = str(exc).strip() or exc.__class__.__name__

    eligible_workers = [
        worker
        for worker in workers
        if _is_active_worker(worker)
        and "hermes_interactive" in set(getattr(worker, "capabilities", []) or [])
        and _metadata_bool(getattr(worker, "metadata", {}) or {}, "hermes_gateway_configured")
    ]
    matching_db_workers = [
        worker
        for worker in eligible_workers
        if _normalize_path((getattr(worker, "metadata", {}) or {}).get("api_db_path")) == api_db_path_str
    ]

    metadata: dict[str, Any] = {
        "api_gateway_configured": api_gateway_configured,
        "api_gateway_health_ok": api_gateway_health_ok,
        "interactive_worker_count": len(eligible_workers),
        "matching_db_worker_count": len(matching_db_workers),
        "api_db_path": api_db_path_str,
    }
    if api_gateway_error:
        metadata["api_gateway_error"] = api_gateway_error

    if not api_gateway_configured:
        return ButlerDoctorCheck(
            name="Hermes interactive callbacks",
            status="degraded",
            detail="API Hermes gateway is not configured; set AUTORESEARCH_HERMES_GATEWAY_BASE_URL",
            metadata=metadata,
        )
    if probe_gateway and not api_gateway_health_ok:
        return ButlerDoctorCheck(
            name="Hermes interactive callbacks",
            status="fail",
            detail="Hermes gateway health probe failed",
            metadata=metadata,
        )
    if not eligible_workers:
        return ButlerDoctorCheck(
            name="Hermes interactive callbacks",
            status="degraded",
            detail="No active worker has hermes_interactive capability with Hermes gateway configured",
            metadata=metadata,
        )
    if not matching_db_workers:
        return ButlerDoctorCheck(
            name="Hermes interactive callbacks",
            status="degraded",
            detail="No Hermes interactive worker shares AUTORESEARCH_API_DB_PATH with the API",
            metadata=metadata,
        )
    return ButlerDoctorCheck(
        name="Hermes interactive callbacks",
        status="ok",
        detail="Hermes interactive callback path is ready",
        metadata=metadata,
    )


def should_include_hermes_interactive_health(*, hermes_transport: Any | None, workers: list[Any]) -> bool:
    if hermes_transport is not None:
        return True
    return any("hermes_interactive" in set(getattr(worker, "capabilities", []) or []) for worker in workers)


def _is_active_worker(worker: Any) -> bool:
    display_status = str(getattr(worker, "display_status", "") or "").strip().lower()
    if display_status:
        return display_status in {"online", "busy"}
    if bool(getattr(worker, "is_stale", False)):
        return False
    mode = str(getattr(worker, "mode", "") or "").strip().lower()
    return mode not in {"offline", "draining"}


def _metadata_bool(metadata: dict[str, Any], key: str) -> bool:
    value = metadata.get(key)
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _normalize_path(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    return str(Path(raw).expanduser().resolve())
