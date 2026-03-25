from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from autoresearch.core.repositories import SQLiteEvaluationRepository
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.executions import ExecutionService
from autoresearch.core.services.evaluations import EvaluationService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.reports import ReportService
from autoresearch.core.services.self_integration import SelfIntegrationService
from autoresearch.core.services.variants import VariantService
from autoresearch.shared.models import (
    ClaudeAgentRunRead,
    ExecutionRead,
    ExperimentRead,
    IntegrationDiscoveryRead,
    IntegrationPromotionRead,
    IntegrationPrototypeRead,
    OpenClawSessionRead,
    OptimizationRead,
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
