from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path

from fastapi import Depends

from autoresearch.agent_protocol.capability_registry import CapabilityManifestRegistry
from autoresearch.agent_protocol.runtime_registry import RuntimeAdapterRegistry
from autoresearch.api.settings import (
    get_admin_settings,
    get_feature_settings,
    get_panel_settings,
    get_runtime_settings,
    get_study_workbench_settings,
    get_telegram_settings,
    get_upstream_watcher_settings,
)
from autoresearch.control_plane.contracts import (
    ControlPlaneApprovalGrantRead,
    ControlPlaneApprovalRead,
    ControlPlaneArtifactRead,
    ControlPlaneAuditEventRead,
    ControlPlanePromotionRead,
    ControlPlaneRunRead,
    ControlPlaneSessionRead,
    ControlPlaneTaskRead,
)
from autoresearch.control_plane.service import ControlPlaneRepositories, ControlPlaneService
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
from autoresearch.core.services.a2a_gateway import A2AGatewayService, A2ATaskRead
from autoresearch.core.services.agent_audit_trail import AgentAuditTrailService
from autoresearch.core.services.approval_decisions import ApprovalDecisionService
from autoresearch.core.services.approval_policy import ApprovalPolicyService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.aep_process_runtime_adapter import AepProcessRuntimeAdapterService
from autoresearch.core.services.autoresearch_planner import AutoResearchPlannerService
from autoresearch.core.services.capability_manifest_service import CapabilityManifestService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.claude_runtime_service import ClaudeRuntimeService
from autoresearch.core.services.claude_session_records import ClaudeSessionRecordService
from autoresearch.core.services.evaluations import EvaluationService
from autoresearch.core.services.executions import ExecutionService
from autoresearch.core.services.federation import (
    FederationLeaseRead,
    FederationService,
    FederationTaskRead,
)
from autoresearch.core.services.github_admin import GitHubAdminService
from autoresearch.core.services.github_ops import GitHubOpsService
from autoresearch.core.services.github_issue_service import GitHubIssueService
from autoresearch.core.services.governance_core import GovernanceCoreService, GovernanceRepositories
from autoresearch.core.services.governed_mcp import GovernedMCPService, ToolPermissionService
from autoresearch.core.services.hermes_gateway_bridge import HttpHermesGatewayTransport
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
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.core.services.study_workbench import StudyWorkbenchService
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.core.services.usage_quota import UsageLedgerEntryRead, UsageQuotaService
from autoresearch.core.services.upstream_watcher import UpstreamWatcherService
from autoresearch.core.services.variants import VariantService
from autoresearch.core.services.worker_schedule_service import WorkerScheduleService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.core.services.worker_inventory import WorkerInventoryService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.butler_agent_state import ButlerAgentStateService
from autoresearch.core.services.butler_dispatch import ButlerDispatchCenter, ButlerModelFillService
from autoresearch.core.services.butler_failure_review import ButlerFailureReviewService
from autoresearch.core.services.butler_router import ButlerIntentRouter
from autoresearch.core.services.butler_tool_broker import ButlerToolBroker
from autoresearch.core.services.excel_audit import ExcelAuditService
from autoresearch.core.repositories.excel_jobs import ExcelJobsRepository
from autoresearch.core.services.commission_engine import CommissionEngine
from autoresearch.core.services.security_audit import SecurityAuditService
from autoresearch.shared.models import (
    ClaudeAgentRunRead,
    ClaudeRuntimeSessionRecordRead,
    AdminAgentConfigRead,
    AdminChannelConfigRead,
    AdminConfigRevisionRead,
    AdminSecretRecordRead,
    ApprovalRequestRead,
    ButlerAgentStateRead,
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
    SessionEventRead,
    VariantRead,
    WorkerLeaseRead,
    WorkerQueueItemRead,
    WorkerRegistrationRead,
    WorkerRunScheduleRead,
)
from autoresearch.shared.governance_core import (
    GovernanceApprovalRead,
    GovernanceArtifactRead,
    GovernanceAuditEventRead,
    GovernanceRunRead,
    GovernanceTaskRead,
)
from autoresearch.shared.autoresearch_planner_contract import AutoResearchPlanRead
from autoresearch.shared.excel_audit_contract import ExcelAuditRead
from autoresearch.core.services.excel_ops import ExcelOpsService
from autoresearch.shared.manager_agent_contract import ManagerDispatchRead
from autoresearch.shared.store import SQLiteModelRepository
from autoresearch.storage.events import SQLiteSessionEventStore
from autoresearch.storage.postgres import PostgresSessionEventStore
from github_admin.contracts import GitHubAdminRunRead
from autoresearch.train.services.experiments import ExperimentService
from autoresearch.train.services.optimizations import OptimizationService
from integrations.apple_bridge.calendar import CalendarService
from orchestrator.mcp_context import MCPContextBlock


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _runtime_manifests_dir() -> Path:
    return _repo_root() / "configs" / "runtime_agents"


