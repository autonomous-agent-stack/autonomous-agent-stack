#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any

from autoresearch.api.dependencies import (
    get_federation_service,
    get_governed_mcp_service,
    get_usage_quota_service,
)
from autoresearch.core.services.federation import (
    FederationLeaseCreateRequest,
    FederationTaskCreateRequest,
)


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _quota_doctor() -> int:
    service = get_usage_quota_service()
    _print(
        {
            "doctor": service.doctor(),
            "local_user_quota": service.quota_for(subject_id="local-user", actor_role="member").model_dump(
                mode="json"
            ),
            "demo_peer_quota": service.quota_for(
                subject_id="demo-peer",
                subject_type="peer",
                actor_role="peer",
            ).model_dump(mode="json"),
        }
    )
    return 0


def _mcp_doctor() -> int:
    service = get_governed_mcp_service()
    _print(service.doctor())
    return 0


def _federation_doctor() -> int:
    service = get_federation_service()
    _print(service.doctor())
    return 0


def _federation_demo(peer_id: str, capability_id: str) -> int:
    service = get_federation_service()
    lease = service.create_lease(
        FederationLeaseCreateRequest(
            peer_id=peer_id,
            capability_id=capability_id,
            duration_seconds=900,
            max_tasks=2,
            quota_units=5,
            requested_by="federation-demo",
            metadata={"demo": True},
        )
    )
    task = service.submit_task(
        FederationTaskCreateRequest(
            peer_id=peer_id,
            lease_id=lease.lease_id,
            capability_id=capability_id,
            task_name="Federation demo task",
            intent="Run a local governed federation demo task",
            parameters={"message": "hello federation"},
            quota_units=1,
            metadata={"demo": True},
        )
    )
    revoked = service.revoke_lease(
        lease.lease_id,
        requested_by="federation-demo",
        reason="demo revoke",
    )
    revoke_rejection = "not checked"
    try:
        service.submit_task(
            FederationTaskCreateRequest(
                peer_id=peer_id,
                lease_id=lease.lease_id,
                capability_id=capability_id,
                task_name="Federation demo task after revoke",
                intent="This request should be rejected after revoke.",
                quota_units=1,
                metadata={"demo": True, "after_revoke": True},
            )
        )
    except PermissionError as exc:
        revoke_rejection = str(exc)

    _print(
        {
            "lease": lease.model_dump(mode="json"),
            "task": task.model_dump(mode="json"),
            "revoked_lease": revoked.model_dump(mode="json"),
            "post_revoke_rejection": revoke_rejection,
        }
    )
    return 0 if revoke_rejection != "not checked" else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Federation-ready AAS v1 smoke helpers")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("quota-doctor")
    sub.add_parser("mcp-doctor")
    sub.add_parser("federation-doctor")
    federation_demo = sub.add_parser("federation-demo")
    federation_demo.add_argument("--peer-id", default="demo-peer")
    federation_demo.add_argument("--capability-id", default="echo")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "quota-doctor":
        return _quota_doctor()
    if args.command == "mcp-doctor":
        return _mcp_doctor()
    if args.command == "federation-doctor":
        return _federation_doctor()
    if args.command == "federation-demo":
        return _federation_demo(args.peer_id, args.capability_id)
    raise ValueError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
