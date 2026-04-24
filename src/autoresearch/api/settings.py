from __future__ import annotations

import logging
import os
import json
import shlex
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_API_DB_PATH = (_REPO_ROOT / "artifacts" / "api" / "evaluations.sqlite3").resolve()
_DEFAULT_PANEL_STATIC_DIR = (_REPO_ROOT / "panel" / "out").resolve()
_WARNED_DEPRECATED_ALIASES: set[tuple[str, str]] = set()


def _warn_deprecated_alias(*, alias: str, canonical: str) -> None:
    if not os.getenv(alias) or os.getenv(canonical):
        return
    key = (alias, canonical)
    if key in _WARNED_DEPRECATED_ALIASES:
        return
    _WARNED_DEPRECATED_ALIASES.add(key)
    logger.warning("Environment variable %s is deprecated; use %s instead.", alias, canonical)


def _parse_csv_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, set):
        return {str(item).strip() for item in value if str(item).strip()}
    if isinstance(value, (list, tuple)):
        return {str(item).strip() for item in value if str(item).strip()}
    raw = str(value).strip()
    if not raw:
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}


def _parse_path_list(value: Any) -> list[Path]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        items = value
    else:
        raw = str(value).strip()
        if not raw:
            return []
        items = raw.split(os.pathsep) if os.pathsep in raw else raw.split(",")
    resolved: list[Path] = []
    for item in items:
        normalized = str(item).strip()
        if not normalized:
            continue
        resolved.append(Path(normalized).expanduser().resolve())
    return resolved


def _parse_path(value: Any) -> Path | None:
    if value is None:
        return None
    if isinstance(value, Path):
        return value.expanduser().resolve()
    normalized = str(value).strip()
    if not normalized:
        return None
    return Path(normalized).expanduser().resolve()


def _parse_string_dict(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return {
            str(key).strip(): str(item).strip()
            for key, item in value.items()
            if str(key).strip() and str(item).strip()
        }
    raw = str(value).strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        return {
            str(key).strip(): str(item).strip()
            for key, item in parsed.items()
            if str(key).strip() and str(item).strip()
        }

    mapping: dict[str, str] = {}
    for item in raw.split(","):
        left, separator, right = item.partition("=")
        if not separator:
            continue
        key = left.strip()
        candidate = right.strip()
        if key and candidate:
            mapping[key] = candidate
    return mapping


class _BaseApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")


class RuntimeSettings(_BaseApiSettings):
    """Runtime settings for the AAS API.

    The `mode` field controls startup behavior:
    - `minimal`: Stable single-machine mode (default). Only core features enabled.
    - `full`: All features enabled, including experimental ones.

    In minimal mode, Telegram, WebAuthn, and cluster features are disabled by default
    unless explicitly enabled via environment variables.
    """
    mode: str = Field(
        default="minimal",
        validation_alias="AUTORESEARCH_MODE",
        description="Application mode: 'minimal' (stable) or 'full' (experimental)",
    )
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("AUTORESEARCH_ENV", "AUTORESEARCH_ENVIRONMENT", "ENVIRONMENT"),
    )
    api_host: str = Field(default="127.0.0.1", validation_alias="AUTORESEARCH_API_HOST")
    api_port: int = Field(default=8001, validation_alias="AUTORESEARCH_API_PORT")
    api_db_path: Path = Field(default=_DEFAULT_API_DB_PATH, validation_alias="AUTORESEARCH_API_DB_PATH")
    api_allow_unsafe_bind: bool = Field(default=False, validation_alias="AUTORESEARCH_API_ALLOW_UNSAFE_BIND")
    enable_cluster: bool = Field(default=False, validation_alias="AUTORESEARCH_ENABLE_CLUSTER")
    enable_admin: bool = Field(default=True, validation_alias="AUTORESEARCH_ENABLE_ADMIN")
    enable_worker_schedule_daemon: bool = Field(
        default=False,
        validation_alias="AUTORESEARCH_ENABLE_WORKER_SCHEDULE_DAEMON",
    )
    worker_schedule_poll_seconds: int = Field(
        default=30,
        ge=1,
        le=3600,
        validation_alias="AUTORESEARCH_WORKER_SCHEDULE_POLL_SECONDS",
    )
    enable_legacy_telegram_webhook: bool = Field(
        default=False,
        validation_alias="AUTORESEARCH_ENABLE_LEGACY_TELEGRAM_WEBHOOK",
    )
    enable_webauthn: bool = Field(default=False, validation_alias="AUTORESEARCH_ENABLE_WEBAUTHN")
    panel_static_dir: Path = Field(default=_DEFAULT_PANEL_STATIC_DIR)

    @field_validator("api_db_path", mode="before")
    @classmethod
    def _normalize_api_db_path(cls, value: Any) -> Path:
        path = _parse_path(value)
        return path or _DEFAULT_API_DB_PATH

    @field_validator("panel_static_dir", mode="before")
    @classmethod
    def _normalize_panel_static_dir(cls, value: Any) -> Path:
        path = _parse_path(value)
        return path or _DEFAULT_PANEL_STATIC_DIR

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in {"prod", "production"}

    @property
    def is_minimal_mode(self) -> bool:
        """True if running in stable minimal mode (default)."""
        return self.mode.strip().lower() == "minimal"

    @field_validator("mode", mode="before")
    @classmethod
    def _normalize_mode(cls, value: Any) -> str:
        raw = str(value).strip().lower() if value is not None else "minimal"
        if raw not in {"minimal", "full"}:
            return "minimal"
        return raw


