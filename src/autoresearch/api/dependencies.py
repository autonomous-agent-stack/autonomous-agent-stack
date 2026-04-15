from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import Depends

from autoresearch.agent_protocol.runtime_registry import RuntimeAdapterRegistry
from autoresearch.api.settings import (
    get_admin_settings,
    get_feature_settings,
    get_panel_settings,
    get_runtime_settings,
    get_telegram_settings,
    get_upstream_watcher_settings,
)
from autoresearch.agents.opensource_searcher import GitHubSearcher
from autoresearch.agents.manager_agent import ManagerAgentService
from autoresearch.core.adapters import (
    AppleCalendarAdapter,
    CapabilityProviderRegistry,
    GitHubSearchAdapter,
    MCPContextProviderAdapter,
    OpenClawSkillProviderAdapter,
)
from autoresearch.github_assistant.service import GitHubAssistantService, GitHubAssistantServiceRegistry
from autoresearch.core.repositories import SQLiteEvaluationRepository
from autoresearch.core.services.admin_auth import AdminAuthService
from autoresearch.core.services.admin_config import AdminConfigService
from autoresearch.core.services.admin_secrets import AdminSecretCipher
from autoresearch.core.services.agent_audit_trail import AgentAuditTrailService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.autoresearch_planner import AutoResearchPlannerService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.claude_runtime_service import ClaudeRuntimeService
from autoresearch.core.services.claude_session_records import ClaudeSessionRecordService
from autoresearch.core.services.evaluations import EvaluationService
from autoresearch.core.services.executions import ExecutionService
from autoresearch.core.services.github_admin import GitHubAdminService
from autoresearch.core.services.github_issue_service import GitHubIssueService
from autoresearch.core.services.mirofish_prediction import MiroFishPredictionService
from autoresearch.core.services.managed_skill_registry import ManagedSkillRegistryService
from autoresearch.core.services.hermes_runtime_adapter import HermesRuntimeAdapterService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_memory import OpenClawMemoryService
from autoresearch.core.services.openclaw_runtime_adapter import OpenClawRuntimeAdapterService
from autoresearch.core.services.runtime_adapter_contract import RuntimeAdapterContract
from autoresearch.core.services.runtime_adapter_registry import RuntimeAdapterServiceRegistry
from autoresearch.core.services.openclaw_skills import OpenClawSkillService
from autoresearch.core.services.openviking_memory import OpenVikingMemoryService
from autoresearch.core.services.panel_access import PanelAccessService
from autoresearch.core.services.panel_audit import PanelAuditService
from autoresearch.core.services.reports import ReportService
from autoresearch.core.services.self_integration import SelfIntegrationService
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.core.services.upstream_watcher import UpstreamWatcherService
from autoresearch.core.services.variants import VariantService
from autoresearch.core.services.commission_engine import CommissionEngine
from autoresearch.core.services.excel_ops import ExcelOpsService
from autoresearch.core.services.worker_schedule_service import WorkerScheduleService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.youtube_agent import YouTubeAgentService
from autoresearch.core.services.butler_router import ButlerIntentRouter
from autoresearch.core.services.excel_audit import ExcelAuditService
from autoresearch.core.repositories.excel_jobs import ExcelJobsRepository
from autoresearch.shared.models import (
    ClaudeAgentRunRead,
    ClaudeRuntimeSessionRecordRead,
    AdminAgentConfigRead,
    AdminChannelConfigRead,
    AdminConfigRevisionRead,
    AdminSecretRecordRead,
    ApprovalRequestRead,
    ExecutionRead,
    ExperimentRead,
    IntegrationDiscoveryRead,
    IntegrationPromotionRead,
    IntegrationPrototypeRead,
    ManagedSkillInstallRead,
    OpenClawMemoryRecordRead,
    OpenClawSessionRead,
    OptimizationRead,
    PanelAuditLogRead,
    ReportRead,
    VariantRead,
    WorkerLeaseRead,
    WorkerQueueItemRead,
    WorkerRegistrationRead,
    WorkerRunScheduleRead,
    YouTubeDigestRead,
    YouTubeRunRead,
    YouTubeSubscriptionRead,
    YouTubeTranscriptRead,
    YouTubeVideoRead,
)
from autoresearch.shared.autoresearch_planner_contract import AutoResearchPlanRead
from autoresearch.shared.excel_audit_contract import ExcelAuditRead
from autoresearch.shared.manager_agent_contract import ManagerDispatchRead
from autoresearch.shared.store import SQLiteModelRepository
from github_admin.contracts import GitHubAdminRunRead
from autoresearch.train.services.experiments import ExperimentService
from autoresearch.train.services.optimizations import OptimizationService
from integrations.apple_bridge.calendar import CalendarService
from orchestrator.mcp_context import MCPContextBlock


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _runtime_manifests_dir() -> Path:
    return _repo_root() / "configs" / "runtime_agents"


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
def get_youtube_agent_service():
    from autoresearch.core.repositories import SQLiteYouTubeRepository
    from autoresearch.core.services.youtube_agent import YouTubeAgentService

    return YouTubeAgentService(
        repository=SQLiteYouTubeRepository(db_path=_api_db_path()),
        repo_root=_repo_root(),
    )


