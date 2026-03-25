from __future__ import annotations

import asyncio
from pathlib import Path
import subprocess

import pytest

from orchestrator.mcp_context import MCPContextBlock
from orchestrator.tool_synthesis import ToolSynthesisError


def test_dynamic_tool_synthesis_and_invocation(tmp_path: Path) -> None:
    context = MCPContextBlock()
    context.enable_dynamic_tool_synthesis(
        workspace=tmp_path / "generated_tools",
        max_tools=5,
        timeout_seconds=5,
        execution_backend="local",
    )

    tool_code = """
def run(payload):
    text = payload.get("text", "")
    return {
        "length": len(text),
        "upper": text.upper(),
    }
"""

    metadata = context.synthesize_tool(
        tool_name="text_stats",
        source_code=tool_code,
        sample_input={"text": "warmup"},
    )
    assert metadata["status"] == "active"

    result = asyncio.run(
        context.call_tool(
            "text_stats",
            {"text": "hello"},
            use_cache=False,
        )
    )
    assert result == {"length": 5, "upper": "HELLO"}


def test_dynamic_tool_synthesis_blocks_unsafe_code(tmp_path: Path) -> None:
    context = MCPContextBlock()
    context.enable_dynamic_tool_synthesis(
        workspace=tmp_path / "generated_tools",
        execution_backend="local",
    )

    dangerous_code = """
import os

def run(payload):
    os.system("rm -rf /")
    return {"ok": True}
"""

    with pytest.raises(ToolSynthesisError):
        context.synthesize_tool(
            tool_name="dangerous",
            source_code=dangerous_code,
            sample_input={},
        )


def test_dynamic_tool_synthesis_respects_tool_limit(tmp_path: Path) -> None:
    context = MCPContextBlock()
    context.enable_dynamic_tool_synthesis(
        workspace=tmp_path / "generated_tools",
        max_tools=1,
        execution_backend="local",
    )

    code = """
def run(payload):
    return {"ok": True}
"""

    context.synthesize_tool(
        tool_name="one_tool",
        source_code=code,
        sample_input={},
    )

    with pytest.raises(ToolSynthesisError):
        context.synthesize_tool(
            tool_name="second_tool",
            source_code=code,
            sample_input={},
        )


def test_dynamic_tool_synthesis_docker_backend_uses_docker_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = MCPContextBlock()
    context.enable_dynamic_tool_synthesis(
        workspace=tmp_path / "generated_tools",
        max_tools=1,
        timeout_seconds=5,
        execution_backend="docker",
        docker_image="python:3.12-alpine",
    )

    commands: list[list[str]] = []

    def _fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        command = list(args[0])
        commands.append(command)
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout='{"ok": true}\n',
            stderr="",
        )

    monkeypatch.setattr("orchestrator.tool_synthesis.shutil.which", lambda cmd: "/usr/bin/docker")
    monkeypatch.setattr("orchestrator.tool_synthesis.subprocess.run", _fake_run)

    metadata = context.synthesize_tool(
        tool_name="dockerized",
        source_code="def run(payload):\n    return {'ok': True}\n",
        sample_input={"warmup": True},
    )
    assert metadata["status"] == "active"

    result = asyncio.run(context.call_tool("dockerized", {"x": 1}, use_cache=False))
    assert result == {"ok": True}
    assert len(commands) >= 2
    assert all(cmd[0] == "docker" for cmd in commands)
