from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from autoresearch.core.services.cluster_manager import (
    LoadBalanceStrategy,
    get_cluster_manager,
)


@dataclass
class DispatchOutcome:
    success: bool
    remote: bool
    payload: dict[str, Any]
    reason: str


class DistributedGateway:
    """Bridge wrapper for cluster-based task dispatch with safe fallback."""

    STRATEGY_MAP = {
        "least_load": LoadBalanceStrategy.LEAST_LOAD,
        "round_robin": LoadBalanceStrategy.ROUND_ROBIN,
        "random": LoadBalanceStrategy.RANDOM,
        "capability": LoadBalanceStrategy.CAPABILITY,
    }

    def __init__(self, backend: str | None = None) -> None:
        # cluster: existing in-repo smart scheduler
        # celery: broker-based LAN fan-out
        self.backend = (backend or os.getenv("BLITZ_DISPATCH_BACKEND", "cluster")).strip().lower()

    async def preview_node(
        self,
        *,
        required_capabilities: list[str] | None = None,
        strategy: str = "least_load",
    ) -> dict[str, Any]:
        if self.backend == "celery":
            return self._preview_celery_target()

        manager = get_cluster_manager()
        strategy_enum = self.STRATEGY_MAP.get(strategy, LoadBalanceStrategy.LEAST_LOAD)
        node = await manager.get_available_node(
            required_capabilities=required_capabilities or [],
            strategy=strategy_enum,
        )
        if node is None:
            return {"available": False, "reason": "no available node"}

        return {
            "available": True,
            "node_id": node.node_id,
            "name": node.name,
            "endpoint": node.endpoint,
            "load": node.load,
            "capabilities": node.capabilities,
            "strategy": strategy_enum.value,
        }

    async def dispatch_or_fallback(
        self,
        *,
        task_payload: dict[str, Any],
        required_capabilities: list[str] | None = None,
        strategy: str = "least_load",
    ) -> DispatchOutcome:
        if self.backend == "celery":
            return self._dispatch_via_celery(task_payload=task_payload)

        manager = get_cluster_manager()
        strategy_enum = self.STRATEGY_MAP.get(strategy, LoadBalanceStrategy.LEAST_LOAD)

        if not manager.nodes:
            return DispatchOutcome(
                success=False,
                remote=False,
                payload={},
                reason="cluster has no registered nodes",
            )

        try:
            result = await manager.dispatch_task_smart(
                task=task_payload,
                required_capabilities=required_capabilities or [],
                strategy=strategy_enum,
            )
            return DispatchOutcome(
                success=True,
                remote=True,
                payload=result,
                reason="dispatched to remote node",
            )
        except Exception as exc:
            return DispatchOutcome(
                success=False,
                remote=False,
                payload={},
                reason=f"dispatch failed: {exc}",
            )

    def _preview_celery_target(self) -> dict[str, Any]:
        broker_url = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
        queue_name = os.getenv("CELERY_QUEUE", "blitz")
        task_name = os.getenv("CELERY_TASK_NAME", "autonomous_agent_stack.execute_task")
        return {
            "available": True,
            "mode": "celery",
            "broker_url": broker_url,
            "queue": queue_name,
            "task_name": task_name,
        }

    def _dispatch_via_celery(self, *, task_payload: dict[str, Any]) -> DispatchOutcome:
        broker_url = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
        result_backend = os.getenv("CELERY_RESULT_BACKEND", broker_url)
        queue_name = os.getenv("CELERY_QUEUE", "blitz")
        task_name = os.getenv("CELERY_TASK_NAME", "autonomous_agent_stack.execute_task")

        try:
            from celery import Celery  # type: ignore
        except Exception as exc:
            return DispatchOutcome(
                success=False,
                remote=False,
                payload={},
                reason=f"celery backend unavailable: {exc}",
            )

        try:
            app = Celery("blitz_dispatch_gateway", broker=broker_url, backend=result_backend)
            async_result = app.send_task(task_name, kwargs={"task_payload": task_payload}, queue=queue_name)
            return DispatchOutcome(
                success=True,
                remote=True,
                payload={
                    "mode": "celery",
                    "task_id": async_result.id,
                    "queue": queue_name,
                    "task_name": task_name,
                    "broker_url": broker_url,
                },
                reason="dispatched to celery broker",
            )
        except Exception as exc:
            return DispatchOutcome(
                success=False,
                remote=False,
                payload={},
                reason=f"celery dispatch failed: {exc}",
            )
