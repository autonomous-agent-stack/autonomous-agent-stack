from __future__ import annotations

import json
import logging
import platform
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import httpx


logger = logging.getLogger(__name__)

ControllerMode = Literal["linux_active", "mac_backup", "mac_active", "linux_recovering"]
ControllerRoute = Literal["forward_to_linux", "local"]

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_STATE_PATH = (_REPO_ROOT / "artifacts" / "runtime" / "telegram_controller_state.json").resolve()


@dataclass(slots=True)
class TelegramControllerNotice:
    kind: Literal["takeover", "release"]
    chat_id: str
    text: str


@dataclass(slots=True)
class TelegramControllerDecision:
    route: ControllerRoute
    mode: ControllerMode
    reason: str
    linux_online: bool
    notices: list[TelegramControllerNotice] = field(default_factory=list)


@dataclass(slots=True)
class TelegramControllerState:
    mode: ControllerMode = "mac_backup"
    lease_expires_at: str | None = None
    last_linux_probe_at: str | None = None
    last_linux_probe_ok: bool | None = None
    last_transition_at: str | None = None
    takeover_notified_at: str | None = None
    release_notified_at: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "TelegramControllerState":
        mode = str(payload.get("mode") or "mac_backup")
        if mode not in {"linux_active", "mac_backup", "mac_active", "linux_recovering"}:
            mode = "mac_backup"
        return cls(
            mode=mode,  # type: ignore[arg-type]
            lease_expires_at=_safe_str(payload.get("lease_expires_at")),
            last_linux_probe_at=_safe_str(payload.get("last_linux_probe_at")),
            last_linux_probe_ok=_safe_bool(payload.get("last_linux_probe_ok")),
            last_transition_at=_safe_str(payload.get("last_transition_at")),
            takeover_notified_at=_safe_str(payload.get("takeover_notified_at")),
            release_notified_at=_safe_str(payload.get("release_notified_at")),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "lease_expires_at": self.lease_expires_at,
            "last_linux_probe_at": self.last_linux_probe_at,
            "last_linux_probe_ok": self.last_linux_probe_ok,
            "last_transition_at": self.last_transition_at,
            "takeover_notified_at": self.takeover_notified_at,
            "release_notified_at": self.release_notified_at,
        }


