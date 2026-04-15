"""Foundation integration tests with real modules.

Smoke tests verifying foundation can connect to real modules:
- excel_audit
- github_admin
- content_kb

These tests use real manifests and minimal valid inputs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from foundation.contracts import JobSpec, JobContext
from foundation.adapters import (
    excel_audit_to_spec,
    excel_audit_from_spec,
    github_admin_to_spec,
    github_admin_from_spec,
    content_kb_to_spec,
    content_kb_from_spec,
)
from foundation.manifest_loader import load_manifest, scan_agents_directory
from foundation.router import Router
from foundation.butler_compat import ButlerCompatAdapter


# ============================================================================
# Real manifest loading
# ============================================================================


class TestRealManifests:
    """Test loading real agent manifests."""

    def test_load_excel_audit_manifest(self):
        """Test loading excel_audit manifest from real agents directory."""
        manifest_path = Path("agents/excel_audit/manifest.yaml")
        manifest = load_manifest(manifest_path)

        assert manifest.id == "excel_audit"
        assert manifest.name == "Excel Audit Agent"
        assert manifest.role == "specialist"
        assert "excel_audit" in manifest.task_types
        assert "commission_check" in manifest.task_types
        assert "reconciliation" in manifest.task_types

    def test_load_github_admin_manifest(self):
        """Test loading github_admin manifest from real agents directory."""
        manifest_path = Path("agents/github_admin/manifest.yaml")
        manifest = load_manifest(manifest_path)

        assert manifest.id == "github_admin"
        assert manifest.name == "GitHub Admin Agent"
        assert manifest.role == "specialist"
        assert "github_admin.inventory" in manifest.task_types
        assert "github_admin.transfer_plan" in manifest.task_types

    def test_load_content_kb_manifest(self):
        """Test loading content_kb manifest from real agents directory."""
        manifest_path = Path("agents/content_kb/manifest.yaml")
        manifest = load_manifest(manifest_path)

        assert manifest.id == "content_kb"
        assert manifest.name == "Content Knowledge Base Agent"
        assert manifest.role == "specialist"
        assert "content_kb.classify_topic" in manifest.task_types
        assert "content_kb.build_index" in manifest.task_types

    def test_scan_real_agents_directory(self):
        """Test scanning real agents directory."""
        agents_dir = Path("agents")
        registry = scan_agents_directory(agents_dir)

        agents = registry.list()
        agent_ids = {m.id for m in agents}

        # Should have at least 3 agents (plus butler_orchestrator)
        assert "excel_audit" in agent_ids
        assert "github_admin" in agent_ids
        assert "content_kb" in agent_ids


# ============================================================================
# Excel Audit integration
# ============================================================================


class TestExcelAuditIntegration:
    """Test excel_audit integration with foundation."""

    def test_excel_audit_adapter_with_real_input(self):
        """Test adapter with minimal valid excel_audit input."""
        # Create a JobSpec matching excel_audit contract
        spec = JobSpec(
            run_id="excel-test-001",
            agent_id="excel_audit",
            task_type="commission_check",
            task="核对2024年Q1提成数据",
            task_brief="验证销售提成计算是否正确",
            attachments=["data/sales_q1_2024.xlsx"],
            context=JobContext(
                dry_run=True,
                requires_approval=False,
                allow_code_change=True,
            ),
        )

        # Convert to adapter format
        excel_spec = excel_audit_to_spec(spec)

        assert excel_spec["run_id"] == "excel-test-001"
        assert excel_spec["agent_id"] == "excel_audit"
        assert excel_spec["task_type"] == "commission_check"
        assert excel_spec["task"] == "核对2024年Q1提成数据"
        assert excel_spec["dry_run"] is True

        # Convert back
        restored = excel_audit_from_spec(excel_spec)

        assert restored.run_id == spec.run_id
        assert restored.agent_id == spec.agent_id
        assert restored.task_type == spec.task_type

    def test_excel_audit_with_reconciliation_task(self):
        """Test adapter with reconciliation task type."""
        spec = JobSpec(
            run_id="recon-test-001",
            agent_id="excel_audit",
            task_type="reconciliation",
            task="账目对账",
            task_brief="对账系统A和系统B的差异",
            attachments=["data/system_a.xlsx", "data/system_b.xlsx"],
            context=JobContext(dry_run=True),
        )

        excel_spec = excel_audit_to_spec(spec)
        assert excel_spec["task_type"] == "reconciliation"


# ============================================================================
# GitHub Admin integration
# ============================================================================


class TestGitHubAdminIntegration:
    """Test github_admin integration with foundation."""

    def test_github_admin_adapter_with_real_input(self):
        """Test adapter with minimal valid github_admin input."""
        spec = JobSpec(
            run_id="gh-test-001",
            agent_id="github_admin",
            task_type="github_admin.inventory",
            task="GitHub 仓库盘点",
            task_brief="列出 owner-org 下的所有仓库",
            attachments=[],
            context=JobContext(
                dry_run=True,
                requires_approval=False,
                allow_code_change=False,
            ),
        )

        # Convert to adapter format
        gh_spec = github_admin_to_spec(spec)

        assert gh_spec["run_id"] == "gh-test-001"
        assert gh_spec["agent_id"] == "github_admin"
        assert gh_spec["task_type"] == "github_admin.inventory"
        assert gh_spec["dry_run"] is True

        # Convert back
        restored = github_admin_from_spec(gh_spec)

        assert restored.run_id == spec.run_id
        assert restored.agent_id == spec.agent_id
        assert restored.task_type == spec.task_type

    def test_github_admin_transfer_plan_requires_approval(self):
        """Test that transfer_plan task requires approval."""
        spec = JobSpec(
            run_id="gh-transfer-001",
            agent_id="github_admin",
            task_type="github_admin.transfer_plan",
            task="仓库迁移规划",
            task_brief="从 old-owner 迁移到 new-owner",
            attachments=[],
            context=JobContext(
                dry_run=True,
                requires_approval=True,  # Transfer needs approval
                allow_code_change=False,
            ),
        )

        gh_spec = github_admin_to_spec(spec)
        assert gh_spec["requires_approval"] is True


# ============================================================================
# Content KB integration
# ============================================================================


class TestContentKbIntegration:
    """Test content_kb integration with foundation."""

    def test_content_kb_adapter_with_real_input(self):
        """Test adapter with minimal valid content_kb input."""
        spec = JobSpec(
            run_id="kb-test-001",
            agent_id="content_kb",
            task_type="content_kb.classify_topic",
            task="视频内容分类",
            task_brief="将视频字幕按技术主题分类",
            attachments=["subtitles/video_001.srt"],
            context=JobContext(
                dry_run=False,
                requires_approval=False,
                allow_code_change=True,
            ),
        )

        # Convert to adapter format
        kb_spec = content_kb_to_spec(spec)

        assert kb_spec["run_id"] == "kb-test-001"
        assert kb_spec["agent_id"] == "content_kb"
        assert kb_spec["task_type"] == "content_kb.classify_topic"
        assert kb_spec["dry_run"] is False

        # Convert back
        restored = content_kb_from_spec(kb_spec)

        assert restored.run_id == spec.run_id
        assert restored.agent_id == spec.agent_id
        assert restored.task_type == spec.task_type


# ============================================================================
# Router integration
# ============================================================================


class TestRouterWithRealAgents:
    """Test router with real agent manifests."""

    def test_router_routes_to_excel_audit(self):
        """Test router routes to excel_audit by task type."""
        router = Router(agents_dir="agents")
        router.initialize()

        result = router.route(
            task_brief="核对提成数据",
            task_type="excel_audit",
        )

        assert result is not None
        assert result.agent_id == "excel_audit"
        assert result.manifest.id == "excel_audit"

    def test_router_routes_to_github_admin(self):
        """Test router routes to github_admin by task type."""
        router = Router(agents_dir="agents")
        router.initialize()

        result = router.route(
            task_brief="仓库盘点",
            task_type="github_admin.inventory",
        )

        assert result is not None
        assert result.agent_id == "github_admin"

    def test_router_routes_to_content_kb(self):
        """Test router routes to content_kb by keyword."""
        router = Router(agents_dir="agents")
        router.initialize()

        result = router.route(
            task_brief="内容索引构建",
            task_type="content_kb.build_index",
        )

        assert result is not None
        assert result.agent_id == "content_kb"

    def test_router_returns_none_for_unknown_task(self):
        """Test router returns None for unknown task types."""
        router = Router(agents_dir="agents")
        router.initialize()

        result = router.route(
            task_brief="完全未知的任务",
            task_type="unknown.task.type",
        )

        assert result is None


# ============================================================================
# Butler compat adapter integration
# ============================================================================


class TestButlerCompatWithRealAgents:
    """Test butler compatibility adapter with real agents."""

    def test_butler_compat_routes_excel_audit(self):
        """Test butler compat routes to excel_audit."""
        router = Router(agents_dir="agents")
        router.initialize()
        adapter = ButlerCompatAdapter(router)

        job_spec = adapter.route(
            task="Excel核对任务",
            task_type="excel_audit",
            attachments=["data.xlsx"],
            dry_run=True,
        )

        assert job_spec is not None
        assert job_spec.agent_id == "excel_audit"
        assert job_spec.task_type == "excel_audit"
        assert job_spec.context.dry_run is True

    def test_butler_compat_routes_github_admin(self):
        """Test butler compat routes to github_admin."""
        router = Router(agents_dir="agents")
        router.initialize()
        adapter = ButlerCompatAdapter(router)

        job_spec = adapter.route(
            task="GitHub仓库盘点",
            task_type="github_admin.inventory",
            attachments=[],
            dry_run=True,
        )

        assert job_spec is not None
        assert job_spec.agent_id == "github_admin"
        assert job_spec.context.dry_run is True

    def test_butler_compat_routes_content_kb(self):
        """Test butler compat routes to content_kb."""
        router = Router(agents_dir="agents")
        router.initialize()
        adapter = ButlerCompatAdapter(router)

        job_spec = adapter.route(
            task="内容分类",
            task_type="content_kb.classify_topic",
            attachments=[],
            dry_run=False,
        )

        assert job_spec is not None
        assert job_spec.agent_id == "content_kb"

    def test_butler_compat_returns_none_for_unknown(self):
        """Test butler compat returns None for unknown tasks."""
        router = Router(agents_dir="agents")
        router.initialize()
        adapter = ButlerCompatAdapter(router)

        job_spec = adapter.route(
            task="未知任务",
            task_type="unknown.task",
            attachments=[],
            dry_run=True,
        )

        assert job_spec is None