class TelegramSettings(_BaseApiSettings):
    bot_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AUTORESEARCH_TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT_TOKEN"),
    )
    secret_token: str | None = Field(default=None, validation_alias="AUTORESEARCH_TELEGRAM_SECRET_TOKEN")
    allowed_uids: set[str] = Field(default_factory=set, validation_alias="AUTORESEARCH_TELEGRAM_ALLOWED_UIDS")
    owner_uids: set[str] = Field(default_factory=set, validation_alias="AUTORESEARCH_TELEGRAM_OWNER_UIDS")
    partner_uids: set[str] = Field(default_factory=set, validation_alias="AUTORESEARCH_TELEGRAM_PARTNER_UIDS")
    internal_groups: set[str] = Field(default_factory=set, validation_alias="AUTORESEARCH_INTERNAL_GROUPS")
    bot_usernames: Annotated[set[str], NoDecode] = Field(
        default_factory=set,
        validation_alias="AUTORESEARCH_TELEGRAM_BOT_USERNAMES",
    )
    shared_assistant_id: str = Field(
        default="telegram-shared",
        validation_alias="AUTORESEARCH_TELEGRAM_SHARED_ASSISTANT_ID",
    )
    agent_name: str | None = Field(default=None, validation_alias="AUTORESEARCH_TELEGRAM_AGENT_NAME")
    timeout_seconds: int = Field(default=900, validation_alias="AUTORESEARCH_TELEGRAM_TIMEOUT_SECONDS")
    generation_depth: int = Field(default=1, validation_alias="AUTORESEARCH_TELEGRAM_GENERATION_DEPTH")
    work_dir: Path | None = Field(default=None, validation_alias="AUTORESEARCH_TELEGRAM_WORK_DIR")
    claude_args_raw: str = Field(default="", validation_alias="AUTORESEARCH_TELEGRAM_CLAUDE_ARGS")
    command_override_raw: str = Field(
        default="",
        validation_alias="AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
    )
    append_prompt: bool = Field(default=True, validation_alias="AUTORESEARCH_TELEGRAM_APPEND_PROMPT")
    api_base: str = Field(default="https://api.telegram.org", validation_alias="AUTORESEARCH_TELEGRAM_API_BASE")
    notify_timeout_seconds: float = Field(
        default=10.0,
        validation_alias="AUTORESEARCH_TELEGRAM_NOTIFY_TIMEOUT_SECONDS",
    )
    channel_key: str = Field(default="telegram-main", validation_alias="AUTORESEARCH_TELEGRAM_CHANNEL_KEY")
    channel_display_name: str = Field(
        default="Telegram Main",
        validation_alias="AUTORESEARCH_TELEGRAM_CHANNEL_DISPLAY_NAME",
    )
    channel_actor: str = Field(default="telegram-webhook", validation_alias="AUTORESEARCH_TELEGRAM_CHANNEL_ACTOR")
    telegram_dispatch_runtime_id: str = Field(
        default="claude",
        validation_alias="AUTORESEARCH_TELEGRAM_RUNTIME_ID",
    )
    telegram_worker_display_name: str = Field(
        default="初代worker",
        validation_alias="AUTORESEARCH_TELEGRAM_WORKER_DISPLAY_NAME",
    )
    telegram_hermes_profile: str = Field(
        default="default",
        validation_alias="AUTORESEARCH_TELEGRAM_HERMES_PROFILE",
    )
    telegram_hermes_toolsets_raw: str = Field(
        default="",
        validation_alias="AUTORESEARCH_TELEGRAM_HERMES_TOOLSETS",
    )
    telegram_hermes_approval_mode: str = Field(
        default="",
        validation_alias="AUTORESEARCH_TELEGRAM_HERMES_APPROVAL_MODE",
    )
    butler_completion_fallback_enabled: bool = Field(
        default=True,
        validation_alias="AUTORESEARCH_TELEGRAM_BUTLER_FALLBACK_ENABLED",
    )
    butler_api_completion_enabled: bool = Field(
        default=True,
        validation_alias="AUTORESEARCH_TELEGRAM_BUTLER_API_COMPLETION_ENABLED",
    )
    butler_live_updates_enabled: bool = Field(
        default=True,
        validation_alias="AUTORESEARCH_TELEGRAM_BUTLER_LIVE_UPDATES_ENABLED",
    )
    butler_live_interval_seconds: float = Field(
        default=30.0,
        ge=5.0,
        le=300.0,
        validation_alias="AUTORESEARCH_TELEGRAM_BUTLER_LIVE_INTERVAL_SECONDS",
    )
    butler_live_on_newline: bool = Field(
        default=False,
        validation_alias="AUTORESEARCH_TELEGRAM_BUTLER_LIVE_ON_NEWLINE",
    )
    hermes_append_eof_instruction: bool = Field(
        default=False,
        validation_alias="AUTORESEARCH_TELEGRAM_HERMES_APPEND_EOF_INSTRUCTION",
    )

    @field_validator("telegram_worker_display_name", mode="before")
    @classmethod
    def _normalize_telegram_worker_display_name(cls, value: Any) -> str:
        if value is None:
            return "初代worker"
        return str(value).strip()

    @field_validator("telegram_hermes_profile", mode="before")
    @classmethod
    def _normalize_telegram_hermes_profile(cls, value: Any) -> str:
        raw = str(value or "").strip()
        if raw.lower() == "butler":
            return "default"
        return raw

    @field_validator("telegram_dispatch_runtime_id", mode="before")
    @classmethod
    def _normalize_telegram_dispatch_runtime_id(cls, value: Any) -> str:
        raw = str(value or "claude").strip().lower()
        return raw if raw in {"claude", "hermes"} else "claude"

    @field_validator("allowed_uids", "owner_uids", "partner_uids", "internal_groups", "bot_usernames", mode="before")
    @classmethod
    def _normalize_sets(cls, value: Any) -> set[str]:
        return _parse_csv_set(value)

    @field_validator("work_dir", mode="before")
    @classmethod
    def _normalize_work_dir(cls, value: Any) -> Path | None:
        return _parse_path(value)

    @property
    def claude_args(self) -> list[str]:
        return shlex.split(self.claude_args_raw) if self.claude_args_raw.strip() else []

    @property
    def command_override(self) -> list[str] | None:
        return shlex.split(self.command_override_raw) if self.command_override_raw.strip() else None

    def hermes_metadata_fragment_for_worker(self) -> dict[str, Any]:
        """Structured defaults for `metadata.hermes` on Telegram → worker → Hermes adapter."""
        out: dict[str, Any] = {"session_mode": "oneshot"}
        profile = self.telegram_hermes_profile.strip()
        if profile:
            out["profile"] = profile
        if self.telegram_hermes_toolsets_raw.strip():
            out["toolsets"] = [
                item.strip()
                for item in self.telegram_hermes_toolsets_raw.split(",")
                if item.strip()
            ]
        mode = self.telegram_hermes_approval_mode.strip().lower()
        if mode in ("manual", "smart"):
            out["approval_mode"] = mode
        return out


