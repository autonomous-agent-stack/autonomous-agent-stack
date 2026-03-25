from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from autoresearch.core.repositories import SQLiteEvaluationRepository
from autoresearch.core.services.evaluations import EvaluationService
from autoresearch.core.services.reports import ReportService
from autoresearch.core.services.variants import VariantService
from autoresearch.shared.store import InMemoryRepository
from autoresearch.train.services.experiments import ExperimentService
from autoresearch.train.services.optimizations import OptimizationService


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _evaluation_db_path() -> Path:
    configured = os.getenv("AUTORESEARCH_API_DB_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return (_repo_root() / "artifacts" / "api" / "evaluations.sqlite3").resolve()


@lru_cache(maxsize=1)
def get_evaluation_service() -> EvaluationService:
    service = EvaluationService(
        repository=SQLiteEvaluationRepository(db_path=_evaluation_db_path()),
        repo_root=_repo_root(),
    )
    service.recover_interrupted()
    return service


@lru_cache(maxsize=1)
def get_report_service() -> ReportService:
    return ReportService(repository=InMemoryRepository())


@lru_cache(maxsize=1)
def get_variant_service() -> VariantService:
    return VariantService(repository=InMemoryRepository())


@lru_cache(maxsize=1)
def get_optimization_service() -> OptimizationService:
    return OptimizationService(repository=InMemoryRepository())


@lru_cache(maxsize=1)
def get_experiment_service() -> ExperimentService:
    return ExperimentService(repository=InMemoryRepository())
