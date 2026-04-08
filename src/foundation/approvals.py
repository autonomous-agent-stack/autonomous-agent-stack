"""Approvals and dry-run unification.

This module provides a unified mechanism for approvals and dry-run mode
across all agents (excel_audit, github_admin, content_kb).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from .contracts import ApprovalRequirement, JobContext, JobSpec, utc_now
from .manifest_loader import AgentManifest


class ApprovalDecision(str, Enum):
    """Decision on an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ApprovalRecord:
    """Record of an approval request."""

    approval_id: str
    status: ApprovalDecision = ApprovalDecision.PENDING
    requested_by: str | None = None
    decided_by: str | None = None
    decision_reason: str | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None
    decided_at: datetime | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = utc_now()
        if self.metadata is None:
            self.metadata = {}

    def is_expired(self) -> bool:
        """Check if the approval has expired."""
        return (
            self.status == ApprovalDecision.PENDING
            and self.expires_at is not None
            and utc_now() > self.expires_at
        )

    def decide(self, decision: ApprovalDecision, decided_by: str, reason: str = "") -> ApprovalRecord:
        """Make a decision on this approval."""
        if self.status != ApprovalDecision.PENDING:
            raise ValueError(f"Cannot decide on approval in state {self.status.value}")
        if self.is_expired():
            self.status = ApprovalDecision.EXPIRED
            return self
        self.status = decision
        self.decided_by = decided_by
        self.decision_reason = reason
        self.decided_at = utc_now()
        return self


class ApprovalStore:
    """In-memory store for approval requests.

    In production, this should be replaced with a persistent store.
    """

    def __init__(self) -> None:
        self._approvals: dict[str, ApprovalRecord] = {}

    def create(
        self,
        approval_id: str,
        requested_by: str | None = None,
        expires_in_seconds: int = 3600,
        metadata: dict[str, Any] | None = None,
    ) -> ApprovalRecord:
        """Create a new approval request."""
        if approval_id in self._approvals:
            raise ValueError(f"Approval {approval_id} already exists")
        record = ApprovalRecord(
            approval_id=approval_id,
            status=ApprovalDecision.PENDING,
            requested_by=requested_by,
            created_at=utc_now(),
            expires_at=utc_now() + timedelta(seconds=expires_in_seconds),
            metadata=metadata or {},
        )
        self._approvals[approval_id] = record
        return record

    def get(self, approval_id: str) -> ApprovalRecord | None:
        """Get an approval by ID."""
        return self._approvals.get(approval_id)

    def decide(
        self,
        approval_id: str,
        decision: ApprovalDecision,
        decided_by: str,
        reason: str = "",
    ) -> ApprovalRecord | None:
        """Make a decision on an approval."""
        record = self._approvals.get(approval_id)
        if record is None:
            return None
        return record.decide(decision, decided_by, reason)

    def list_pending(self) -> list[ApprovalRecord]:
        """List all pending approvals."""
        return [
            record
            for record in self._approvals.values()
            if record.status == ApprovalDecision.PENDING and not record.is_expired()
        ]