class PanelSettings(_BaseApiSettings):
    jwt_secret: str | None = Field(default=None, validation_alias="AUTORESEARCH_PANEL_JWT_SECRET")
    base_url: str = Field(
        default="http://127.0.0.1:8001/api/v1/panel/view",
        validation_alias=AliasChoices("AUTORESEARCH_PANEL_BASE_URL", "AUTORESEARCH_BASE_URL"),
    )
    jwt_issuer: str = Field(default="autoresearch.telegram", validation_alias="AUTORESEARCH_PANEL_JWT_ISSUER")
    jwt_audience: str = Field(default="autoresearch.panel", validation_alias="AUTORESEARCH_PANEL_JWT_AUDIENCE")
    magic_link_ttl_seconds: int = Field(
        default=300,
        validation_alias="AUTORESEARCH_PANEL_MAGIC_LINK_TTL_SECONDS",
    )
    magic_link_max_ttl_seconds: int = Field(
        default=3600,
        validation_alias="AUTORESEARCH_PANEL_MAGIC_LINK_MAX_TTL_SECONDS",
    )
    telegram_initdata_max_age_seconds: int = Field(
        default=900,
        validation_alias="AUTORESEARCH_PANEL_TELEGRAM_INITDATA_MAX_AGE_SECONDS",
    )
    mini_app_url: str | None = Field(default=None, validation_alias="AUTORESEARCH_TELEGRAM_MINI_APP_URL")


