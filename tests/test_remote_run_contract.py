from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from autoresearch.agent_protocol.models import JobSpec
from autoresearch.shared.remote_run_contract import DispatchLane, RemoteRunRecord, RemoteTaskSpec, RemoteRunSummary


def _load_export_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "export_remote_run_schemas.py"
    spec = importlib.util.spec_from_file_location("export_remote_run_schemas", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_remote_contract_rejects_absolute_artifact_paths() -> None:
    with pytest.raises(ValidationError):
        RemoteRunRecord(
            run_id="run-contract",
            artifact_paths={"summary": "/tmp/summary.json"},
        )


def test_remote_contract_rejects_parent_traversal_artifact_paths() -> None:
    with pytest.raises(ValidationError):
        RemoteRunSummary(
            run_id="run-contract",
            artifact_paths={"summary": "../outside.json"},
        )


def test_remote_task_spec_rejects_invalid_lane() -> None:
    with pytest.raises(ValidationError):
        RemoteTaskSpec(
            run_id="run-contract",
            requested_lane=DispatchLane.LOCAL,
            lane="bogus",
            runtime_mode="day",
            job=JobSpec(run_id="run-contract", agent_id="openhands", task="demo"),
        )


def test_remote_task_spec_requires_run_id() -> None:
    with pytest.raises(ValidationError):
        RemoteTaskSpec(
            run_id="",
            job=JobSpec(run_id="run-contract", agent_id="openhands", task="demo"),
        )


def test_exported_remote_schemas_match_model_json_schema(tmp_path: Path) -> None:
    module = _load_export_module()
    written = module.export_schemas(tmp_path)

    task_schema = json.loads((tmp_path / "task_run.schema.json").read_text(encoding="utf-8"))
    summary_schema = json.loads((tmp_path / "run_summary.schema.json").read_text(encoding="utf-8"))

    assert {path.name for path in written} == {"task_run.schema.json", "run_summary.schema.json"}
    assert task_schema == RemoteTaskSpec.model_json_schema()
    assert summary_schema == RemoteRunSummary.model_json_schema()
