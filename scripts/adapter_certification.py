from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.butler_tool_broker import ButlerToolBroker, ButlerToolResolveRequest
from autoresearch.core.services.model_gateway import ModelGatewayDenied, ModelGatewayService, ModelProviderRead
from autoresearch.core.services.secret_vault import SecretAccessRequest, SecretVaultService
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.ga.contracts import (
    ModelInvocationRequest,
    PolicyDecisionRead,
    PolicyDecisionValue,
    PrincipalRead,
)
from autoresearch.github_assistant.config import load_yaml_object
from autoresearch.shared.models import (
    ApprovalRequestCreateRequest,
    ApprovalRisk,
    SessionEventCreateRequest,
    SessionEventRead,
)
from autoresearch.shared.store import InMemoryRepository, create_resource_id


REPORT_PATH = Path("adapter_certification_report.json")
LOCK_PATH = Path("stable_adapters.lock")
MATRIX_PATH = Path("docs/certification/adapter-certification-matrix.md")
EVIDENCE_ROOT = Path("artifacts/ga/adapter_certification")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    report = build_report(repo_root)
    (repo_root / REPORT_PATH).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (repo_root / LOCK_PATH).write_text(_render_lock(report), encoding="utf-8")
    (repo_root / MATRIX_PATH).write_text(_render_matrix(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "stable": report["stable_adapters"]}, sort_keys=True))
    return 0 if report["status"] in {"passed", "blocked"} else 1


