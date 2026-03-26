from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from bridge.distributed_gateway import DistributedGateway


class _DummyManager:
    def __init__(self) -> None:
        self.nodes = {}

    async def get_available_node(self, required_capabilities=None, strategy=None):
        return None


@pytest.mark.asyncio
async def test_cluster_preview_no_node(monkeypatch):
    monkeypatch.setenv("BLITZ_DISPATCH_BACKEND", "cluster")
    monkeypatch.setattr(
        "bridge.distributed_gateway.get_cluster_manager",
        lambda: _DummyManager(),
    )

    gateway = DistributedGateway()
    preview = await gateway.preview_node(required_capabilities=["gpu"], strategy="least_load")

    assert preview["available"] is False
    assert "no available node" in preview["reason"]


@pytest.mark.asyncio
async def test_celery_preview(monkeypatch):
    monkeypatch.setenv("BLITZ_DISPATCH_BACKEND", "celery")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://10.0.0.7:6379/0")
    monkeypatch.setenv("CELERY_QUEUE", "blitz")
    monkeypatch.setenv("CELERY_TASK_NAME", "autonomous_agent_stack.execute_task")

    gateway = DistributedGateway()
    preview = await gateway.preview_node()

    assert preview["available"] is True
    assert preview["mode"] == "celery"
    assert preview["broker_url"] == "redis://10.0.0.7:6379/0"


@pytest.mark.asyncio
async def test_celery_dispatch_success_with_fake_module(monkeypatch):
    monkeypatch.setenv("BLITZ_DISPATCH_BACKEND", "celery")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/1")
    monkeypatch.setenv("CELERY_QUEUE", "blitz")
    monkeypatch.setenv("CELERY_TASK_NAME", "autonomous_agent_stack.execute_task")

    class _FakeAsyncResult:
        id = "task-123"

    class _FakeCeleryApp:
        def send_task(self, task_name, kwargs=None, queue=None):
            assert task_name == "autonomous_agent_stack.execute_task"
            assert queue == "blitz"
            assert kwargs["task_payload"]["task_name"] == "demo"
            return _FakeAsyncResult()

    class _FakeCelery:
        def __init__(self, *args, **kwargs):
            pass

        def send_task(self, task_name, kwargs=None, queue=None):
            return _FakeCeleryApp().send_task(task_name, kwargs=kwargs, queue=queue)

    monkeypatch.setitem(sys.modules, "celery", SimpleNamespace(Celery=_FakeCelery))

    gateway = DistributedGateway()
    outcome = await gateway.dispatch_or_fallback(task_payload={"task_name": "demo"})

    assert outcome.success is True
    assert outcome.remote is True
    assert outcome.payload["task_id"] == "task-123"