class TelegramControllerHandoffService:
    """Minimal single-active-controller handoff for Telegram routing."""

    def __init__(
        self,
        *,
        linux_control_base_url: str | None,
        state_path: Path = _DEFAULT_STATE_PATH,
        probe_timeout_seconds: float = 2.5,
        lease_ttl_seconds: int = 15,
        forward_timeout_seconds: float = 10.0,
    ) -> None:
        self._linux_control_base_url = (linux_control_base_url or "").strip() or None
        self._state_path = state_path.expanduser().resolve()
        self._probe_timeout_seconds = max(0.5, float(probe_timeout_seconds))
        self._lease_ttl_seconds = max(5, int(lease_ttl_seconds))
        self._forward_timeout_seconds = max(1.0, float(forward_timeout_seconds))
        self._lock = threading.Lock()

    @property
    def linux_control_base_url(self) -> str | None:
        return self._linux_control_base_url

    @property
    def state_path(self) -> Path:
        return self._state_path

    @property
    def forward_timeout_seconds(self) -> float:
        return self._forward_timeout_seconds

    def evaluate(
        self,
        *,
        chat_id: str,
        text: str,
        forwarded_from_controller: bool = False,
    ) -> TelegramControllerDecision:
        current_platform = platform.system().strip().lower()
        if current_platform == "linux" or forwarded_from_controller:
            return TelegramControllerDecision(
                route="local",
                mode="linux_active",
                reason="linux runtime handles the forwarded update locally",
                linux_online=True,
            )

        with self._lock:
            state = self._load_state()
            now = datetime.now(timezone.utc)
            lease_expires_at = _parse_datetime(state.lease_expires_at)
            if state.mode == "linux_active" and lease_expires_at and lease_expires_at > now:
                return TelegramControllerDecision(
                    route="forward_to_linux",
                    mode="linux_active",
                    reason="cached linux lease is still valid",
                    linux_online=True,
                )

            if not self._linux_control_base_url:
                return self._enter_mac_active(
                    state=state,
                    now=now,
                    chat_id=chat_id,
                    reason="linux control base url is not configured",
                )

            linux_online = self._probe_linux_controller()
            state.last_linux_probe_at = now.isoformat()
            state.last_linux_probe_ok = linux_online

            if linux_online:
                previous_mode = state.mode
                notices: list[TelegramControllerNotice] = []
                if previous_mode == "mac_active":
                    notices.append(
                        TelegramControllerNotice(
                            kind="release",
                            chat_id=chat_id,
                            text=(
                                "Linux 管家已恢复在线，Mac 已释放接管，"
                                "当前 bot A 已切回 Linux 主控制。"
                            ),
                        )
                    )
                    self._clear_state()
                elif self._state_path.is_file():
                    self._clear_state()
                return TelegramControllerDecision(
                    route="forward_to_linux",
                    mode="linux_active",
                    reason="linux probe succeeded",
                    linux_online=True,
                    notices=notices,
                )

            return self._enter_mac_active(
                state=state,
                now=now,
                chat_id=chat_id,
                reason="linux probe failed or timed out",
            )

    def force_mac_active(self, *, chat_id: str, reason: str) -> TelegramControllerDecision:
        with self._lock:
            state = self._load_state()
            return self._enter_mac_active(
                state=state,
                now=datetime.now(timezone.utc),
                chat_id=chat_id,
                reason=reason,
            )

    def _enter_mac_active(
        self,
        *,
        state: TelegramControllerState,
        now: datetime,
        chat_id: str,
        reason: str,
    ) -> TelegramControllerDecision:
        previous_mode = state.mode
        state.mode = "mac_active"
        state.lease_expires_at = self._expiry(now)
        state.last_transition_at = now.isoformat()
        state.last_linux_probe_at = now.isoformat()
        state.last_linux_probe_ok = False

        notices: list[TelegramControllerNotice] = []
        if previous_mode != "mac_active":
            state.takeover_notified_at = now.isoformat()
            notices.append(
                TelegramControllerNotice(
                    kind="takeover",
                    chat_id=chat_id,
                    text=(
                        "Linux 管家当前不可用，Mac 已进入降级接管模式。"
                        "当前只处理 help/status/通知/审批/短时低风险任务。"
                    ),
                )
            )

        self._save_state(state)
        return TelegramControllerDecision(
            route="local",
            mode="mac_active",
            reason=reason,
            linux_online=False,
            notices=notices,
        )

    def _probe_linux_controller(self) -> bool:
        assert self._linux_control_base_url is not None
        url = f"{self._linux_control_base_url.rstrip('/')}/api/v1/cluster/health"
        try:
            with httpx.Client(timeout=self._probe_timeout_seconds) as client:
                response = client.get(url, headers={"X-Autoresearch-Controller-Probe": "1"})
            if response.status_code == 200:
                return True
            logger.info("linux controller probe returned %s", response.status_code)
            return False
        except Exception as exc:
            logger.info("linux controller probe failed: %s", exc)
            return False

    def _load_state(self) -> TelegramControllerState:
        if not self._state_path.is_file():
            return TelegramControllerState()
        try:
            payload = json.loads(self._state_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return TelegramControllerState.from_dict(payload)
        except Exception as exc:
            logger.warning("failed to load telegram controller state: %s", exc)
        return TelegramControllerState()

    def _save_state(self, state: TelegramControllerState) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._state_path.with_suffix(self._state_path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(self._state_path)

    def _clear_state(self) -> None:
        try:
            self._state_path.unlink(missing_ok=True)
        except TypeError:
            if self._state_path.exists():
                self._state_path.unlink()

    def _expiry(self, now: datetime) -> str:
        return (now + timedelta(seconds=self._lease_ttl_seconds)).isoformat()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _safe_str(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _safe_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    return None
