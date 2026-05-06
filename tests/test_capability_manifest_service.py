from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from autoresearch.agent_protocol.capability_models import CapabilityRunRequest
from autoresearch.agent_protocol.capability_registry import CapabilityManifestRegistry
from autoresearch.agent_protocol.runtime_models import RuntimeRunRead, RuntimeRunRequest
from autoresearch.core.services.capability_manifest_service import CapabilityManifestService
from autoresearch.shared.models import JobStatus


class _Runtime:
    def run(self, request: RuntimeRunRequest) -> RuntimeRunRead:
        now = datetime.now(UTC)
        return RuntimeRunRead(
            runtime_id=request.runtime_id,
            run_id="run-1",
            session_id=request.session_id,
            task_name=request.task_name,
            status=JobStatus.COMPLETED,
            summary=request.prompt,
            changed_paths=[],
            output_artifacts=[],
            command=["fake"],
            timeout_seconds=request.timeout_seconds,
            created_at=now,
            updated_at=now,
            metadata=dict(request.metadata),
        )


class _RuntimeRegistry:
    def list_runtime_ids(self) -> list[str]:
        return ["crewai"]

    def get(self, runtime_id: str) -> _Runtime:
        assert runtime_id == "crewai"
        return _Runtime()


def test_capability_manifest_runs_through_bound_runtime(tmp_path: Path) -> None:
    manifests = tmp_path / "capabilities"
    manifests.mkdir()
    (manifests / "research.demo.yaml").write_text(
        """
capability_id: research.demo
kind: runtime
provided_by: crewai
display_name: Demo research
input_schema: {type: object}
output_schema: {type: object}
risk_tier: common_read
policy_refs: [tool_proxy.read_only]
artifact_types: [report]
lease_enabled: true
""",
        encoding="utf-8",
    )
    service = CapabilityManifestService(
        registry=CapabilityManifestRegistry(manifests),
        runtime_registry=_RuntimeRegistry(),  # type: ignore[arg-type]
    )

    listed = service.list_manifests()
    result = service.run_capability(
        "research.demo",
        CapabilityRunRequest(task_name="Research", prompt="Summarize Agent-Reach"),
    )

    assert listed[0].capability_id == "research.demo"
    assert result.runtime_id == "crewai"
    assert result.runtime_run.summary == "Summarize Agent-Reach"
    assert result.runtime_run.metadata["capability_id"] == "research.demo"