class FeatureSettings(_BaseApiSettings):
    enable_mirofish_gate: bool = Field(
        default=False,
        validation_alias=AliasChoices("AUTORESEARCH_ENABLE_MIROFISH_GATE", "AUTORESEARCH_MIROFISH_ENABLED"),
    )
    mirofish_min_confidence: float = Field(
        default=0.5,
        validation_alias="AUTORESEARCH_MIROFISH_MIN_CONFIDENCE",
    )
    mirofish_engine: str = Field(
        default="mirofish_heuristic_v1",
        validation_alias="AUTORESEARCH_MIROFISH_ENGINE",
    )
    openclaw_skill_dirs: list[Path] = Field(
        default_factory=list,
        validation_alias="AUTORESEARCH_OPENCLAW_SKILLS_DIRS",
    )
    openclaw_skill_max_bytes: int = Field(
        default=256_000,
        validation_alias="AUTORESEARCH_OPENCLAW_SKILL_MAX_BYTES",
    )
    openclaw_skill_max_per_root: int = Field(
        default=300,
        validation_alias="AUTORESEARCH_OPENCLAW_SKILLS_MAX_PER_ROOT",
    )
    managed_skill_active_dir: Path = Field(
        default=(_REPO_ROOT / "artifacts" / "managed_skills" / "active").resolve(),
        validation_alias="AUTORESEARCH_MANAGED_SKILL_ACTIVE_DIR",
    )
    managed_skill_quarantine_dir: Path = Field(
        default=(_REPO_ROOT / "artifacts" / "managed_skills" / "quarantine").resolve(),
        validation_alias="AUTORESEARCH_MANAGED_SKILL_QUARANTINE_DIR",
    )
    managed_skill_manifest_name: str = Field(
        default="managed-skill.json",
        validation_alias="AUTORESEARCH_MANAGED_SKILL_MANIFEST_NAME",
    )
    managed_skill_trusted_signers: dict[str, str] = Field(
        default_factory=dict,
        validation_alias="AUTORESEARCH_MANAGED_SKILL_TRUSTED_SIGNERS",
    )
    managed_skill_allowed_capabilities: set[str] = Field(
        default_factory=lambda: {
            "prompt",
            "filesystem_read",
            "filesystem_write",
            "shell",
            "browser",
            "network",
        },
        validation_alias="AUTORESEARCH_MANAGED_SKILL_ALLOWED_CAPABILITIES",
    )
    agent_max_concurrency: int = Field(default=20, validation_alias="AUTORESEARCH_AGENT_MAX_CONCURRENCY")
    agent_max_depth: int = Field(default=3, validation_alias="AUTORESEARCH_AGENT_MAX_DEPTH")

    @field_validator("openclaw_skill_dirs", mode="before")
    @classmethod
    def _normalize_skill_dirs(cls, value: Any) -> list[Path]:
        return _parse_path_list(value)

    @field_validator("managed_skill_active_dir", "managed_skill_quarantine_dir", mode="before")
    @classmethod
    def _normalize_managed_skill_dirs(cls, value: Any) -> Path:
        path = _parse_path(value)
        if path is None:
            raise ValueError("managed skill directory is required")
        return path

    @field_validator("managed_skill_trusted_signers", mode="before")
    @classmethod
    def _normalize_managed_skill_trusted_signers(cls, value: Any) -> dict[str, str]:
        return _parse_string_dict(value)

    @field_validator("managed_skill_allowed_capabilities", mode="before")
    @classmethod
    def _normalize_managed_skill_capabilities(cls, value: Any) -> set[str]:
        return _parse_csv_set(value)


