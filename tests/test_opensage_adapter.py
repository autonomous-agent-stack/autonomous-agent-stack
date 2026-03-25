from __future__ import annotations

import asyncio
from pathlib import Path
import subprocess

import pytest

from orchestrator.node_protocol import NodeAdapter, NodeOutput, NodeRegistry, NodeStatus
from orchestrator.tool_synthesis import ToolSynthesisError, ToolSynthesisPolicy, ToolSynthesizer


class DummyAdapter(NodeAdapter):
    async def execute(self, input_data: dict[str, object]) -> NodeOutput:
        return NodeOutput(
            status=NodeStatus.SUCCESS,
            data={"echo": input_data},
            metadata={"source": "dummy"},
            error=None,
        )


def _make_synth(tmp_path: Path, backend: str = "local") -> ToolSynthesizer:
    return ToolSynthesizer(
        workspace=tmp_path / "opensage_workspace",
        policy=ToolSynthesisPolicy(max_tools=5, timeout_seconds=5, execution_backend=backend),
    )


def test_parse_error_detection(tmp_path: Path) -> None:
    synth = _make_synth(tmp_path, backend="local")

    with pytest.raises(ToolSynthesisError, match="tool output is not valid JSON"):
        synth._parse_json_output("not json\nstill not json")


def test_dynamic_script_generation(tmp_path: Path) -> None:
    synth = _make_synth(tmp_path, backend="local")
    code = "def run(payload):\n    return {'ok': True, 'x': payload.get('x', 0)}\n"

    record = synth.synthesize(
        tool_name="OpenSage Dynamic",
        source_code=code,
        entrypoint="run",
        sample_input={"x": 1},
    )
    result = synth.invoke("OpenSage Dynamic", {"x": 7})

    assert record.status == "active"
    assert Path(record.module_path).exists()
    assert result == {"ok": True, "x": 7}


def test_docker_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    synth = _make_synth(tmp_path, backend="docker")
    code = "def run(payload):\n    return {'docker': True}\n"

    commands: list[list[str]] = []

    def _fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        command = list(args[0])
        commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout='{"docker": true}\n', stderr="")

    monkeypatch.setattr("orchestrator.tool_synthesis.shutil.which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr("orchestrator.tool_synthesis.subprocess.run", _fake_run)

    record = synth.synthesize("docker_validator", code, sample_input={"warmup": True})
    result = synth.invoke("docker_validator", {"payload": 1})

    assert record.status == "active"
    assert result == {"docker": True}
    assert len(commands) >= 2
    assert all(cmd[0] == "docker" for cmd in commands)


def test_adapter_registration() -> None:
    NodeRegistry._registry.clear()
    adapter = DummyAdapter()

    NodeRegistry.register("opensage_adapter", adapter)
    fetched = NodeRegistry.get("opensage_adapter")
    output = asyncio.run(fetched.execute({"v": 42}))

    assert fetched is adapter
    assert "opensage_adapter" in NodeRegistry.list_registered()
    assert output.to_dict() == {
        "status": "success",
        "data": {"echo": {"v": 42}},
        "metadata": {"source": "dummy"},
        "error": None,
    }


def test_appledouble_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    synth = _make_synth(tmp_path, backend="docker")

    dirty_dir = synth.workspace / "nested"
    dirty_dir.mkdir(parents=True, exist_ok=True)
    appledouble_file = dirty_dir / "._temp.py"
    ds_store = dirty_dir / ".DS_Store"
    appledouble_file.write_text("x", encoding="utf-8")
    ds_store.write_text("x", encoding="utf-8")

    module_path = synth.workspace / "tools" / "clean_target.py"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text("def run(payload):\n    return {'ok': True}\n", encoding="utf-8")

    monkeypatch.setattr("orchestrator.tool_synthesis.shutil.which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(
        "orchestrator.tool_synthesis.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args=args[0], returncode=0, stdout='{"ok": true}\n', stderr=""),
    )

    synth._execute_in_docker(module_path, "run", "{}")

    assert not appledouble_file.exists()
    assert not ds_store.exists()
