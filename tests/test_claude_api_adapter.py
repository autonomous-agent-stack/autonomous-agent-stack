from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from autoresearch.core.services.claude_api_adapter import ClaudeAPIAdapter


class TestClaudeAPIAdapter:
    @pytest.mark.asyncio
    async def test_normal_execution_uses_gateway_client(self) -> None:
        adapter = ClaudeAPIAdapter()
        adapter.client.generate = AsyncMock(return_value="Hello, World!")  # type: ignore[method-assign]

        result = await adapter.execute("test prompt")

        assert result == "Hello, World!"
        adapter.client.generate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_json_mode_success(self) -> None:
        adapter = ClaudeAPIAdapter()
        adapter.client.generate = AsyncMock(return_value='{"status": "success", "data": "test"}')  # type: ignore[method-assign]

        result = await adapter.execute("test prompt", require_json=True)

        parsed = json.loads(result)
        assert parsed["status"] == "success"

    @pytest.mark.asyncio
    async def test_json_mode_failure(self) -> None:
        adapter = ClaudeAPIAdapter()
        adapter.client.generate = AsyncMock(return_value="not json")  # type: ignore[method-assign]

        result = await adapter.execute("test prompt", require_json=True)

        parsed = json.loads(result)
        assert parsed["status"] == "error"
        assert "Failed to parse JSON output" in parsed["message"]


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_timeout_error(self) -> None:
        adapter = ClaudeAPIAdapter()
        adapter.client.generate = AsyncMock(side_effect=TimeoutError("timeout"))  # type: ignore[method-assign]

        result = await adapter.execute("test prompt")

        parsed = json.loads(result)
        assert parsed["status"] == "error"
        assert "timeout" in parsed["message"].lower()

    @pytest.mark.asyncio
    async def test_generic_error(self) -> None:
        adapter = ClaudeAPIAdapter()
        adapter.client.generate = AsyncMock(side_effect=Exception("Unknown error"))  # type: ignore[method-assign]

        result = await adapter.execute("test prompt")

        parsed = json.loads(result)
        assert parsed["status"] == "error"
        assert "Unknown error" in parsed["message"]


class TestConfiguration:
    def test_does_not_require_direct_environment_secret(self) -> None:
        adapter = ClaudeAPIAdapter()

        assert adapter.model == "claude-3-5-sonnet"
        assert adapter.client.timeout == 45.0


class TestPerformance:
    @pytest.mark.asyncio
    async def test_concurrent_requests(self) -> None:
        adapter = ClaudeAPIAdapter()
        adapter.client.generate = AsyncMock(return_value="Response")  # type: ignore[method-assign]

        results = await asyncio.gather(*(adapter.execute(f"test {index}") for index in range(10)))

        assert len(results) == 10
        assert all(item == "Response" for item in results)

    @pytest.mark.asyncio
    async def test_response_time(self) -> None:
        import time

        adapter = ClaudeAPIAdapter()
        adapter.client.generate = AsyncMock(return_value="Fast response")  # type: ignore[method-assign]

        start = time.time()
        result = await adapter.execute("test prompt")
        elapsed = time.time() - start

        assert elapsed < 1.0
        assert result == "Fast response"