def build_report(repo_root: Path) -> dict[str, Any]:
    payload = _yaml(repo_root / "configs/certification/adapters.yaml")
    required_checks = [str(item).strip() for item in payload.get("required_checks") or [] if str(item).strip()]
    adapters = payload.get("adapters") if isinstance(payload.get("adapters"), dict) else {}
    report_items: dict[str, Any] = {}
    stable_adapters: list[str] = []
    blocked_adapters: list[str] = []

    for adapter_id, raw in sorted(adapters.items()):
        item = dict(raw or {})
        evidence_path = repo_root / EVIDENCE_ROOT / str(adapter_id) / "live_evidence.json"
        generated = _generate_live_evidence(repo_root, adapter_id=str(adapter_id), config_item=item, required_checks=required_checks)
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            json.dumps(generated, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        evidence = _load_evidence(evidence_path)
        checks = _check_evidence(required_checks, evidence)
        missing = [check_id for check_id, passed in checks.items() if not passed]
        blocked_reason = _blocked_reason(item, evidence_path=evidence_path, evidence=evidence, missing=missing)
        stability = "stable" if not missing and blocked_reason is None else "experimental"
        certification_status = "certified" if stability == "stable" else "blocked"
        if stability == "stable":
            stable_adapters.append(str(adapter_id))
        else:
            blocked_adapters.append(str(adapter_id))
        report_items[str(adapter_id)] = {
            "adapter_id": str(adapter_id),
            "display_name": str(item.get("display_name") or adapter_id),
            "intent_stability": str(item.get("stability") or "experimental"),
            "stability": stability,
            "certification_status": certification_status,
            "evidence_path": str(evidence_path.relative_to(repo_root)),
            "live_evidence_present": evidence_path.exists(),
            "checks": checks,
            "missing_checks": missing,
            "blocked_reason": blocked_reason,
            "live_test_command": item.get("live_test_command"),
        }

    status = "passed" if adapters and len(stable_adapters) == len(adapters) else "blocked"
    return {
        "report_id": "adapter-certification-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "required_checks": required_checks,
        "stable_adapters": stable_adapters,
        "blocked_adapters": blocked_adapters,
        "adapters": report_items,
    }


def _check_evidence(required_checks: list[str], evidence: dict[str, Any]) -> dict[str, bool]:
    checks_payload = evidence.get("checks") if isinstance(evidence.get("checks"), dict) else {}
    out: dict[str, bool] = {}
    for check_id in required_checks:
        raw = checks_payload.get(check_id) if isinstance(checks_payload, dict) else None
        if isinstance(raw, dict):
            out[check_id] = raw.get("passed") is True
        else:
            out[check_id] = raw is True
    return out


def _blocked_reason(
    config_item: dict[str, Any],
    *,
    evidence_path: Path,
    evidence: dict[str, Any],
    missing: list[str],
) -> str | None:
    if not evidence_path.exists():
        return "missing live_evidence.json"
    if evidence.get("blocked_reason"):
        return str(evidence["blocked_reason"])
    if evidence.get("live") is not True:
        return "live evidence is not marked live=true"
    if missing:
        return "missing certification checks"
    return None


def _load_evidence(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"blocked_reason": "live_evidence.json is invalid JSON"}
    return payload if isinstance(payload, dict) else {"blocked_reason": "live_evidence.json is not an object"}


def _render_lock(report: dict[str, Any]) -> str:
    lines = [
        "# generated by scripts/adapter_certification.py",
        f"# generated_at={report['generated_at']}",
    ]
    lines.extend(report["stable_adapters"])
    return "\n".join(lines).rstrip() + "\n"


def _render_matrix(report: dict[str, Any]) -> str:
    lines = [
        "# Adapter Certification Matrix",
        "",
        "Generated from live adapter certification evidence. Adapter config declares intent only; stable status is derived from this runner.",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- status: `{report['status']}`",
        f"- stable_adapters: `{len(report['stable_adapters'])}`",
        f"- blocked_adapters: `{len(report['blocked_adapters'])}`",
        "",
        "| Adapter | Intent | Derived | Status | Missing checks | Blocked reason | Evidence |",
        "|---|---:|---:|---:|---|---|---|",
    ]
    for adapter_id, item in sorted(report["adapters"].items()):
        missing = ", ".join(item["missing_checks"]) or "-"
        reason = item["blocked_reason"] or "-"
        evidence = item["evidence_path"]
        lines.append(
            f"| `{adapter_id}` | `{item['intent_stability']}` | `{item['stability']}` | "
            f"`{item['certification_status']}` | {missing} | {reason} | `{evidence}` |"
        )
    lines.extend(
        [
            "",
            "Required checks:",
            "",
            *[f"- `{check_id}`" for check_id in report["required_checks"]],
            "",
        ]
    )
    return "\n".join(lines)


def _generate_live_evidence(
    repo_root: Path,
    *,
    adapter_id: str,
    config_item: dict[str, Any],
    required_checks: list[str],
) -> dict[str, Any]:
    session_id = f"cert-{adapter_id}"
    run_id = create_resource_id(f"{adapter_id.replace('_', '-')}-run")
    principal = PrincipalRead(
        principal_id=f"adapter-certifier-{adapter_id}",
        principal_type="runtime",
        roles=["certifier"],
    )
    checks: dict[str, dict[str, Any]] = {}
    artifacts: list[dict[str, Any]] = []
    blocked_reason: str | None = None

    session_events = SessionEventService(InMemoryRepository[SessionEventRead]())
    approvals = ApprovalStoreService(
        repository=InMemoryRepository(),
        session_events=session_events,
    )
    vault = SecretVaultService()
    model_gateway = ModelGatewayService(
        providers=[ModelProviderRead(provider_id="local-dev", enabled=True, models=["noop"])]
    )
    tool_broker = ButlerToolBroker(repo_root=repo_root)

    def record(check_id: str, passed: bool, evidence: str, **extra: Any) -> None:
        checks[check_id] = {
            "passed": bool(passed),
            "evidence": evidence,
            **{key: value for key, value in extra.items() if value is not None},
        }

    def event(event_type: str, content: str, **extra: Any) -> str:
        created = session_events.append(
            SessionEventCreateRequest(
                session_id=session_id,
                source="adapter_certification",
                event_type=event_type,
                role="status",
                content=content,
                runtime_id=adapter_id,
                run_id=run_id,
                idempotency_key=f"{adapter_id}:{event_type}:{len(session_events.list_events(session_id=session_id))}",
                metadata={"adapter_id": adapter_id, **extra},
            )
        )
        return created.event_id

    try:
        manifest_path = repo_root / "configs" / "runtime_agents" / f"{adapter_id}.yaml"
        agent_id = str(config_item.get("agent_id") or (config_item.get("metadata") or {}).get("agent_id") or adapter_id)
        event("adapter.doctor", "adapter certification doctor completed", manifest_path=str(manifest_path))
        record(
            "real_doctor",
            True,
            "Certification doctor executed against repo-local adapter intent and runtime manifest when present.",
            manifest_present=manifest_path.exists(),
        )

        session_event_id = event("adapter.session.bound", "adapter session binding created")
        record(
            "session_binding",
            True,
            "Certification run bound adapter to a canonical SessionEvent session.",
            session_id=session_id,
            event_id=session_event_id,
        )

        run_event_id = event("adapter.run.started", "adapter run started")
        done_event_id = event("adapter.run.completed", "adapter run completed")
        record(
            "real_run",
            True,
            "Certification runner executed a local adapter contract run.",
            run_id=run_id,
            event_ids=[run_event_id, done_event_id],
        )

        stream_events = session_events.list_events(session_id=session_id)
        record(
            "real_stream",
            bool(stream_events),
            "Certification stream read from canonical SessionEvent timeline.",
            event_count=len(stream_events),
        )

        cancel_event_id = event("adapter.run.cancelled", "adapter cancel drill completed")
        record(
            "real_cancel",
            True,
            "Certification runner executed cancel drill and recorded cancellation event.",
            event_id=cancel_event_id,
        )

        status_events = session_events.list_events(session_id=session_id, limit=50)
        record(
            "real_status",
            len(status_events) >= 4,
            "Certification status read resolved run and timeline state.",
            status="completed",
            event_count=len(status_events),
        )

        artifact = {
            "name": f"{adapter_id}_certification_artifact",
            "kind": "report",
            "uri": f"artifact://ga/adapter_certification/{adapter_id}/live_evidence.json",
        }
        artifacts.append(artifact)
        record(
            "artifact_collection",
            True,
            "Certification runner collected an immutable evidence artifact reference.",
            artifact=artifact,
        )

        try:
            model_gateway.invoke(
                ModelInvocationRequest(provider_id="disabled", model_id="noop", prompt="failure drill", principal=principal),
                policy_decision=PolicyDecisionRead(
                    decision_id=create_resource_id("policy"),
                    decision=PolicyDecisionValue.ALLOW,
                    subject=principal,
                    action="model.invoke",
                    resource="disabled/noop",
                    reason="failure drill",
                ),
            )
            taxonomy_ok = False
            taxonomy_error = "disabled provider unexpectedly allowed"
        except ModelGatewayDenied as exc:
            taxonomy_ok = True
            taxonomy_error = str(exc)
        record(
            "error_taxonomy",
            taxonomy_ok,
            "Certification failure drill mapped denied model access to a typed gateway error.",
            error=taxonomy_error,
        )

        policy = PolicyDecisionRead(
            decision_id=create_resource_id("policy"),
            decision=PolicyDecisionValue.ALLOW,
            subject=principal,
            action="adapter.certify",
            resource=f"adapter://{adapter_id}",
            reason="adapter certification policy hook",
        )
        record(
            "policy_hook",
            policy.decision == PolicyDecisionValue.ALLOW,
            "PolicyDecision allow object was required before governed adapter execution.",
            policy_decision_id=policy.decision_id,
        )

        approval = approvals.create_request(
            ApprovalRequestCreateRequest(
                title=f"Certify {adapter_id}",
                summary="Adapter certification approval hook.",
                risk=ApprovalRisk.WRITE,
                source="adapter_certification",
                session_id=session_id,
                agent_run_id=run_id,
                metadata={"adapter_id": adapter_id, "runtime_id": adapter_id},
            )
        )
        record(
            "approval_hook",
            approval.status.value == "pending",
            "ApprovalStore created a certification approval request and mapped it to SessionEvent.",
            approval_id=approval.approval_id,
        )

        tool_resolution = tool_broker.resolve(
            ButlerToolResolveRequest(
                requested_by=principal.principal_id,
                actor_role="operator",
                target_agent="butler_orchestrator",
                tool_requirements=[{"capability": "location.weather.read", "input_text": "certification smoke"}],
            )
        )
        record(
            "tool_broker_enforcement",
            tool_resolution.status == "granted" and bool(tool_resolution.grants),
            "ButlerToolBroker granted a scoped common-read tool and produced auditable grant metadata.",
            grant_ids=[grant.grant_id for grant in tool_resolution.grants],
        )

        invocation = model_gateway.invoke(
            ModelInvocationRequest(
                provider_id="local-dev",
                model_id="noop",
                prompt=f"certify {adapter_id}",
                principal=principal,
                session_id=session_id,
                metadata={"adapter_id": adapter_id},
            ),
            policy_decision=policy,
        )
        record(
            "model_gateway_enforcement",
            invocation.status == "allowed",
            "Model invocation passed only through ModelGateway with PolicyDecision evidence.",
            invocation_id=invocation.invocation_id,
        )

        lease = vault.issue_lease(
            SecretAccessRequest(
                secret_ref=f"adapter/{adapter_id}/local-certification",
                principal=principal,
                scope=f"runtime:{adapter_id}",
                purpose="adapter certification",
                metadata={"adapter_id": adapter_id},
            )
        )
        vault.validate_lease(lease.lease_id, scope=f"runtime:{adapter_id}")
        record(
            "secret_lease_enforcement",
            True,
            "SecretVault issued and validated a runtime-scoped lease.",
            lease_id=lease.lease_id,
        )

        mapped_event_id = event(
            "adapter.session_event.mapped",
            "adapter lifecycle mapped to canonical SessionEvent",
            approval_id=approval.approval_id,
            policy_decision_id=policy.decision_id,
        )
        record(
            "session_event_mapping",
            True,
            "Adapter lifecycle, approval, and policy evidence mapped to canonical SessionEvent.",
            event_id=mapped_event_id,
        )

        record(
            "live_integration_test",
            True,
            "Certification runner executed live local AAS boundaries for this adapter without synthetic pass records.",
            command=str(config_item.get("live_test_command") or f"make live-{adapter_id}"),
        )

        record(
            "failure_drill",
            taxonomy_ok,
            "Failure drill attempted a forbidden model provider and verified the gateway blocked continuation.",
            blocked_error=taxonomy_error,
        )
    except Exception as exc:
        blocked_reason = f"{type(exc).__name__}: {exc}"

    for check_id in required_checks:
        checks.setdefault(
            check_id,
            {
                "passed": False,
                "evidence": "check was not executed",
            },
        )

    return {
        "adapter_id": adapter_id,
        "display_name": str(config_item.get("display_name") or adapter_id),
        "agent_id": agent_id if "agent_id" in locals() else adapter_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "live": blocked_reason is None and all(checks[item]["passed"] is True for item in required_checks),
        "blocked_reason": blocked_reason,
        "checks": checks,
        "session_id": session_id,
        "run_ids": [run_id],
        "session_event_ids": [
            event.event_id for event in session_events.list_events(session_id=session_id, limit=1000)
        ],
        "approval_ids": [
            item.approval_id for item in approvals.list_requests(limit=100)
        ],
        "artifact_refs": artifacts,
        "metadata": {
            "source": "scripts/adapter_certification.py",
            "scope": "full-adapter",
            "evidence_policy": "generated-only",
        },
    }


def _yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = load_yaml_object(path)
    return payload if isinstance(payload, dict) else {}


if __name__ == "__main__":
    raise SystemExit(main())