@lru_cache(maxsize=1)
def get_autoresearch_planner_service() -> AutoResearchPlannerService:
    return AutoResearchPlannerService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="autoresearch_plans",
            model_cls=AutoResearchPlanRead,
        ),
        repo_root=_repo_root(),
        upstream_watcher=get_upstream_watcher_service(),
    )


@lru_cache(maxsize=1)
def get_manager_agent_service() -> ManagerAgentService:
    return ManagerAgentService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="manager_agent_dispatches",
            model_cls=ManagerDispatchRead,
        ),
        repo_root=_repo_root(),
    )


@lru_cache(maxsize=1)
def get_github_issue_service() -> GitHubIssueService:
    return GitHubIssueService(repo_root=_repo_root())


@lru_cache(maxsize=1)
def get_github_assistant_service_registry() -> GitHubAssistantServiceRegistry:
    return GitHubAssistantServiceRegistry(repo_root=_repo_root())


def get_github_assistant_service(profile: str | None = None) -> GitHubAssistantService:
    return get_github_assistant_service_registry().get(profile)


@lru_cache(maxsize=1)
def get_github_admin_service() -> GitHubAdminService:
    return GitHubAdminService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="github_admin_runs",
            model_cls=GitHubAdminRunRead,
        ),
        repo_root=_repo_root(),
    )


@lru_cache(maxsize=1)
def get_worker_registry_service() -> WorkerRegistryService:
    return WorkerRegistryService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="worker_registrations",
            model_cls=WorkerRegistrationRead,
        )
    )


@lru_cache(maxsize=1)
def get_worker_scheduler_service() -> WorkerSchedulerService:
    return WorkerSchedulerService(
        worker_registry=get_worker_registry_service(),
        queue_repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="worker_run_queue",
            model_cls=WorkerQueueItemRead,
        ),
        lease_repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="worker_leases",
            model_cls=WorkerLeaseRead,
        ),
    )


@lru_cache(maxsize=1)
def get_worker_schedule_service() -> WorkerScheduleService:
    return WorkerScheduleService(
        worker_scheduler=get_worker_scheduler_service(),
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="worker_schedules",
            model_cls=WorkerRunScheduleRead,
        ),
    )


