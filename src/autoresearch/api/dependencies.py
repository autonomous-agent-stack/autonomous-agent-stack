from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from autoresearch.core.repositories import SQLiteEvaluationRepository
from autoresearch.core.services.admin_config import AdminConfigService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.executions import ExecutionService
from autoresearch.core.services.evaluations import EvaluationService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_skills import OpenClawSkillService
from autoresearch.core.services.panel_access import PanelAccessService
from autoresearch.core.services.panel_audit import PanelAuditService
from autoresearch.core.services.reports import ReportService
from autoresearch.core.services.self_integration import SelfIntegrationService
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.core.services.variants import VariantService
from autoresearch.shared.models import (
    ClaudeAgentRunRead,
    AdminAgentConfigRead,
    AdminChannelConfigRead,
    AdminConfigRevisionRead,
    ExecutionRead,
    ExperimentRead,
    IntegrationDiscoveryRead,
    IntegrationPromotionRead,
    IntegrationPrototypeRead,
    OpenClawSessionRead,
    OptimizationRead,
    PanelAuditLogRead,
    ReportRead,
    VariantRead,
)
from autoresearch.shared.store import SQLiteModelRepository
from autoresearch.train.services.experiments import ExperimentService
from autoresearch.train.services.optimizations import OptimizationService


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _api_db_path() -> Path:
    configured = os.getenv("AUTORESEARCH_API_DB_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return (_repo_root() / "artifacts" / "api" / "evaluations.sqlite3").resolve()


def _env_csv(name: str) -> set[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}


def _env_path_list(name: str) -> list[Path]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    if os.pathsep in raw:
        parts = raw.split(os.pathsep)
    else:
        parts = raw.split(",")
    resolved: list[Path] = []
    for item in parts:
        value = item.strip()
        if not value:
            continue
        resolved.append(Path(value).expanduser().resolve())
    return resolved


def _env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        parsed = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, parsed))


def _env_float(name: str, default: float, *, minimum: float, maximum: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        parsed = float(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, parsed))


@lru_cache(maxsize=1)
def get_evaluation_service() -> EvaluationService:
    service = EvaluationService(
        repository=SQLiteEvaluationRepository(db_path=_api_db_path()),
        repo_root=_repo_root(),
    )
    service.recover_interrupted()
    return service


@lru_cache(maxsize=1)
def get_report_service() -> ReportService:
    return ReportService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="report_runs",
            model_cls=ReportRead,
        )
    )


@lru_cache(maxsize=1)
def get_variant_service() -> VariantService:
    return VariantService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="variant_runs",
            model_cls=VariantRead,
        )
    )


@lru_cache(maxsize=1)
def get_optimization_service() -> OptimizationService:
    return OptimizationService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="optimization_runs",
            model_cls=OptimizationRead,
        )
    )


@lru_cache(maxsize=1)
def get_experiment_service() -> ExperimentService:
    return ExperimentService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="experiment_runs",
            model_cls=ExperimentRead,
        )
    )


@lru_cache(maxsize=1)
def get_execution_service() -> ExecutionService:
    return ExecutionService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="execution_runs",
            model_cls=ExecutionRead,
        ),
        repo_root=_repo_root(),
    )


@lru_cache(maxsize=1)
def get_openclaw_compat_service() -> OpenClawCompatService:
    return OpenClawCompatService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="openclaw_sessions",
            model_cls=OpenClawSessionRead,
        )
    )


@lru_cache(maxsize=1)
def get_openclaw_skill_service() -> OpenClawSkillService:
    return OpenClawSkillService(
        repo_root=_repo_root(),
        skill_roots=_env_path_list("AUTORESEARCH_OPENCLAW_SKILLS_DIRS") or None,
        max_skill_file_bytes=_env_int(
            "AUTORESEARCH_OPENCLAW_SKILL_MAX_BYTES",
            256_000,
            minimum=8_192,
            maximum=2_000_000,
        ),
        max_skills_per_root=_env_int(
            "AUTORESEARCH_OPENCLAW_SKILLS_MAX_PER_ROOT",
            300,
            minimum=1,
            maximum=10_000,
        ),
    )