def _capability_manifests_dir() -> Path:
    return _repo_root() / "configs" / "capabilities"


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
def get_governance_core_service() -> GovernanceCoreService:
    return GovernanceCoreService(
        repositories=GovernanceRepositories(
            tasks=SQLiteModelRepository(
                db_path=_api_db_path(),
                table_name="governance_tasks",
                model_cls=GovernanceTaskRead,
            ),
            runs=SQLiteModelRepository(
                db_path=_api_db_path(),
                table_name="governance_runs",
                model_cls=GovernanceRunRead,
            ),
            approvals=SQLiteModelRepository(
                db_path=_api_db_path(),
                table_name="governance_approvals",
                model_cls=GovernanceApprovalRead,
            ),
            artifacts=SQLiteModelRepository(
                db_path=_api_db_path(),
                table_name="governance_artifacts",
                model_cls=GovernanceArtifactRead,
            ),
            audit_events=SQLiteModelRepository(
                db_path=_api_db_path(),
                table_name="governance_audit_events",
                model_cls=GovernanceAuditEventRead,
            ),
        )
    )


@lru_cache(maxsize=1)
def get_control_plane_service() -> ControlPlaneService:
    return ControlPlaneService(
        repositories=ControlPlaneRepositories(
            sessions=SQLiteModelRepository(
                db_path=_api_db_path(),
                table_name="control_plane_sessions",
                model_cls=ControlPlaneSessionRead,
            ),
            tasks=SQLiteModelRepository(
                db_path=_api_db_path(),
                table_name="control_plane_tasks",
                model_cls=ControlPlaneTaskRead,
            ),
            runs=SQLiteModelRepository(
                db_path=_api_db_path(),
                table_name="control_plane_runs",
                model_cls=ControlPlaneRunRead,
            ),
            approvals=SQLiteModelRepository(
                db_path=_api_db_path(),
                table_name="control_plane_approvals",
                model_cls=ControlPlaneApprovalRead,
            ),
            approval_grants=SQLiteModelRepository(
                db_path=_api_db_path(),
                table_name="control_plane_approval_grants",
                model_cls=ControlPlaneApprovalGrantRead,
            ),
            artifacts=SQLiteModelRepository(
                db_path=_api_db_path(),
                table_name="control_plane_artifacts",
                model_cls=ControlPlaneArtifactRead,
            ),
            audit_events=SQLiteModelRepository(
                db_path=_api_db_path(),
                table_name="control_plane_audit_events",
                model_cls=ControlPlaneAuditEventRead,
            ),
            promotions=SQLiteModelRepository(
                db_path=_api_db_path(),
                table_name="control_plane_promotions",
                model_cls=ControlPlanePromotionRead,
            ),
        ),
        worker_scheduler=get_worker_scheduler_service(),
        session_events=get_session_event_service(),
        failure_review_service=get_butler_failure_review_service(),
    )


@lru_cache(maxsize=1)
def get_butler_failure_review_service() -> ButlerFailureReviewService:
    return ButlerFailureReviewService(
        session_events=get_session_event_service(),
        rule_candidates_path=_repo_root() / "configs" / "butler" / "rule_candidates.yaml",
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
def get_youtube_oauth_service():
    from packages.entertainment_curator.youtube_oauth import YouTubeOAuthProfileRegistry

    return YouTubeOAuthProfileRegistry()


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
def get_approval_policy_service() -> ApprovalPolicyService:
    return ApprovalPolicyService(policy_path=_repo_root() / "configs" / "approval_policy.yaml")


@lru_cache(maxsize=1)
def get_butler_tool_broker_service() -> ButlerToolBroker:
    return ButlerToolBroker(
        repo_root=_repo_root(),
        mcp_registry=get_capability_provider_registry(),
    )


@lru_cache(maxsize=1)
def get_github_ops_service() -> GitHubOpsService:
    return GitHubOpsService(
        repo_root=_repo_root(),
        approval_policy=get_approval_policy_service(),
        approval_store=get_approval_store_service(),
    )


@lru_cache(maxsize=1)
def get_butler_agent_state_service() -> ButlerAgentStateService:
    return ButlerAgentStateService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="butler_agent_states",
            model_cls=ButlerAgentStateRead,
        )
    )


