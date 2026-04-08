"""Adapter/integration layer for foundation.

This module provides adapters to integrate foundation with existing modules:
- excel_audit
- github_admin
- content_kb
"""

from __future__ import annotations

from typing import Any

from foundation.contracts import (
    JobSpec,
    JobContext,
)


# ============================================================================
# Excel Audit Adapter
# ============================================================================


def excel_audit_to_spec(spec: JobSpec) -> dict[str, Any]:
    """Convert excel_audit spec to foundation dict format."""
    return {
        "run_id": spec.run_id,
        "agent_id": "excel_audit",
        "task_type": spec.task_type or "excel_audit",
        "task": spec.task,
        "task_brief": spec.task_brief,
        "attachments": spec.attachments or [],
        "dry_run": spec.context.dry_run,
        "requires_approval": spec.context.requires_approval,
    }


def excel_audit_from_spec(data: dict[str, Any]) -> JobSpec:
    """Convert excel_audit dict format to foundation JobSpec."""
    return JobSpec(
        run_id=data["run_id"],
        agent_id="excel_audit",
        task_type=data.get("task_type", "excel_audit"),
        role="specialist",
        task=data["task"],
        task_brief=data.get("task_brief"),
        attachments=data.get("attachments", []),
        context=JobContext(
            dry_run=data.get("dry_run", True),
            requires_approval=data.get("requires_approval", False),
        ),
    )


# ============================================================================
# GitHub Admin Adapter
# ============================================================================


def github_admin_to_spec(spec: JobSpec) -> dict[str, Any]:
    """Convert github_admin spec to foundation dict format."""
    return {
        "run_id": spec.run_id,
        "agent_id": "github_admin",
        "task_type": spec.task_type or "github_admin",
        "task": spec.task,
        "task_brief": spec.task_brief,
        "attachments": spec.attachments or [],
        "dry_run": spec.context.dry_run,
        "requires_approval": spec.context.requires_approval,
    }


def github_admin_from_spec(data: dict[str, Any]) -> JobSpec:
    """Convert github_admin dict format to foundation JobSpec."""
    return JobSpec(
        run_id=data["run_id"],
        agent_id="github_admin",
        task_type=data.get("task_type", "github_admin"),
        role="specialist",
        task=data["task"],
        task_brief=data.get("task_brief"),
        attachments=data.get("attachments", []),
        context=JobContext(
            dry_run=data.get("dry_run", True),
            requires_approval=data.get("requires_approval", False),
        ),
    )


# ============================================================================
# Content KB Adapter
# ============================================================================


def content_kb_to_spec(spec: JobSpec) -> dict[str, Any]:
    """Convert content_kb spec to foundation dict format."""
    return {
        "run_id": spec.run_id,
        "agent_id": "content_kb",
        "task_type": spec.task_type or "content_kb",
        "task": spec.task,
        "task_brief": spec.task_brief,
        "attachments": spec.attachments or [],
        "dry_run": spec.context.dry_run,
        "requires_approval": spec.context.requires_approval,
    }


def content_kb_from_spec(data: dict[str, Any]) -> JobSpec:
    """Convert content_kb dict format to foundation JobSpec."""
    return JobSpec(
        run_id=data["run_id"],
        agent_id="content_kb",
        task_type=data.get("task_type", "content_kb"),
        role="specialist",
        task=data["task"],
        task_brief=data.get("task_brief"),
        attachments=data.get("attachments", []),
        context=JobContext(
            dry_run=data.get("dry_run", False),
            requires_approval=data.get("requires_approval", False),
        ),
    )
