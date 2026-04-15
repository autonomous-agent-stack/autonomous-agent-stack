"""
Commission Engine - Deterministic Rule Execution Interface

IMPORTANT: This module provides a deterministic interface for commission calculation.
It does NOT contain business logic - business rules must be provided via contracts.

When business assets arrive (requirement #4), this engine will:
- Load rule contracts from configuration
- Execute rules deterministically on normalized Excel data
- Return structured calculation results
- Never use LLM/freeform reasoning for money math

Current state: Awaiting business rule contracts
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from autoresearch.shared.models import StrictModel

logger = logging.getLogger(__name__)


class CommissionEngineStatus(str, Enum):
    """Status of commission engine operations."""
    READY = "ready"
    BLOCKED_AWAITING_CONTRACTS = "blocked_awaiting_contracts"
    BLOCKED_INVALID_CONTRACTS = "blocked_invalid_contracts"
    ERROR = "error"


@dataclass(frozen=True)
class CommissionRuleContract:
    """
    Contract for a single commission calculation rule.

    Business must provide:
    - rule_id: Unique identifier
    - name: Human-readable name
    - formula: Deterministic calculation formula (TBD based on business requirements)
    - conditions: When this rule applies
    - priority: Execution order
    """
    rule_id: str
    name: str
    formula: str
    conditions: dict[str, Any]
    priority: int


@dataclass(frozen=True)
class CommissionCalculationRequest:
    """
    Request for commission calculation.

    Contains normalized input data from Excel files.
    Schema will be defined by business-provided contracts.
    """
    job_id: str
    input_data: dict[str, Any]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class CommissionCalculationResult:
    """
    Result of deterministic commission calculation.

    When business rules are implemented:
    - calculated_values: Commission amounts per agent/transaction
    - applied_rules: Which rules were executed
    - intermediate_steps: Audit trail of calculations
    - status: Success/failure with explicit error details
    """
    job_id: str
    status: CommissionEngineStatus
    calculated_values: dict[str, Any]
    applied_rules: list[str]
    intermediate_steps: list[dict[str, Any]]
    error_message: str | None = None


class CommissionCalculationError(Exception):
    """Raised when calculation fails deterministically."""
    pass


class CommissionEngineContractMissing(CommissionCalculationError):
    """Raised when business rule contracts are not provided."""
    pass


class CommissionEngine:
    """
    Deterministic commission calculation engine.

    IMPORTANT: This is a scaffold. Business rules must be provided
    via requirement #4 assets before any real calculations occur.

    Current behavior:
    - All calculations return BLOCKED_AWAITING_CONTRACTS status
    - Explicit error messages explain what's missing
    - No silent failures or fallback calculations

    Future behavior (when business assets arrive):
    - Load rule contracts from config/fixtures
    - Validate contracts at startup
    - Execute rules deterministically
    - Return detailed audit trail
    """

    def __init__(
        self,
        contracts_dir: Path | None = None,
        strict_mode: bool = True,
    ) -> None:
        """
        Initialize commission engine.

        Args:
            contracts_dir: Directory containing business rule contracts
            strict_mode: If True, refuse to calculate without valid contracts
        """
        self._contracts_dir = contracts_dir or Path("tests/fixtures/requirement4_contracts")
        self._strict_mode = strict_mode
        self._contracts_loaded = False
        self._rules: dict[str, CommissionRuleContract] = {}

        logger.info(
            "CommissionEngine initialized (strict_mode=%s, contracts_dir=%s)",
            strict_mode,
            contracts_dir,
        )

    def load_contracts(self) -> CommissionEngineStatus:
        """
        Load business rule contracts from filesystem.

        Returns:
            READY if contracts loaded successfully
            BLOCKED_AWAITING_CONTRACTS if contracts directory missing/empty
            BLOCKED_INVALID_CONTRACTS if contracts fail validation
        """
        if not self._contracts_dir.exists():
            logger.warning("Contracts directory not found: %s", self._contracts_dir)
            return CommissionEngineStatus.BLOCKED_AWAITING_CONTRACTS

        contract_files = list(self._contracts_dir.glob("*.json"))
        if not contract_files:
            logger.warning("No contract files found in: %s", self._contracts_dir)
            return CommissionEngineStatus.BLOCKED_AWAITING_CONTRACTS

        # TODO: Load and validate contracts when business provides them
        # For now, we acknowledge files exist but don't have schemas
        logger.info("Found %d contract files (awaiting business schema)", len(contract_files))
        return CommissionEngineStatus.BLOCKED_AWAITING_CONTRACTS

    def calculate(
        self,
        request: CommissionCalculationRequest,
    ) -> CommissionCalculationResult:
        """
        Calculate commissions deterministically.

        Args:
            request: Calculation request with normalized input data

        Returns:
            Calculation result with status and values (or error details)

        Raises:
            CommissionEngineContractMissing: If contracts not loaded and strict_mode=True
        """
        contract_status = self.load_contracts()

        if contract_status != CommissionEngineStatus.READY:
            if self._strict_mode:
                return CommissionCalculationResult(
                    job_id=request.job_id,
                    status=CommissionEngineStatus.BLOCKED_AWAITING_CONTRACTS,
                    calculated_values={},
                    applied_rules=[],
                    intermediate_steps=[],
                    error_message=(
                        f"Commission calculation blocked: {contract_status.value}. "
                        f"Business rule contracts must be provided in {self._contracts_dir}. "
                        "See docs/requirement4/ for contract specification."
                    ),
                )
            # Non-strict mode: return placeholder (never used in production)
            logger.warning("Non-strict mode: returning empty calculation result")

        return CommissionCalculationResult(
            job_id=request.job_id,
            status=CommissionEngineStatus.BLOCKED_AWAITING_CONTRACTS,
            calculated_values={},
            applied_rules=[],
            intermediate_steps=[],
            error_message=(
                "Commission calculation requires business rule contracts. "
                "This is a scaffold implementation - see requirement #4."
            ),
        )

    def validate_contracts(
        self,
        contracts: list[CommissionRuleContract],
    ) -> list[str]:
        """
        Validate business rule contracts.

        Args:
            contracts: List of contracts to validate

        Returns:
            List of validation error messages (empty if all valid)
        """
        errors = []

        for contract in contracts:
            if not contract.rule_id:
                errors.append(f"Contract missing rule_id")
            if not contract.formula:
                errors.append(f"Contract {contract.rule_id}: missing formula")
            # TODO: Add more validation when business provides schema

        return errors

    def get_status(self) -> dict[str, Any]:
        """
        Get engine status and diagnostics.

        Returns:
            Status dict with readiness info
        """
        contract_status = self.load_contracts()

        return {
            "status": contract_status.value,
            "contracts_dir": str(self._contracts_dir),
            "contracts_loaded": self._contracts_loaded,
            "rules_count": len(self._rules),
            "strict_mode": self._strict_mode,
            "ready_for_calculation": contract_status == CommissionEngineStatus.READY,
        }