@lru_cache(maxsize=1)
def get_claude_agent_service() -> ClaudeAgentService:
    return ClaudeAgentService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="claude_agent_runs",
            model_cls=ClaudeAgentRunRead,
        ),
        openclaw_service=get_openclaw_compat_service(),
        repo_root=_repo_root(),
        max_agents=int(os.getenv("AUTORESEARCH_AGENT_MAX_CONCURRENCY", "20")),
        max_depth=int(os.getenv("AUTORESEARCH_AGENT_MAX_DEPTH", "3")),
        openclaw_skill_service=get_openclaw_skill_service(),
    )


@lru_cache(maxsize=1)
def get_self_integration_service() -> SelfIntegrationService:
    return SelfIntegrationService(
        discovery_repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="integration_discoveries",
            model_cls=IntegrationDiscoveryRead,
        ),
        prototype_repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="integration_prototypes",
            model_cls=IntegrationPrototypeRead,
        ),
        promotion_repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="integration_promotions",
            model_cls=IntegrationPromotionRead,
        ),
    )


@lru_cache(maxsize=1)
def get_panel_access_service() -> PanelAccessService:
    return PanelAccessService(
        secret=os.getenv("AUTORESEARCH_PANEL_JWT_SECRET"),
        base_url=os.getenv("AUTORESEARCH_PANEL_BASE_URL", "http://127.0.0.1:8000/api/v1/panel/view"),
        issuer=os.getenv("AUTORESEARCH_PANEL_JWT_ISSUER", "autoresearch.telegram"),
        audience=os.getenv("AUTORESEARCH_PANEL_JWT_AUDIENCE", "autoresearch.panel"),
        default_ttl_seconds=_env_int(
            "AUTORESEARCH_PANEL_MAGIC_LINK_TTL_SECONDS",
            300,
            minimum=30,
            maximum=3600,
        ),
        max_ttl_seconds=_env_int(
            "AUTORESEARCH_PANEL_MAGIC_LINK_MAX_TTL_SECONDS",
            3600,
            minimum=30,
            maximum=86400,
        ),
        telegram_bot_token=os.getenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN"),
        telegram_init_data_max_age_seconds=_env_int(
            "AUTORESEARCH_PANEL_TELEGRAM_INITDATA_MAX_AGE_SECONDS",
            900,
            minimum=60,
            maximum=86400,
        ),
        allowed_uids=_env_csv("AUTORESEARCH_TELEGRAM_ALLOWED_UIDS"),
    )


@lru_cache(maxsize=1)
def get_panel_audit_service() -> PanelAuditService:
    return PanelAuditService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="panel_audit_logs",
            model_cls=PanelAuditLogRead,
        )
    )


@lru_cache(maxsize=1)
def get_telegram_notifier_service() -> TelegramNotifierService:
    return TelegramNotifierService(
        bot_token=os.getenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN"),
        api_base=os.getenv("AUTORESEARCH_TELEGRAM_API_BASE", "https://api.telegram.org"),
        timeout_seconds=_env_float(
            "AUTORESEARCH_TELEGRAM_NOTIFY_TIMEOUT_SECONDS",
            10.0,
            minimum=1.0,
            maximum=120.0,
        ),
    )


@lru_cache(maxsize=1)
def get_admin_config_service() -> AdminConfigService:
    return AdminConfigService(
        agent_repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="admin_agent_configs",
            model_cls=AdminAgentConfigRead,
        ),
        channel_repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="admin_channel_configs",
            model_cls=AdminChannelConfigRead,
        ),
        revision_repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="admin_config_revisions",
            model_cls=AdminConfigRevisionRead,
        ),
    )