class AdminSettings(_BaseApiSettings):
    secret_key: str | None = Field(default=None, validation_alias="AUTORESEARCH_ADMIN_SECRET_KEY")
    jwt_secret: str | None = Field(default=None, validation_alias="AUTORESEARCH_ADMIN_JWT_SECRET")
    bootstrap_key: str | None = Field(default=None, validation_alias="AUTORESEARCH_ADMIN_BOOTSTRAP_KEY")
    jwt_issuer: str = Field(default="autoresearch.admin", validation_alias="AUTORESEARCH_ADMIN_JWT_ISSUER")
    jwt_audience: str = Field(
        default="autoresearch.admin.api",
        validation_alias="AUTORESEARCH_ADMIN_JWT_AUDIENCE",
    )
    token_ttl_seconds: int = Field(default=3600, validation_alias="AUTORESEARCH_ADMIN_TOKEN_TTL_SECONDS")
    token_max_ttl_seconds: int = Field(
        default=86400,
        validation_alias="AUTORESEARCH_ADMIN_TOKEN_MAX_TTL_SECONDS",
    )
    allowed_roles: set[str] = Field(default_factory=set, validation_alias="AUTORESEARCH_ADMIN_ALLOWED_ROLES")

    @field_validator("allowed_roles", mode="before")
    @classmethod
    def _normalize_allowed_roles(cls, value: Any) -> set[str]:
        roles = _parse_csv_set(value)
        return roles or {"viewer", "editor", "admin", "owner"}


class UpstreamWatcherSettings(_BaseApiSettings):
    upstream_url: str = Field(
        default="https://github.com/openclaw/openclaw.git",
        validation_alias="AUTORESEARCH_UPSTREAM_WATCH_URL",
    )
    workspace_root: Path = Field(
        default=Path("/Volumes/AI_LAB/ai_lab/workspace"),
        validation_alias="AUTORESEARCH_UPSTREAM_WATCH_WORKSPACE_ROOT",
    )
    max_commits: int = Field(default=5, validation_alias="AUTORESEARCH_UPSTREAM_WATCH_MAX_COMMITS")

    @field_validator("workspace_root", mode="before")
    @classmethod
    def _normalize_workspace_root(cls, value: Any) -> Path:
        path = _parse_path(value)
        return path or Path("/Volumes/AI_LAB/ai_lab/workspace")


def load_runtime_settings() -> RuntimeSettings:
    return RuntimeSettings()


def load_telegram_settings() -> TelegramSettings:
    _warn_deprecated_alias(alias="TELEGRAM_BOT_TOKEN", canonical="AUTORESEARCH_TELEGRAM_BOT_TOKEN")
    return TelegramSettings()


def load_panel_settings() -> PanelSettings:
    _warn_deprecated_alias(alias="AUTORESEARCH_BASE_URL", canonical="AUTORESEARCH_PANEL_BASE_URL")
    return PanelSettings()


def load_feature_settings() -> FeatureSettings:
    return FeatureSettings()


def load_admin_settings() -> AdminSettings:
    return AdminSettings()


def load_upstream_watcher_settings() -> UpstreamWatcherSettings:
    return UpstreamWatcherSettings()


@lru_cache(maxsize=1)
def get_runtime_settings() -> RuntimeSettings:
    return load_runtime_settings()


@lru_cache(maxsize=1)
def get_telegram_settings() -> TelegramSettings:
    return load_telegram_settings()


@lru_cache(maxsize=1)
def get_panel_settings() -> PanelSettings:
    return load_panel_settings()


@lru_cache(maxsize=1)
def get_feature_settings() -> FeatureSettings:
    return load_feature_settings()


@lru_cache(maxsize=1)
def get_admin_settings() -> AdminSettings:
    return load_admin_settings()


@lru_cache(maxsize=1)
def get_upstream_watcher_settings() -> UpstreamWatcherSettings:
    return load_upstream_watcher_settings()


def clear_settings_caches() -> None:
    get_runtime_settings.cache_clear()
    get_telegram_settings.cache_clear()
    get_panel_settings.cache_clear()
    get_feature_settings.cache_clear()
    get_admin_settings.cache_clear()
    get_upstream_watcher_settings.cache_clear()
    _WARNED_DEPRECATED_ALIASES.clear()
