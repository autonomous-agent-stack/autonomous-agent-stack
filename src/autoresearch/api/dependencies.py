from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import Depends

from autoresearch.api.settings import (
    get_admin_settings,
    get_feature_settings,
    get_panel_settings,
    get_runtime_settings,
    get_telegram_settings,
)
from autoresearch.core.repositories import SQLiteEvaluationRepository
from autoresearch.core.services.admin_auth import AdminAuthService
from autoresearch.core.services.admin_config import AdminConfigService
from autoresearch.core.services.admin_secrets import AdminSecretCipher
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.evaluations import EvaluationService
from autoresearch.core.services.executions import ExecutionService
from autoresearch.core.services.mirofish_prediction import MiroFishPredictionService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_skills import OpenClawSkillService
from autoresearch.core.services.openviking_memory import OpenVikingMemoryService
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
    AdminSecretRecordRead,
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
    return get_runtime_settings().api_db_path


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
    feature_settings = get_feature_settings()
    return OpenClawSkillService(
        repo_root=_repo_root(),
        skill_roots=feature_settings.openclaw_skill_dirs or None,
        max_skill_file_bytes=max(8_192, min(feature_settings.openclaw_skill_max_bytes, 2_000_000)),
        max_skills_per_root=max(1, min(feature_settings.openclaw_skill_max_per_root, 10_000)),
    )


@lru_cache(maxsize=1)
def get_claude_agent_service() -> ClaudeAgentService:
    feature_settings = get_feature_settings()
    return ClaudeAgentService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="claude_agent_runs",
            model_cls=ClaudeAgentRunRead,
        ),
        openclaw_service=get_openclaw_compat_service(),
        repo_root=_repo_root(),
        max_agents=feature_settings.agent_max_concurrency,
        max_depth=feature_settings.agent_max_depth,
        openclaw_skill_service=get_openclaw_skill_service(),
    )


def get_openviking_memory_service(
    openclaw_service: OpenClawCompatService = Depends(get_openclaw_compat_service),
) -> OpenVikingMemoryService:
    return OpenVikingMemoryService(openclaw_service=openclaw_service)


@lru_cache(maxsize=1)
def get_mirofish_prediction_service() -> MiroFishPredictionService:
    return MiroFishPredictionService(engine=get_feature_settings().mirofish_engine)


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
    panel_settings = get_panel_settings()
    telegram_settings = get_telegram_settings()
    return PanelAccessService(
        secret=panel_settings.jwt_secret,
        base_url=panel_settings.base_url,
        issuer=panel_settings.jwt_issuer,
        audience=panel_settings.jwt_audience,
        default_ttl_seconds=max(30, min(panel_settings.magic_link_ttl_seconds, 3600)),
        max_ttl_seconds=max(30, min(panel_settings.magic_link_max_ttl_seconds, 86400)),
        telegram_bot_token=telegram_settings.bot_token,
        telegram_init_data_max_age_seconds=max(60, min(panel_settings.telegram_initdata_max_age_seconds, 86400)),
        allowed_uids=telegram_settings.allowed_uids,
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
    telegram_settings = get_telegram_settings()
    return TelegramNotifierService(
        bot_token=telegram_settings.bot_token,
        api_base=telegram_settings.api_base,
        timeout_seconds=max(1.0, min(telegram_settings.notify_timeout_seconds, 120.0)),
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
        secret_repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="admin_secret_records",
            model_cls=AdminSecretRecordRead,
        ),
        secret_cipher=get_admin_secret_cipher(),
    )


@lru_cache(maxsize=1)
def get_admin_secret_cipher() -> AdminSecretCipher:
    return AdminSecretCipher(secret_key=get_admin_settings().secret_key)


@lru_cache(maxsize=1)
def get_admin_auth_service() -> AdminAuthService:
    admin_settings = get_admin_settings()
    return AdminAuthService(
        secret=admin_settings.jwt_secret,
        bootstrap_key=admin_settings.bootstrap_key,
        issuer=admin_settings.jwt_issuer,
        audience=admin_settings.jwt_audience,
        default_ttl_seconds=max(60, min(admin_settings.token_ttl_seconds, 86400)),
        max_ttl_seconds=max(300, min(admin_settings.token_max_ttl_seconds, 604800)),
        allowed_roles=admin_settings.allowed_roles,
    )


def clear_dependency_caches() -> None:
    get_evaluation_service.cache_clear()
    get_report_service.cache_clear()
    get_variant_service.cache_clear()
    get_optimization_service.cache_clear()
    get_experiment_service.cache_clear()
    get_execution_service.cache_clear()
    get_openclaw_compat_service.cache_clear()
    get_openclaw_skill_service.cache_clear()
    get_claude_agent_service.cache_clear()
    get_mirofish_prediction_service.cache_clear()
    get_self_integration_service.cache_clear()
    get_panel_access_service.cache_clear()
    get_panel_audit_service.cache_clear()
    get_telegram_notifier_service.cache_clear()
    get_admin_config_service.cache_clear()
    get_admin_secret_cipher.cache_clear()
    get_admin_auth_service.cache_clear()