@lru_cache(maxsize=1)
def get_excel_ops_service() -> ExcelOpsService:
    repo_root = _repo_root()
    return ExcelOpsService(
        repository=ExcelJobsRepository(db_path=_api_db_path()),
        commission_engine=CommissionEngine(
            contracts_dir=repo_root / "tests" / "fixtures" / "requirement4_contracts",
            strict_mode=True,
        ),
        repo_root=repo_root,
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
    managed_registry = get_managed_skill_registry_service()
    skill_roots = list(feature_settings.openclaw_skill_dirs)
    managed_root = managed_registry.active_root
    if skill_roots:
        if managed_root not in skill_roots:
            skill_roots.append(managed_root)
    return OpenClawSkillService(
        repo_root=_repo_root(),
        skill_roots=skill_roots or None,
        managed_skill_roots=[managed_root],
        managed_skill_install_status_resolver=managed_registry.get_install_status,
        managed_skill_state_file_name=managed_registry.runtime_state_name,
        max_skill_file_bytes=max(8_192, min(feature_settings.openclaw_skill_max_bytes, 2_000_000)),
        max_skills_per_root=max(1, min(feature_settings.openclaw_skill_max_per_root, 10_000)),
    )


@lru_cache(maxsize=1)
def get_openclaw_runtime_adapter_service() -> OpenClawRuntimeAdapterService:
    return OpenClawRuntimeAdapterService(
        openclaw_service=get_openclaw_compat_service(),
        claude_service=get_claude_agent_service(),
    )


@lru_cache(maxsize=1)
def get_hermes_runtime_adapter_service() -> HermesRuntimeAdapterService:
    return HermesRuntimeAdapterService(
        openclaw_service=get_openclaw_compat_service(),
        claude_service=get_claude_agent_service(),
    )


@lru_cache(maxsize=1)
def get_runtime_adapter_registry_service() -> RuntimeAdapterServiceRegistry:
    manifest_registry = RuntimeAdapterRegistry(_runtime_manifests_dir())
    return RuntimeAdapterServiceRegistry(
        manifest_registry=manifest_registry,
        factories={
            "openclaw": get_openclaw_runtime_adapter_service,
            "hermes": get_hermes_runtime_adapter_service,
        },
    )


def get_runtime_adapter_service(runtime_id: str = "openclaw") -> RuntimeAdapterContract:
    return get_runtime_adapter_registry_service().get(runtime_id)


@lru_cache(maxsize=1)
def get_managed_skill_registry_service() -> ManagedSkillRegistryService:
    feature_settings = get_feature_settings()
    return ManagedSkillRegistryService(
        repo_root=_repo_root(),
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="managed_skill_installs",
            model_cls=ManagedSkillInstallRead,
        ),
        quarantine_root=feature_settings.managed_skill_quarantine_dir,
        active_root=feature_settings.managed_skill_active_dir,
        trusted_signers=feature_settings.managed_skill_trusted_signers,
        allowed_capabilities=feature_settings.managed_skill_allowed_capabilities,
        manifest_name=feature_settings.managed_skill_manifest_name,
        max_skill_file_bytes=max(8_192, min(feature_settings.openclaw_skill_max_bytes, 2_000_000)),
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


@lru_cache(maxsize=1)
def get_claude_session_record_service() -> ClaudeSessionRecordService:
    return ClaudeSessionRecordService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="claude_runtime_session_records",
            model_cls=ClaudeRuntimeSessionRecordRead,
        )
    )


@lru_cache(maxsize=1)
def get_claude_runtime_service() -> ClaudeRuntimeService:
    return ClaudeRuntimeService(
        agent_service=get_claude_agent_service(),
        session_record_service=get_claude_session_record_service(),
    )


def get_openviking_memory_service(
    openclaw_service: OpenClawCompatService = Depends(get_openclaw_compat_service),
) -> OpenVikingMemoryService:
    return OpenVikingMemoryService(openclaw_service=openclaw_service)


@lru_cache(maxsize=1)
def get_openclaw_memory_service() -> OpenClawMemoryService:
    return OpenClawMemoryService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="openclaw_long_term_memories",
            model_cls=OpenClawMemoryRecordRead,
        ),
        openclaw_service=get_openclaw_compat_service(),
    )