@lru_cache(maxsize=1)
def get_security_audit_service() -> SecurityAuditService:
    return SecurityAuditService(
        repo_root=_repo_root(),
        control_plane=get_control_plane_service(),
        worker_scheduler=get_worker_scheduler_service(),
        approval_store=get_approval_store_service(),
    )


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
    settings = get_runtime_settings()
    return WorkerSchedulerService(
        worker_registry=get_worker_registry_service(),
        butler_agent_state=get_butler_agent_state_service(),
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
        retry_backoff_seconds=settings.worker_retry_backoff_seconds,
        session_events=get_session_event_service(),
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
def get_study_workbench_service() -> StudyWorkbenchService:
    return StudyWorkbenchService(
        settings=get_study_workbench_settings(),
        state_db_path=_api_db_path(),
        artifact_root=_api_db_path().parent / "study_workbench",
    )


@lru_cache(maxsize=1)
def get_worker_inventory_service() -> WorkerInventoryService:
    return WorkerInventoryService(
        worker_registry=get_worker_registry_service(),
        worker_scheduler=get_worker_scheduler_service(),
        butler_agent_state=get_butler_agent_state_service(),
    )


@lru_cache(maxsize=1)
def get_openclaw_compat_service() -> OpenClawCompatService:
    return OpenClawCompatService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="openclaw_sessions",
            model_cls=OpenClawSessionRead,
        ),
        session_events=get_session_event_service(),
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


def _aep_runtime(
    *,
    runtime_id: str,
    agent_id: str,
    display_name: str,
    optional_dependencies: list[str] | None = None,
) -> AepProcessRuntimeAdapterService:
    return AepProcessRuntimeAdapterService(
        repo_root=_repo_root(),
        runtime_id=runtime_id,
        agent_id=agent_id,
        display_name=display_name,
        optional_dependencies=optional_dependencies,
    )


@lru_cache(maxsize=1)
def get_openhands_runtime_adapter_service() -> AepProcessRuntimeAdapterService:
    return _aep_runtime(
        runtime_id="openhands",
        agent_id="openhands",
        display_name="OpenHands coding worker",
    )


@lru_cache(maxsize=1)
def get_crewai_runtime_adapter_service() -> AepProcessRuntimeAdapterService:
    return _aep_runtime(
        runtime_id="crewai",
        agent_id="agent_reach_crewai_researcher",
        display_name="CrewAI multi-agent worker",
        optional_dependencies=["crewai"],
    )


@lru_cache(maxsize=1)
def get_haystack_runtime_adapter_service() -> AepProcessRuntimeAdapterService:
    return _aep_runtime(
        runtime_id="haystack",
        agent_id="haystack_demo",
        display_name="Haystack knowledge worker",
        optional_dependencies=["haystack"],
    )


@lru_cache(maxsize=1)
def get_langgraph_runtime_adapter_service() -> AepProcessRuntimeAdapterService:
    return _aep_runtime(
        runtime_id="langgraph",
        agent_id="langgraph_order_flow",
        display_name="LangGraph workflow worker",
        optional_dependencies=["langgraph"],
    )


@lru_cache(maxsize=1)
def get_a2a_runtime_adapter_service() -> AepProcessRuntimeAdapterService:
    return _aep_runtime(
        runtime_id="a2a",
        agent_id="a2a_bridge",
        display_name="A2A federated agent bridge",
        optional_dependencies=["a2a"],
    )


@lru_cache(maxsize=1)
def get_runtime_adapter_registry_service() -> RuntimeAdapterServiceRegistry:
    manifest_registry = RuntimeAdapterRegistry(_runtime_manifests_dir())
    return RuntimeAdapterServiceRegistry(
        manifest_registry=manifest_registry,
        factories={
            "openclaw": get_openclaw_runtime_adapter_service,
            "hermes": get_hermes_runtime_adapter_service,
            "openhands": get_openhands_runtime_adapter_service,
            "crewai": get_crewai_runtime_adapter_service,
            "haystack": get_haystack_runtime_adapter_service,
            "langgraph": get_langgraph_runtime_adapter_service,
            "a2a": get_a2a_runtime_adapter_service,
        },
    )


