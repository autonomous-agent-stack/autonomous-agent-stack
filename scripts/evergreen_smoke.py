#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any

from autoresearch.agent_protocol.capability_models import CapabilityRunRequest
from autoresearch.api.dependencies import (
    clear_dependency_caches,
    get_a2a_gateway_service,
    get_capability_manifest_service,
    get_runtime_adapter_registry_service,
)
from autoresearch.core.services.a2a_gateway import A2ATaskCreateRequest


def _print(payload: Any) -> None:
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def runtime_doctor() -> None:
    registry = get_runtime_adapter_registry_service()
    _print([item.model_dump(mode="json") for item in registry.doctor_all()])


def capability_doctor() -> None:
    service = get_capability_manifest_service()
    _print(service.doctor())


def run_capability(capability_id: str, task: str) -> None:
    service = get_capability_manifest_service()
    result = service.run_capability(
        capability_id,
        CapabilityRunRequest(
            task_name=capability_id,
            prompt=task,
            parameters={"prompt": task},
            metadata={"source": "evergreen_smoke"},
        ),
    )
    _print(result)


def a2a_demo() -> None:
    service = get_a2a_gateway_service()
    card = service.agent_card()
    task = service.submit_task(
        A2ATaskCreateRequest(
            capability_id="federation.a2a_bridge",
            task="Run a governed local A2A bridge demo.",
            metadata={"source": "evergreen_smoke"},
        )
    )
    _print({"agent_card": card.model_dump(mode="json"), "task": task.model_dump(mode="json")})


def evergreen_demo() -> None:
    runtime_doctor()
    capability_doctor()
    run_capability("research.agent_reach_crewai", "总结 https://github.com/Panniantong/Agent-Reach 的 AAS 接入边界")
    run_capability("knowledge.haystack_demo", "解释 AAS 为什么应把 Haystack 当知识 runtime")
    run_capability("workflow.langgraph_order", "演示报价审批流程 checkpoint")
    a2a_demo()


def main() -> int:
    parser = argparse.ArgumentParser(description="Evergreen AAS runtime/capability smoke commands.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("runtime-doctor")
    sub.add_parser("capability-doctor")
    sub.add_parser("agent-reach-crewai-demo")
    sub.add_parser("haystack-demo")
    sub.add_parser("langgraph-demo")
    sub.add_parser("a2a-demo")
    sub.add_parser("evergreen-demo")
    args = parser.parse_args()

    clear_dependency_caches()
    if args.command == "runtime-doctor":
        runtime_doctor()
    elif args.command == "capability-doctor":
        capability_doctor()
    elif args.command == "agent-reach-crewai-demo":
        run_capability("research.agent_reach_crewai", "总结 https://github.com/Panniantong/Agent-Reach 的 AAS 接入边界")
    elif args.command == "haystack-demo":
        run_capability("knowledge.haystack_demo", "解释 AAS 为什么应把 Haystack 当知识 runtime")
    elif args.command == "langgraph-demo":
        run_capability("workflow.langgraph_order", "演示报价审批流程 checkpoint")
    elif args.command == "a2a-demo":
        a2a_demo()
    elif args.command == "evergreen-demo":
        evergreen_demo()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