@lru_cache(maxsize=1)
def get_approval_store_service() -> ApprovalStoreService:
    return ApprovalStoreService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="approval_requests",
            model_cls=ApprovalRequestRead,
        )
    )


@lru_cache(maxsize=1)
def get_capability_provider_registry() -> CapabilityProviderRegistry:
    registry = CapabilityProviderRegistry()
    registry.register_many(
        [
            AppleCalendarAdapter(CalendarService()),
            GitHubSearchAdapter(GitHubSearcher()),
            OpenClawSkillProviderAdapter(get_openclaw_skill_service()),
            MCPContextProviderAdapter(MCPContextBlock()),
        ]
    )
    return registry


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
        mini_app_url=panel_settings.mini_app_url,
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
def get_agent_audit_trail_service() -> AgentAuditTrailService:
    return AgentAuditTrailService(
        repo_root=_repo_root(),
        planner_service=get_autoresearch_planner_service(),
        manager_service=get_manager_agent_service(),
        agent_service=get_claude_agent_service(),
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
def get_upstream_watcher_service() -> UpstreamWatcherService:
    settings = get_upstream_watcher_settings()
    return UpstreamWatcherService(
        upstream_url=settings.upstream_url,
        workspace_root=settings.workspace_root,
        max_commits=max(1, min(settings.max_commits, 20)),
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
    _safe_cache_clear(get_evaluation_service)
    _safe_cache_clear(get_report_service)
    _safe_cache_clear(get_variant_service)
    _safe_cache_clear(get_optimization_service)
    _safe_cache_clear(get_experiment_service)
    _safe_cache_clear(get_execution_service)
    _safe_cache_clear(get_youtube_agent_service)
    _safe_cache_clear(get_manager_agent_service)
    _safe_cache_clear(get_github_admin_service)
    _safe_cache_clear(get_github_issue_service)
    _safe_cache_clear(get_worker_registry_service)
    _safe_cache_clear(get_worker_scheduler_service)
    _safe_cache_clear(get_worker_schedule_service)
    _safe_cache_clear(get_openclaw_compat_service)
    _safe_cache_clear(get_openclaw_memory_service)
    _safe_cache_clear(get_capability_provider_registry)
    _safe_cache_clear(get_managed_skill_registry_service)
    _safe_cache_clear(get_openclaw_skill_service)
    _safe_cache_clear(get_openclaw_runtime_adapter_service)
    _safe_cache_clear(get_hermes_runtime_adapter_service)
    _safe_cache_clear(get_runtime_adapter_registry_service)
    _safe_cache_clear(get_claude_agent_service)
    _safe_cache_clear(get_claude_session_record_service)
    _safe_cache_clear(get_claude_runtime_service)
    _safe_cache_clear(get_mirofish_prediction_service)
    _safe_cache_clear(get_self_integration_service)
    _safe_cache_clear(get_panel_access_service)
    _safe_cache_clear(get_panel_audit_service)
    _safe_cache_clear(get_agent_audit_trail_service)
    _safe_cache_clear(get_telegram_notifier_service)
    _safe_cache_clear(get_upstream_watcher_service)
    _safe_cache_clear(get_admin_config_service)
    _safe_cache_clear(get_admin_secret_cipher)
    _safe_cache_clear(get_admin_auth_service)
    _safe_cache_clear(get_excel_audit_service)
    _safe_cache_clear(get_excel_ops_service)
    _safe_cache_clear(get_butler_router)


@lru_cache(maxsize=1)
def get_excel_audit_service() -> ExcelAuditService:
    return ExcelAuditService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="excel_audits",
            model_cls=ExcelAuditRead,
        ),
        repo_root=_repo_root(),
    )


def _safe_cache_clear(func: object) -> None:
    if callable(func) and hasattr(func, "cache_clear"):
        func.cache_clear()


@lru_cache(maxsize=1)
def get_butler_router() -> ButlerIntentRouter:
    return ButlerIntentRouter()