def get_runtime_adapter_service(runtime_id: str = "openclaw") -> RuntimeAdapterContract:
    return get_runtime_adapter_registry_service().get(runtime_id)


@lru_cache(maxsize=1)
def get_capability_manifest_service() -> CapabilityManifestService:
    return CapabilityManifestService(
        registry=CapabilityManifestRegistry(_capability_manifests_dir()),
        runtime_registry=get_runtime_adapter_registry_service(),
    )


@lru_cache(maxsize=1)
def get_a2a_gateway_service() -> A2AGatewayService:
    return A2AGatewayService(
        capability_service=get_capability_manifest_service(),
        task_repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="a2a_tasks",
            model_cls=A2ATaskRead,
        ),
    )


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
        ),
        session_events=get_session_event_service(),
    )


@lru_cache(maxsize=1)
def get_session_event_service() -> SessionEventService:
    settings = get_runtime_settings()
    postgres_dsn = os.getenv("AUTORESEARCH_POSTGRES_DSN", "").strip()
    if settings.is_production:
        if not postgres_dsn:
            raise RuntimeError("production SessionEvent store requires AUTORESEARCH_POSTGRES_DSN")
        return SessionEventService(event_store=PostgresSessionEventStore(postgres_dsn))
    if os.getenv("AUTORESEARCH_SESSION_EVENT_STORE", "").strip().lower() == "sqlite":
        return SessionEventService(event_store=SQLiteSessionEventStore(_api_db_path()))
    return SessionEventService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="session_events",
            model_cls=SessionEventRead,
        )
    )


@lru_cache(maxsize=1)
def get_usage_quota_service() -> UsageQuotaService:
    return UsageQuotaService(
        repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="usage_ledger",
            model_cls=UsageLedgerEntryRead,
        ),
        policy_path=_repo_root() / "configs" / "quota_policy.yaml",
        session_events=get_session_event_service(),
    )


@lru_cache(maxsize=1)
def get_tool_permission_service() -> ToolPermissionService:
    return ToolPermissionService(policy_path=_repo_root() / "configs" / "tool_permissions.yaml")


@lru_cache(maxsize=1)
def get_governed_mcp_service() -> GovernedMCPService:
    return GovernedMCPService(
        servers_path=_repo_root() / "configs" / "mcp_servers.yaml",
        permission_service=get_tool_permission_service(),
        quota_service=get_usage_quota_service(),
        approval_store=get_approval_store_service(),
        session_events=get_session_event_service(),
        failure_review_service=get_butler_failure_review_service(),
    )


@lru_cache(maxsize=1)
def get_federation_service() -> FederationService:
    return FederationService(
        peers_path=_repo_root() / "configs" / "federation_peers.yaml",
        lease_repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="federation_leases",
            model_cls=FederationLeaseRead,
        ),
        task_repository=SQLiteModelRepository(
            db_path=_api_db_path(),
            table_name="federation_tasks",
            model_cls=FederationTaskRead,
        ),
        control_plane=get_control_plane_service(),
        capability_service=get_capability_manifest_service(),
        quota_service=get_usage_quota_service(),
        session_events=get_session_event_service(),
        failure_review_service=get_butler_failure_review_service(),
    )


@lru_cache(maxsize=1)
def get_hermes_gateway_transport() -> HttpHermesGatewayTransport | None:
    base_url = (os.getenv("AUTORESEARCH_HERMES_GATEWAY_BASE_URL") or "").strip()
    if not base_url:
        return None
    timeout_raw = os.getenv("AUTORESEARCH_HERMES_GATEWAY_TIMEOUT_SECONDS", "10")
    try:
        timeout_seconds = float(timeout_raw)
    except ValueError:
        timeout_seconds = 10.0
    return HttpHermesGatewayTransport(
        base_url=base_url,
        health_path=(os.getenv("AUTORESEARCH_HERMES_GATEWAY_HEALTH_PATH") or "/health").strip() or "/health",
        timeout_seconds=max(1.0, min(timeout_seconds, 120.0)),
    )