class ApprovalManager:
    """Manages approvals for task execution.

    This provides a unified approval mechanism that integrates with:
    - JobSpec (via requires_approval and approval_requirement)
    - AgentManifest (via gates.approvals)
    - TaskGateResult (via requires_human_review)
    """

    def __init__(
        self,
        store: ApprovalStore | None = None,
        agent_manifests: dict[str, AgentManifest] | None = None,
    ) -> None:
        self.store = store or ApprovalStore()
        self.agent_manifests = agent_manifests or {}

    def check_approval_required(
        self,
        job_spec: JobSpec,
        manifest: AgentManifest | None = None,
    ) -> ApprovalRequirement | None:
        """Check if an approval is required for a job.

        Args:
            job_spec: The job specification
            manifest: The agent manifest (optional)

        Returns:
            ApprovalRequirement if approval is required, None otherwise
        """
        # Check JobSpec first
        if job_spec.context.requires_approval:
            return job_spec.context.approval_requirement or ApprovalRequirement(
                required=True,
                scope="job_context",
                reason="Approval required by job context",
            )
        # Check manifest gates
        if manifest:
            for scope, _ in manifest.gates.approvals.items():
                # Check if this scope is triggered by the job
                if self._scope_matches_job(scope, job_spec):
                    return ApprovalRequirement(
                        required=True,
                        scope=scope,
                        reason=f"Approval required by manifest gates: {scope}",
                        approver_roles=["owner", "admin"],
                    )
        return None

    def _scope_matches_job(self, scope: str, job_spec: JobSpec) -> bool:
        """Check if an approval scope matches the job.

        This is a simple heuristic that can be extended based on business rules.
        """
        scope_lower = scope.lower()
        job_lower = job_spec.task.lower()
        attachments_lower = [a.lower() for a in job_spec.attachments]

        # Check common scope patterns
        if scope_lower == "writeback_to_source_excel":
            return any(
                "writeback" in job_lower or "回写" in job_lower
                for att in attachments_lower
                if att.endswith((".xlsx", ".xls"))
            ) or "writeback" in job_lower or "回写" in job_lower

        if scope_lower == "merge_to_main":
            return "merge" in job_lower or "push" in job_lower

        if scope_lower == "execute_transfer":
            return "transfer" in job_lower or "execute" in job_lower

        if scope_lower == "real_github_operation":
            return "github" in job_lower and not job_spec.context.dry_run

        # Default: no match
        return False

    def request_approval(
        self,
        job_spec: JobSpec,
        manifest: AgentManifest | None = None,
        expires_in_seconds: int = 3600,
    ) -> ApprovalRecord | None:
        """Request an approval for a job.

        Args:
            job_spec: The job specification
            manifest: The agent manifest (optional)
            expires_in_seconds: Approval expiration time

        Returns:
            ApprovalRecord for the request, or None if no approval required
        """
        requirement = self.check_approval_required(job_spec, manifest)
        if requirement is None or not requirement.required:
            return None
        approval_id = f"approval-{job_spec.run_id}"
        return self.store.create(
            approval_id=approval_id,
            requested_by=job_spec.requested_by,
            expires_in_seconds=min(expires_in_seconds, requirement.expires_in_seconds),
            metadata={
                "run_id": job_spec.run_id,
                "agent_id": job_spec.agent_id,
                "task_type": job_spec.task_type,
                "scope": requirement.scope,
                "risk_level": requirement.risk_level,
            },
        )

    def check_approval(
        self,
        approval_id: str,
    ) -> ApprovalDecision:
        """Check the status of an approval.

        Args:
            approval_id: The approval ID

        Returns:
            ApprovalDecision indicating the current status
        """
        record = self.store.get(approval_id)
        if record is None:
            return ApprovalDecision.REJECTED
        if record.is_expired():
            return ApprovalDecision.EXPIRED
        return record.status

    def decide_approval(
        self,
        approval_id: str,
        decision: ApprovalDecision,
        decided_by: str,
        reason: str = "",
    ) -> ApprovalRecord | None:
        """Make a decision on an approval.

        Args:
            approval_id: The approval ID
            decision: The decision (APPROVED or REJECTED)
            decided_by: Who made the decision
            reason: Reason for the decision

        Returns:
            Updated ApprovalRecord or None if not found
        """
        return self.store.decide(approval_id, decision, decided_by, reason)

    def ensure_dry_run_for_unapproved(
        self,
        job_spec: JobSpec,
        manifest: AgentManifest | None = None,
    ) -> JobSpec:
        """Ensure dry-run mode for unapproved jobs.

        This method enforces the dry-run requirement for jobs that need approval
        but haven't been approved yet. This is critical for safety.

        Args:
            job_spec: The job specification
            manifest: The agent manifest (optional)

        Returns:
            Modified JobSpec with dry_run=True if approval is needed but not granted
        """
        requirement = self.check_approval_required(job_spec, manifest)
        if requirement is None or not requirement.required:
            return job_spec
        # Check if already approved
        approval_id = f"approval-{job_spec.run_id}"
        decision = self.check_approval(approval_id)
        if decision == ApprovalDecision.APPROVED:
            return job_spec
        # Force dry-run mode
        if not job_spec.context.dry_run:
            return job_spec.model_copy(
                update={
                    "context": job_spec.context.model_copy(
                        update={"dry_run": True}
                    )
                }
            )
        return job_spec
