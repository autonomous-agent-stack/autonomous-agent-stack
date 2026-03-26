from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from masfactory import MASContext
from masfactory.nodes import GeneratorNode
import masfactory.nodes as mas_nodes


def _clear_llm_env(monkeypatch) -> None:
    for name in (
        "MAS_FACTORY_LLM_API_KEY",
        "GLM_API_KEY",
        "ZHIPUAI_API_KEY",
        "OPENAI_API_KEY",
        "MAS_FACTORY_LLM_BASE_URL",
        "GLM_BASE_URL",
        "OPENAI_BASE_URL",
        "MAS_FACTORY_LLM_MODEL",
        "MAS_FACTORY_LLM_TIMEOUT",
    ):
        monkeypatch.delenv(name, raising=False)


class _DummyResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = mas_nodes.httpx.Request("POST", "https://unit.test/chat/completions")
            response = mas_nodes.httpx.Response(self.status_code, request=request)
            raise mas_nodes.httpx.HTTPStatusError("http error", request=request, response=response)

    def json(self) -> dict[str, Any]:
        return self._payload


def _mock_async_client(monkeypatch, *, payload: dict[str, Any], error: Exception | None = None, capture: dict[str, Any] | None = None) -> None:
    class _DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            self.timeout = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url: str, headers: dict[str, Any] | None = None, json: dict[str, Any] | None = None):
            if capture is not None:
                capture["url"] = url
                capture["headers"] = headers
                capture["json"] = json
            if error is not None:
                raise error
            return _DummyResponse(payload=payload)

    monkeypatch.setattr(mas_nodes.httpx, "AsyncClient", _DummyAsyncClient)


def test_generator_calls_llm_and_sets_generated_code(tmp_path: Path, monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GLM_API_KEY", "glm-key")
    capture: dict[str, Any] = {}
    _mock_async_client(
        monkeypatch,
        payload={
            "choices": [
                {
                    "message": {
                        "content": "```python\ndef solve_task():\n    return {'ok': True}\n```"
                    }
                }
            ]
        },
        capture=capture,
    )

    context = MASContext(workspace=tmp_path, goal="collect runtime stats")
    context.set("plan", {"goal": "collect runtime stats"})
    result = asyncio.run(GeneratorNode().execute(context))

    assert result["generation_mode"] == "llm_api"
    assert result["model"] == "glm-5"
    assert context.get("generation_mode") == "llm_api"
    assert "def solve_task" in context.get("generated_code", "")
    assert capture["url"] == "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    assert capture["json"]["model"] == "glm-5"


def test_generator_parses_markdown_python_block(tmp_path: Path, monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GLM_API_KEY", "glm-key")
    _mock_async_client(
        monkeypatch,
        payload={
            "choices": [
                {
                    "message": {
                        "content": (
                            "I prepared your script.\n"
                            "```python\n"
                            "# parsed\n"
                            "def solve_task():\n"
                            "    return {'ok': 'parsed'}\n"
                            "```\n"
                            "Done."
                        )
                    }
                }
            ]
        },
    )

    context = MASContext(workspace=tmp_path, goal="parse fenced code")
    context.set("plan", {"goal": "parse fenced code"})
    result = asyncio.run(GeneratorNode().execute(context))

    assert result["generation_mode"] == "llm_api"
    assert result["code"].startswith("# parsed")
    assert "I prepared your script." not in result["code"]


def test_generator_fallback_when_no_api_key(tmp_path: Path, monkeypatch):
    _clear_llm_env(monkeypatch)
    context = MASContext(workspace=tmp_path, goal="fallback with no key")
    context.set("plan", {"goal": "fallback with no key"})

    result = asyncio.run(GeneratorNode().execute(context))

    assert result["generation_mode"] == "fallback_mock"
    assert "No LLM API credentials available" in result["generation_error"]
    assert "def solve_task" in result["code"]
    assert context.get("generated_code", "").startswith("GOAL = ")


def test_generator_fallback_on_network_failure(tmp_path: Path, monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GLM_API_KEY", "glm-key")
    request = mas_nodes.httpx.Request("POST", "https://unit.test/chat/completions")
    _mock_async_client(
        monkeypatch,
        payload={"choices": []},
        error=mas_nodes.httpx.RequestError("network failed", request=request),
    )

    context = MASContext(workspace=tmp_path, goal="network failure")
    context.set("plan", {"goal": "network failure"})
    result = asyncio.run(GeneratorNode().execute(context))

    assert result["generation_mode"] == "fallback_mock"
    assert "LLM generation failed" in result["generation_error"]
    assert "def solve_task" in result["code"]


def test_generator_fallback_on_invalid_llm_output(tmp_path: Path, monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GLM_API_KEY", "glm-key")
    _mock_async_client(
        monkeypatch,
        payload={
            "choices": [
                {
                    "message": {
                        "content": "```python\nprint('missing solve_task')\n```"
                    }
                }
            ]
        },
    )

    context = MASContext(workspace=tmp_path, goal="invalid llm output")
    context.set("plan", {"goal": "invalid llm output"})
    result = asyncio.run(GeneratorNode().execute(context))

    assert result["generation_mode"] == "fallback_mock"
    assert "did not define solve_task" in result["generation_error"]
    assert "def solve_task" in result["code"]


def test_generator_uses_preseeded_memory_hits(tmp_path: Path, monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GLM_API_KEY", "glm-key")
    capture: dict[str, Any] = {}
    _mock_async_client(
        monkeypatch,
        payload={"choices": [{"message": {"content": "def solve_task():\n    return {'ok': True}\n"}}]},
        capture=capture,
    )

    context = MASContext(workspace=tmp_path, goal="use seeded memory")
    context.set("plan", {"goal": "use seeded memory"})
    seeded_hits = [{"path": "/tmp/memory-note.md", "match_preview": "important memory"}]
    context.set("memory_hits", seeded_hits)

    def fail_search(*args, **kwargs):
        raise AssertionError("search_memory should not be called when memory_hits is preseeded")

    monkeypatch.setattr(context, "search_memory", fail_search)

    result = asyncio.run(GeneratorNode().execute(context))

    assert result["generation_mode"] == "llm_api"
    assert result["memory_hits"] == seeded_hits
    assert context.get("memory_hits") == seeded_hits
    assert "/tmp/memory-note.md" in capture["json"]["messages"][1]["content"]