def get_approval_decision_service(
    approval_store: ApprovalStoreService = Depends(get_approval_store_service),
    worker_scheduler: WorkerSchedulerService = Depends(get_worker_scheduler_service),
    hermes_transport: HttpHermesGatewayTransport | None = Depends(get_hermes_gateway_transport),
    github_ops_service: GitHubOpsService = Depends(get_github_ops_service),
) -> ApprovalDecisionService:
    return ApprovalDecisionService(
        approval_store=approval_store,
        worker_scheduler=worker_scheduler,
        hermes_transport=hermes_transport,
        github_ops_service=github_ops_service,
        session_events=get_session_event_service(),
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
        proxy_url=telegram_settings.proxy_url,
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
    _safe_cache_clear(get_governance_core_service)
    _safe_cache_clear(get_control_plane_service)
    _safe_cache_clear(get_youtube_agent_service)
    _safe_cache_clear(get_youtube_oauth_service)
    _safe_cache_clear(get_manager_agent_service)
    _safe_cache_clear(get_approval_policy_service)
    _safe_cache_clear(get_butler_tool_broker_service)
    _safe_cache_clear(get_github_ops_service)
    _safe_cache_clear(get_butler_agent_state_service)
    _safe_cache_clear(get_security_audit_service)
    _safe_cache_clear(get_github_admin_service)
    _safe_cache_clear(get_github_issue_service)
    _safe_cache_clear(get_worker_registry_service)
    _safe_cache_clear(get_worker_scheduler_service)
    _safe_cache_clear(get_worker_schedule_service)
    _safe_cache_clear(get_openclaw_compat_service)
    _safe_cache_clear(get_openclaw_memory_service)
    _safe_cache_clear(get_session_event_service)
    _safe_cache_clear(get_usage_quota_service)
    _safe_cache_clear(get_tool_permission_service)
    _safe_cache_clear(get_governed_mcp_service)
    _safe_cache_clear(get_federation_service)
    _safe_cache_clear(get_capability_provider_registry)
    _safe_cache_clear(get_managed_skill_registry_service)
    _safe_cache_clear(get_openclaw_skill_service)
    _safe_cache_clear(get_openclaw_runtime_adapter_service)
    _safe_cache_clear(get_hermes_runtime_adapter_service)
    _safe_cache_clear(get_openhands_runtime_adapter_service)
    _safe_cache_clear(get_crewai_runtime_adapter_service)
    _safe_cache_clear(get_haystack_runtime_adapter_service)
    _safe_cache_clear(get_langgraph_runtime_adapter_service)
    _safe_cache_clear(get_a2a_runtime_adapter_service)
    _safe_cache_clear(get_runtime_adapter_registry_service)
    _safe_cache_clear(get_capability_manifest_service)
    _safe_cache_clear(get_a2a_gateway_service)
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
    _safe_cache_clear(get_butler_model_fill_service)
    _safe_cache_clear(get_butler_dispatch_center)
    _safe_cache_clear(get_hermes_gateway_transport)
    _safe_cache_clear(get_approval_decision_service)


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


@lru_cache(maxsize=1)
def get_excel_ops_service() -> ExcelOpsService:
    return ExcelOpsService(
        repository=ExcelJobsRepository(db_path=_api_db_path()),
        commission_engine=CommissionEngine(),
        repo_root=_repo_root(),
    )


def _safe_cache_clear(func: object) -> None:
    if callable(func) and hasattr(func, "cache_clear"):
        func.cache_clear()


@lru_cache(maxsize=1)
def get_butler_router() -> ButlerIntentRouter:
    return ButlerIntentRouter()


@lru_cache(maxsize=1)
def get_butler_model_fill_service() -> ButlerModelFillService:
    provider = os.getenv("AUTORESEARCH_BUTLER_MODEL_PROVIDER", "openai").strip().lower()
    enabled = os.getenv("AUTORESEARCH_BUTLER_MODEL_FILL_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    backend = None
    if enabled:
        from autoresearch.llm.gateway import create_gateway_backend

        backend = create_gateway_backend(
            provider=provider,
            model=os.getenv("AUTORESEARCH_BUTLER_MODEL_NAME", None),
        )
    return ButlerModelFillService(backend=backend, enabled=enabled)


@lru_cache(maxsize=1)
def get_butler_dispatch_center() -> ButlerDispatchCenter:
    return ButlerDispatchCenter(
        rule_router=get_butler_router(),
        model_fill=get_butler_model_fill_service(),
    )
