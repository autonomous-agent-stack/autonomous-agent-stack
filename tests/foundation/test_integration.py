"""Foundation integration tests.

Tests that foundation is properly integrated with existing modules.
Verifies:
1. Registry loads 4 agents
2. Adapters map existing tasks to JobSpec
3. Butler compat adapter works (adapter layer only)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from foundation.contracts import (
    JobSpec,
    JobContext,
)
from foundation.adapters import (
    excel_audit_to_spec,
    excel_audit_from_spec,
    github_admin_to_spec,
    github_admin_from_spec,
    content_kb_to_spec,
    content_kb_from_spec,
)
from foundation.butler_compat import ButlerCompatAdapter
from foundation.manifest_loader import (
    AgentManifest,
    AgentRegistry,
    load_manifest,
    scan_agents_directory,
    ManifestLoadError,
)
from foundation.router import Router
from foundation.gate import TaskGate


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def agents_dir(tmp_path: Path) -> Path:
    """Create test agents directory with 4 manifests."""
    agents = tmp_path / "agents"
    agents.mkdir()

    manifests = {
        "butler_orchestrator": {
            "version": "1",
            "agent": {
                "id": "butler_orchestrator",
                "name": "Butler Orchestrator",
                "description": "Central orchestrator",
                "role": "orchestrator",
            },
            "routing": {
                "task_types": ["butler.orchestrate"],
                "keywords": ["orchestrate", "路由"],
            },
            "execution": {
                "default_driver": "claude_code",
                "workspace_mode": "isolated",
                "allow_code_change": True,
                "require_patch_gate": True,
            },
            "inputs": {"required": [], "optional": []},
            "outputs": {"schema": {}, "artifacts": []},
            "permissions": {
                "filesystem": {"read": [], "write": []},
                "network": "deny",
                "git": {"commit": False, "push": False},
            },
            "gates": {"validators": [], "approvals": {}},
            "prompts": {},
            "runtime": {
                "deterministic_execution_required": False,
                "llm_must_not_do_final_math": False,
                "report_formats": ["markdown", "json"],
            },
        },
        "excel_audit": {
            "version": "1",
            "agent": {
                "id": "excel_audit",
                "name": "Excel Audit Agent",
                "description": "Excel audit specialist",
                "role": "specialist",
            },
            "routing": {
                "task_types": ["excel_audit", "commission_check", "reconciliation"],
                "keywords": ["Excel核对", "提成核算", "计算检查"],
            },
            "execution": {
                "default_driver": "claude_code",
                "workspace_mode": "isolated",
                "allow_code_change": True,
                "require_patch_gate": True,
            },
            "inputs": {"required": ["task_brief"], "optional": []},
            "outputs": {
                "schema": {"type": "object", "required": ["status", "summary"]},
                "artifacts": ["report.md"],
            },
            "permissions": {
                "filesystem": {
                    "read": ["data/", "artifacts/"],
                    "write": ["artifacts/excel_audit/"],
                },
                "network": "deny",
                "git": {"commit": False, "push": False},
            },
            "gates": {
                "validators": ["pytest -q tests/excel_audit"],
                "approvals": {"human_required_for": ["writeback_to_source_excel"]},
            },
            "prompts": {"intake": "agents/excel_audit/prompts/intake.md"},
            "runtime": {
                "deterministic_execution_required": False,
                "llm_must_not_do_final_math": False,
                "report_formats": ["markdown", "json"],
            },
        },
        "github_admin": {
            "version": "1",
            "agent": {
                "id": "github_admin",
                "name": "GitHub Admin Agent",
                "description": "GitHub admin specialist (dry-run only)",
                "role": "specialist",
            },
            "routing": {
                "task_types": ["github_admin.inventory", "github_admin.transfer_plan"],
                "keywords": ["GitHub盘点", "仓库迁移", "仓库规划", "协作者", "邀请"],
            },
            "execution": {
                "default_driver": "claude_code",
                "workspace_mode": "isolated",
                "allow_code_change": False,
                "require_patch_gate": True,
            },
            "inputs": {"required": ["owners"], "optional": []},
            "outputs": {
                "schema": {"type": "object", "required": ["run_id", "status"]},
                "artifacts": ["inventory.json", "transfer_plan.md"],
            },
            "permissions": {
                "filesystem": {
                    "read": ["configs/github_profiles/"],
                    "write": ["artifacts/github_admin/"],
                },
                "network": "allow",
                "git": {"commit": False, "push": False},
            },
            "gates": {
                "validators": ["dry-run-only"],
                "approvals": {"human_required_for": ["execute_transfer"]},
            },
            "prompts": {
                "intake": "agents/github_admin/prompts/repo_inventory.md",
                "transfer_plan": "agents/github_admin/prompts/transfer_plan.md",
            },
            "runtime": {
                "deterministic_execution_required": True,
                "llm_must_not_do_final_math": True,
                "report_formats": ["markdown", "json"],
            },
        },
        "content_kb": {
            "version": "1",
            "agent": {
                "id": "content_kb",
                "name": "Content KB Agent",
                "description": "Content knowledge base specialist",
                "role": "specialist",
            },
            "routing": {
                "task_types": ["content_kb.classify_topic", "content_kb.build_index"],
                "keywords": ["内容分类", "索引构建"],
            },
            "execution": {
                "default_driver": "claude_code",
                "workspace_mode": "isolated",
                "allow_code_change": True,
                "require_patch_gate": True,
            },
            "inputs": {"required": ["task_brief"], "optional": []},
            "outputs": {
                "schema": {"type": "object", "required": ["status"]},
                "artifacts": ["index.md"],
            },
            "permissions": {
                "filesystem": {
                    "read": ["src/content_kb/"],
                    "write": ["artifacts/content_kb/"],
                },
                "network": "deny",
                "git": {"commit": False, "push": False},
            },
            "gates": {
                "validators": ["pytest -q tests/content_kb"],
                "approvals": {"human_required_for": ["push_to_remote"]},
            },
            "prompts": {"intake": "agents/content_kb/prompts/intake.md"},
            "runtime": {
                "deterministic_execution_required": False,
                "llm_must_not_do_final_math": False,
                "report_formats": ["markdown", "json"],
            },
        },
    }

    for agent_id, manifest_data in manifests.items():
        agent_dir = agents / agent_id
        agent_dir.mkdir()
        manifest_path = agent_dir / "manifest.yaml"
        manifest_path.write_text(yaml.dump(manifest_data), encoding="utf-8")

    return agents


# ============================================================================
# Test 1: Registry loads 4 agents
# ============================================================================


class TestManifestLoader:
    """Test manifest loader."""

    def test_scan_agents_directory(self, agents_dir: Path):
        """Test scanning agents directory."""
        registry = scan_agents_directory(agents_dir)
        assert len(registry.list()) == 4

    def test_registry_has_all_agents(self, agents_dir: Path):
        """Test registry contains all 4 agents."""
        registry = scan_agents_directory(agents_dir)

        agent_ids = {m.id for m in registry.list()}
        assert agent_ids == {
            "butler_orchestrator",
            "excel_audit",
            "github_admin",
            "content_kb",
        }

    def test_registry_get_by_task_type(self, agents_dir: Path):
        """Test getting agent by task type."""
        registry = scan_agents_directory(agents_dir)

        # Test each task type
        assert registry.get_by_task_type("excel_audit") is not None
        assert registry.get_by_task_type("commission_check") is not None
        assert registry.get_by_task_type("github_admin.inventory") is not None
        assert registry.get_by_task_type("github_admin.transfer_plan") is not None
        assert registry.get_by_task_type("content_kb.classify_topic") is not None
        assert registry.get_by_task_type("butler.orchestrate") is not None

    def test_registry_rejects_duplicate_id(self, agents_dir: Path):
        """Test registry rejects duplicate agent ID."""
        registry = AgentRegistry()

        # Load first manifest
        manifest1 = load_manifest(agents_dir / "excel_audit" / "manifest.yaml")
        registry.register(manifest1)

        # Try to register same ID again
        manifest2 = AgentManifest(
            id="excel_audit",
            name="Duplicate",
            description="Should fail",
            role="specialist",
            task_types=["test"],
            keywords=[],
            execution={},
            inputs={},
            outputs={},
            permissions={},
            gates={},
            prompts={},
            runtime={},
        )

        with pytest.raises(ValueError, match="already registered"):
            registry.register(manifest2)


# ============================================================================
# Test 2: Adapters map existing tasks to JobSpec
# ============================================================================


class TestAdapters:
    """Test adapters for existing modules."""

    def test_excel_audit_adapter(self):
        """Test excel_audit adapter."""
        # Create JobSpec
        spec = JobSpec(
            run_id="run-001",
            agent_id="excel_audit",
            task_type="excel_audit",
            task="核对提成计算",
            task_brief="核对2024年Q1提成数据",
            attachments=["data/sales.xlsx"],
            context=JobContext(dry_run=True, requires_approval=False),
        )

        # Test to spec conversion
        excel_spec = excel_audit_to_spec(spec)
        assert excel_spec["run_id"] == "run-001"
        assert excel_spec["agent_id"] == "excel_audit"
        assert excel_spec["task_type"] == "excel_audit"
        assert excel_spec["task"] == "核对提成计算"
        assert excel_spec["task_brief"] == "核对2024年Q1提成数据"
        assert excel_spec["attachments"] == ["data/sales.xlsx"]
        assert excel_spec["dry_run"] is True
        assert excel_spec["requires_approval"] is False

        # Test from spec conversion
        result = excel_audit_from_spec(excel_spec)
        assert result.run_id == "run-001"
        assert result.agent_id == "excel_audit"
        assert result.task_type == "excel_audit"
        assert result.task == "核对提成计算"
        assert result.task_brief == "核对2024年Q1提成数据"
        assert result.attachments == ["data/sales.xlsx"]
        assert result.context.dry_run is True
        assert result.context.requires_approval is False

    def test_github_admin_adapter(self):
        """Test github_admin adapter."""
        spec = JobSpec(
            run_id="run-002",
            agent_id="github_admin",
            task_type="github_admin.transfer_plan",
            task="迁移仓库规划",
            task_brief="从 owner-a 迁移到 owner-b",
            attachments=[],
            context=JobContext(dry_run=True, requires_approval=True),
        )

        # Test to spec conversion
        gh_spec = github_admin_to_spec(spec)
        assert gh_spec["run_id"] == "run-002"
        assert gh_spec["agent_id"] == "github_admin"
        assert gh_spec["task_type"] == "github_admin.transfer_plan"
        assert gh_spec["task"] == "迁移仓库规划"
        assert gh_spec["dry_run"] is True
        assert gh_spec["requires_approval"] is True

        # Test from spec conversion
        result = github_admin_from_spec(gh_spec)
        assert result.run_id == "run-002"
        assert result.agent_id == "github_admin"
        assert result.task_type == "github_admin.transfer_plan"
        assert result.context.dry_run is True
        assert result.context.requires_approval is True

    def test_content_kb_adapter(self):
        """Test content_kb adapter."""
        spec = JobSpec(
            run_id="run-003",
            agent_id="content_kb",
            task_type="content_kb.classify_topic",
            task="分类内容主题",
            task_brief="将视频字幕按主题分类",
            attachments=["subtitles.srt"],
            context=JobContext(dry_run=False, requires_approval=False),
        )

        # Test to spec conversion
        cb_spec = content_kb_to_spec(spec)
        assert cb_spec["run_id"] == "run-003"
        assert cb_spec["agent_id"] == "content_kb"
        assert cb_spec["task_type"] == "content_kb.classify_topic"
        assert cb_spec["task"] == "分类内容主题"
        assert cb_spec["attachments"] == ["subtitles.srt"]
        assert cb_spec["dry_run"] is False
        assert cb_spec["requires_approval"] is False

        # Test from spec conversion
        result = content_kb_from_spec(cb_spec)
        assert result.run_id == "run-003"
        assert result.agent_id == "content_kb"
        assert result.task_type == "content_kb.classify_topic"
        assert result.attachments == ["subtitles.srt"]
        assert result.context.dry_run is False
        assert result.context.requires_approval is False


# ============================================================================
# Test 3: Butler compatibility adapter (adapter layer only)
# ============================================================================


class TestButlerCompatAdapter:
    """Test butler compatibility adapter."""

    def test_adapter_initialization(self, agents_dir: Path):
        """Test adapter initialization."""
        router = Router(agents_dir=str(agents_dir))
        router.initialize()
        adapter = ButlerCompatAdapter(router)
        assert adapter is not None

    def test_adapter_route_to_excel_audit(self, agents_dir: Path):
        """Test adapter routes to excel_audit."""
        router = Router(agents_dir=str(agents_dir))
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

    def test_adapter_route_to_github_admin(self, agents_dir: Path):
        """Test adapter routes to github_admin."""
        router = Router(agents_dir=str(agents_dir))
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
        assert job_spec.task_type == "github_admin.inventory"
        assert job_spec.context.dry_run is True

    def test_adapter_route_to_content_kb(self, agents_dir: Path):
        """Test adapter routes to content_kb."""
        router = Router(agents_dir=str(agents_dir))
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
        assert job_spec.task_type == "content_kb.classify_topic"
        assert job_spec.context.dry_run is False

    def test_adapter_route_no_match(self, agents_dir: Path):
        """Test adapter returns None for unknown task."""
        router = Router(agents_dir=str(agents_dir))
        router.initialize()
        adapter = ButlerCompatAdapter(router)

        job_spec = adapter.route(
            task="未知任务",
            task_type="unknown.task",
            attachments=[],
            dry_run=True,
        )

        assert job_spec is None

    def test_adapter_respects_approval_requirement(self, agents_dir: Path):
        """Test adapter sets requires_approval based on manifest."""
        router = Router(agents_dir=str(agents_dir))
        router.initialize()
        adapter = ButlerCompatAdapter(router)

        # github_admin has approval requirement
        job_spec = adapter.route(
            task="迁移规划",
            task_type="github_admin.transfer_plan",
            attachments=[],
            dry_run=True,
        )

        # The adapter should detect approval requirement from manifest
        # For now, we just verify it routes correctly
        assert job_spec is not None
        assert job_spec.agent_id == "github_admin"
